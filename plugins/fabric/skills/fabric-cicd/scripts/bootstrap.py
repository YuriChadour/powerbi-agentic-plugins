"""Focused, offline helpers for the reference Fabric CI/CD bootstrap.

This module deliberately has no Fabric or Azure DevOps HTTP client. The rendered
PowerShell entry point owns authenticated ``fab`` and ``az`` calls; this module
only validates non-secret contracts, selects package content and proves artifact
identity offline.
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

import yaml

GUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,127}$")
TARGETS = {"UAT", "TEST", "PROD", "REHEARSAL"}
ITEM_TYPES = {"Lakehouse", "Notebook", "DataPipeline"}
ROLE_TYPES = {"User", "Group", "ServicePrincipal", "ServicePrincipalProfile"}
ROLES = {"Admin", "Member", "Contributor", "Viewer"}
SECRET_MARKERS = ("password", "secret", "connectionstring", "client_secret", "access_token")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Bootstrap configuration must be a JSON object")
    return value


def load_manifest(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Managed-item manifest must be a YAML object")
    return value


def is_placeholder(value: object) -> bool:
    return isinstance(value, str) and ("REPLACE_" in value or value.startswith("<") or "{{" in value)


def relative_path(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(f"{field} must be a nonempty repository-relative POSIX path")
    path = PurePosixPath(value.strip("/"))
    if not str(path) or path.is_absolute() or ".." in path.parts or any(is_placeholder(part) for part in path.parts):
        raise ValueError(f"{field} must be a nonempty repository-relative POSIX path")
    return str(path)


def nonempty(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or is_placeholder(value):
        raise ValueError(f"{field} is required")
    return value.strip()


def guid(value: object, field: str) -> str:
    value = nonempty(value, field)
    if not GUID.fullmatch(value):
        raise ValueError(f"{field} must be a GUID")
    return value.lower()


def validate_config(config: object) -> list[str]:
    errors: list[str] = []
    try:
        if not isinstance(config, dict) or set(config) - {"version", "repository", "azure_devops", "dev_workspace", "targets", "roles", "pipelines", "protected_resources"}:
            raise ValueError("Configuration contains unsupported fields")
        if config.get("version") != 1:
            raise ValueError("version must be 1")
        repository = config.get("repository")
        if not isinstance(repository, dict) or set(repository) != {"fabric_source_folder", "ci_folder", "dev_branch", "prod_branch"}:
            raise ValueError("repository must declare Fabric and CI folders plus DEV and PROD branches")
        fabric_root = relative_path(repository["fabric_source_folder"], "repository.fabric_source_folder")
        ci_root = relative_path(repository["ci_folder"], "repository.ci_folder")
        if fabric_root == ci_root:
            raise ValueError("Fabric source and CI folders must differ")
        for key in ("dev_branch", "prod_branch"):
            branch = nonempty(repository[key], f"repository.{key}")
            if branch.startswith("refs/") or any(char.isspace() for char in branch):
                raise ValueError(f"repository.{key} must be a branch name")
        ado = config.get("azure_devops")
        if not isinstance(ado, dict) or set(ado) != {"organization", "project", "repository"}:
            raise ValueError("azure_devops must declare organization, project and repository")
        for key, value in ado.items():
            if not NAME.fullmatch(nonempty(value, f"azure_devops.{key}")):
                raise ValueError(f"azure_devops.{key} contains unsupported characters")
        dev_workspace = config.get("dev_workspace")
        if not isinstance(dev_workspace, dict) or set(dev_workspace) != {"workspace_name", "workspace_id"}:
            raise ValueError("dev_workspace must declare the existing DEV workspace name and ID")
        if not NAME.fullmatch(nonempty(dev_workspace.get("workspace_name"), "dev_workspace.workspace_name")):
            raise ValueError("dev_workspace.workspace_name contains unsupported characters")
        guid(dev_workspace.get("workspace_id"), "dev_workspace.workspace_id")
        targets = config.get("targets")
        if not isinstance(targets, dict) or not {"TEST", "PROD"}.issubset(targets) or set(targets) - TARGETS:
            raise ValueError("targets must include TEST and PROD and may include UAT or REHEARSAL")
        for target, item in targets.items():
            if not isinstance(item, dict) or set(item) - {"workspace_name", "workspace_id", "capacity_name", "environment", "variable_group"}:
                raise ValueError(f"targets.{target} contains unsupported fields")
            if not NAME.fullmatch(nonempty(item.get("workspace_name"), f"targets.{target}.workspace_name")):
                raise ValueError(f"targets.{target}.workspace_name contains unsupported characters")
            if item.get("workspace_id") is not None:
                guid(item["workspace_id"], f"targets.{target}.workspace_id")
            elif not item.get("capacity_name"):
                raise ValueError(f"targets.{target} needs workspace_id or capacity_name")
            nonempty(item.get("environment"), f"targets.{target}.environment")
            nonempty(item.get("variable_group"), f"targets.{target}.variable_group")
        roles = config.get("roles")
        if not isinstance(roles, list):
            raise ValueError("roles must be a list")
        seen_roles = set()
        for index, item in enumerate(roles):
            if not isinstance(item, dict) or set(item) != {"target", "object_id", "principal_type", "role"}:
                raise ValueError(f"roles[{index}] must declare target, object_id, principal_type and role")
            target = nonempty(item["target"], f"roles[{index}].target").upper()
            if target not in targets:
                raise ValueError(f"roles[{index}].target is not configured")
            object_id = guid(item["object_id"], f"roles[{index}].object_id")
            if item["principal_type"] not in ROLE_TYPES or item["role"] not in ROLES:
                raise ValueError(f"roles[{index}] has an unsupported principal type or workspace role")
            key = (target, object_id)
            if key in seen_roles:
                raise ValueError(f"roles[{index}] duplicates a principal mapping")
            seen_roles.add(key)
        pipelines = config.get("pipelines")
        if not isinstance(pipelines, dict) or not {"TEST", "PROD"}.issubset(pipelines) or set(pipelines) - set(targets):
            raise ValueError("pipelines must configure TEST and PROD targets only when their target profile exists")
        for target, item in pipelines.items():
            if not isinstance(item, dict) or set(item) != {"name", "yaml_path", "source_branch"}:
                raise ValueError(f"pipelines.{target} must declare name, yaml_path and source_branch")
            nonempty(item["name"], f"pipelines.{target}.name")
            relative_path(item["yaml_path"], f"pipelines.{target}.yaml_path")
            branch = nonempty(item["source_branch"], f"pipelines.{target}.source_branch")
            expected = repository["dev_branch"] if target == "TEST" else repository["prod_branch"] if target == "PROD" else branch
            if branch != expected:
                raise ValueError(f"pipelines.{target}.source_branch must match the configured {target} release branch")
        protected = config.get("protected_resources")
        if not isinstance(protected, dict) or set(protected) - set(targets):
            raise ValueError("protected_resources must map only configured targets")
        for target in ("TEST", "PROD"):
            if not isinstance(protected.get(target), dict) or set(protected[target]) != {"service_connection", "write_guard"}:
                raise ValueError(f"protected_resources.{target} must declare service_connection and write_guard")
            nonempty(protected[target]["service_connection"], f"protected_resources.{target}.service_connection")
            nonempty(protected[target]["write_guard"], f"protected_resources.{target}.write_guard")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def validate_manifest(manifest: object, expected_source_root: str | None = None) -> list[str]:
    errors: list[str] = []
    try:
        if not isinstance(manifest, dict) or set(manifest) - {"version", "source_root", "managed_items", "excluded"}:
            raise ValueError("Managed-item manifest contains unsupported fields")
        if manifest.get("version") != 1:
            raise ValueError("Managed-item manifest version must be 1")
        source_root = relative_path(manifest.get("source_root"), "source_root")
        if expected_source_root and source_root != expected_source_root:
            raise ValueError("managed-item source_root differs from bootstrap Fabric source folder")
        items = manifest.get("managed_items")
        if not isinstance(items, list) or not items:
            raise ValueError("managed_items must be a nonempty list")
        names = set()
        for index, item in enumerate(items):
            if not isinstance(item, dict) or set(item) - {"folder", "type", "logical_id", "dependencies", "data_policy"} or not {"folder", "type", "dependencies"}.issubset(item):
                raise ValueError(f"managed_items[{index}] has an invalid shape")
            folder = relative_path(item["folder"], f"managed_items[{index}].folder")
            if item["type"] not in ITEM_TYPES:
                raise ValueError(f"managed_items[{index}].type is unsupported")
            if folder in names:
                raise ValueError(f"managed_items[{index}].folder is duplicated")
            names.add(folder)
            if not isinstance(item["dependencies"], list) or any(not isinstance(value, str) or not value for value in item["dependencies"]):
                raise ValueError(f"managed_items[{index}].dependencies must be a list of folders")
        for item in items:
            for dependency in item["dependencies"]:
                if dependency not in names:
                    raise ValueError(f"managed item {item['folder']} references missing dependency {dependency}")
        excluded = manifest.get("excluded")
        if not isinstance(excluded, list) or not excluded:
            raise ValueError("excluded must be a nonempty list")
        for index, item in enumerate(excluded):
            if not isinstance(item, dict) or set(item) != {"path", "reason"}:
                raise ValueError(f"excluded[{index}] must declare path and reason")
            nonempty(item["path"], f"excluded[{index}].path")
            nonempty(item["reason"], f"excluded[{index}].reason")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def plan(config: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    errors = validate_config(config)
    if not errors:
        errors = validate_manifest(manifest, config["repository"]["fabric_source_folder"])
    if errors:
        return {"status": "blocked", "external_writes": False, "errors": errors}
    return {
        "status": "planned",
        "external_writes": False,
        "fabric_source_folder": config["repository"]["fabric_source_folder"],
        "ci_folder": config["repository"]["ci_folder"],
        "targets": sorted(config["targets"]),
        "role_mappings": len(config["roles"]),
        "pipelines": {key: value["yaml_path"] for key, value in config["pipelines"].items()},
        "managed_items": [item["folder"] for item in manifest["managed_items"]],
        "deployment": "not-queued",
        "verification": "pending",
    }


def ignored(path: PurePosixPath, patterns: list[str]) -> bool:
    text = str(path)
    return any(fnmatch.fnmatchcase(text, pattern) for pattern in patterns)


def source_digest(root: Path, source_root: str, manifest: dict[str, Any]) -> tuple[str, list[Path]]:
    root = root.resolve()
    base = (root / source_root).resolve()
    if not base.is_dir():
        raise ValueError("Configured Fabric source folder is missing")
    selected = {PurePosixPath(item["folder"]) for item in manifest["managed_items"]}
    excluded = [item["path"].replace("\\", "/") for item in manifest["excluded"]]
    files: list[Path] = []
    for folder in selected:
        candidate = (base / folder).resolve()
        if base not in candidate.parents or not candidate.exists():
            raise ValueError(f"Managed item is missing: {folder}")
        for file in candidate.rglob("*"):
            relative = file.relative_to(root).as_posix()
            if file.is_file() and not ignored(PurePosixPath(relative), excluded):
                files.append(file)
    files = sorted(set(files))
    digest = hashlib.sha256()
    for file in files:
        relative = file.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        content = file.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest(), files


def package(root: Path, config: dict[str, Any], manifest: dict[str, Any], target: str, output: Path, revision: str) -> dict[str, Any]:
    root = root.resolve()
    if target not in config["targets"]:
        raise ValueError("Package target is not configured")
    digest, files = source_digest(root, config["repository"]["fabric_source_folder"], manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError("Package output already exists")
    metadata = {"version": 1, "target": target, "source_digest": digest, "source_revision": nonempty(revision, "revision"), "managed_items": [item["folder"] for item in manifest["managed_items"]]}
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            archive.write(file, "payload/" + file.relative_to(root).as_posix())
        archive.writestr("release.json", json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n")
    return {"artifact": str(output), **metadata}


def release_gate(artifact: Path, expected_digest: str, expected_target: str = "TEST") -> dict[str, Any]:
    with zipfile.ZipFile(artifact) as archive:
        metadata = json.loads(archive.read("release.json"))
    if metadata.get("target") != expected_target or metadata.get("source_digest") != expected_digest:
        return {"status": "blocked", "reason": "TEST artifact target or Fabric source digest does not match PROD candidate"}
    return {"status": "verified", "source_digest": expected_digest, "source_revision": metadata.get("source_revision")}


def scan_sources(root: Path, source_root: str) -> list[str]:
    findings = []
    root = root.resolve()
    base = (root / source_root).resolve()
    for file in base.rglob("*"):
        if not file.is_file() or file.stat().st_size > 2 * 1024 * 1024:
            continue
        lowered = file.read_text(encoding="utf-8", errors="ignore").casefold()
        if any(marker in lowered for marker in SECRET_MARKERS):
            findings.append(file.relative_to(root).as_posix())
    return sorted(findings)


def _main() -> int:
    parser = argparse.ArgumentParser(description="Offline support for the focused Fabric CI/CD bootstrap")
    parser.add_argument("command", choices=("validate", "plan", "package", "source-digest", "release-gate", "scan", "managed-items"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--target")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--revision")
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--expected-digest")
    args = parser.parse_args()
    try:
        config, manifest = load_json(args.config), load_manifest(args.manifest)
        if args.command == "validate":
            result = {"config_errors": validate_config(config), "manifest_errors": validate_manifest(manifest, config.get("repository", {}).get("fabric_source_folder"))}
            result["status"] = "valid" if not result["config_errors"] and not result["manifest_errors"] else "invalid"
        elif args.command == "plan":
            result = plan(config, manifest)
        elif args.command == "source-digest":
            digest, files = source_digest(args.repo.resolve(), config["repository"]["fabric_source_folder"], manifest)
            result = {"status": "valid", "source_digest": digest, "files": [file.relative_to(args.repo.resolve()).as_posix() for file in files]}
        elif args.command == "package":
            if not args.target or not args.out or not args.revision:
                raise ValueError("package requires --target, --out and --revision")
            result = package(args.repo.resolve(), config, manifest, args.target, args.out, args.revision)
        elif args.command == "release-gate":
            if not args.artifact or not args.expected_digest:
                raise ValueError("release-gate requires --artifact and --expected-digest")
            result = release_gate(args.artifact, args.expected_digest)
        elif args.command == "managed-items":
            errors = validate_manifest(manifest, config.get("repository", {}).get("fabric_source_folder"))
            result = {"status": "valid", "source_root": manifest.get("source_root"), "managed_items": manifest.get("managed_items", [])}
            if errors:
                result = {"status": "invalid", "errors": errors}
        else:
            result = {"status": "clean", "findings": scan_sources(args.repo.resolve(), config["repository"]["fabric_source_folder"])}
            if result["findings"]:
                result["status"] = "blocked"
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("status") in {"valid", "planned", "verified", "clean"} else 2
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(_main())
