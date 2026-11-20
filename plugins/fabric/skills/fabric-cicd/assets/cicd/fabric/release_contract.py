"""Shared, secretless release-contract helpers (standard library only)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

GENERATED_ARTIFACT_FILES = {"managed-manifest.json", "content-hashes.json", "release-metadata.json"}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def deployment_relevant_names(names: set[str]) -> set[str]:
    return {
        name
        for name in names
        if (name.startswith("fabric/") or name.startswith("cicd/fabric/"))
        and name not in GENERATED_ARTIFACT_FILES
        and "/__pycache__/" not in name
        and not name.endswith(".pyc")
    }


def archive_source_hashes(archive: ZipFile) -> dict[str, str]:
    hashes = json.loads(archive.read("content-hashes.json"))
    if not isinstance(hashes, dict):
        raise ValueError("content-hashes.json must be an object")
    return {
        name: value
        for name, value in hashes.items()
        if name in deployment_relevant_names(set(hashes))
    }


def artifact_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_artifact_metadata(path: Path) -> dict:
    with ZipFile(path) as archive:
        metadata = json.loads(archive.read("release-metadata.json"))
        if not isinstance(metadata, dict):
            raise ValueError("release-metadata.json must be an object")
        return metadata


def workspace_contract(manifest: dict, environment: str) -> dict:
    profiles = manifest.get("profiles")
    if isinstance(profiles, dict):
        profile = profiles.get(environment)
        workspace = profile.get("workspace") if isinstance(profile, dict) else None
        if not isinstance(workspace, dict) or not workspace.get("id") or not workspace.get("name"):
            raise ValueError(f"missing {environment} workspace contract")
        return workspace
    workspace = manifest.get(f"{environment.lower()}_workspace")
    if not isinstance(workspace, dict) or not workspace.get("id") or not workspace.get("name"):
        raise ValueError(f"missing {environment} workspace contract")
    return workspace
