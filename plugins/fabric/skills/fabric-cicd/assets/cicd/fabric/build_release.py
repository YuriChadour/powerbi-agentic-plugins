"""Build an immutable release bundle from the checked-out revision."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

from release_contract import artifact_digest, deployment_relevant_names
from profile_loader import profile_keys


def revision(root: Path) -> str:
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def file_hashes(staging: Path) -> dict[str, str]:
    return {
        str(path.relative_to(staging)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(staging.rglob("*"))
        if path.is_file()
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--validation", default="artifacts/managed-manifest.json")
    parser.add_argument("--out", default="artifacts/release.zip")
    parser.add_argument("--target", required=True)
    parser.add_argument("--expected-revision")
    args = parser.parse_args()

    root, out = Path(args.root).resolve(), Path(args.out).resolve()
    data = json.loads((root / args.validation).resolve().read_text(encoding="utf-8"))
    if args.target not in profile_keys(data):
        raise SystemExit(f"target '{args.target}' is not a configured profile")
    data["revision"] = revision(root)
    data["artifact_target"] = args.target
    if args.expected_revision and data["revision"] != args.expected_revision:
        raise SystemExit(f"checked-out revision {data['revision']} does not match expected revision {args.expected_revision}")

    staging = out.parent / "release-staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(root / "fabric", staging / "fabric", ignore=ignore)
    shutil.copytree(root / "cicd" / "fabric", staging / "cicd" / "fabric", ignore=ignore)
    (staging / "managed-manifest.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    hashes = file_hashes(staging)
    source_hashes = {name: value for name, value in hashes.items() if name in deployment_relevant_names(set(hashes))}
    (staging / "release-metadata.json").write_text(
        json.dumps(
            {"artifact_target": args.target, "revision": data["revision"], "source_hashes": source_hashes, "managed_manifest": "managed-manifest.json"},
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    (staging / "content-hashes.json").write_text(json.dumps(file_hashes(staging), indent=2) + "\n", encoding="utf-8")

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(staging))
    print(f"Release artifact: {out}")
    print(f"Revision: {data['revision']}")
    print(f"Artifact SHA-256: {artifact_digest(out)}")


if __name__ == "__main__":
    main()
