"""Record an explicitly supplied Jira key without disturbing other resume content."""

import argparse
import re
import sys
from pathlib import Path

START = "<!-- jira-current-ticket:start -->"
END = "<!-- jira-current-ticket:end -->"
KEY = re.compile(r"[A-Z]+-[0-9]+\Z")


def record(repo: Path, ticket: str) -> None:
    if not KEY.fullmatch(ticket):
        raise ValueError("Supply an uppercase Jira ticket key, for example FIN-123.")
    if not repo.is_dir():
        raise ValueError("The repository directory does not exist.")
    path = repo / "RESUME.md"
    with path.open("r", encoding="utf-8", newline="") if path.exists() else _empty() as source:
        original = source.read()
    if original.count(START) != original.count(END) or original.count(START) > 1:
        raise ValueError("Ambiguous Jira ticket markers in RESUME.md; resolve them before continuing.")
    newline = "\r\n" if "\r\n" in original else "\n"
    block = newline.join((START, f"Current Jira ticket: {ticket}", END))
    if START in original:
        start = original.index(START)
        end = original.index(END)
        if end < start:
            raise ValueError("Jira ticket markers are reversed in RESUME.md.")
        updated = original[:start] + block + original[end + len(END):]
    else:
        separator = "" if not original or original.endswith(("\n", "\r")) else newline
        updated = original + separator + block + newline
    if updated != original:
        with path.open("w", encoding="utf-8", newline="") as destination:
            destination.write(updated)


def _empty():
    from io import StringIO
    return StringIO("")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--ticket", required=True, help="Jira key provided by the user")
    args = parser.parse_args()
    try:
        record(args.repo, args.ticket)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Cannot record current ticket: {exc}", file=sys.stderr)
        return 1
    print(f"Recorded current ticket {args.ticket} in RESUME.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
