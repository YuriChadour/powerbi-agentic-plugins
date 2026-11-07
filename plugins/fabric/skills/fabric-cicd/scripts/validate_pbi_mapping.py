"""Validate explicit, non-secret Power BI deployment mappings."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import UUID


def validate(config: object) -> list[str]:
    if not isinstance(config, dict):
        return ["Power BI mapping must be an object"]
    errors = []
    approved = config.get("approved")
    if approved is not True:
        errors.append("Power BI deployment requires an explicit approved mapping")
    mappings = config.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        errors.append("At least one explicit source-to-workspace mapping is required")
        return errors
    names = set()
    for index, item in enumerate(mappings):
        label = f"mappings[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        name, source, workspace = item.get("name"), item.get("source"), item.get("workspace_id")
        if not isinstance(name, str) or not name.strip() or name in names:
            errors.append(f"{label}.name must be nonempty and unique")
        else:
            names.add(name)
        if not isinstance(source, str) or not source.strip() or Path(source).is_absolute() or ".." in Path(source.replace("\\", "/")).parts:
            errors.append(f"{label}.source must be a nonempty repository-relative path")
        try:
            if not isinstance(workspace, str) or UUID(workspace).int == 0:
                raise ValueError()
        except ValueError:
            errors.append(f"{label}.workspace_id must be a nonzero UUID")
        prerequisites = item.get("fabric_prerequisites", [])
        if not isinstance(prerequisites, list) or any(not isinstance(x, str) or not x.strip() for x in prerequisites):
            errors.append(f"{label}.fabric_prerequisites must be a list of named dependencies")
        unknown = set(item) - {"name", "source", "workspace_id", "fabric_prerequisites"}
        if unknown:
            errors.append(f"{label} contains unsupported fields")
    if set(config) - {"approved", "mappings"}:
        errors.append("Power BI mapping contains unsupported fields")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a JSON-formatted YAML Power BI mapping")
    parser.add_argument("mapping", type=Path, help="Explicit pbi-assets.yml mapping (JSON is valid YAML)")
    args = parser.parse_args()
    try:
        config = json.loads(args.mapping.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        parser.exit(2, "Cannot read mapping as JSON-formatted YAML.\n")
    errors = validate(config)
    for error in errors:
        print(error)
    if errors:
        return 1
    print("Power BI mapping is valid; this does not authorize or perform deployment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
