"""Fail CI on committed credentials or accidental data exports without echoing values."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


DATA_EXTENSIONS = {".parquet", ".csv", ".delta", ".xlsx", ".zip", ".bak", ".db", ".sqlite", ".pbix"}
TOKEN_PATTERNS = (
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b", re.IGNORECASE),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_.-]+", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----", re.IGNORECASE),
)
ASSIGNMENT = re.compile(
    r"(?im)^\s*[A-Za-z0-9_.-]*(?:password|secret|token|api[_-]?key|connection[_-]?string)[A-Za-z0-9_.-]*\s*[:=]\s*['\"]?([^\s'\"#]{8,})"
)
PLACEHOLDER = re.compile(r"^(?:\$\([A-Za-z0-9_. -]+\)|\$\{[^}]+\}|<[^>]+>)$")
SAFE_RUNTIME_REFERENCE = re.compile(r"^(?:os\.environ(?:\.get)?\[?|[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\()")
# AzureKeyVault@2 uses this field for a non-secret Key Vault object name. Remove
# only that complete YAML field before applying generic assignment detection.
KEY_VAULT_SECRET_FILTER = re.compile(
    r"(?im)^\s*SecretsFilter\s*:\s*['\"]?[A-Za-z0-9][A-Za-z0-9-]{0,127}['\"]?\s*$"
)
# Generated setup manifests declare the Key Vault object name under a key_vault
# block. It is metadata, not a credential. Do not exempt arbitrary `secret:`
# assignments: only remove this exact declarative configuration shape.
KEY_VAULT_REFERENCE_BLOCK = re.compile(
    r"(?im)^(?P<indent>[ \t]*)key_vault\s*:\s*(?:&[A-Za-z0-9_-]+\s*)?\r?\n"
    r"(?P<body>(?:(?P=indent)[ \t]+(?:name|service_connection)\s*:[^\r\n]*\r?\n)*)"
    r"(?P<secret>(?P=indent)[ \t]+secret\s*:\s*[A-Za-z0-9][A-Za-z0-9-]{0,127}\s*$)"
)
EXCLUDED_PARTS = {".git", "__pycache__", "artifacts", "tmp", "node_modules"}


def contains_secret(text: str) -> bool:
    if any(pattern.search(text) for pattern in TOKEN_PATTERNS):
        return True
    text = KEY_VAULT_SECRET_FILTER.sub("", text)
    text = KEY_VAULT_REFERENCE_BLOCK.sub(
        lambda match: f"{match.group('indent')}key_vault:\n{match.group('body')}",
        text,
    )
    return any(
        not PLACEHOLDER.fullmatch(value) and not SAFE_RUNTIME_REFERENCE.match(value)
        for value in ASSIGNMENT.findall(text)
    )


def scan(root: Path) -> list[Path]:
    findings: list[Path] = []
    for scope in ("fabric", "pbi", "cicd"):
        directory = root / scope
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or any(part in EXCLUDED_PARTS for part in path.parts):
                continue
            relative = path.relative_to(root)
            if path.suffix.lower() in DATA_EXTENSIONS:
                findings.append(relative)
                continue
            if contains_secret(path.read_text(encoding="utf-8", errors="ignore")):
                findings.append(relative)
    return findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--verify-synthetic-fixture", action="store_true")
    parser.add_argument("--exercise-synthetic-fixture", action="store_true")
    args = parser.parse_args()
    synthetic_fixture = "client" + "_secret=" + "synthetic-secret-value-for-scanner"
    synthetic_detected = contains_secret(synthetic_fixture)
    if args.verify_synthetic_fixture and not synthetic_detected:
        raise SystemExit("synthetic secret fixture was not detected")
    if args.exercise_synthetic_fixture:
        if synthetic_detected:
            print("ERROR: credential-like content detected in synthetic fixture", file=sys.stderr)
            raise SystemExit(1)
        raise SystemExit("synthetic secret fixture was not detected")
    findings = scan(Path(args.root).resolve())
    for path in findings:
        print(f"ERROR: credential-like content or data export detected in {path}", file=sys.stderr)
    if findings:
        raise SystemExit(1)
    print("Repository secret and data-export scan passed")


if __name__ == "__main__":
    main()
