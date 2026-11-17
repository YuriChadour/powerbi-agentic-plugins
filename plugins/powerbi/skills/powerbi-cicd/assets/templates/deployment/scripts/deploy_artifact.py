"""Verify a release artifact before a protected deployment stage."""
from __future__ import annotations
import argparse
from pathlib import Path
from powerbi_cicd import check_artifact
parser = argparse.ArgumentParser()
parser.add_argument('--artifact', type=Path, required=True)
parser.add_argument('--target', required=True)
parser.add_argument('--revision')
parser.add_argument('--digest')
parser.add_argument('--test-digest')
if __name__ == '__main__':
    a = parser.parse_args(); result = check_artifact(a.artifact, a.target, a.revision, a.digest, a.test_digest); raise SystemExit(0 if result['status'] == 'verified' else 2)
