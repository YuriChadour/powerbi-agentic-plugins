"""Generate fabric-cicd binding rules from managed source and a DEV item listing (offline, deterministic)."""
from __future__ import annotations

import json
import re
from pathlib import Path

GUID = re.compile(r"(?i)(?<![0-9a-f])[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?![0-9a-f])")
ZERO_GUID = "00000000-0000-0000-0000-000000000000"
ITEM_TYPES = ("Lakehouse", "Notebook", "DataPipeline", "CopyJob")
ENVIRONMENTS = ("DEV", "TEST", "PROD", "HOTFIX")
TEXT_SUFFIXES = {".py", ".json", ".sql", ".yml", ".yaml", ".txt", ".md"}


def known_references(dev_workspace_id: str, dev_items: list[dict]) -> dict[str, str]:
    """Map every DEV identifier (direct, Git logical ID, SQL endpoint) to its target-resolved reference."""
    known = {ZERO_GUID: "$workspace.$id", dev_workspace_id.lower(): "$workspace.$id"}
    for item in dev_items:
        if item["type"] == "SQLEndpoint":
            known[item["id"].lower()] = f"$items.Lakehouse.{item['name']}.$sqlendpointid"
            continue
        if item["type"] not in ITEM_TYPES:
            continue
        reference = f"$items.{item['type']}.{item['name']}.$id"
        for key in ("id", "logicalId"):
            if item.get(key):
                known[item[key].lower()] = reference
        if item["type"] == "Lakehouse" and item.get("sqlendpointid"):
            known[item["sqlendpointid"].lower()] = f"$items.Lakehouse.{item['name']}.$sqlendpointid"
    return known


def connection_ids(value, found: set[str] | None = None) -> set[str]:
    """GUID-valued ``connection`` fields in a pipeline or Copy Job definition."""
    found = set() if found is None else found
    if isinstance(value, dict):
        connection = value.get("connection")
        if isinstance(connection, str) and GUID.fullmatch(connection):
            found.add(connection.lower())
        for child in value.values():
            connection_ids(child, found)
    elif isinstance(value, list):
        for child in value:
            connection_ids(child, found)
    return found


def definition_files(folder: Path):
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.name != ".platform" and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def generate_rules(
    source: Path,
    managed: list[dict],
    dev_workspace_id: str,
    dev_items: list[dict],
    excluded_guids: set[str] | frozenset = frozenset(),
    mapped_guids: dict[str, str] | None = None,
) -> dict:
    """Return rules, connection IDs, item dependencies and blocking gaps for the managed items.

    managed: [{"folder", "type", "name"}] with folder relative to ``source``.
    dev_items: [{"type", "name", "id", "logicalId", "sqlendpointid"}] from the DEV workspace listing.
    """
    known = known_references(dev_workspace_id, dev_items)
    known.update({guid.lower(): expression for guid, expression in (mapped_guids or {}).items()})
    folder_of = {f"{item['type']}.{item['name']}": item["folder"] for item in managed}
    excluded = {guid.lower() for guid in excluded_guids}
    rules: dict[tuple[str, str], str] = {}
    all_connections: set[str] = set()
    dependencies: dict[str, set[str]] = {item["folder"]: set() for item in managed}
    gaps: list[dict] = []
    contents: dict[str, tuple[set[str], list]] = {}

    for item in managed:
        files = []
        own_connections: set[str] = set()
        for path in definition_files(source / item["folder"]):
            text = path.read_text(encoding="utf-8", errors="ignore")
            files.append((path, text))
            if path.suffix.lower() == ".json":
                try:
                    own_connections |= connection_ids(json.loads(text))
                except json.JSONDecodeError:
                    pass
        all_connections |= own_connections
        contents[item["folder"]] = (own_connections, files)

    for item in managed:
        own_connections, files = contents[item["folder"]]
        for path, text in files:
            for guid in sorted({match.lower() for match in GUID.findall(text)}):
                if guid in own_connections:
                    rules[(guid, item["type"])] = guid
                elif guid in excluded or guid in all_connections:
                    continue
                elif guid in known:
                    rules[(guid, item["type"])] = known[guid]
                    referenced = known[guid].removeprefix("$items.").rsplit(".$", 1)[0]
                    target = folder_of.get(referenced)
                    if target and target != item["folder"]:
                        dependencies[item["folder"]].add(target)
                else:
                    gaps.append({"guid": guid, "file": str(path.relative_to(source)).replace("\\", "/")})
    return {
        "rules": [
            {"find_value": guid, "item_type": item_type, "replace_value": {env: expression for env in ENVIRONMENTS}}
            for (guid, item_type), expression in sorted(rules.items(), key=lambda pair: (pair[0][1], pair[0][0]))
        ],
        "connection_ids": sorted(all_connections),
        "dependencies": {folder: sorted(values) for folder, values in sorted(dependencies.items())},
        "gaps": sorted(gaps, key=lambda gap: (gap["guid"], gap["file"])),
    }
