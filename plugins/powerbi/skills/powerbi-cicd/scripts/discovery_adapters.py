"""Narrow read-only Fabric, Power BI and Azure DevOps discovery adapters."""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Sequence

POWER_BI_RESOURCE = "https://analysis.windows.net/powerbi/api"
ADO_RESOURCE = "499b84ac-1321-427f-aa17-267ca6975798"
READ_ONLY_AZ_PREFIXES = (
    ("account", "show"),
    ("ad", "sp", "show"),
    ("ad", "signed-in-user", "show"),
    ("pipelines", "list"),
    ("pipelines", "show"),
    ("pipelines", "variable-group", "list"),
    ("pipelines", "pool", "list"),
    ("devops", "service-endpoint", "list"),
)
WRITE_WORDS = {"create", "delete", "patch", "post", "put", "update", "remove", "add"}


@dataclass(frozen=True)
class Lookup:
    value: Any
    question: dict[str, str] | None = None


CommandRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]


class ReadOnlyDiscovery:
    def __init__(self, runner: CommandRunner | None = None):
        self.runner = runner or self._run

    @staticmethod
    def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
        executable = shutil.which(command[0])
        if not executable:
            raise OSError(f"{command[0]} is not installed or not on PATH")
        return subprocess.run([executable, *command[1:]], capture_output=True, text=True, check=False)

    @staticmethod
    def _question(key: str, question: str, example: str) -> dict[str, str]:
        return {"key": key, "question": question, "example": example}

    @staticmethod
    def _json(done: subprocess.CompletedProcess[str]) -> Any:
        if done.returncode:
            return None
        try:
            return json.loads(done.stdout)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _assert_read_only(command: list[str]) -> None:
        lowered = [str(part).casefold() for part in command]
        if "-x" in lowered or "--method" in lowered:
            methods = [lowered[index + 1] for index, part in enumerate(lowered[:-1]) if part in {"-x", "--method"}]
            if any(method != "get" for method in methods):
                raise ValueError("discovery commands may only use GET")
        if any(part in WRITE_WORDS for part in lowered):
            raise ValueError("discovery commands may not perform writes")

    def _az(self, *args: str, key: str, question: str, example: str) -> Lookup:
        if not any(tuple(args[: len(prefix)]) == prefix for prefix in READ_ONLY_AZ_PREFIXES):
            raise ValueError(f"unsupported read-only Azure CLI query: {' '.join(args[:3])}")
        command = ["az", *args, "--output", "json"]
        self._assert_read_only(command)
        try:
            value = self._json(self.runner(command))
        except (OSError, subprocess.TimeoutExpired):
            value = None
        if value is None:
            return Lookup(None, self._question(key, question, example))
        return Lookup(value)

    def fab_get(self, path: str, *, key: str, question: str, example: str) -> Lookup:
        normalized = path.strip("/")
        if not normalized or any(token in normalized for token in ("?", "*", "..")):
            raise ValueError("fab discovery path must be a fixed relative API path")
        allowed = normalized == "workspaces" or normalized == "capacities" or normalized.startswith("workspaces/") or normalized.startswith("connections/")
        if not allowed:
            raise ValueError(f"unsupported fab discovery path: {normalized}")
        command = ["fab", "api", normalized]
        self._assert_read_only(command)
        try:
            body = self._json(self.runner(command))
        except (OSError, subprocess.TimeoutExpired):
            body = None
        value = body.get("text") if isinstance(body, dict) and body.get("status_code") == 200 else None
        return Lookup(value, None if value is not None else self._question(key, question, example))

    def powerbi_get(self, path: str, *, key: str, question: str, example: str) -> Lookup:
        normalized = path.strip("/")
        if not normalized.startswith(("groups/", "admin/")) or ".." in normalized:
            raise ValueError("unsupported Power BI read-only path")
        command = [
            "az", "rest", "--resource", POWER_BI_RESOURCE, "--method", "GET",
            "--url", f"https://api.powerbi.com/v1.0/myorg/{normalized}", "--output", "json",
        ]
        self._assert_read_only(command)
        try:
            value = self._json(self.runner(command))
        except (OSError, subprocess.TimeoutExpired):
            value = None
        return Lookup(value, None if value is not None else self._question(key, question, example))

    def workspaces(self) -> Lookup:
        return self.fab_get("workspaces", key="lookup.workspaces", question="Which Fabric workspaces are approved for Power BI setup?", example="Finance DEV, Finance TEST, Finance PROD, Finance HOTFIX")

    def capacities(self) -> Lookup:
        return self.fab_get("capacities", key="lookup.capacities", question="Which Fabric capacity is approved for the target workspaces?", example="Finance Capacity")

    def workspace(self, workspace: str) -> Lookup:
        return self.fab_get(f"workspaces/{workspace}", key=f"lookup.workspace.{workspace}", question=f"Confirm workspace '{workspace}' and its approved ID.", example="00000000-0000-4000-8000-000000000001")

    def items(self, workspace_id: str) -> Lookup:
        return self.fab_get(f"workspaces/{workspace_id}/items", key=f"lookup.items.{workspace_id}", question=f"Can the developer read items in workspace '{workspace_id}'?", example="grant Viewer or a reviewed equivalent")

    def connection(self, connection_id: str) -> Lookup:
        return self.fab_get(f"connections/{connection_id}", key=f"lookup.connection.{connection_id}", question=f"Confirm the approved Power BI connection '{connection_id}'.", example="Finance SQL connection GUID")

    def connection_roles(self, connection_id: str) -> Lookup:
        return self.fab_get(f"connections/{connection_id}/roleAssignments", key=f"lookup.connection_roles.{connection_id}", question=f"Can the connection owner disclose roles for '{connection_id}'?", example="grant Owner or request explicit access evidence")

    def powerbi_datasets(self, workspace_id: str) -> Lookup:
        return self.powerbi_get(f"groups/{workspace_id}/datasets", key=f"lookup.datasets.{workspace_id}", question=f"Can the developer read semantic models in workspace '{workspace_id}'?", example="grant the Power BI workspace Viewer role")

    def account(self) -> Lookup:
        return self._az("account", "show", key="lookup.tenant", question="What is the Entra tenant ID?", example="00000000-0000-4000-8000-000000000001")

    def service_principal(self, app_id: str) -> Lookup:
        return self._az("ad", "sp", "show", "--id", app_id, key="lookup.service_principal", question=f"What is the object ID for service principal {app_id}?", example="00000000-0000-4000-8000-000000000001")

    def variable_group(self, name: str, organization: str, project: str) -> Lookup:
        return self._az("pipelines", "variable-group", "list", "--group-name", name, "--org", organization, "--project", project, key=f"lookup.variable_group.{name}", question=f"Confirm Azure DevOps variable group '{name}' is readable.", example="grant the developer Library read permission")

    def private_pools(self, organization: str) -> Lookup:
        return self._az("pipelines", "pool", "list", "--org", organization, key="lookup.private_pools", question="Which Azure DevOps private pool is approved for protected Windows execution?", example="Power BI Protected Windows")

    def key_vault_connections(self, organization: str, project: str) -> Lookup:
        return self._az("devops", "service-endpoint", "list", "--org", organization, "--project", project, key="lookup.key_vault_connections", question="Which WIF Key Vault service connection is approved?", example="Power BI Production Key Vault (WIF)")

    def pipelines(self, organization: str, project: str) -> Lookup:
        return self._az("pipelines", "list", "--org", organization, "--project", project, key="lookup.pipelines", question="Which Azure DevOps pipelines are registered for Power BI CI/CD?", example="Power BI DEV; Power BI TEST; Power BI PROD; Power BI HOTFIX")

    def ado_get(self, url: str, *, key: str, question: str, example: str) -> Lookup:
        if not url.startswith("https://dev.azure.com/"):
            raise ValueError("Azure DevOps discovery requires an Azure DevOps HTTPS URL")
        command = ["az", "rest", "--resource", ADO_RESOURCE, "--method", "GET", "--url", url, "--output", "json"]
        self._assert_read_only(command)
        try:
            value = self._json(self.runner(command))
        except (OSError, subprocess.TimeoutExpired):
            value = None
        return Lookup(value, None if value is not None else self._question(key, question, example))

    def environments(self, organization: str, project: str) -> Lookup:
        url = f"{organization}/{project}/_apis/distributedtask/environments?api-version=7.1"
        return self.ado_get(url, key="lookup.environments", question="Which Azure DevOps environments are available for deployment?", example="powerbi-dev, powerbi-test, powerbi-prod, powerbi-hotfix")
