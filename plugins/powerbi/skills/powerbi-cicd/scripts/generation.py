"""Deterministically generate the retained Power BI release inputs from setup.yml."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

SKILL = Path(__file__).resolve().parents[1]
TEMPLATES = SKILL / "assets" / "templates"
DEPLOYMENT = TEMPLATES / "deployment"
RELEASE_TARGETS = ("TEST", "PROD", "HOTFIX", "UAT", "REHEARSAL")


def _json(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def compatibility_config(setup: dict[str, Any]) -> dict[str, Any]:
    repository = setup["repository"]
    dev = setup["environments"]["DEV"]
    targets = {}
    for target in RELEASE_TARGETS:
        if target not in setup["environments"]:
            continue
        environment = setup["environments"][target]
        targets[target] = {
            "workspace_name": environment["workspace"]["name"],
            "workspace_id": environment["workspace"]["id"],
            "capacity_name": environment["capacity"]["name"],
            "target_owner": environment["target_owner"],
            "environment": environment["ado_environment"],
            "pipeline_name": environment["pipeline_name"],
            "approval_policy": environment["approval_policy"],
            "artifact_route": environment["artifact_route"],
            "verification_profile": environment["verification_profile"],
            "git_connected": False,
        }
    return {
        "version": 1,
        "repository": {
            "powerbi_source_folder": repository["source_root"],
            "ci_folder": repository["ci_folder"],
            "dev_branch": repository["branches"]["DEV"],
            "prod_branch": repository["branches"]["PROD"],
        },
        "azure_devops": dict(repository["azure_devops"]),
        "dev_workspace": {
            "workspace_name": dev["workspace"]["name"],
            "workspace_id": dev["workspace"]["id"],
            "git_connected": True,
        },
        "targets": targets,
        "roles": [
            {"target": role["target"], "object_id": role["object_id"], "principal_type": role["principal_type"], "role": role["role"]}
            for role in setup["roles"] if role["target"] in setup["environments"]
        ],
        "pipelines": {
            target: {
                "name": setup["environments"][target]["pipeline_name"],
                "yaml_path": setup["environments"][target]["pipeline_yaml"],
                "source_branch": setup["environments"][target]["branch"],
            }
            for target in ("DEV", "TEST", "PROD", "HOTFIX", "UAT", "REHEARSAL") if target in setup["environments"]
        },
        "protected_resources": {
            target: {
                "identity_reference": setup["environments"][target]["runtime_identity"]["reference"],
                "write_guard": f"ALLOW_POWERBI_{target}_WRITE",
            }
            for target in setup["environments"]
        },
    }


def compatibility_manifest(setup: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": 1,
        "source_root": setup["repository"]["source_root"],
        "items": [
            {
                "id": item["id"],
                "type": item["type"],
                "path": item["path"],
                "dependencies": list(item["dependencies"]),
                **({"binding": dict(item["binding"])} if item["binding"] is not None else {}),
                "substitutions": {"rules": [dict(rule) for rule in item["substitutions"]["rules"]]},
            }
            for item in setup["managed_items"]
        ],
        "semantic_model_bindings": {
            model: {target: list(connection_ids) for target, connection_ids in values.items()}
            for model, values in setup["semantic_model_bindings"].items()
        },
        "excluded": [dict(item) for item in setup["excluded"]],
    }


def bindings_document(setup: dict[str, Any]) -> dict[str, Any]:
    rdl = [
        {"item": item["id"], **item["binding"]}
        for item in setup["managed_items"] if item["type"] == "PaginatedReport"
    ]
    return {
        "version": 1,
        "semantic_models": compatibility_manifest(setup)["semantic_model_bindings"],
        "paginated_reports": rdl,
        "connections": [dict(connection) for connection in setup["connections"]],
        "hotfix_content_environment": "PROD",
    }


def pipeline_text(setup: dict[str, Any]) -> str:
    ci_folder = setup["repository"]["ci_folder"].rstrip("/")
    template = (TEMPLATES / "deployment" / "azure-pipelines.yml").read_text(encoding="utf-8")
    template = template.replace("cicd/powerbi/bootstrap-config.json", f"{ci_folder}/bootstrap-config.json")
    template = template.replace("cicd/powerbi/powerbi-assets.yml", f"{ci_folder}/powerbi-assets.yml")
    template = template.replace("deployment/scripts/", f"{ci_folder}/deployment/scripts/")
    template = template.replace("templates/deploy-stage.yml", f"{ci_folder}/deployment/templates/deploy-stage.yml")
    configured = set(setup["environments"])
    if "HOTFIX" not in configured:
        raise ValueError("HOTFIX environment is required")
    return template.replace("\r\n", "\n")


def validation_text(setup: dict[str, Any]) -> str:
    ci_folder = setup["repository"]["ci_folder"].rstrip("/")
    text = (TEMPLATES / "powerbi-validation.yml").read_text(encoding="utf-8")
    return text.replace("cicd/powerbi-bootstrap.json", f"{ci_folder}/bootstrap-config.json").replace("cicd/powerbi-assets.yml", f"{ci_folder}/powerbi-assets.yml").replace("scripts/powerbi_cicd.py", f"{ci_folder}/scripts/powerbi_cicd.py")


def generated_files(setup: dict[str, Any]) -> dict[str, str]:
    ci_folder = setup["repository"]["ci_folder"].rstrip("/")
    files: dict[str, str] = {
        f"{ci_folder}/bootstrap-config.json": _json(compatibility_config(setup)),
        f"{ci_folder}/powerbi-assets.yml": _json(compatibility_manifest(setup)),
        f"{ci_folder}/bindings.yml": yaml.safe_dump(bindings_document(setup), sort_keys=False, default_flow_style=False),
        f"{ci_folder}/azure-pipelines.yml": pipeline_text(setup),
        f"{ci_folder}/powerbi-validation.yml": validation_text(setup),
        f"{ci_folder}/scripts/powerbi_cicd.py": (SKILL / "scripts" / "powerbi_cicd.py").read_text(encoding="utf-8"),
        f"{ci_folder}/scripts/deploy_adapter.py": (SKILL / "scripts" / "deploy_adapter.py").read_text(encoding="utf-8"),
    }
    for source in sorted(
        path for path in DEPLOYMENT.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix.casefold() not in {".pyc", ".pyo"}
    ):
        relative = source.relative_to(DEPLOYMENT).as_posix()
        files[f"{ci_folder}/deployment/{relative}"] = source.read_text(encoding="utf-8")
    return dict(sorted(files.items()))


def write_files(repo: Path, files: dict[str, str]) -> list[str]:
    changed: list[str] = []
    for relative, content in files.items():
        path = repo / relative
        if path.exists() and path.read_text(encoding="utf-8") == content:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        changed.append(relative)
    return changed
