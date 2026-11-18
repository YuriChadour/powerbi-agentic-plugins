"""Render the release pipeline YAML from the approved setup values (deterministic)."""
from __future__ import annotations

import re
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parents[1] / "assets" / "templates" / "pipelines"
PLACEHOLDER = re.compile(r"\{\{[A-Za-z_]+\}\}")
FILES = {"DEV": "fabric-dev.yml", "TEST": "fabric-test.yml", "HOTFIX": "fabric-hotfix.yml", "PROD": "fabric-prod.yml"}


def substitute(template: str, values: dict[str, str]) -> str:
    text = template
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    leftover = PLACEHOLDER.findall(text)
    if leftover:
        raise ValueError("unresolved placeholders: " + ", ".join(sorted(set(leftover))))
    return text


def render_all(setup: dict) -> dict[str, str]:
    """setup: branches{env: branch}, environments{env: workspace_id, variable_group, ado_environment, pipeline_name}."""
    branches, envs = setup["branches"], setup["environments"]
    files = {"validation-steps.yml": (TEMPLATES / "validation-steps.yml").read_text(encoding="utf-8")}
    release = (TEMPLATES / "fabric-release.yml").read_text(encoding="utf-8")
    for env in ("DEV", "TEST", "HOTFIX"):
        values = {
            "ENV": env, "env": env.lower(), "ENV_TITLE": env.title(), "BRANCH": branches[env],
            "WORKSPACE_ID": envs[env]["workspace_id"], "VARIABLE_GROUP": envs[env]["variable_group"],
            "ADO_ENVIRONMENT": envs[env]["ado_environment"], "PRIVATE_POOL": envs[env]["private_pool"],
            "KEY_VAULT_SERVICE_CONNECTION": envs[env]["key_vault_service_connection"],
            "KEY_VAULT_NAME": envs[env]["key_vault_name"], "KEY_VAULT_SECRET": envs[env]["key_vault_secret"],
        }
        files[FILES[env]] = substitute(release, values)
    files[FILES["PROD"]] = substitute(
        (TEMPLATES / "fabric-prod.yml").read_text(encoding="utf-8"),
        {
            "BRANCH": branches["PROD"], "TEST_BRANCH": branches["TEST"],
            "TEST_PIPELINE": envs["TEST"]["pipeline_name"], "HOTFIX_PIPELINE": envs["HOTFIX"]["pipeline_name"],
            "WORKSPACE_ID": envs["PROD"]["workspace_id"], "VARIABLE_GROUP": envs["PROD"]["variable_group"],
            "ADO_ENVIRONMENT": envs["PROD"]["ado_environment"], "PRIVATE_POOL": envs["PROD"]["private_pool"],
            "KEY_VAULT_SERVICE_CONNECTION": envs["PROD"]["key_vault_service_connection"],
            "KEY_VAULT_NAME": envs["PROD"]["key_vault_name"], "KEY_VAULT_SECRET": envs["PROD"]["key_vault_secret"],
        },
    )
    return dict(sorted(files.items()))
