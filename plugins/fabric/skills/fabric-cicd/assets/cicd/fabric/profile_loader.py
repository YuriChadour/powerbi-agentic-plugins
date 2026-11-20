"""Shared, fail-closed runtime profile registry for generated CI/CD files."""
from __future__ import annotations

import json
from pathlib import Path

import yaml


def load_manifest(path: str | Path) -> dict:
    path = Path(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8")) if path.suffix == ".json" else yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        raise SystemExit(f"cannot read approved profile manifest {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"approved profile manifest {path} must be a mapping")
    return value


def profile_keys(manifest: dict) -> tuple[str, ...]:
    profiles = manifest.get("profiles")
    if isinstance(profiles, dict) and profiles:
        return tuple(profiles)
    keys = tuple(manifest.get("environments", ()))
    if keys:
        return keys
    raise SystemExit("approved manifest has no configured profiles")


def profile(manifest: dict, key: str) -> dict:
    profiles = manifest.get("profiles")
    if isinstance(profiles, dict) and key in profiles and isinstance(profiles[key], dict):
        return profiles[key]
    if key in profile_keys(manifest):
        workspace = manifest.get(f"{key.lower()}_workspace")
        if isinstance(workspace, dict):
            return {"workspace": workspace}
    raise SystemExit(f"profile '{key}' is not configured")


def workspace(manifest: dict, key: str) -> dict:
    value = profile(manifest, key).get("workspace")
    if not isinstance(value, dict) or not isinstance(value.get("id"), str) or not value.get("id"):
        raise SystemExit(f"profile '{key}' has no fixed workspace identity")
    return value
