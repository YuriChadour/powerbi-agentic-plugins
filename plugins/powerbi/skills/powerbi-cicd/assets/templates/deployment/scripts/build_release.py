"""Build the configured immutable Power BI release artifact.

This wrapper is packaged with every release; it has no adopter-specific
source root, artifact name, target, or identity defaults.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from powerbi_cicd import load_object, package

parser = argparse.ArgumentParser()
parser.add_argument('--config', type=Path, required=True)
parser.add_argument('--manifest', type=Path, required=True)
parser.add_argument('--repo', type=Path, required=True)
parser.add_argument('--target', required=True)
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--revision', required=True)
if __name__ == '__main__':
    a = parser.parse_args()
    package(a.repo, load_object(a.config, 'configuration'), load_object(a.manifest, 'manifest'), a.target, a.out, a.revision)
