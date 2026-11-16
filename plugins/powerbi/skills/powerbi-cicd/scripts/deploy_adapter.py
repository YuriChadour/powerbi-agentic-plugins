"""Guarded Power BI deployment adapter backed only by Microsoft fabric-cicd."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from powerbi_cicd import TARGETS, check_artifact, load_object, redact, validate_config, validate_manifest, validate_source

SUPPORTED = {
    "SemanticModel": "fabric_cicd.deploy_with_config",
    "Report": "fabric_cicd.deploy_with_config",
    "PaginatedReport": "fabric_cicd.deploy_with_config",
}


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


def preflight(root: Path, config: dict[str, Any], manifest: dict[str, Any], target: str, artifact: Path | None = None, expected_digest: str | None = None, test_digest: str | None = None) -> dict[str, Any]:
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
    return {"status": "ready", "adapter": "fabric-cicd", "adapter_operation": sorted({SUPPORTED[item["type"]] for item in manifest["items"]}), "target": target, "identity_reference": identity, "integrity": integrity, "workspace_write": False, "live_target": "unverified until authenticated read-only preflight"}


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


def deploy(root: Path, config: dict[str, Any], manifest: dict[str, Any], target: str, artifact: Path, allow_target_write: bool, expected_digest: str | None, test_digest: str | None) -> dict[str, Any]:
    gate = preflight(root, config, manifest, target, artifact, expected_digest, test_digest)
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
        credential = ClientSecretCredential(tenant_id=tenant, client_id=client_id, client_secret=client_secret)
        results = []
        for item_types in deployment_groups(artifact_manifest):
            native, override = native_config(artifact_config, artifact_manifest, target, release_root / "payload" / artifact_manifest["source_root"], item_types)
            native_path = release_root / ("fabric-cicd-" + item_types[0] + ".json")
            native_path.write_text(json.dumps(native), encoding="utf-8")
            result = deploy_with_config(str(native_path), environment=target, token_credential=credential, config_override=override)
            results.append({"item_types": item_types, "result": getattr(result, "message", "completed")})
    return {"status": "deployed", "adapter": "fabric-cicd", "target": target, "result": results, "deployment_order": deployment_groups(artifact_manifest), "workspace_write": True}


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
    if missing or mismatched or bindings or substitutions or not_ready:
        return {"status": "blocked", "reason": "post-deployment verification failed", "missing": missing, "type_mismatches": mismatched, "binding_mismatches": bindings, "substitution_mismatches": substitutions, "semantic_models_not_ready": not_ready, "workspace_write": False}
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
        if args.command == "preflight":
            result = preflight(args.repo.resolve(), config, manifest, args.target, args.artifact, args.expected_digest, args.test_digest)
        elif args.command in {"deploy", "recover"}:
            if not args.artifact:
                raise ValueError(f"{args.command} requires --artifact")
            result = deploy(args.repo.resolve(), config, manifest, args.target, args.artifact, args.allow_target_write, args.expected_digest, args.test_digest)
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
