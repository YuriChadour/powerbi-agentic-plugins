"""Validate protected runtime identity presence without emitting secret values."""
from __future__ import annotations

import argparse
import os


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--identity-reference", required=True)
    args = parser.parse_args()
    if not args.identity_reference.strip():
        raise SystemExit("a configured protected identity reference is required")
    # Secrets are resolved only by the trusted pipeline.  This check proves
    # their presence but intentionally never prints them.
    missing = [name for name in ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET") if not os.getenv(name)]
    if missing:
        raise SystemExit("protected deployment identity is unavailable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
