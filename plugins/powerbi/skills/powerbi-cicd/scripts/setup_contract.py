"""Versioned, secretless Power BI setup contract and deterministic serialization."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any
from uuid import UUID

import yaml

SCHEMA_VERSION = 1
CONTENT_TARGETS = {"DEV", "TEST", "PROD", "UAT", "REHEARSAL"}
OPTIONAL_TARGETS = {"UAT", "REHEARSAL"}
REQUIRED_TARGETS = {"DEV", "TEST", "PROD", "HOTFIX"}
ALLOWED_TARGETS = REQUIRED_TARGETS | OPTIONAL_TARGETS
SECRET_FIELDS = ("password", "token", "clientsecret", "client_secret", "connectionstring", "credential", "apikey", "accesskey", "access_key")
ITEM_TYPES = {"SemanticModel", "Report", "PaginatedReport"}


def dump_setup(setup: dict[str, Any]) -> str:
    """Serialize a setup contract without sorting rules, maps, or replacement values."""
    return yaml.safe_dump(setup, sort_keys=False, default_flow_style=False, allow_unicode=False, width=4096)


def load_setup(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("setup.yml must contain an object")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a completed string")
    return value


def _path(value: object, field: str) -> str:
    text = _string(value, field).replace("\\", "/")
    candidate = PurePosixPath(text)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"{field} must be a repository-relative path")
    return str(candidate)


def _guid(value: object, field: str) -> str:
    text = _string(value, field)
    try:
        parsed = UUID(text)
    except (AttributeError, ValueError) as error:
        raise ValueError(f"{field} must be a UUID") from error
    if parsed.int == 0:
        raise ValueError(f"{field} must be a nonzero UUID")
    return str(parsed)


def _secret_fields(value: object, path: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            location = f"{path}.{key}" if path else str(key)
            compact = str(key).replace("_", "").replace("-", "").casefold()
            if any(word.replace("_", "") in compact for word in SECRET_FIELDS):
                errors.append(f"{location} is a secret-bearing field and is not permitted")
            else:
                errors.extend(_secret_fields(child, location))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_secret_fields(child, f"{path}[{index}]"))
    return errors


def binding_environment(target: str) -> str:
    return "PROD" if target == "HOTFIX" else target


def validate_setup(setup: object) -> list[str]:
    """Return deterministic schema, completeness, and target consistency errors."""
    errors = _secret_fields(setup)
    try:
        if not isinstance(setup, dict):
            raise ValueError("setup must be an object")
        required = {
            "version", "repository", "tenant_id", "service_principal", "environments",
            "managed_items", "semantic_model_bindings", "connections", "roles", "excluded",
            "gaps", "answers", "open_questions", "provenance",
        }
        if set(setup) != required:
            missing = sorted(required - set(setup))
            unsupported = sorted(set(setup) - required)
            raise ValueError(f"setup has missing fields {missing} or unsupported fields {unsupported}")
        if setup["version"] != SCHEMA_VERSION:
            raise ValueError("setup version must be 1")
        _guid(setup["tenant_id"], "tenant_id")
        repository = setup["repository"]
        if not isinstance(repository, dict) or set(repository) != {
            "source_root", "ci_folder", "azure_devops", "branches"
        }:
            raise ValueError("repository shape is invalid")
        _path(repository["source_root"], "repository.source_root")
        _path(repository["ci_folder"], "repository.ci_folder")
        azure = repository["azure_devops"]
        if not isinstance(azure, dict) or set(azure) != {"organization", "project", "repository"}:
            raise ValueError("repository.azure_devops shape is invalid")
        for field in azure:
            _string(azure[field], f"repository.azure_devops.{field}")
        branches = repository["branches"]
        if not isinstance(branches, dict):
            raise ValueError("repository.branches must be an object")
        service_principal = setup["service_principal"]
        if not isinstance(service_principal, dict) or set(service_principal) != {"app_id", "object_id"}:
            raise ValueError("service_principal shape is invalid")
        _guid(service_principal["app_id"], "service_principal.app_id")
        _guid(service_principal["object_id"], "service_principal.object_id")
        environments = setup["environments"]
        if not isinstance(environments, dict) or not REQUIRED_TARGETS.issubset(environments) or set(environments) - ALLOWED_TARGETS:
            raise ValueError("environments must include DEV, TEST, PROD, HOTFIX and only supported optional targets")
        if set(branches) != set(environments):
            raise ValueError("repository.branches must map every and only configured target")
        for field in branches:
            _string(branches[field], f"repository.branches.{field}")
        for target, config in environments.items():
            expected = {
                "workspace", "capacity", "runtime_identity", "variable_group", "private_pool",
                "key_vault", "ado_environment", "pipeline_name", "pipeline_yaml", "branch",
                "target_owner", "approval_policy", "artifact_route", "verification_profile",
                "git_connected", "direct_roles",
            }
            if not isinstance(config, dict) or set(config) != expected:
                raise ValueError(f"environments.{target} has missing or unsupported fields")
            workspace = config["workspace"]
            if not isinstance(workspace, dict) or set(workspace) != {"name", "id", "create"}:
                raise ValueError(f"environments.{target}.workspace shape is invalid")
            _string(workspace["name"], f"environments.{target}.workspace.name")
            if workspace.get("id"):
                _guid(workspace["id"], f"environments.{target}.workspace.id")
            elif workspace.get("create") is not True:
                raise ValueError(f"environments.{target}.workspace is unresolved")
            capacity = config["capacity"]
            if not isinstance(capacity, dict) or set(capacity) != {"id", "name"}:
                raise ValueError(f"environments.{target}.capacity shape is invalid")
            _string(capacity["name"], f"environments.{target}.capacity.name")
            if capacity.get("id"):
                _guid(capacity["id"], f"environments.{target}.capacity.id")
            runtime = config["runtime_identity"]
            if not isinstance(runtime, dict) or set(runtime) != {"reference", "app_id", "object_id"}:
                raise ValueError(f"environments.{target}.runtime_identity shape is invalid")
            for field in runtime:
                _string(runtime[field], f"environments.{target}.runtime_identity.{field}")
            _guid(runtime["app_id"], f"environments.{target}.runtime_identity.app_id")
            _guid(runtime["object_id"], f"environments.{target}.runtime_identity.object_id")
            for field in ("variable_group", "private_pool"):
                _string(config[field], f"environments.{target}.{field}")
            key_vault = config["key_vault"]
            if not isinstance(key_vault, dict) or set(key_vault) != {"service_connection", "service_connection_id", "name", "secret_reference"}:
                raise ValueError(f"environments.{target}.key_vault shape is invalid")
            _string(key_vault["service_connection"], f"environments.{target}.key_vault.service_connection")
            if key_vault.get("service_connection_id"):
                _guid(key_vault["service_connection_id"], f"environments.{target}.key_vault.service_connection_id")
            _string(key_vault["name"], f"environments.{target}.key_vault.name")
            _string(key_vault["secret_reference"], f"environments.{target}.key_vault.secret_reference")
            for field in ("ado_environment", "pipeline_name", "pipeline_yaml", "branch", "target_owner", "approval_policy", "artifact_route", "verification_profile"):
                _string(config[field], f"environments.{target}.{field}")
            _path(config["pipeline_yaml"], f"environments.{target}.pipeline_yaml")
            if config["artifact_route"] != "immutable":
                raise ValueError(f"environments.{target}.artifact_route must be immutable")
            if config["git_connected"] is not False:
                raise ValueError(f"environments.{target}.git_connected must be false")
            if config["branch"] != branches[target]:
                raise ValueError(f"environments.{target}.branch differs from repository.branches.{target}")
            roles = config["direct_roles"]
            if not isinstance(roles, list):
                raise ValueError(f"environments.{target}.direct_roles must be a list")
            for index, role in enumerate(roles):
                if not isinstance(role, dict) or set(role) != {"object_id", "principal_type", "role"}:
                    raise ValueError(f"environments.{target}.direct_roles[{index}] shape is invalid")
                _guid(role["object_id"], f"environments.{target}.direct_roles[{index}].object_id")
                if role["principal_type"] not in {"User", "Group", "ServicePrincipal", "ServicePrincipalProfile"} or role["role"] not in {"Admin", "Member", "Contributor", "Viewer"}:
                    raise ValueError(f"environments.{target}.direct_roles[{index}] has an unsupported role")
        hotfix_workspace = environments["HOTFIX"]["workspace"]["id"]
        for content_target in ("TEST", "PROD"):
            if hotfix_workspace and hotfix_workspace == environments[content_target]["workspace"]["id"]:
                raise ValueError(f"environments.HOTFIX.workspace cannot target the {content_target} workspace")
        items = setup["managed_items"]
        if not isinstance(items, list) or not items:
            raise ValueError("managed_items must be a nonempty list")
        ids: set[str] = set()
        for index, item in enumerate(items):
            if not isinstance(item, dict) or set(item) != {"id", "type", "path", "dependencies", "binding", "substitutions"}:
                raise ValueError(f"managed_items[{index}] shape is invalid")
            identity = _string(item["id"], f"managed_items[{index}].id")
            if identity in ids:
                raise ValueError(f"managed_items[{index}].id is duplicated")
            ids.add(identity)
            if item["type"] not in ITEM_TYPES:
                raise ValueError(f"managed_items[{index}].type is unsupported")
            _path(item["path"], f"managed_items[{index}].path")
            if not isinstance(item["dependencies"], list):
                raise ValueError(f"managed_items[{index}].dependencies must be a list")
            for dependency in item["dependencies"]:
                _string(dependency, f"managed_items[{index}].dependencies")
            binding = item["binding"]
            if item["type"] == "PaginatedReport":
                if not isinstance(binding, dict) or set(binding) != {"kind", "target"} or binding["kind"] not in {"semantic_model", "data_source"}:
                    raise ValueError(f"managed_items[{index}].binding is invalid")
                _string(binding["target"], f"managed_items[{index}].binding.target")
            elif binding is not None:
                raise ValueError(f"managed_items[{index}].binding is only valid for PaginatedReport")
            substitutions = item["substitutions"]
            if not isinstance(substitutions, dict) or set(substitutions) != {"rules"} or not isinstance(substitutions["rules"], list):
                raise ValueError(f"managed_items[{index}].substitutions shape is invalid")
            for rule_index, rule in enumerate(substitutions["rules"]):
                if not isinstance(rule, dict) or set(rule) != {"type", "path", "find", "values"} or rule["type"] != "find_replace":
                    raise ValueError(f"managed_items[{index}].substitutions.rules[{rule_index}] is invalid")
                _path(rule["path"], f"managed_items[{index}].substitutions.rules[{rule_index}].path")
                _string(rule["find"], f"managed_items[{index}].substitutions.rules[{rule_index}].find")
                values = rule["values"]
                required_values = set(environments) - {"HOTFIX"}
                if not isinstance(values, dict) or set(values) != required_values:
                    raise ValueError(f"managed_items[{index}].substitutions.rules[{rule_index}] values must map every content environment and omit HOTFIX")
                for env, replacement in values.items():
                    if not isinstance(replacement, str):
                        raise ValueError(f"managed_items[{index}].substitutions.rules[{rule_index}].values.{env} must remain a string")
        item_by_id = {item["id"]: item for item in items}
        for identity, item in item_by_id.items():
            for dependency in item["dependencies"]:
                if dependency not in item_by_id or dependency == identity:
                    raise ValueError(f"managed item {identity} has unresolved dependency {dependency}")
            if item["type"] == "Report" and not any(item_by_id[d]["type"] == "SemanticModel" for d in item["dependencies"]):
                raise ValueError(f"report {identity} must depend on a semantic model")
            if item["type"] == "PaginatedReport" and item["binding"]["kind"] == "semantic_model" and item["binding"]["target"] not in item_by_id:
                raise ValueError(f"paginated report {identity} has an unresolved binding")
        bindings = setup["semantic_model_bindings"]
        model_ids = {item["id"] for item in items if item["type"] == "SemanticModel"}
        if not isinstance(bindings, dict) or set(bindings) != model_ids:
            raise ValueError("semantic_model_bindings must map every and only semantic model")
        for identity, target_map in bindings.items():
            required_maps = set(environments) - {"HOTFIX"}
            if not isinstance(target_map, dict) or set(target_map) != required_maps:
                raise ValueError(f"semantic_model_bindings.{identity} must map every content environment and omit HOTFIX")
            for target, connection_ids in target_map.items():
                if not isinstance(connection_ids, list) or not connection_ids:
                    raise ValueError(f"semantic_model_bindings.{identity}.{target} must be a nonempty list")
                normalized = [_guid(connection_id, f"semantic_model_bindings.{identity}.{target}") for connection_id in connection_ids]
                if len(set(normalized)) != len(normalized):
                    raise ValueError(f"semantic_model_bindings.{identity}.{target} contains duplicates")
        if not isinstance(setup["connections"], list):
            raise ValueError("connections must be a list")
        connection_ids: set[str] = set()
        for index, connection in enumerate(setup["connections"]):
            if not isinstance(connection, dict) or set(connection) != {"id", "display_name", "required_permission"}:
                raise ValueError(f"connections[{index}] shape is invalid")
            connection_id = _guid(connection["id"], f"connections[{index}].id")
            if connection_id in connection_ids:
                raise ValueError(f"connections[{index}] duplicates connection {connection_id}")
            connection_ids.add(connection_id)
            _string(connection["display_name"], f"connections[{index}].display_name")
            _string(connection["required_permission"], f"connections[{index}].required_permission")
        referenced_connections = {
            str(connection_id)
            for values in bindings.values()
            for connection_ids_for_target in values.values()
            for connection_id in connection_ids_for_target
        }
        if referenced_connections - connection_ids:
            raise ValueError("semantic model bindings reference an unlisted connection")
        if not isinstance(setup["roles"], list) or not isinstance(setup["excluded"], list):
            raise ValueError("roles and excluded must be lists")
        if not isinstance(setup["provenance"], dict) or not isinstance(setup["answers"], dict):
            raise ValueError("provenance and answers must be objects")
        for key, value in setup["provenance"].items():
            if value not in {"discovered", "assumed", "user", "generated"}:
                raise ValueError(f"provenance.{key} has unsupported source {value}")
        if not isinstance(setup["gaps"], list) or not isinstance(setup["open_questions"], list):
            raise ValueError("gaps and open_questions must be lists")
    except (KeyError, TypeError, ValueError) as error:
        errors.append(str(error))
    return sorted(set(errors))
