"""Guarded Power BI deployment adapter backed only by Microsoft fabric-cicd."""
from __future__ import annotations

import argparse
import fnmatch
import importlib.metadata
import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from powerbi_cicd import TARGETS, check_artifact, load_object, redact, validate_config, validate_manifest, validate_source

SUPPORTED = {
    "SemanticModel": "fabric_cicd.deploy_with_config",
    "Report": "fabric_cicd.deploy_with_config",
    "PaginatedReport": "fabric_cicd.deploy_with_config",
}
POWER_BI_API = "https://api.powerbi.com/v1.0/myorg"


def resolve_hotfix_release(completed_prs: list[dict[str, Any]], merged_revision: str, second_parent: str | None, builds: list[dict[str, Any]]) -> dict[str, str]:
    """Resolve only a completed hotfix PR build with successful validation."""
    source_revision = next((str(pr.get("source_revision")) for pr in completed_prs if pr.get("merge_revision") == merged_revision and str(pr.get("source_branch", "")).startswith("hotfix/")), second_parent)
    if not source_revision:
        raise ValueError("no completed hotfix PR or merge second-parent is available")
    matches = [build for build in builds if build.get("source_revision") == source_revision and str(build.get("source_branch", "")).startswith("hotfix/") and build.get("status") == "succeeded" and build.get("validate_hotfix") == "succeeded"]
    if len(matches) != 1:
        raise ValueError("no uniquely successful HOTFIX-validated build exists for the hotfix revision")
    return {"source_revision": source_revision, "build_id": str(matches[0].get("id"))}


def release_files_match(repo: Path, selected_revision: str, deployment_revision: str, release_paths: list[str]) -> bool:
    """Return whether protected release inputs are identical at both revisions.

    Promotion stages invoke this after resolving their immutable source
    revision.  A failed lookup is fail-closed, exactly like a changed file.
    """
    if not selected_revision or not deployment_revision or not release_paths:
        return False
    result = subprocess.run(
        ["git", "-C", str(repo), "diff", "--quiet", selected_revision, deployment_revision, "--", *release_paths],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def artifact_contract(artifact: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    with zipfile.ZipFile(artifact) as archive:
        config = json.loads(archive.read("config.json"))
        manifest = json.loads(archive.read("manifest.json"))
    if not isinstance(config, dict) or not isinstance(manifest, dict):
        raise ValueError("artifact contains an invalid configuration or manifest")
    return config, manifest


def deployment_groups(manifest: dict[str, Any]) -> list[list[str]]:
    """Return supported item types in the only permitted write order."""
    present = {item["type"] for item in manifest["items"]}
    return [[item_type] for item_type in ("SemanticModel", "Report", "PaginatedReport") if item_type in present]


def binding_environment(target: str) -> str:
    """HOTFIX validates the PROD mapping; other targets bind to themselves."""
    return "PROD" if target == "HOTFIX" else target


def expected_semantic_model_connections(manifest: dict[str, Any], target: str) -> dict[str, list[str]]:
    environment = binding_environment(target)
    result: dict[str, list[str]] = {}
    for item in manifest["items"]:
        if item["type"] != "SemanticModel":
            continue
        selected = manifest["semantic_model_bindings"].get(item["id"], {}).get(environment)
        if not isinstance(selected, list) or not selected:
            raise ValueError(f"semantic model {item['id']} has no approved {environment} connection binding")
        result[item["id"]] = sorted(str(connection_id).lower() for connection_id in selected)
    return result


def validate_connection_preflight(manifest: dict[str, Any], target: str, live_inventory: dict[str, Any]) -> dict[str, Any]:
    """Validate a supplied authenticated, read-only connection inventory.

    The caller owns acquiring this inventory.  A connection must be directly
    usable by the deployment identity; connection-sharing elevation and
    personal-cloud connections are intentionally rejected.
    """
    expected = expected_semantic_model_connections(manifest, target)
    observed = {item.get("id"): item for item in live_inventory.get("items", []) if isinstance(item, dict)}
    issues: list[str] = []
    for model_id, connection_ids in expected.items():
        model = observed.get(model_id)
        if model is None:  # New model: publication will establish the binding.
            continue
        connections = model.get("connections")
        if not isinstance(connections, list):
            issues.append(f"{model_id} has no readable connection inventory")
            continue
        actual = {str(connection.get("id", "")).lower(): connection for connection in connections if isinstance(connection, dict)}
        if set(actual) != set(connection_ids):
            issues.append(f"{model_id} has missing or unexpected approved connections")
        for connection_id in connection_ids:
            connection = actual.get(connection_id)
            if connection is None:
                continue
            if connection.get("direct_identity_access") is not True:
                issues.append(f"{model_id} connection {connection_id} lacks direct deployment-identity access")
            if connection.get("personal_cloud") is True or connection.get("sharing_role") == "UserWithReshare":
                issues.append(f"{model_id} connection {connection_id} uses prohibited personal-cloud or reshared access")
    return {"status": "ready" if not issues else "blocked", "connection_bindings": expected, "issues": sorted(issues), "workspace_write": False}


def substitution_rules(manifest: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [(item["id"], rule) for item in manifest["items"] for rule in item.get("substitutions", {}).get("rules", [])]


def validate_substitution_coverage(artifact: Path, manifest: dict[str, Any], target: str) -> dict[str, Any]:
    """Ensure every target rule resolves and matches packaged payload before writes."""
    environment = binding_environment(target)
    resolved: list[dict[str, str]] = []
    issues: list[str] = []
    with zipfile.ZipFile(artifact) as archive:
        names = archive.namelist()
        for item_id, rule in substitution_rules(manifest):
            value = rule["values"].get(environment)
            if not isinstance(value, str) or not value:
                issues.append(f"{item_id} substitution has no {environment} value")
                continue
            pattern = "payload/" + manifest["source_root"].strip("/") + "/" + rule["path"].replace("\\", "/")
            matches = [name for name in names if fnmatch.fnmatchcase(name, pattern)]
            if not matches:
                issues.append(f"{item_id} substitution matches no packaged file")
                continue
            matched = 0
            for name in matches:
                matched += archive.read(name).decode("utf-8", errors="ignore").count(rule["find"])
            if not matched:
                issues.append(f"{item_id} substitution find value matches no packaged file content")
                continue
            resolved.append({"item": item_id, "path": rule["path"], "target": environment, "value": value})
    return {"status": "ready" if not issues else "blocked", "resolved": resolved, "issues": sorted(issues), "workspace_write": False}


def apply_substitutions(release_root: Path, manifest: dict[str, Any], target: str) -> list[dict[str, str]]:
    """Apply only already-validated rules to the extracted staging copy.

    This deliberately never edits the immutable archive or its hash manifest.
    """
    environment = binding_environment(target)
    resolved: list[dict[str, str]] = []
    for item_id, rule in substitution_rules(manifest):
        value = rule["values"][environment]
        pattern = rule["path"].replace("\\", "/")
        for path in (release_root / "payload" / manifest["source_root"]).rglob("*"):
            if path.is_file() and fnmatch.fnmatchcase(path.relative_to(release_root / "payload" / manifest["source_root"]).as_posix(), pattern):
                path.write_text(path.read_text(encoding="utf-8").replace(rule["find"], value), encoding="utf-8")
        resolved.append({"item": item_id, "path": rule["path"], "target": environment, "value": value})
    return resolved


def preflight(root: Path, config: dict[str, Any], manifest: dict[str, Any], target: str, artifact: Path | None = None, expected_digest: str | None = None, test_digest: str | None = None, live_inventory: dict[str, Any] | None = None, deployment_revision: str | None = None) -> dict[str, Any]:
    source_validation_required = artifact is None
    if artifact is not None:
        artifact_config, artifact_manifest = artifact_contract(artifact)
        if artifact_config != config or artifact_manifest != manifest:
            return {"status": "blocked", "reason": "artifact configuration or manifest differs from the approved target mapping", "workspace_write": False}
    if target not in config.get("targets", {}) or target not in TARGETS:
        return {"status": "blocked", "reason": "target is not explicitly configured", "workspace_write": False}
    errors = validate_config(config) + validate_manifest(manifest, config.get("repository", {}).get("powerbi_source_folder"))
    if errors:
        return {"status": "blocked", "reason": "manifest is invalid", "errors": errors, "workspace_write": False}
    unsupported = sorted({item["type"] for item in manifest["items"]} - set(SUPPORTED))
    if unsupported:
        return {"status": "blocked", "reason": "unsupported item classification", "item_types": unsupported, "workspace_write": False}
    identity = config.get("protected_resources", {}).get(target, {}).get("identity_reference")
    if not isinstance(identity, str) or not identity.strip():
        return {"status": "blocked", "reason": "protected identity reference is unavailable", "workspace_write": False}
    if source_validation_required:
        source = validate_source(root, config, manifest)
        if source["status"] != "valid":
            return {"status": "blocked", "reason": "source preflight failed", "errors": source["errors"], "workspace_write": False}
    integrity: dict[str, Any] = {"status": "not-applicable"}
    if artifact is not None:
        integrity = check_artifact(artifact, target, None, expected_digest, test_digest)
        if integrity["status"] != "verified":
            return {"status": "blocked", "reason": "artifact preflight failed", "integrity": integrity, "workspace_write": False}
        if deployment_revision and not release_files_match(
            root, str(integrity["source_revision"]), deployment_revision,
            [manifest["source_root"], config["repository"].get("ci_folder", "cicd")],
        ):
            return {"status": "blocked", "reason": "selected release files drift from the deployment revision", "workspace_write": False}
        substitutions = validate_substitution_coverage(artifact, manifest, target)
        if substitutions["status"] != "ready":
            return {"status": "blocked", "reason": "substitution preflight failed", "substitutions": substitutions, "workspace_write": False}
    else:
        substitutions = {"status": "not-applicable", "resolved": []}
    if live_inventory is not None:
        connection_check = validate_connection_preflight(manifest, target, live_inventory)
        if connection_check["status"] != "ready":
            return {"status": "blocked", "reason": "semantic-model connection preflight failed", "connection_check": connection_check, "workspace_write": False}
    else:
        connection_check = {"status": "unverified", "reason": "authenticated read-only connection inventory is required before publication"}
    return {"status": "ready", "adapter": "fabric-cicd", "adapter_operation": sorted({SUPPORTED[item["type"]] for item in manifest["items"]}), "target": target, "identity_reference": identity, "integrity": integrity, "connection_check": connection_check, "substitutions": substitutions, "workspace_write": False, "live_target": "unverified until authenticated read-only preflight"}


def native_config(config: dict[str, Any], manifest: dict[str, Any], target: str, repository_directory: Path, item_types: list[str] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    target_config = config["targets"][target]
    native = {
        "core": {
            "workspace": {target: target_config["workspace_name"]},
            "workspace_id": {target: target_config["workspace_id"]},
            "repository_directory": str(repository_directory),
            "item_types_in_scope": item_types or sorted({item["type"] for item in manifest["items"]}),
        }
    }
    override = {"core": {"workspace_id": {target: target_config["workspace_id"]}}}
    return native, override


def required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"required protected runtime variable {name} is unavailable")
    return value


def power_bi_json(url: str, token: str, method: str = "GET") -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        raise ValueError(f"Power BI ownership operation failed ({error.code})") from error
    except urllib.error.URLError as error:
        raise ValueError("Power BI ownership operation could not be completed") from error
    if not body:
        return {}
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("Power BI ownership operation returned an invalid response")
    return payload


def take_over_semantic_model_if_present(workspace_id: str, model_name: str, client_id: str, credential: Any) -> str:
    """Idempotently take ownership before native connection binding.

    The Power BI TakeOver API is deliberately used only for an existing,
    managed semantic model.  Missing models are new publications and therefore
    do not need a takeover.
    """
    token = credential.get_token("https://analysis.windows.net/powerbi/api/.default").token
    datasets = power_bi_json(f"{POWER_BI_API}/groups/{workspace_id}/datasets", token).get("value", [])
    matches = [dataset for dataset in datasets if isinstance(dataset, dict) and dataset.get("name") == model_name]
    if not matches:
        return "new-model"
    if len(matches) != 1 or not matches[0].get("id"):
        raise ValueError(f"managed semantic model {model_name!r} does not resolve uniquely")
    dataset_id = str(matches[0]["id"])
    details = power_bi_json(f"{POWER_BI_API}/groups/{workspace_id}/datasets/{dataset_id}", token)
    if str(details.get("configuredBy", "")).casefold() == client_id.casefold():
        return "already-owned"
    power_bi_json(f"{POWER_BI_API}/groups/{workspace_id}/datasets/{dataset_id}/Default.TakeOver", token, method="POST")
    return "ownership-transferred"


def deploy(root: Path, config: dict[str, Any], manifest: dict[str, Any], target: str, artifact: Path, allow_target_write: bool, expected_digest: str | None, test_digest: str | None, live_inventory: dict[str, Any] | None = None) -> dict[str, Any]:
    if live_inventory is None:
        return {"status": "blocked", "reason": "authenticated read-only connection inventory is required before a workspace write", "workspace_write": False}
    gate = preflight(root, config, manifest, target, artifact, expected_digest, test_digest, live_inventory)
    if gate["status"] != "ready":
        return gate
    if not allow_target_write:
        return {"status": "blocked", "reason": "explicit target-write approval is required", "workspace_write": False}
    guard = config["protected_resources"][target]["write_guard"]
    if os.environ.get(guard) != "true":
        return {"status": "blocked", "reason": "protected target write guard is not true", "workspace_write": False}
    try:
        actual_version = importlib.metadata.version("fabric-cicd")
        if actual_version != "1.3.0":
            return {"status": "blocked", "reason": f"fabric-cicd 1.3.0 is required; found {actual_version}", "workspace_write": False}
        from azure.identity import ClientSecretCredential
        from fabric_cicd import deploy_with_config
    except (ImportError, importlib.metadata.PackageNotFoundError) as error:
        return {"status": "blocked", "reason": f"supported deployment adapter is unavailable: {type(error).__name__}", "workspace_write": False}
    tenant = required_environment("AZURE_TENANT_ID")
    client_id = required_environment("AZURE_CLIENT_ID")
    client_secret = required_environment("AZURE_CLIENT_SECRET")
    with tempfile.TemporaryDirectory(prefix="powerbi-cicd-") as temporary:
        release_root = Path(temporary)
        with zipfile.ZipFile(artifact) as archive:
            archive.extractall(release_root)
        artifact_config, artifact_manifest = artifact_contract(artifact)
        resolved_substitutions = apply_substitutions(release_root, artifact_manifest, target)
        credential = ClientSecretCredential(tenant_id=tenant, client_id=client_id, client_secret=client_secret)
        results = []
        for item_types in deployment_groups(artifact_manifest):
            ownership: dict[str, str] = {}
            if item_types == ["SemanticModel"]:
                for item in artifact_manifest["items"]:
                    if item["type"] == "SemanticModel":
                        ownership[item["id"]] = take_over_semantic_model_if_present(
                            artifact_config["targets"][target]["workspace_id"], item["id"], client_id, credential
                        )
            native, override = native_config(artifact_config, artifact_manifest, target, release_root / "payload" / artifact_manifest["source_root"], item_types)
            native_path = release_root / ("fabric-cicd-" + item_types[0] + ".json")
            native_path.write_text(json.dumps(native), encoding="utf-8")
            result = deploy_with_config(str(native_path), environment=target, token_credential=credential, config_override=override)
            results.append({"item_types": item_types, "ownership": ownership, "result": getattr(result, "message", "completed")})
    return {"status": "deployed", "adapter": "fabric-cicd", "target": target, "result": results, "resolved_substitutions": resolved_substitutions, "deployment_order": deployment_groups(artifact_manifest), "workspace_write": True}


def verify(manifest: dict[str, Any], target: str, live_inventory: dict[str, Any]) -> dict[str, Any]:
    if live_inventory.get("target") != target or not isinstance(live_inventory.get("items"), list):
        return {"status": "blocked", "reason": "read-only target inventory does not match the selected target", "workspace_write": False}
    expected = {item["id"]: item for item in manifest["items"]}
    observed = {item.get("id"): item for item in live_inventory["items"] if isinstance(item, dict) and isinstance(item.get("id"), str)}
    missing = sorted(set(expected) - set(observed))
    mismatched = sorted(identity for identity, item in expected.items() if identity in observed and observed[identity].get("type") != item["type"])
    bindings = sorted(item["id"] for item in manifest["items"] if item["type"] == "PaginatedReport" and observed.get(item["id"], {}).get("binding") != item["binding"])
    substitutions = sorted(item["id"] for item in manifest["items"] if item.get("substitutions") and observed.get(item["id"], {}).get("substitutions") != item["substitutions"])
    not_ready = sorted(item["id"] for item in manifest["items"] if item["type"] == "SemanticModel" and observed.get(item["id"], {}).get("ready") is not True)
    connection_check = validate_connection_preflight(manifest, target, live_inventory)
    if missing or mismatched or bindings or substitutions or not_ready or connection_check["status"] != "ready":
        return {"status": "blocked", "reason": "post-deployment verification failed", "missing": missing, "type_mismatches": mismatched, "binding_mismatches": bindings, "substitution_mismatches": substitutions, "semantic_models_not_ready": not_ready, "semantic_model_connection_issues": connection_check["issues"], "workspace_write": False}
    return {"status": "verified", "target": target, "managed_scope": sorted(expected), "workspace_write": False}


def drift(manifest: dict[str, Any], target: str, live_inventory: dict[str, Any]) -> dict[str, Any]:
    verification = verify(manifest, target, live_inventory)
    expected = {item["id"] for item in manifest["items"]}
    unmanaged = sorted(item["id"] for item in live_inventory.get("items", []) if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"] not in expected)
    return {"status": "clean" if verification["status"] == "verified" else "drift", "target": target, "managed_verification": verification, "unmanaged_items": unmanaged, "unmanaged_action": "none", "workspace_write": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="Protected fabric-cicd Power BI adapter")
    parser.add_argument("command", choices=("preflight", "deploy", "verify", "drift", "recover"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--target", required=True)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--expected-digest")
    parser.add_argument("--test-digest")
    parser.add_argument("--allow-target-write", action="store_true")
    parser.add_argument("--live-inventory", type=Path)
    args = parser.parse_args()
    try:
        config, manifest = load_object(args.config, "configuration"), load_object(args.manifest, "manifest")
        inventory = load_object(args.live_inventory, "live inventory") if args.live_inventory else None
        if args.command == "preflight":
            result = preflight(args.repo.resolve(), config, manifest, args.target, args.artifact, args.expected_digest, args.test_digest, inventory)
        elif args.command in {"deploy", "recover"}:
            if not args.artifact:
                raise ValueError(f"{args.command} requires --artifact")
            result = deploy(args.repo.resolve(), config, manifest, args.target, args.artifact, args.allow_target_write, args.expected_digest, args.test_digest, inventory)
            if args.command == "recover" and result["status"] == "deployed":
                result["recovery"] = "known-good artifact redeployed through the protected adapter; unmanaged workspace items were not addressed"
        elif args.command == "drift":
            if not args.live_inventory:
                raise ValueError("drift requires --live-inventory from a read-only target inspection")
            result = drift(manifest, args.target, load_object(args.live_inventory, "live inventory"))
        else:
            if not args.live_inventory:
                raise ValueError("verify requires --live-inventory from a read-only target inspection")
            result = verify(manifest, args.target, load_object(args.live_inventory, "live inventory"))
        print(json.dumps(redact(result), indent=2, sort_keys=True))
        return 0 if result["status"] in {"ready", "deployed", "verified"} else 2
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
