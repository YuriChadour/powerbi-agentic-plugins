"""Approve a reviewed setup.yml by recording its SHA-256; refuse while anything blocking remains."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import yaml


def blocking_problems(setup: dict) -> list[str]:
    problems = [f"open question: {q['key']}" for q in setup.get("open_questions", [])]
    problems += [f"gap: {g.get('file') or g.get('item')} {g.get('guid', '')}".strip() for g in setup.get("gaps", [])]
    problems += [f"unacknowledged overwrite: {path}" for path in setup.get("unacknowledged_overwrites", [])]
    if not setup.get("tenant_id"):
        problems.append("tenant_id is missing")
    if not setup.get("service_principal", {}).get("object_id"):
        problems.append("service principal object ID is missing")
    ado = setup.get("repository", {}).get("azure_devops", {})
    if not all(ado.get(key) for key in ("organization", "project", "repository")):
        problems.append("Azure DevOps organization, project and repository are required")
    for env, config in setup.get("environments", {}).items():
        workspace = config["workspace"]
        if not workspace.get("id") and not workspace.get("create"):
            problems.append(f"{env} workspace is unresolved")
        if not (workspace.get("capacity") or {}).get("id"):
            problems.append(f"{env} capacity is unresolved")
    return problems


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup", default="cicd/fabric/setup.yml")
    args = parser.parse_args(argv)
    path = Path(args.setup).resolve()
    problems = blocking_problems(yaml.safe_load(path.read_text(encoding="utf-8")))
    if problems:
        print("Approval refused; resolve these and re-run plan:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    path.with_name("setup.approved").write_text(digest(path) + "\n", encoding="utf-8")
    print(f"Approved {path.name} ({digest(path)[:12]}); run apply next")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
