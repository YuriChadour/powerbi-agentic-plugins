"""Offline, fail-closed utilities for the Power BI CI/CD lifecycle.

This module deliberately has no Fabric, Power BI, Azure DevOps, or credential
client.  It proves an approved source contract, creates immutable artifacts,
and emits redacted review evidence before a separately approved target adapter
can write to a workspace.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import UUID

TARGETS = {"UAT", "TEST", "PROD", "REHEARSAL"}
ITEM_TYPES = {"SemanticModel", "Report", "PaginatedReport"}
SECRET_WORDS = ("password", "secret", "token", "connectionstring", "client_secret", "access_key", "apikey")
PLACEHOLDER = re.compile(r"REPLACE_|\{\{|^<")
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,127}$")


def load_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object (JSON is valid YAML)")
    return value


def required_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or PLACEHOLDER.search(value):
        raise ValueError(f"{field} must be a completed non-secret string")
    return value


def relative_path(value: object, field: str) -> str:
    text = required_string(value, field).replace("\\", "/")
    candidate = PurePosixPath(text)
    if candidate.is_absolute() or ".." in candidate.parts or text.startswith("/"):
        raise ValueError(f"{field} must be a repository-relative path")
    return str(candidate)


def guid(value: object, field: str) -> str:
    text = required_string(value, field)
    try:
        parsed = UUID(text)
    except (ValueError, AttributeError) as error:
        raise ValueError(f"{field} must be a nonzero UUID") from error
    if parsed.int == 0:
        raise ValueError(f"{field} must be a nonzero UUID")
    return str(parsed)


def no_secrets(value: object, path: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            location = f"{path}.{key}" if path else str(key)
            if any(word in str(key).casefold() for word in SECRET_WORDS):
                errors.append(f"{location} is a secret-bearing field and is not permitted")
            errors.extend(no_secrets(child, location))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(no_secrets(child, f"{path}[{index}]"))
    return errors


def validate_config(config: object) -> list[str]:
    errors = no_secrets(config)
    try:
        if not isinstance(config, dict) or set(config) != {"version", "repository", "azure_devops", "dev_workspace", "targets", "roles", "pipelines", "protected_resources"}:
            raise ValueError("configuration has missing or unsupported top-level fields")
        if config["version"] != 1:
            raise ValueError("configuration version must be 1")
        repository = config["repository"]
        if not isinstance(repository, dict) or set(repository) != {"powerbi_source_folder", "ci_folder", "dev_branch", "prod_branch"}:
            raise ValueError("repository must declare only powerbi_source_folder, ci_folder, dev_branch, and prod_branch")
        for field in ("powerbi_source_folder", "ci_folder"):
            relative_path(repository[field], f"repository.{field}")
        for field in ("dev_branch", "prod_branch"):
            required_string(repository[field], f"repository.{field}")
        azure = config["azure_devops"]
        if not isinstance(azure, dict) or set(azure) != {"organization", "project", "repository"}:
            raise ValueError("azure_devops must declare organization, project, and repository")
        for field in azure:
            required_string(azure[field], f"azure_devops.{field}")
        dev = config["dev_workspace"]
        if not isinstance(dev, dict) or set(dev) != {"workspace_name", "workspace_id", "git_connected"}:
            raise ValueError("dev_workspace must declare workspace_name, workspace_id, and git_connected")
        if dev["git_connected"] is not True:
            raise ValueError("dev_workspace.git_connected must be true")
        if not NAME.fullmatch(required_string(dev["workspace_name"], "dev_workspace.workspace_name")):
            raise ValueError("dev_workspace.workspace_name contains unsupported characters")
        guid(dev["workspace_id"], "dev_workspace.workspace_id")
        targets = config["targets"]
        if not isinstance(targets, dict) or not {"TEST", "PROD"}.issubset(targets) or set(targets) - TARGETS:
            raise ValueError("targets must include TEST and PROD and may include only UAT or REHEARSAL")
        target_fields = {"workspace_name", "workspace_id", "capacity_name", "target_owner", "environment", "pipeline_name", "approval_policy", "artifact_route", "verification_profile", "git_connected"}
        for target, target_config in targets.items():
            if not isinstance(target_config, dict) or set(target_config) != target_fields:
                raise ValueError(f"targets.{target} has missing or unsupported fields")
            if target_config["git_connected"] is not False:
                raise ValueError(f"targets.{target}.git_connected must be false")
            if target_config["artifact_route"] != "immutable":
                raise ValueError(f"targets.{target}.artifact_route must be immutable")
            for field in target_fields - {"workspace_id", "git_connected", "artifact_route"}:
                required_string(target_config[field], f"targets.{target}.{field}")
            if not NAME.fullmatch(required_string(target_config["workspace_name"], f"targets.{target}.workspace_name")):
                raise ValueError(f"targets.{target}.workspace_name contains unsupported characters")
            guid(target_config["workspace_id"], f"targets.{target}.workspace_id")
        roles = config["roles"]
        if not isinstance(roles, list):
            raise ValueError("roles must be a list")
        seen_roles: set[tuple[str, str]] = set()
        for index, role in enumerate(roles):
            if not isinstance(role, dict) or set(role) != {"target", "object_id", "principal_type", "role"}:
                raise ValueError(f"roles[{index}] must declare target, object_id, principal_type, and role")
            target = required_string(role["target"], f"roles[{index}].target").upper()
            if target not in targets:
                raise ValueError(f"roles[{index}].target is not configured")
            key = (target, guid(role["object_id"], f"roles[{index}].object_id"))
            if key in seen_roles:
                raise ValueError(f"roles[{index}] duplicates a direct role mapping")
            seen_roles.add(key)
            if role["principal_type"] not in {"User", "Group", "ServicePrincipal", "ServicePrincipalProfile"} or role["role"] not in {"Admin", "Member", "Contributor", "Viewer"}:
                raise ValueError(f"roles[{index}] has an unsupported principal type or workspace role")
        pipelines = config["pipelines"]
        if not isinstance(pipelines, dict) or set(pipelines) != set(targets):
            raise ValueError("pipelines must map every and only configured target")
        protected = config["protected_resources"]
        if not isinstance(protected, dict) or set(protected) != set(targets):
            raise ValueError("protected_resources must map every and only configured target")
        for target in targets:
            pipeline = pipelines[target]
            if not isinstance(pipeline, dict) or set(pipeline) != {"yaml_path", "source_branch"}:
                raise ValueError(f"pipelines.{target} must declare yaml_path and source_branch")
            relative_path(pipeline["yaml_path"], f"pipelines.{target}.yaml_path")
            expected_branch = repository["dev_branch"] if target == "TEST" else repository["prod_branch"]
            if required_string(pipeline["source_branch"], f"pipelines.{target}.source_branch") != expected_branch:
                raise ValueError(f"pipelines.{target}.source_branch does not match the approved release branch")
            resource = protected[target]
            if not isinstance(resource, dict) or set(resource) != {"identity_reference", "write_guard"}:
                raise ValueError(f"protected_resources.{target} must declare identity_reference and write_guard")
            for field in resource:
                required_string(resource[field], f"protected_resources.{target}.{field}")
    except (KeyError, TypeError, ValueError) as error:
        errors.append(str(error))
    return sorted(set(errors))


def validate_manifest(manifest: object, source_root: str | None = None) -> list[str]:
    errors = no_secrets(manifest)
    try:
        if not isinstance(manifest, dict) or set(manifest) != {"version", "source_root", "items", "excluded"}:
            raise ValueError("manifest has missing or unsupported fields")
        if manifest["version"] != 1:
            raise ValueError("manifest version must be 1")
        actual_root = relative_path(manifest["source_root"], "source_root")
        if source_root is not None and actual_root != source_root:
            raise ValueError("manifest source_root differs from repository.powerbi_source_folder")
        items = manifest["items"]
        if not isinstance(items, list) or not items:
            raise ValueError("items must be a nonempty list")
        ids: set[str] = set()
        item_by_id: dict[str, dict[str, Any]] = {}
        for index, item in enumerate(items):
            if not isinstance(item, dict) or set(item) - {"id", "type", "path", "dependencies", "binding", "substitutions"} or not {"id", "type", "path", "dependencies", "substitutions"}.issubset(item):
                raise ValueError(f"items[{index}] has an invalid shape")
            identity = required_string(item["id"], f"items[{index}].id")
            if identity in ids:
                raise ValueError(f"items[{index}].id is duplicated")
            ids.add(identity)
            item_by_id[identity] = item
            if item["type"] not in ITEM_TYPES:
                raise ValueError(f"items[{index}].type is unsupported")
            relative_path(item["path"], f"items[{index}].path")
            dependencies = item["dependencies"]
            if not isinstance(dependencies, list) or any(not isinstance(value, str) or not value.strip() for value in dependencies):
                raise ValueError(f"items[{index}].dependencies must be a list of logical IDs")
            if not isinstance(item["substitutions"], dict):
                raise ValueError(f"items[{index}].substitutions must be an object")
            if item["type"] == "PaginatedReport":
                binding = item.get("binding")
                if not isinstance(binding, dict) or set(binding) != {"kind", "target"} or binding.get("kind") not in {"semantic_model", "data_source"}:
                    raise ValueError(f"items[{index}] paginated reports require an explicit supported binding")
                required_string(binding["target"], f"items[{index}].binding.target")
            elif "binding" in item:
                raise ValueError(f"items[{index}].binding is only valid for a paginated report")
        for identity, item in item_by_id.items():
            for dependency in item["dependencies"]:
                if dependency not in item_by_id or dependency == identity:
                    raise ValueError(f"item {identity} references an unresolved dependency")
            if item["type"] == "Report" and not any(item_by_id[dep]["type"] == "SemanticModel" for dep in item["dependencies"]):
                raise ValueError(f"report {identity} must explicitly depend on a semantic model")
            if item["type"] == "PaginatedReport" and item["binding"]["kind"] == "semantic_model" and item["binding"]["target"] not in item_by_id:
                raise ValueError(f"paginated report {identity} binding is unresolved")
        excluded = manifest["excluded"]
        if not isinstance(excluded, list):
            raise ValueError("excluded must be a list")
        for index, excluded_item in enumerate(excluded):
            if not isinstance(excluded_item, dict) or set(excluded_item) != {"path", "reason"}:
                raise ValueError(f"excluded[{index}] must declare path and reason")
            required_string(excluded_item["path"], f"excluded[{index}].path")
            required_string(excluded_item["reason"], f"excluded[{index}].reason")
    except (KeyError, TypeError, ValueError) as error:
        errors.append(str(error))
    return sorted(set(errors))


def ordered_items(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    remaining = {item["id"]: item for item in manifest["items"]}
    result: list[dict[str, Any]] = []
    while remaining:
        ready = sorted(identity for identity, item in remaining.items() if all(dependency not in remaining for dependency in item["dependencies"]))
        if not ready:
            raise ValueError("dependency graph contains a cycle")
        for identity in ready:
            result.append(remaining.pop(identity))
    return result


def source_files(root: Path, manifest: dict[str, Any]) -> tuple[Path, list[Path]]:
    root = root.resolve()
    source_root = (root / manifest["source_root"]).resolve()
    if not source_root.is_dir():
        raise ValueError("approved Power BI source folder is missing")
    selected: list[Path] = []
    excluded = [entry["path"].replace("\\", "/") for entry in manifest["excluded"]]
    for item in manifest["items"]:
        candidate = (source_root / item["path"]).resolve()
        if source_root != candidate and source_root not in candidate.parents:
            raise ValueError(f"item {item['id']} escapes the approved source folder")
        if not candidate.exists():
            raise ValueError(f"item {item['id']} source path is missing")
        if item["type"] == "SemanticModel" and not candidate.name.endswith(".SemanticModel"):
            raise ValueError(f"semantic model {item['id']} must use a .SemanticModel source directory")
        if item["type"] == "Report" and not candidate.name.endswith(".Report"):
            raise ValueError(f"report {item['id']} must use a .Report source directory")
        if item["type"] == "PaginatedReport" and (not candidate.is_file() or candidate.suffix.casefold() != ".rdl"):
            raise ValueError(f"paginated report {item['id']} must use an .rdl source file")
        if item["type"] == "SemanticModel" and candidate.is_dir() and not any(path.suffix.casefold() == ".tmdl" or path.name.casefold() in {"model.bim", "definition.pbism"} for path in candidate.rglob("*") if path.is_file()):
            raise ValueError(f"semantic model {item['id']} has no TMDL or supported model definition")
        if item["type"] == "Report" and candidate.is_dir() and not any(path.name.casefold() in {"report.json", "definition.pbir"} for path in candidate.rglob("*") if path.is_file()):
            raise ValueError(f"report {item['id']} has no PBIR definition")
        if candidate.is_dir():
            files = [path for path in candidate.rglob("*") if path.is_file()]
        else:
            files = [candidate]
        if not files:
            raise ValueError(f"item {item['id']} contains no source files")
        selected.extend(files)
    accepted = []
    for file in sorted(set(selected)):
        relative = file.relative_to(root).as_posix()
        if not any(fnmatch.fnmatchcase(relative, pattern) for pattern in excluded):
            accepted.append(file)
    if not accepted:
        raise ValueError("source exclusions remove every selected Power BI file")
    return source_root, accepted


def scan_file_secrets(files: list[Path], root: Path) -> list[str]:
    findings = []
    pattern = re.compile(r"(?i)(password|client_secret|access_token|api[_-]?key|connectionstring)\s*[:=]\s*['\"]?[^\s,'\"]+")
    for file in files:
        if file.stat().st_size <= 2 * 1024 * 1024 and pattern.search(file.read_text(encoding="utf-8", errors="ignore")):
            findings.append(file.relative_to(root).as_posix())
    return sorted(findings)


def validate_source(root: Path, config: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    errors = validate_config(config) + validate_manifest(manifest, config.get("repository", {}).get("powerbi_source_folder"))
    files: list[Path] = []
    if not errors:
        try:
            _, files = source_files(root, manifest)
            errors.extend(f"committed secret candidate in {item}" for item in scan_file_secrets(files, root))
            ordered_items(manifest)
        except ValueError as error:
            errors.append(str(error))
    return {
        "status": "valid" if not errors else "blocked",
        "source_root": manifest.get("source_root"),
        "items": [item.get("id") for item in manifest.get("items", [])],
        "ordered_items": [item["id"] for item in ordered_items(manifest)] if not errors else [],
        "files": [file.relative_to(root).as_posix() for file in files],
        "errors": sorted(set(errors)),
        "workspace_authentication": False,
        "external_writes": False,
    }


def hash_files(files: list[Path], root: Path) -> tuple[str, dict[str, str]]:
    content_hashes: dict[str, str] = {}
    digest = hashlib.sha256()
    for file in sorted(files):
        relative = file.relative_to(root).as_posix()
        content = file.read_bytes()
        content_hashes[relative] = hashlib.sha256(content).hexdigest()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content_hashes[relative].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest(), content_hashes


def dependency_lock(manifest: dict[str, Any]) -> dict[str, Any]:
    return {"version": 1, "items": [{"id": item["id"], "type": item["type"], "dependencies": item["dependencies"], **({"binding": item["binding"]} if "binding" in item else {})} for item in ordered_items(manifest)]}


def package(root: Path, config: dict[str, Any], manifest: dict[str, Any], target: str, output: Path, revision: str) -> dict[str, Any]:
    root = root.resolve()
    if target not in config["targets"]:
        raise ValueError("target is not configured")
    validation = validate_source(root, config, manifest)
    if validation["status"] != "valid":
        raise ValueError("cannot package an invalid Power BI source contract")
    if output.exists():
        raise ValueError("package output already exists")
    _, files = source_files(root, manifest)
    digest, content_hashes = hash_files(files, root)
    lock = dependency_lock(manifest)
    metadata = {"version": 1, "package_target": target, "source_revision": required_string(revision, "revision"), "source_digest": digest, "content_hashes": content_hashes, "dependency_lock": lock, "managed_scope": [item["id"] for item in ordered_items(manifest)]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            archive.write(file, "payload/" + file.relative_to(root).as_posix())
        archive.writestr("config.json", json.dumps(config, sort_keys=True, separators=(",", ":")) + "\n")
        archive.writestr("manifest.json", json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
        archive.writestr("dependency-lock.json", json.dumps(lock, sort_keys=True, separators=(",", ":")) + "\n")
        archive.writestr("release.json", json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n")
    return {"status": "packaged", "artifact": str(output), **metadata}


def check_artifact(path: Path, target: str, expected_revision: str | None, expected_digest: str | None, test_digest: str | None) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        metadata = json.loads(archive.read("release.json"))
        hashes = metadata.get("content_hashes")
        if not isinstance(hashes, dict):
            raise ValueError("artifact has no content hashes")
        for relative, expected_hash in hashes.items():
            actual = hashlib.sha256(archive.read("payload/" + relative)).hexdigest()
            if actual != expected_hash:
                return {"status": "blocked", "reason": f"changed digest for {relative}", "external_writes": False}
    if target not in TARGETS:
        return {"status": "blocked", "reason": "unsupported target", "external_writes": False}
    if expected_revision and metadata.get("source_revision") != expected_revision:
        return {"status": "blocked", "reason": "revision mismatch", "external_writes": False}
    if expected_digest and metadata.get("source_digest") != expected_digest:
        return {"status": "blocked", "reason": "digest mismatch", "external_writes": False}
    if target == "PROD" and test_digest != metadata.get("source_digest"):
        return {"status": "blocked", "reason": "matching TEST verification digest is required before PROD", "external_writes": False}
    return {"status": "verified", "target": target, "source_digest": metadata["source_digest"], "source_revision": metadata["source_revision"], "deployment_order": [item["id"] for item in metadata["dependency_lock"]["items"]], "external_writes": False}


def redact(value: object, key: str = "") -> object:
    if any(word in key.casefold() for word in SECRET_WORDS):
        return "<redacted>"
    if isinstance(value, dict):
        return {str(item): redact(child, str(item)) for item, child in value.items()}
    if isinstance(value, list):
        return [redact(child) for child in value]
    return value


def write_evidence(output: Path, config: dict[str, Any], manifest: dict[str, Any], target: str | None, revision: str | None, digest: str | None, result: str = "planned") -> dict[str, Any]:
    payload = redact({"source_revision": revision, "source_digest": digest, "environment": target, "target": target, "managed_scope": [item["id"] for item in manifest.get("items", [])], "approval": "pending", "identity_reference": config.get("protected_resources", {}).get(target or "", {}).get("identity_reference"), "result": result})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": "recorded", "evidence": str(output), "external_writes": False}


def discover(root: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    candidates = sorted(path.relative_to(root).as_posix() for path in root.rglob("*.pbip"))
    candidates += sorted(path.relative_to(root).as_posix() for path in root.rglob("*.rdl"))
    candidates += sorted(path.relative_to(root).as_posix() for path in root.rglob("*.SemanticModel") if path.is_dir())
    candidates += sorted(path.relative_to(root).as_posix() for path in root.rglob("*.Report") if path.is_dir())
    cicd_files = sorted(path.relative_to(root).as_posix() for path in root.rglob("*cicd*") if path.is_file())
    return {"schema_version": 1, "scope_candidates": "power-bi" if candidates else "unconfigured", "scope_approved": False, "candidate_powerbi_roots": sorted(set(candidates)), "existing_cicd_assets": cicd_files, "mapping_gaps": ["explicit approved config", "explicit manifest", "TEST and PROD targets"], "external_writes": False, "workspace_calls": False}


def render(output: Path, overwrite: bool) -> dict[str, Any]:
    templates = Path(__file__).resolve().parents[1] / "assets" / "templates"
    files = {"powerbi-validation.yml": "powerbi-validation.yml", "Initialize-PowerBiCicd.ps1": "Initialize-PowerBiCicd.ps1", "powerbi_cicd.py": "scripts/powerbi_cicd.py", "scripts/deploy_adapter.py": "scripts/deploy_adapter.py"}
    for destination, source in files.items():
        target = output / destination
        if target.exists() and not overwrite:
            raise ValueError(f"refusing to overwrite {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if source == "scripts/powerbi_cicd.py":
            source_path = Path(__file__)
        elif source == "scripts/deploy_adapter.py":
            source_path = Path(__file__).with_name("deploy_adapter.py")
        else:
            source_path = templates / source
        shutil.copyfile(source_path, target)
    return {"status": "rendered", "output": str(output), "external_writes": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline Power BI CI/CD lifecycle helper")
    parser.add_argument("command", choices=("validate", "plan", "discover", "package", "artifact-check", "evidence", "render", "status"))
    parser.add_argument("--config", type=Path, required=False)
    parser.add_argument("--manifest", type=Path, required=False)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--target")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--revision")
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--expected-revision")
    parser.add_argument("--expected-digest")
    parser.add_argument("--test-digest")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-overwrite", action="store_true")
    args = parser.parse_args()
    try:
        root = args.repo.resolve()
        if args.command == "discover":
            result = discover(root)
        elif args.command == "render":
            if not args.output:
                raise ValueError("render requires --output")
            result = render(args.output, args.allow_overwrite)
        else:
            if not args.config or not args.manifest:
                raise ValueError(f"{args.command} requires --config and --manifest")
            config, manifest = load_object(args.config, "configuration"), load_object(args.manifest, "manifest")
            if args.command == "validate":
                result = validate_source(root, config, manifest)
            elif args.command == "plan":
                result = validate_source(root, config, manifest)
                result["status"] = "planned" if result["status"] == "valid" else "blocked"
                result["proposed_external_actions"] = [] if result["status"] == "planned" else None
            elif args.command == "package":
                if not args.target or not args.out or not args.revision:
                    raise ValueError("package requires --target, --out, and --revision")
                result = package(root, config, manifest, args.target, args.out, args.revision)
            elif args.command == "artifact-check":
                if not args.artifact or not args.target:
                    raise ValueError("artifact-check requires --artifact and --target")
                result = check_artifact(args.artifact, args.target, args.expected_revision, args.expected_digest, args.test_digest)
            elif args.command == "evidence":
                if not args.out:
                    raise ValueError("evidence requires --out")
                result = write_evidence(args.out, config, manifest, args.target, args.revision, args.expected_digest)
            else:
                result = {"status": "not-deployed", "deployment_adapter": "blocked pending tenant-approved supported-item matrix", "external_writes": False}
        print(json.dumps(redact(result), indent=2, sort_keys=True))
        return 0 if result.get("status") in {"valid", "planned", "packaged", "verified", "rendered", "recorded", "not-deployed"} else 2
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
