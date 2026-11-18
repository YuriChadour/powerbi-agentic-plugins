"""Authenticated Fabric deployment entry point for protected environments.

``fabric-cicd`` creates new items through the generic Items API, which can fail
for notebooks with "The feature is not available". Missing notebook shells are
created through the notebook-specific API first; ``fabric-cicd`` then applies
the full definitions and bindings. Lakehouses are never created here because
schema support is a creation-time property.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml
from azure.identity import ClientSecretCredential

FABRIC_API_ROOT = "https://api.fabric.microsoft.com"


def protected_identity(approved_app_id: str) -> ClientSecretCredential:
    """Return only the approved service-principal credential, never a fallback."""
    tenant = os.getenv("FABRIC_TENANT_ID") or os.getenv("AZURE_TENANT_ID")
    client = os.getenv("FABRIC_APP_ID") or os.getenv("AZURE_CLIENT_ID")
    secret = os.getenv("FABRIC_APP_SECRET") or os.getenv("AZURE_CLIENT_SECRET")
    if not all((tenant, client, secret)):
        raise SystemExit("approved Fabric service-principal inputs are not available")
    if client.lower() != approved_app_id.lower():
        raise SystemExit("configured Fabric application is not the approved service principal")
    return ClientSecretCredential(tenant_id=tenant, client_id=client, client_secret=secret)


def workspace_id(config_path: Path, environment: str, expected: str) -> str:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    value = config.get("core", {}).get("workspace_id", {}).get(environment)
    if not isinstance(value, str) or not value:
        raise SystemExit(f"missing workspace ID for {environment}")
    if value.lower() != expected.lower():
        raise SystemExit(f"configured {environment} workspace does not match the verified artifact target")
    return value


def request_json(credential: ClientSecretCredential, method: str, url: str, body: dict | None = None) -> dict:
    token = credential.get_token("https://api.fabric.microsoft.com/.default").token
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"Fabric API request failed ({exc.code}): {detail}") from exc


def list_items(credential: ClientSecretCredential, workspace: str) -> list[dict]:
    items = request_json(credential, "GET", f"{FABRIC_API_ROOT}/v1/workspaces/{workspace}/items").get("value", [])
    if not isinstance(items, list):
        raise SystemExit("Fabric item inventory returned an invalid response")
    return items


def definitions(config_path: Path, suffix: str) -> list[tuple[str, str]]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    repository = (config_path.parent / config["core"]["repository_directory"]).resolve()
    result = []
    for folder in sorted(repository.rglob(f"*.{suffix}")):
        platform = folder / ".platform"
        try:
            metadata = json.loads(platform.read_text(encoding="utf-8"))["metadata"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise SystemExit(f"invalid {suffix} platform metadata: {platform}") from exc
        name = metadata.get("displayName")
        description = metadata.get("description", "")
        if not isinstance(name, str) or not name:
            raise SystemExit(f"{suffix} displayName is missing: {platform}")
        result.append((name, description if isinstance(description, str) else ""))
    return result


def validate_lakehouses(config_path: Path, environment: str, credential: ClientSecretCredential, expected: str) -> None:
    workspace = workspace_id(config_path, environment, expected)
    existing = {item.get("displayName"): item.get("id") for item in list_items(credential, workspace) if item.get("type") == "Lakehouse"}
    for name, _ in definitions(config_path, "Lakehouse"):
        lakehouse = existing.get(name)
        if not lakehouse:
            raise SystemExit(f"Lakehouse '{name}' is missing in {environment}; run apply to create it with schema support before deployment")
        details = request_json(credential, "GET", f"{FABRIC_API_ROOT}/v1/workspaces/{workspace}/lakehouses/{lakehouse}")
        if not isinstance(details.get("properties", {}).get("defaultSchema"), str):
            raise SystemExit(f"Lakehouse '{name}' in {environment} is not schema-enabled; it must be replaced before deployment")
        print(f"Validated schema-enabled Lakehouse '{name}' in {environment}")


def precreate_notebooks(config_path: Path, environment: str, credential: ClientSecretCredential, expected: str) -> None:
    workspace = workspace_id(config_path, environment, expected)

    def notebook_names() -> set[str]:
        return {item.get("displayName") for item in list_items(credential, workspace) if item.get("type") == "Notebook"}

    existing = notebook_names()
    for name, description in definitions(config_path, "Notebook"):
        if name in existing:
            continue
        print(f"Creating notebook shell '{name}' in {environment}")
        request_json(credential, "POST", f"{FABRIC_API_ROOT}/v1/workspaces/{workspace}/notebooks", {"displayName": name, "description": description})
        deadline = time.monotonic() + 180
        while name not in notebook_names():
            if time.monotonic() > deadline:
                raise SystemExit(f"timed out waiting for Fabric notebook creation: {name}")
            time.sleep(3)
        existing.add(name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--environment", required=True, choices=["DEV", "TEST", "PROD", "HOTFIX"])
    parser.add_argument("--approved-app-id", required=True)
    parser.add_argument("--expected-workspace", required=True)
    args = parser.parse_args()
    credential = protected_identity(args.approved_app_id)
    validate_lakehouses(args.config, args.environment, credential, args.expected_workspace)
    precreate_notebooks(args.config, args.environment, credential, args.expected_workspace)
    from fabric_cicd import deploy_with_config

    options = {"config_file_path": str(args.config.resolve()), "token_credential": credential, "environment": args.environment}
    result = deploy_with_config(**options)
    print(f"fabric-cicd deployment completed: {result}")


if __name__ == "__main__":
    main()
