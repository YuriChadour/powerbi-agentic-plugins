"""Validate Fabric notebook source without executing a notebook or calling Fabric."""
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

import yaml

RUN_MAGIC = re.compile(r'^%run\s+"[^"\r\n]+"\s*$')
CELL_MAGIC = re.compile(r"^%%[A-Za-z][A-Za-z0-9_-]*(?:\s+.*)?$")


def parse_source(path: Path) -> list[str]:
    errors: list[str] = []
    filtered: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("%"):
            valid = RUN_MAGIC.fullmatch(stripped) if stripped.startswith("%run") else CELL_MAGIC.fullmatch(stripped)
            if not valid:
                errors.append(f"{path}: line {line_number}: invalid Fabric magic syntax")
            filtered.append(f"# Fabric magic omitted at source line {line_number}")
        else:
            filtered.append(line)
    try:
        ast.parse("\n".join(filtered), filename=str(path))
    except SyntaxError as exc:
        errors.append(f"{path}: line {exc.lineno}: {exc.msg}")
    return errors


def validate_notebooks(root: Path, manifest_path: Path) -> list[str]:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    errors: list[str] = []
    fabric_root = root / manifest.get("source_root", "fabric")
    for item in manifest.get("managed_items", []):
        if item.get("type") != "Notebook":
            continue
        path = fabric_root / item["folder"] / "notebook-content.py"
        if not path.exists():
            errors.append(f"{path}: notebook source is missing")
            continue
        errors.extend(parse_source(path))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--manifest", default="cicd/fabric/managed-items.yml")
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    manifest_path = Path(args.manifest) if Path(args.manifest).is_absolute() else (root / args.manifest).resolve()
    errors = validate_notebooks(root, manifest_path)
    if args.output:
        output = Path(args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"checked": "managed Fabric notebook sources", "errors": errors}, indent=2) + "\n", encoding="utf-8")
    for error in errors:
        print("ERROR: " + error)
    print("Fabric notebook syntax checks failed" if errors else "Fabric notebook syntax checks passed")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
