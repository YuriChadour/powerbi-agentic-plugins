"""Verify immutable semantic-model connection maps against read-only inventory."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from deploy_adapter import verify


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--live-inventory", required=True, type=Path)
    args = parser.parse_args()
    result = verify(json.loads(args.manifest.read_text(encoding="utf-8")), args.environment, json.loads(args.live_inventory.read_text(encoding="utf-8")))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "verified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
