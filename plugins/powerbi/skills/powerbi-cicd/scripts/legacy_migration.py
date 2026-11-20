"""Import explicit, validated legacy Power BI CI/CD inputs into setup.yml."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from powerbi_cicd import validate_config, validate_manifest


def _load(path: Path, label: str) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return None, [{"path": f"legacy.{label}", "reason": f"Cannot import {path.name}: {error}"}]
    if not isinstance(value, dict):
        return None, [{"path": f"legacy.{label}", "reason": f"{path.name} must contain a JSON object"}]
    return value, []


def _same_or_gap(setup: dict[str, Any], path: str, value: object) -> bool:
    target: object = setup
    keys = path.split(".")
    for key in keys[:-1]:
        target = target[key]
    current = target[keys[-1]]  # type: ignore[index]
    if current in (None, "", [], {}) or path.endswith(".id") and str(current).strip() == "":
        target[keys[-1]] = copy.deepcopy(value)  # type: ignore[index]
        return True
    if current != value:
        setup["gaps"].append({"path": path, "reason": f"Legacy value conflicts with the current reviewed or discovered value ({current!r} != {value!r})"})
        return False
    return True


def import_legacy(setup: dict[str, Any], config_path: Path | None, manifest_path: Path | None) -> dict[str, Any]:
    """Merge legacy compatibility inputs without mutating either source file."""
    if config_path is None and manifest_path is None:
        return setup
    config, config_load = _load(config_path, "config") if config_path else (None, [])
    manifest, manifest_load = _load(manifest_path, "manifest") if manifest_path else (None, [])
    setup["gaps"].extend(config_load)
    setup["gaps"].extend(manifest_load)
    if (config_path and config is None) or (manifest_path and manifest is None):
        return setup

    problems: list[str] = []
    if config is not None:
        problems.extend(validate_config(config))
    if manifest is not None:
        source_root = config.get("repository", {}).get("powerbi_source_folder") if config else setup["repository"]["source_root"]
        problems.extend(validate_manifest(manifest, source_root))
    if problems:
        setup["gaps"].extend({"path": "legacy", "reason": f"Legacy input is not safe to import: {problem}"} for problem in problems)
        return setup

    if config is not None:
        repository = config["repository"]
        _same_or_gap(setup, "repository.source_root", repository["powerbi_source_folder"])
        _same_or_gap(setup, "repository.ci_folder", repository["ci_folder"])
        azure = config["azure_devops"]
        for field in azure:
            _same_or_gap(setup, f"repository.azure_devops.{field}", azure[field])
        branches = {"DEV": repository["dev_branch"], **{target: value["source_branch"] for target, value in config["pipelines"].items()}}
        for target, branch in branches.items():
            if target in setup["environments"]:
                _same_or_gap(setup, f"repository.branches.{target}", branch)
                _same_or_gap(setup, f"environments.{target}.branch", branch)
        dev = config["dev_workspace"]
        _same_or_gap(setup, "environments.DEV.workspace.name", dev["workspace_name"])
        _same_or_gap(setup, "environments.DEV.workspace.id", dev["workspace_id"])
        for target, target_config in config["targets"].items():
            if target not in setup["environments"]:
                setup["gaps"].append({"path": f"environments.{target}", "reason": "Legacy target is not selected for this plan"})
                continue
            environment = setup["environments"][target]
            _same_or_gap(setup, f"environments.{target}.workspace.name", target_config["workspace_name"])
            _same_or_gap(setup, f"environments.{target}.workspace.id", target_config["workspace_id"])
            _same_or_gap(setup, f"environments.{target}.capacity.name", target_config["capacity_name"])
            _same_or_gap(setup, f"environments.{target}.ado_environment", target_config["environment"])
            _same_or_gap(setup, f"environments.{target}.pipeline_name", target_config["pipeline_name"])
            _same_or_gap(setup, f"environments.{target}.target_owner", target_config["target_owner"])
            _same_or_gap(setup, f"environments.{target}.approval_policy", target_config["approval_policy"])
            _same_or_gap(setup, f"environments.{target}.artifact_route", target_config["artifact_route"])
            _same_or_gap(setup, f"environments.{target}.verification_profile", target_config["verification_profile"])
            environment["git_connected"] = False
        for target, pipeline in config["pipelines"].items():
            if target in setup["environments"]:
                _same_or_gap(setup, f"environments.{target}.pipeline_name", pipeline["name"])
                _same_or_gap(setup, f"environments.{target}.pipeline_yaml", pipeline["yaml_path"])
        for target, resource in config["protected_resources"].items():
            if target in setup["environments"]:
                _same_or_gap(setup, f"environments.{target}.runtime_identity.reference", resource["identity_reference"])

    if manifest is not None:
        current_items = {item["id"]: item for item in setup["managed_items"]}
        legacy_items = []
        for item in manifest["items"]:
            current = current_items.get(item["id"])
            imported = {
                "id": item["id"], "type": item["type"], "path": item["path"],
                "dependencies": copy.deepcopy(item["dependencies"]),
                "binding": copy.deepcopy(item.get("binding")),
                "substitutions": {"rules": copy.deepcopy(item.get("substitutions", {}).get("rules", []))},
            }
            if current is None:
                setup["gaps"].append({"path": f"managed_items.{item['id']}", "reason": "Legacy managed item was not discovered under the approved source boundary"})
            elif any(current.get(key) != imported.get(key) for key in ("type", "path", "dependencies", "binding")):
                setup["gaps"].append({"path": f"managed_items.{item['id']}", "reason": "Legacy item identity or dependency mapping conflicts with source discovery"})
            legacy_items.append(imported)
        if len(legacy_items) == len(current_items):
            setup["managed_items"] = legacy_items
        setup["semantic_model_bindings"] = copy.deepcopy(manifest["semantic_model_bindings"])
        existing_ids = {connection["id"] for connection in setup["connections"]}
        for model_values in manifest["semantic_model_bindings"].values():
            for connection_ids in model_values.values():
                for connection_id in connection_ids:
                    if connection_id not in existing_ids:
                        setup["connections"].append({"id": connection_id, "display_name": f"Legacy connection {connection_id}", "required_permission": "User"})
                        existing_ids.add(connection_id)
        setup["excluded"] = copy.deepcopy(manifest["excluded"])
        imported_questions = {
            question["key"] for question in setup["open_questions"]
            if question["key"].startswith("binding.") or question["key"].startswith("connection_name.")
        }
        setup["open_questions"] = [question for question in setup["open_questions"] if question["key"] not in imported_questions]

    setup["provenance"]["legacy_inputs"] = "generated"
    return setup
