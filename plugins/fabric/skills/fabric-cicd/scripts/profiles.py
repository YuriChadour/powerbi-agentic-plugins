"""Versioned, fail-closed Fabric CI/CD environment profile support.

The generator historically stored four fixed entries under ``environments``.
This module is deliberately dependency-free so it can also ship with generated
release helpers.  It translates that shape once, then exposes an ordered,
validated profile registry to every caller.
"""
from __future__ import annotations

import copy
import fnmatch
import re


KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")
GUID = re.compile(r"(?i)^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
# Values end up in YAML or command arguments.  Spaces, slash, dot, star and
# brackets are legitimate names/branches; shell/YAML control characters are not.
UNSAFE = re.compile(r"[\r\n`$;&|<>!{}\[\]#'\"\\\\]")


class ProfileError(ValueError):
    pass


def _fail(key: str, field: str, message: str) -> None:
    raise ProfileError(f"profile {key}: {field} {message}")


def _text(key: str, field: str, value, *, pattern: re.Pattern | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(key, field, "is required")
    if UNSAFE.search(value):
        _fail(key, field, "contains an unsafe YAML or PowerShell metacharacter")
    if pattern and not pattern.fullmatch(value):
        _fail(key, field, "has an invalid format")
    return value


def translate_v1(setup: dict) -> dict:
    """Translate the legacy four-environment model without changing its values."""
    envs = setup.get("environments")
    if not isinstance(envs, dict):
        raise ProfileError("v1 setup: environments is required")
    required = ("DEV", "TEST", "PROD", "HOTFIX")
    missing = [key for key in required if key not in envs]
    if missing:
        raise ProfileError("v1 setup: missing environments " + ", ".join(missing))
    translated = copy.deepcopy(setup)
    profiles = {}
    for key in required:
        value = envs[key]
        profiles[key] = {
            "source_branch": value.get("branch"),
            "workspace": value.get("workspace"),
            "azure_devops": {
                "pipeline_name": value.get("pipeline_name"),
                "pipeline_yaml": value.get("pipeline_yaml"),
                "protected_environment": value.get("ado_environment"),
                "variable_group": (value.get("variable_group") or {}).get("name") if isinstance(value.get("variable_group"), dict) else value.get("variable_group"),
                "private_pool": (value.get("private_pool") or {}).get("name") if isinstance(value.get("private_pool"), dict) else value.get("private_pool"),
            },
            "credentials": {"key_vault": value.get("key_vault")},
            "deploy": {"enabled": True},
            "verification": {"manual_boundary": False},
            "promotion": {"accepts_from": ["TEST", "HOTFIX"] if key == "PROD" else []},
        }
    translated["version"] = 2
    translated["profiles"] = profiles
    return translated


def _normalize(key: str, value: dict) -> dict:
    if not isinstance(value, dict):
        _fail(key, "profile", "must be a mapping")
    _text(key, "key", key, pattern=KEY)
    workspace = value.get("workspace")
    if not isinstance(workspace, dict): _fail(key, "workspace", "is required")
    _text(key, "workspace.name", workspace.get("name"))
    capacity = workspace.get("capacity")
    if not isinstance(capacity, dict): _fail(key, "workspace.capacity", "is required")
    _text(key, "workspace.capacity.name", capacity.get("name"))
    ado = value.get("azure_devops")
    if not isinstance(ado, dict): _fail(key, "azure_devops", "is required")
    for field in ("pipeline_name", "pipeline_yaml", "protected_environment", "variable_group", "private_pool"):
        _text(key, "azure_devops." + field, ado.get(field))
    if not ado["pipeline_yaml"].startswith("cicd/fabric/") or not ado["pipeline_yaml"].endswith(".yml"):
        _fail(key, "azure_devops.pipeline_yaml", "must be under cicd/fabric and end in .yml")
    credential = (value.get("credentials") or {}).get("key_vault")
    if not isinstance(credential, dict): _fail(key, "credentials.key_vault", "is required")
    for field in ("service_connection", "name", "secret"):
        _text(key, "credentials.key_vault." + field, credential.get(field))
    deploy = value.get("deploy")
    verification = value.get("verification")
    promotion = value.get("promotion")
    if not isinstance(deploy, dict) or not isinstance(deploy.get("enabled"), bool): _fail(key, "deploy.enabled", "must be boolean")
    if not isinstance(verification, dict) or not isinstance(verification.get("manual_boundary"), bool): _fail(key, "verification.manual_boundary", "must be boolean")
    accepts = promotion.get("accepts_from") if isinstance(promotion, dict) else None
    if not isinstance(accepts, list) or not all(isinstance(source, str) and KEY.fullmatch(source) for source in accepts):
        _fail(key, "promotion.accepts_from", "must be a list of profile keys")
    result = copy.deepcopy(value)
    result["source_branch"] = _text(key, "source_branch", value.get("source_branch"))
    result["promotion"]["accepts_from"] = list(accepts)
    return result


def normalize_setup(setup: dict) -> dict:
    """Return a deterministic v2 setup, rejecting ambiguity before any write."""
    if not isinstance(setup, dict): raise ProfileError("setup must be a mapping")
    source = translate_v1(setup) if "profiles" not in setup else copy.deepcopy(setup)
    raw = source.get("profiles")
    if not isinstance(raw, dict) or not raw: raise ProfileError("profiles must be a non-empty mapping")
    seen, normalized = set(), {}
    routes, paths, protected, ownership = {}, {}, {}, {}
    for key in sorted(raw, key=str.upper):
        lowered = key.lower() if isinstance(key, str) else ""
        if lowered in seen: raise ProfileError(f"duplicate profile key: {key}")
        seen.add(lowered)
        profile = _normalize(key, raw[key])
        for label, store, candidate in (
            ("source_branch", routes, profile["source_branch"]),
            ("azure_devops.pipeline_yaml", paths, profile["azure_devops"]["pipeline_yaml"]),
            ("azure_devops.protected_environment", protected, profile["azure_devops"]["protected_environment"]),
            ("workspace", ownership, (profile["workspace"].get("id") or profile["workspace"]["name"]).lower()),
        ):
            if candidate in store: _fail(key, label, f"conflicts with profile {store[candidate]}")
            store[candidate] = key
        normalized[key] = profile
    for key, profile in normalized.items():
        unknown = [source for source in profile["promotion"]["accepts_from"] if source not in normalized]
        if unknown: _fail(key, "promotion.accepts_from", "references unknown profile " + ", ".join(unknown))
        if len(set(profile["promotion"]["accepts_from"])) != len(profile["promotion"]["accepts_from"]): _fail(key, "promotion.accepts_from", "contains duplicates")
    source["version"], source["profiles"] = 2, normalized
    return source


def profiles(setup: dict) -> dict:
    return normalize_setup(setup)["profiles"]


def legacy_environments(setup: dict) -> dict:
    """Compatibility view for generated code that still consumes legacy keys."""
    result = {}
    for key, profile in profiles(setup).items():
        ado, vault = profile["azure_devops"], profile["credentials"]["key_vault"]
        result[key] = {
            "workspace": profile["workspace"], "branch": profile["source_branch"],
            "variable_group": {"name": ado["variable_group"]}, "private_pool": {"name": ado["private_pool"]},
            "key_vault": vault, "ado_environment": ado["protected_environment"],
            "pipeline_name": ado["pipeline_name"], "pipeline_yaml": ado["pipeline_yaml"],
            "deploy": profile["deploy"], "verification": profile["verification"], "promotion": profile["promotion"],
        }
    return result


def route_branch(setup: dict, branch: str) -> tuple[str, dict]:
    matches = [(key, profile) for key, profile in profiles(setup).items() if fnmatch.fnmatchcase(branch, profile["source_branch"])]
    if len(matches) != 1:
        raise ProfileError(f"source branch '{branch}' routes to " + ("no profile" if not matches else "multiple profiles: " + ", ".join(key for key, _ in matches)))
    return matches[0]
