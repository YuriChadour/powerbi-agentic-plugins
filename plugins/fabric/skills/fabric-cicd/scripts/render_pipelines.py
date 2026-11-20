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
    """Render all configured profiles; the legacy four-profile input still works."""
    branches, envs = setup["branches"], setup["environments"]
    profiles = setup.get("profiles", {})
    files = {"validation-steps.yml": (TEMPLATES / "validation-steps.yml").read_text(encoding="utf-8")}
    release, promotion, contract = ((TEMPLATES / name).read_text(encoding="utf-8") for name in ("fabric-release.yml", "fabric-prod.yml", "fabric-contract.yml"))
    for env in sorted(envs):
        cfg, profile = envs[env], profiles.get(env, {})
        filename = (profile.get("azure_devops") or {}).get("pipeline_yaml", "").rsplit("/", 1)[-1] or FILES.get(env, f"fabric-{env.lower()}.yml")
        values = {
            "ENV": env, "env": env.lower(), "ENV_TITLE": env.title(), "BRANCH": branches[env],
            "WORKSPACE_ID": cfg["workspace_id"], "VARIABLE_GROUP": cfg["variable_group"],
            "ADO_ENVIRONMENT": cfg["ado_environment"], "PRIVATE_POOL": cfg["private_pool"],
            "KEY_VAULT_SERVICE_CONNECTION": cfg["key_vault_service_connection"],
            "KEY_VAULT_NAME": cfg["key_vault_name"], "KEY_VAULT_SECRET": cfg["key_vault_secret"],
        }
        sources = (profile.get("promotion") or {}).get("accepts_from", []) or (["TEST", "HOTFIX"] if env == "PROD" and not profiles else [])
        if profile.get("deployment_mode", "standard") == "contract":
            files[filename] = substitute(contract, values)
        elif sources:
            first, second = sources[0], sources[1] if len(sources) > 1 else sources[0]
            values.update({"TEST_BRANCH": branches[first], "TEST_PIPELINE": envs[first]["pipeline_name"], "HOTFIX_PIPELINE": envs[second]["pipeline_name"]})
            files[filename] = substitute(promotion, values)
        else:
            files[filename] = substitute(release, values)
    return dict(sorted(files.items()))
