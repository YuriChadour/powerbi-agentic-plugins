"""Approve a complete Power BI setup by recording its exact SHA-256."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

from setup_contract import load_setup, validate_setup


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blocking_problems(setup: dict) -> list[str]:
    problems = [f"open question: {question['key']}" for question in setup.get("open_questions", [])]
    problems += [f"gap: {gap.get('path', 'setup')} {gap.get('reason', '')}".strip() for gap in setup.get("gaps", [])]
    problems += [f"schema: {error}" for error in validate_setup(setup)]
    return sorted(set(problems))


def marker(path: Path) -> Path:
    return path.with_name("setup.approved")


def verify_approval(path: Path) -> dict:
    approved = marker(path)
    if not approved.exists():
        raise ValueError("setup.yml is not approved; review SETUP.md and run approve.py")
    try:
        record = json.loads(approved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("setup.approved is invalid; review SETUP.md and run approve.py again") from error
    if record.get("version") != 1 or not isinstance(record.get("sha256"), str):
        raise ValueError("setup.approved is invalid; review SETUP.md and run approve.py again")
    if record["sha256"] != digest(path):
        raise ValueError("setup.yml changed after approval; review it and run approve.py again")
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup", default="cicd/powerbi/setup.yml")
    args = parser.parse_args(argv)
    path = Path(args.setup).resolve()
    setup = load_setup(path)
    problems = blocking_problems(setup)
    if problems:
        print("Approval refused; resolve these and re-run plan:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    record = {"version": 1, "sha256": digest(path)}
    marker(path).write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Approved {path.name} ({record['sha256'][:12]}); run apply next")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
