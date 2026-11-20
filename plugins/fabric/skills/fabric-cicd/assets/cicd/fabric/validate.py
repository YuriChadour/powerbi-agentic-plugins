"""Offline CI gates for the Fabric release boundary."""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

from validate_notebooks import validate_notebooks

GUID = re.compile(r"(?i)(?<![0-9a-f])[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?![0-9a-f])")
DEFAULT_WORKSPACE_GUID = "00000000-0000-0000-0000-000000000000"
SECRET = re.compile(r"(?i)(password|client_secret|clientsecret|access_token|private_key|connection_string)\s*[:=]")
SECRET_VALUE = re.compile(r"(?i)(ghp_[A-Za-z0-9]{20,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_.-]+|-----BEGIN [A-Z ]+PRIVATE KEY-----)")
DATA_EXTENSIONS = {".parquet", ".csv", ".delta", ".xlsx", ".zip", ".bak", ".db", ".sqlite"}
ITEM_FILES = {
    "Lakehouse": ".platform",
    "Notebook": "notebook-content.py",
    "DataPipeline": "pipeline-content.json",
    "CopyJob": "copyjob-content.json",
}


def load(path: Path):
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def find_pipeline_connection_ids(fabric: Path) -> set[str]:
    """Return GUID-valued Fabric connection references from pipeline definitions."""
    found: set[str] = set()

    def visit(value) -> None:
        if isinstance(value, dict):
            connection = value.get("connection")
            if isinstance(connection, str) and GUID.fullmatch(connection):
                found.add(connection.lower())
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for path in sorted(fabric.rglob("*.DataPipeline/pipeline-content.json")):
        try:
            visit(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue  # reported by the JSON check
    return found


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_file():
        digest.update(path.read_bytes())
    else:
        for child in sorted(path.rglob("*")):
            if child.is_file():
                digest.update(str(child.relative_to(path)).encode())
                digest.update(sha256(child).encode())
    return digest.hexdigest()


def is_excluded(relative: str, manifest: dict) -> bool:
    return any(fnmatch.fnmatch(relative, entry["path"]) for entry in manifest.get("excluded", []))


def validate_workspace_contract(manifest: dict) -> list[str]:
    profile_map = manifest.get("profiles") if isinstance(manifest.get("profiles"), dict) else {}
    environments = tuple(profile_map) or ("DEV", "TEST", "PROD", "HOTFIX")
    workspaces = {env: (profile_map[env].get("workspace") if profile_map else manifest.get(f"{env.lower()}_workspace")) for env in environments}
    missing = [env for env, workspace in workspaces.items() if not isinstance(workspace, dict)]
    if missing:
        return ["missing workspace mapping(s): " + ", ".join(missing)]
    errors = []
    ids = {env: workspace.get("id") for env, workspace in workspaces.items()}
    if any(not isinstance(value, str) or not GUID.fullmatch(value) for value in ids.values()):
        errors.append("every workspace mapping must contain a valid GUID")
    if len(set(ids.values())) != len(ids):
        errors.append("workspace IDs must be distinct across " + ", ".join(environments))
    for env, workspace in workspaces.items():
        if not isinstance(workspace.get("capacity"), dict):
            errors.append(f"{env} workspace must record its approved capacity")
    return errors


def validate(root: Path, manifest_path: Path, output: Path) -> int:
    manifest = load(manifest_path)
    if manifest["source_root"] != "fabric":
        return fail(["source_root must be 'fabric'"])
    fabric = root / "fabric"
    expected = {item["folder"]: item for item in manifest["managed_items"]}
    suffixes = tuple("." + item_type for item_type in ITEM_FILES)
    actual = {
        str(path.relative_to(fabric)).replace("\\", "/"): path
        for path in fabric.rglob("*")
        if path.is_dir() and path.name.endswith(suffixes) and "__pycache__" not in path.parts
        and not is_excluded("fabric/" + str(path.relative_to(fabric)).replace("\\", "/"), manifest)
    }
    errors = []
    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected))
    if missing:
        errors.append("missing managed folders: " + ", ".join(missing))
    if unexpected:
        errors.append("item folders absent from manifest: " + ", ".join(unexpected))
    for folder, item in expected.items():
        if folder not in actual:
            continue
        if item["type"] not in ITEM_FILES:
            errors.append(f"{folder}: unsupported managed item type {item['type']}")
            continue
        if not folder.endswith("." + item["type"]):
            errors.append(f"{folder}: manifest type does not match folder suffix")
        if not (actual[folder] / ITEM_FILES[item["type"]]).exists():
            errors.append(f"{folder}: missing {ITEM_FILES[item['type']]}")
    for path in sorted(fabric.rglob("*")):
        relative = str(path.relative_to(root)).replace("\\", "/")
        if not path.is_file() or is_excluded(relative, manifest):
            continue
        if path.suffix.lower() in DATA_EXTENSIONS:
            errors.append(f"data export or unsupported file in fabric scope: {relative}")
        text = path.read_text(encoding="utf-8", errors="ignore")
        if SECRET.search(text) or SECRET_VALUE.search(text):
            errors.append(f"secret-like content detected in {relative}")
        if path.suffix.lower() == ".json":
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSON {relative}: line {exc.lineno}")
    errors.extend(validate_workspace_contract(manifest))
    errors.extend(validate_notebooks(root, manifest_path))
    errors.extend(validate_bindings(root, fabric))
    errors.extend(validate_copy_jobs(fabric, expected))
    errors.extend(validate_connection_bindings(root / "cicd" / "fabric" / "connection-bindings.yml"))
    environments = list((manifest.get("profiles") or {}).keys()) or ["DEV", "TEST", "PROD", "HOTFIX"]
    result = {
        "manifest_version": manifest["version"],
        "source_root": "fabric",
        "deployment_identity": manifest.get("deployment_identity"),
        "managed_items": manifest["managed_items"],
        "errors": errors,
        "unpublish_skip": True,
        "environments": environments,
        "profiles": manifest.get("profiles"),
        "hashes": {name: sha256(path) for name, path in sorted(actual.items())},
    }
    for env in environments:
        result[f"{env.lower()}_workspace"] = manifest.get(f"{env.lower()}_workspace")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for error in errors:
        print("ERROR: " + error, file=sys.stderr)
    print(f"Validated {len(expected)} managed Fabric folders; unpublish.skip=true")
    return 1 if errors else 0


def validate_bindings(root: Path, fabric: Path) -> list[str]:
    parameter_path = root / "cicd" / "fabric" / "parameter.yml"
    if "${" in parameter_path.read_text(encoding="utf-8"):
        return ["parameter file contains unsupported shell-style placeholders"]
    rules = {
        str(rule.get("find_value", "")).lower(): rule
        for rule in (load(parameter_path) or {}).get("find_replace", [])
        if rule.get("item_type") == "DataPipeline"
    }
    errors = []
    connections = find_pipeline_connection_ids(fabric) - {DEFAULT_WORKSPACE_GUID}
    unmapped = sorted(connections - set(rules))
    if unmapped:
        errors.append("unmapped Fabric pipeline connection reference(s): " + ", ".join(unmapped))
    manifest = load(root / "cicd" / "fabric" / "managed-items.yml") or {}
    environments = set((manifest.get("profiles") or {}).keys()) or {"DEV", "TEST", "PROD", "HOTFIX"}
    incomplete = sorted(
        cid for cid in connections & set(rules)
        if not isinstance(rules[cid].get("replace_value"), dict) or not environments <= set(rules[cid]["replace_value"])
    )
    if incomplete:
        errors.append("pipeline connection mapping(s) must define " + ", ".join(sorted(environments)) + ": " + ", ".join(incomplete))
    return errors


def validate_copy_jobs(fabric: Path, expected: dict) -> list[str]:
    """Every Copy Job a pipeline invokes must be a managed item (deployed before the pipeline)."""
    managed_ids = set()
    for folder, item in expected.items():
        if item["type"] != "CopyJob":
            continue
        try:
            managed_ids.add(json.loads((fabric / folder / ".platform").read_text(encoding="utf-8"))["config"]["logicalId"].lower())
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            continue

    def invoked(value):
        if isinstance(value, dict):
            if value.get("type") == "InvokeCopyJob":
                yield (value.get("typeProperties") or {}).get("copyJobId")
            for child in value.values():
                yield from invoked(child)
        elif isinstance(value, list):
            for child in value:
                yield from invoked(child)

    errors = []
    for path in sorted(fabric.rglob("*.DataPipeline/pipeline-content.json")):
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for copy_job_id in invoked(content):
            if not isinstance(copy_job_id, str) or copy_job_id.lower() not in managed_ids:
                errors.append(f"{path.parent.name}: invokes Copy Job {copy_job_id} that is not a managed CopyJob item")
    return errors


def validate_connection_bindings(path: Path) -> list[str]:
    if not path.exists():
        return []
    document = load(path) or {}
    errors = []
    for connection in document.get("connections", []):
        if not all(isinstance(connection.get(key), str) and connection[key] for key in ("key", "connection_id", "display_name", "required_permission")):
            errors.append("connection-bindings.yml: each connection needs key, connection_id, display_name and required_permission")
        elif not GUID.fullmatch(connection["connection_id"]):
            errors.append(f"connection-bindings.yml: {connection['key']} connection_id is not a GUID")
    return errors


def fail(errors: list[str]) -> int:
    for error in errors:
        print("ERROR: " + error, file=sys.stderr)
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--manifest", default="cicd/fabric/managed-items.yml")
    parser.add_argument("--output", default="artifacts/managed-manifest.json")
    args = parser.parse_args()
    raise SystemExit(validate(Path(args.root).resolve(), Path(args.manifest).resolve(), Path(args.output).resolve()))
