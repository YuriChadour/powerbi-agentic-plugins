"""Re-verify and deploy a release artifact from its protected extracted root.

Standard library only. The release YAML verifies archive paths and hashes with
inline PowerShell before extraction; this module repeats the trust checks from
within the extracted package before any target write.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

from release_contract import workspace_contract


def archive_members(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    """Reject duplicate, symlink, absolute, and traversal archive members."""
    members: dict[str, zipfile.ZipInfo] = {}
    for info in archive.infolist():
        if info.is_dir():
            continue
        name = info.filename
        posix_path = PurePosixPath(name)
        if (
            not name
            or "\\" in name
            or posix_path.is_absolute()
            or PureWindowsPath(name).is_absolute()
            or ".." in posix_path.parts
            or name != str(posix_path)
            or stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK
        ):
            raise SystemExit(f"unsafe archive member: {name!r}")
        if name in members:
            raise SystemExit(f"duplicate archive member: {name!r}")
        members[name] = info
    return members


def verify_archive(artifact: Path, expected_revision: str | None, expected_environment: str, expected_lakehouse: str | None = None, artifact_target: str | None = None) -> tuple[dict[str, zipfile.ZipInfo], dict]:
    artifact_target = artifact_target or expected_environment
    with zipfile.ZipFile(artifact) as archive:
        members = archive_members(archive)
        try:
            hashes = json.loads(archive.read("content-hashes.json"))
            manifest = json.loads(archive.read("managed-manifest.json"))
            metadata = json.loads(archive.read("release-metadata.json"))
        except KeyError as exc:
            raise SystemExit(f"release artifact is missing required file: {exc}") from exc
        if not isinstance(hashes, dict):
            raise SystemExit("content-hashes.json must be an object")
        if set(hashes) != set(members) - {"content-hashes.json"}:
            raise SystemExit("artifact content-hash manifest does not match packaged files")
        for name, expected_hash in hashes.items():
            if not isinstance(expected_hash, str) or hashlib.sha256(archive.read(members[name])).hexdigest() != expected_hash:
                raise SystemExit(f"artifact content hash mismatch: {name}")
        if expected_lakehouse:
            try:
                contract = json.loads(archive.read("target-contract.json"))
            except KeyError as exc:
                raise SystemExit("release artifact is missing target-contract.json") from exc
            if (contract.get("lakehouse") or {}).get("id") != expected_lakehouse:
                raise SystemExit("artifact Lakehouse does not match the approved target contract")
    if expected_revision and manifest.get("revision") != expected_revision:
        raise SystemExit("artifact revision does not match the trusted merged revision")
    if manifest.get("artifact_target") != artifact_target or metadata.get("artifact_target") != artifact_target:
        raise SystemExit("artifact target does not match the expected build environment")
    try:
        workspace_contract(manifest, expected_environment)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    return members, manifest


def extract_verified(artifact: Path, destination: Path, members: dict[str, zipfile.ZipInfo]) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(artifact) as archive:
        for name, info in members.items():
            target = (root / name).resolve()
            if root not in target.parents:
                raise SystemExit(f"unsafe archive member: {name!r}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
    return root


def verify_extracted(root: Path, members: dict[str, zipfile.ZipInfo]) -> None:
    actual_files = {
        str(path.relative_to(root)).replace("\\", "/")
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    if actual_files != set(members):
        raise SystemExit("extracted artifact content does not match the verified archive")


def deploy(root: Path, environment: str, approved_app_id: str, expected_workspace: str) -> None:
    if os.environ.get(f"ALLOW_FABRIC_{environment}_WRITE") != "true":
        raise SystemExit(f"{environment} write guard not enabled")
    print(f"{environment} write guard enabled; deploying the verified extracted artifact")
    subprocess.run(
        [
            sys.executable, str(root / "cicd" / "fabric" / "deploy_runner.py"),
            "--config", str(root / "cicd" / "fabric" / "config.yml"),
            "--environment", environment,
            "--approved-app-id", approved_app_id,
            "--expected-workspace", expected_workspace,
        ],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--expected-revision")
    parser.add_argument("--artifact-target", help="configured profile that built the artifact; defaults to --environment")
    parser.add_argument("--expected-lakehouse", help="required Lakehouse ID from the approved target contract")
    parser.add_argument("--extract-to")
    parser.add_argument("--extracted-root")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.extract_to and args.extracted_root:
        raise SystemExit("use either --extract-to or --extracted-root, not both")

    artifact = Path(args.artifact).resolve()
    members, manifest = verify_archive(artifact, args.expected_revision, args.environment, args.expected_lakehouse, args.artifact_target)
    print(f"Verified immutable artifact revision {manifest['revision']} with {len(manifest['managed_items'])} managed items")
    if args.extract_to:
        extract_verified(artifact, Path(args.extract_to), members)
        return
    approved_app_id = manifest.get("deployment_identity", {}).get("app_id")
    if not isinstance(approved_app_id, str) or not approved_app_id:
        raise SystemExit("release artifact does not declare an approved service-principal application ID")
    expected_workspace = workspace_contract(manifest, args.environment)["id"]
    if args.extracted_root:
        root = Path(args.extracted_root).resolve()
        verify_extracted(root, members)
        if not args.verify_only:
            deploy(root, args.environment, approved_app_id, expected_workspace)
        return
    with tempfile.TemporaryDirectory() as directory:
        root = extract_verified(artifact, Path(directory), members)
        if not args.verify_only:
            deploy(root, args.environment, approved_app_id, expected_workspace)


if __name__ == "__main__":
    main()
