"""Write a redacted, machine-readable deployment result."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--status", required=True, choices=("succeeded", "failed", "partial"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    record = {"captured_at": datetime.now(timezone.utc).isoformat(), "environment": args.environment, "source_revision": args.revision, "source_digest": args.digest, "result": args.status}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
