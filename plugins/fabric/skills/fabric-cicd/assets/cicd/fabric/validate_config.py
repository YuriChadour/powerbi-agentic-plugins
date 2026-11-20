"""Run fabric-cicd's native, offline configuration validation."""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from fabric_cicd import constants
from fabric_cicd._common._config_utils import config_overrides_scope, load_config_file


FABRIC_API_ROOT_URL = "https://api.fabric.microsoft.com"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="cicd/fabric/config.yml")
    parser.add_argument("--environment", action="append", required=True)
    args = parser.parse_args()
    config = str(Path(args.config).resolve())
    configured = (yaml.safe_load(Path(args.config).read_text(encoding="utf-8")) or {}).get("core", {}).get("workspace_id", {})
    for environment in args.environment:
        if environment not in configured:
            raise SystemExit(f"environment '{environment}' is not a configured profile")
        parsed_config = load_config_file(config, environment)
        if parsed_config.get("constants", {}).get("DEFAULT_API_ROOT_URL") != FABRIC_API_ROOT_URL:
            raise SystemExit(
                "DEFAULT_API_ROOT_URL must target https://api.fabric.microsoft.com "
                "so Notebook publishing does not use the unsupported Power BI Items API"
            )
        original_api_root = constants.DEFAULT_API_ROOT_URL
        with config_overrides_scope(parsed_config, environment):
            if constants.DEFAULT_API_ROOT_URL != FABRIC_API_ROOT_URL:
                raise SystemExit("fabric-cicd did not apply the Fabric API root override")
        if constants.DEFAULT_API_ROOT_URL != original_api_root:
            raise SystemExit("fabric-cicd API root override leaked outside deployment scope")
        print(f"fabric-cicd configuration is valid for {environment}")


if __name__ == "__main__":
    main()
