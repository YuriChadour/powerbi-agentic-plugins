"""Compare deployment-relevant source inputs from TEST and PROD artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from zipfile import ZipFile

from release_contract import archive_source_hashes, artifact_digest, read_artifact_metadata


def compare(test_artifact: Path, prod_artifact: Path) -> dict:
    with ZipFile(test_artifact) as test_zip, ZipFile(prod_artifact) as prod_zip:
        test_hashes = archive_source_hashes(test_zip)
        prod_hashes = archive_source_hashes(prod_zip)
    test_names, prod_names = set(test_hashes), set(prod_hashes)
    added = sorted(prod_names - test_names)
    deleted = sorted(test_names - prod_names)
    modified = sorted(name for name in test_names & prod_names if test_hashes[name] != prod_hashes[name])
    return {
        "result": "PASS" if not added and not deleted and not modified else "FAIL",
        "test_artifact": test_artifact.name,
        "prod_artifact": prod_artifact.name,
        "test_artifact_sha256": artifact_digest(test_artifact),
        "prod_artifact_sha256": artifact_digest(prod_artifact),
        "test_revision": read_artifact_metadata(test_artifact).get("revision"),
        "prod_revision": read_artifact_metadata(prod_artifact).get("revision"),
        "added": added,
        "deleted": deleted,
        "modified": modified,
        "matched_file_hashes": {name: test_hashes[name] for name in sorted(test_names & prod_names) if test_hashes[name] == prod_hashes[name]},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-artifact", required=True, type=Path)
    parser.add_argument("--prod-artifact", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = compare(args.test_artifact, args.prod_artifact)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if result["result"] != "PASS":
        print("ERROR: TEST and PROD deployment-relevant source differs")
        print(json.dumps({key: result[key] for key in ("added", "deleted", "modified")}, indent=2))
        return 1
    print(f"Compared {len(result['matched_file_hashes'])} deployment-relevant source files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
