"""Fail-closed validation of an approved non-secret Power BI release contract."""
from __future__ import annotations

import argparse
from pathlib import Path

from powerbi_cicd import load_object, validate_config, validate_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    config = load_object(args.config, "configuration")
    manifest = load_object(args.manifest, "manifest")
    source_root = config.get("repository", {}).get("powerbi_source_folder", "")
    errors = validate_config(config) + validate_manifest(manifest, source_root)
    if errors:
        raise SystemExit("\n".join(errors))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
