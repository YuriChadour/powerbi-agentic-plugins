"""Run the native, dependency-aware Power BI adapter from a verified artifact."""
from __future__ import annotations

import argparse
from pathlib import Path

from deploy_adapter import deploy
from powerbi_cicd import load_object


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--target", required=True)
    parser.add_argument("--digest")
    parser.add_argument("--test-digest")
    parser.add_argument("--live-inventory", required=True, type=Path)
    args = parser.parse_args()
    result = deploy(
        args.repo, load_object(args.config, "configuration"), load_object(args.manifest, "manifest"),
        args.target, args.artifact, True, args.digest, args.test_digest,
        load_object(args.live_inventory, "live inventory"),
    )
    if result.get("status") != "deployed":
        raise SystemExit("deployment did not complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
