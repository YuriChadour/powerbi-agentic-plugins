"""Read-only repository discovery for the Fabric CI/CD lifecycle."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def git_lines(root: Path, *args: str) -> dict:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True,
            text=True, timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "unknown", "values": [], "reason": type(exc).__name__}
    if result.returncode:
        return {"status": "unknown", "values": [], "reason": "git command failed"}
    return {"status": "known", "values": sorted(line for line in result.stdout.splitlines() if line)}


def discover(root: Path) -> dict:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Repository path must be a directory")
    fabric = (root / "fabric").is_dir()
    pbi = (root / "pbi").is_dir()
    scope = "mixed" if fabric and pbi else "fabric-only" if fabric else "power-bi-only" if pbi else "unconfigured"
    cicd = root / "cicd"
    assets = sorted(str(path.relative_to(root)).replace("\\", "/") for path in cicd.rglob("*") if path.is_file() and "__pycache__" not in path.parts) if cicd.is_dir() else []
    # Folder presence is discovery evidence, never approval to deploy.
    return {
        "schema_version": 1,
        "repository": str(root),
        "scope_candidates": scope,
        "scope_approved": False,
        "source_roots": {"fabric": fabric, "power_bi": pbi},
        "existing_cicd_files": assets,
        "git_remotes": git_lines(root, "remote"),
        "local_branches": git_lines(root, "for-each-ref", "--format=%(refname:short)", "refs/heads"),
        "fabric_git_connection": {"status": "unknown", "reason": "Live connection not inspected"},
        "initial_sync_evidence": {"status": "unknown", "reason": "Requires explicit adopter evidence"},
        "target_branches": {"status": "unresolved", "reason": "Require explicit adopter mapping"},
        "next_action": "Review scope and supply target and synchronization evidence before bootstrap.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover candidate CI/CD assets without writes or credentials")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Repository root to inspect")
    args = parser.parse_args()
    try:
        report = discover(args.repo)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Discovery failed: {exc}\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
