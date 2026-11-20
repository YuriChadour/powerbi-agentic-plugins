"""Read-only PBIP/PBIR/TMDL/RDL discovery for the Power BI setup contract."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any

SUPPORTED_SUFFIXES = (".SemanticModel", ".Report", ".rdl")
DEFAULT_EXCLUDED = [
    {"path": "**/*.pbix", "reason": "PBIX binaries are not approved source artifacts"},
    {"path": "**/*.pbit", "reason": "PBIT binaries are not approved source artifacts"},
    {"path": "**/*.csv", "reason": "Data files are not deployed as Power BI source"},
    {"path": "**/*.schedules", "reason": "Schedules are separately approved operational state"},
]
WORD_BOUNDARY = re.compile(r"[^A-Za-z0-9]+")


def stable_id(value: str) -> str:
    parts = [part for part in WORD_BOUNDARY.split(value) if part]
    return "".join(part[:1].upper() + part[1:] for part in parts)


def _display_name(path: Path) -> str:
    platform = path / ".platform" if path.is_dir() else path.with_name(".platform")
    if platform.exists():
        try:
            value = json.loads(platform.read_text(encoding="utf-8"))
            display_name = value.get("metadata", {}).get("displayName")
            if isinstance(display_name, str) and display_name.strip():
                return display_name
        except (OSError, json.JSONDecodeError):
            pass
    if path.name.endswith(".SemanticModel"):
        return path.name.removesuffix(".SemanticModel")
    if path.name.endswith(".Report"):
        return path.name.removesuffix(".Report")
    return path.stem


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _report_model_paths(report: Path) -> list[str]:
    references: set[str] = set()
    for definition in sorted(report.rglob("*")):
        if not definition.is_file() or definition.name.casefold() not in {"definition.pbir", "report.json", "model.json"}:
            continue
        try:
            text = definition.read_text(encoding="utf-8")
        except OSError:
            continue
        for path in re.findall(r"(?:\.\.?[/\\])?[^\"']+?\.SemanticModel", text):
            normalized = path.replace("\\", "/")
            references.add(str(PurePosixPath((report.relative_to(report.parent) / normalized).as_posix())))
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            continue

        def visit(node: object) -> None:
            if isinstance(node, dict):
                by_path = node.get("byPath")
                if isinstance(by_path, dict) and isinstance(by_path.get("path"), str):
                    references.add(by_path["path"].replace("\\", "/"))
                for child in node.values():
                    visit(child)
            elif isinstance(node, list):
                for child in node:
                    visit(child)

        visit(value)
    return sorted(references)


def _rdl_binding(path: Path) -> tuple[dict[str, str] | None, list[str]]:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as error:
        return None, [f"invalid RDL XML: {error}"]
    references: set[str] = set()
    connections: set[str] = set()
    for element in root.iter():
        local = element.tag.rsplit("}", 1)[-1]
        text = (element.text or "").strip()
        if not text:
            continue
        if local == "DataSourceReference":
            references.add(text)
        elif local in {"ConnectString", "ConnectionString"}:
            connections.add(text)
    if len(references) > 1:
        return None, ["RDL declares more than one data source reference"]
    if references:
        return {"kind": "data_source", "target": next(iter(references))}, []
    if connections:
        return {"kind": "data_source", "target": sorted(connections)[0]}, [] if len(connections) == 1 else ["RDL declares more than one connection string"]
    return None, ["RDL data source binding is missing"]


def _model_items(source: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    items: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    candidates = sorted(
        [path for path in source.rglob("*") if path.is_dir() and path.name.endswith((".SemanticModel", ".Report"))]
        + [path for path in source.rglob("*.rdl") if path.is_file()],
        key=lambda path: path.as_posix().casefold(),
    )
    for path in candidates:
        if path.name.endswith(".SemanticModel"):
            if not any(file.suffix.casefold() == ".tmdl" or file.name.casefold() in {"model.bim", "definition.pbism"} for file in path.rglob("*") if file.is_file()):
                gaps.append({"path": _relative(path, source), "reason": "semantic model has no TMDL or supported model definition"})
                continue
            item_type = "SemanticModel"
        elif path.name.endswith(".Report"):
            if not any(file.name.casefold() in {"definition.pbir", "report.json"} for file in path.rglob("*") if file.is_file()):
                gaps.append({"path": _relative(path, source), "reason": "report has no PBIR definition"})
                continue
            item_type = "Report"
        else:
            item_type = "PaginatedReport"
        name = _display_name(path)
        identity = stable_id(name)
        if not identity:
            gaps.append({"path": _relative(path, source), "reason": "cannot derive a stable item ID"})
            continue
        items.append({
            "id": identity,
            "type": item_type,
            "path": _relative(path, source),
            "name": name,
            "dependencies": [],
            "binding": None,
            "substitutions": {"rules": []},
        })
    by_name: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_name.setdefault(item["name"].casefold(), []).append(item)
    for name, matches in by_name.items():
        if len(matches) > 1:
            for item in matches:
                gaps.append({"path": item["path"], "reason": f"duplicate display name '{name}' makes the logical item ID ambiguous"})
    for item in items:
        source_path = source / item["path"]
        if item["type"] == "Report":
            references = _report_model_paths(source_path)
            models = []
            for reference in references:
                resolved = (source_path / reference).resolve(strict=False)
                try:
                    relative = resolved.relative_to(source.resolve()).as_posix()
                except ValueError:
                    continue
                models.extend(model for model in items if model["type"] == "SemanticModel" and model["path"] == relative)
                models.extend(model for model in items if model["type"] == "SemanticModel" and reference.replace("\\", "/").endswith(model["path"]))
            unique = {model["id"]: model for model in models}
            if len(unique) != 1:
                gaps.append({"path": item["path"], "reason": "report model reference is missing or ambiguous"})
            else:
                item["dependencies"] = [next(iter(unique))]
        elif item["type"] == "PaginatedReport":
            binding, binding_gaps = _rdl_binding(source_path)
            item["binding"] = binding
            gaps.extend({"path": item["path"], "reason": reason} for reason in binding_gaps)
            if binding and binding["kind"] == "semantic_model":
                item["dependencies"] = [binding["target"]]
    return items, gaps


def ordered_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    remaining = {item["id"]: dict(item) for item in items}
    ordered: list[dict[str, Any]] = []
    while remaining:
        ready = sorted(identity for identity, item in remaining.items() if all(dep not in remaining for dep in item["dependencies"]))
        if not ready:
            raise ValueError("Power BI dependency graph contains a cycle")
        for identity in ready:
            ordered.append(remaining.pop(identity))
    return ordered


def discover_source(repo: Path, source_root: str) -> dict[str, Any]:
    repo = repo.resolve(strict=True)
    source = (repo / source_root).resolve()
    if not source.is_dir() or source != repo / source_root and repo not in source.parents:
        raise ValueError("approved Power BI source root is missing or escapes the repository")
    items, gaps = _model_items(source)
    unsupported = sorted(path.relative_to(repo).as_posix() for path in source.rglob("*") if path.is_file() and path.suffix.casefold() in {".pbip", ".pbix", ".pbit"})
    for path in unsupported:
        if path.endswith(".pbip"):
            gaps.append({"path": path, "reason": "PBIP project file is not a managed deployment item; select its PBIR/TMDL source boundary"})
    identities = [item["id"] for item in items]
    if len(set(identities)) != len(identities):
        gaps.append({"path": source_root, "reason": "stable logical item IDs are duplicated"})
    external_writes = False
    try:
        items = ordered_items(items) if not gaps else items
    except ValueError as error:
        gaps.append({"path": source_root, "reason": str(error)})
    return {"managed_items": items, "excluded": DEFAULT_EXCLUDED, "gaps": gaps, "external_writes": external_writes}
