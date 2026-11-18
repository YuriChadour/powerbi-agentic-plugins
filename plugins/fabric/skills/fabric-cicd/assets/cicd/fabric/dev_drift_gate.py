"""Compare live DEV Fabric definitions with the canonical repository source."""
from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml


IGNORED_JSON_KEYS = {
    "annotations",
    "etag",
    "folder",
    "id",
    "lastModifiedBy",
    "lastPublishTime",
    "type",
}


def normalize_text(lines: list[str] | str) -> str:
    if isinstance(lines, str):
        lines = lines.splitlines()
    normalized = [str(line).replace("\r\n", "\n").replace("\r", "\n").rstrip() for line in lines]
    while normalized and not normalized[0].strip():
        normalized.pop(0)
    while normalized and not normalized[-1].strip():
        normalized.pop()
    return "\n".join(normalized)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def parse_fabric_notebook(path: Path) -> list[tuple[str, str]]:
    """Parse notebook-content.py while ignoring Fabric metadata sections."""
    cells: list[tuple[str, str]] = []
    active: str | None = None
    buffer: list[str] = []
    marker = re.compile(r"^\s*#\s*(MARKDOWN|CELL|METADATA|META)\b", re.IGNORECASE)

    def flush() -> None:
        nonlocal active, buffer
        if active is not None:
            cells.append((active, normalize_text(buffer)))
        active = None
        buffer = []

    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = marker.match(line)
        if match:
            flush()
            tag = match.group(1).upper()
            active = "markdown" if tag == "MARKDOWN" else "code" if tag == "CELL" else None
            continue
        if active == "markdown":
            buffer.append(re.sub(r"^\s*# ?", "", line, count=1))
        elif active == "code":
            buffer.append(line)
    flush()
    return cells


def parse_ipynb(path: Path) -> list[tuple[str, str]]:
    document = load_json(path)
    cells: list[tuple[str, str]] = []
    for cell in document.get("cells", []):
        source = cell.get("source", [])
        cells.append((cell.get("cell_type", "unknown"), normalize_text(source)))
    return cells


def clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: clean_json(child)
            for key, child in value.items()
            if key not in IGNORED_JSON_KEYS
        }
    if isinstance(value, list):
        return [clean_json(child) for child in value]
    return value


def clean_platform(value: dict[str, Any]) -> dict[str, Any]:
    cleaned = clean_json(value)
    config = cleaned.get("config")
    if isinstance(config, dict):
        config.pop("logicalId", None)
    metadata = cleaned.get("metadata")
    if isinstance(metadata, dict) and metadata.get("description") in (None, ""):
        metadata["description"] = ""
    return cleaned


def notebook_diffs(canonical: Path, exported: Path) -> list[str]:
    expected = parse_fabric_notebook(canonical)
    actual = parse_ipynb(exported)
    differences: list[str] = []
    for index in range(max(len(expected), len(actual))):
        if index >= len(expected):
            differences.append(f"cell {index + 1}: present in DEV export but missing from repo")
            continue
        if index >= len(actual):
            differences.append(f"cell {index + 1}: present in repo but missing from DEV export")
            continue
        expected_type, expected_source = expected[index]
        actual_type, actual_source = actual[index]
        if expected_type != actual_type:
            differences.append(
                f"cell {index + 1}: type repo={expected_type!r}, DEV={actual_type!r}"
            )
        if expected_source != actual_source:
            diff = list(
                difflib.unified_diff(
                    expected_source.splitlines(),
                    actual_source.splitlines(),
                    fromfile="repo",
                    tofile="DEV",
                    n=1,
                )
            )
            detail = "\\n".join(diff[:24])
            differences.append(f"cell {index + 1}: source differs\\n{detail}")
    return differences


def json_diffs(canonical: Any, exported: Any, path: str = "$") -> list[str]:
    if type(canonical) is not type(exported):
        return [f"{path}: repo={type(canonical).__name__}, DEV={type(exported).__name__}"]
    if isinstance(canonical, dict):
        differences: list[str] = []
        for key in sorted(set(canonical) | set(exported)):
            if key not in canonical:
                differences.append(f"{path}.{key}: present only in DEV")
            elif key not in exported:
                differences.append(f"{path}.{key}: present only in repo")
            else:
                differences.extend(json_diffs(canonical[key], exported[key], f"{path}.{key}"))
        return differences
    if isinstance(canonical, list):
        differences = []
        if len(canonical) != len(exported):
            differences.append(f"{path}: repo length={len(canonical)}, DEV length={len(exported)}")
        for index, (repo_value, dev_value) in enumerate(zip(canonical, exported)):
            differences.extend(json_diffs(repo_value, dev_value, f"{path}[{index}]"))
        return differences
    return [] if canonical == exported else [f"{path}: repo={canonical!r}, DEV={exported!r}"]


def export_item(fab: str, item_path: str, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    command = [fab, "export", item_path, "-o", str(destination), "-f"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(
            f"fab export failed for {item_path} (exit {result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    item_name = item_path.rsplit("/", 1)[-1]
    exported_item = destination / item_name
    if exported_item.exists():
        return exported_item
    candidates = [path for path in destination.rglob("*") if path.is_dir() and path.name == item_name]
    if len(candidates) != 1:
        raise RuntimeError(f"Could not locate exported definition for {item_path} under {destination}")
    return candidates[0]


def compare_item(item: dict[str, Any], repo_root: Path, exported: Path) -> list[str]:
    folder = item["folder"]
    item_type = item["type"]
    canonical_folder = repo_root / "fabric" / folder
    differences: list[str] = []
    if item_type == "Notebook":
        differences.extend(
            notebook_diffs(
                canonical_folder / "notebook-content.py",
                exported / "notebook-content.ipynb",
            )
        )
    elif item_type == "DataPipeline":
        differences.extend(
            json_diffs(
                clean_json(load_json(canonical_folder / "pipeline-content.json")),
                clean_json(load_json(exported / "pipeline-content.json")),
            )
        )
    elif item_type == "CopyJob":
        differences.extend(
            json_diffs(
                clean_json(load_json(canonical_folder / "copyjob-content.json")),
                clean_json(load_json(exported / "copyjob-content.json")),
            )
        )
    elif item_type == "Lakehouse":
        differences.extend(
            json_diffs(
                clean_platform(load_json(canonical_folder / ".platform")),
                clean_platform(load_json(exported / ".platform")),
            )
        )
    else:
        raise ValueError(f"Unsupported managed item type: {item_type}")
    return differences


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--manifest", default="cicd/fabric/managed-items.yml")
    parser.add_argument("--fab", default="fab")
    parser.add_argument("--export-root")
    parser.add_argument("--report", default="artifacts/dev-drift-report.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    manifest = load_yaml(root / args.manifest)
    workspace = manifest["dev_workspace"]["name"]
    export_root = Path(args.export_root).resolve() if args.export_root else Path(tempfile.mkdtemp(prefix="fabric-dev-drift-"))
    report: dict[str, Any] = {
        "workspace": workspace,
        "source_root": manifest["source_root"],
        "items": [],
    }
    errors: list[str] = []

    for item in manifest["managed_items"]:
        item_path = f"{workspace}.Workspace/{item['folder'].rsplit('/', 1)[-1]}"
        try:
            exported = export_item(args.fab, item_path, export_root / item["folder"])
            differences = compare_item(item, root, exported)
            status = "DRIFT" if differences else "MATCH"
            if differences:
                errors.append(f"{item['folder']}: definition drift detected")
            report["items"].append({"folder": item["folder"], "type": item["type"], "status": status, "differences": differences})
            print(f"{status}: {item['folder']}")
            for difference in differences[:20]:
                print(f"  {difference}")
        except Exception as exc:
            errors.append(f"{item['folder']}: {exc}")
            report["items"].append({"folder": item["folder"], "type": item["type"], "status": "ERROR", "differences": [str(exc)]})
            print(f"ERROR: {item['folder']}: {exc}", file=sys.stderr)

    report["status"] = "FAIL" if errors else "PASS"
    report["errors"] = errors
    report_path = root / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"DEV drift report: {report_path}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
