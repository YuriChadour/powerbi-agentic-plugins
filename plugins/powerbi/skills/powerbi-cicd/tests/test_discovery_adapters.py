from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from discovery_adapters import ReadOnlyDiscovery


class FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], object] | None = None):
        self.responses = responses or {}
        self.calls: list[list[str]] = []

    def __call__(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(command)
        key = tuple(command[:5])
        value = self.responses.get(key)
        if value is None:
            return subprocess.CompletedProcess(command, 1, "", "not found")
        if command[0] == "fab":
            body = {"status_code": 200, "text": value}
        else:
            body = value
        return subprocess.CompletedProcess(command, 0, json.dumps(body), "")


class DiscoveryAdapterTests(unittest.TestCase):
    def test_all_supported_adapters_issue_only_read_calls(self) -> None:
        runner = FakeRunner({
            ("fab", "api", "workspaces"): {"value": []},
            ("fab", "api", "capacities"): {"value": []},
            ("fab", "api", "workspaces/id/items"): {"value": []},
            ("fab", "api", "connections/id"): {"displayName": "SQL"},
            ("fab", "api", "connections/id/roleAssignments"): {"value": []},
            ("az", "rest", "--resource", "https://analysis.windows.net/powerbi/api", "--method"): {"value": []},
            ("az", "account", "show", "--output", "json"): {"tenantId": "tenant"},
            ("az", "ad", "sp", "show", "--id"): {"id": "object"},
            ("az", "pipelines", "variable-group", "list", "--group-name"): [],
            ("az", "pipelines", "pool", "list", "--org"): [],
            ("az", "devops", "service-endpoint", "list", "--org"): [],
            ("az", "pipelines", "list", "--org", "org"): [],
        })
        discovery = ReadOnlyDiscovery(runner)
        lookups = [
            discovery.workspaces(), discovery.capacities(), discovery.items("id"),
            discovery.connection("id"), discovery.connection_roles("id"),
            discovery.powerbi_datasets("id"), discovery.account(), discovery.service_principal("app"),
            discovery.variable_group("group", "org", "project"), discovery.private_pools("org"),
            discovery.key_vault_connections("org", "project"), discovery.pipelines("org", "project"),
            discovery.environments("https://dev.azure.com/org", "project"),
        ]
        self.assertTrue(all(lookup.value is not None for lookup in lookups[:-1]))
        for command in runner.calls:
            lowered = [part.casefold() for part in command]
            self.assertNotIn("post", lowered)
            self.assertNotIn("patch", lowered)
            self.assertNotIn("put", lowered)
            self.assertNotIn("create", lowered)

    def test_failures_become_named_questions(self) -> None:
        runner = FakeRunner()
        discovery = ReadOnlyDiscovery(runner)
        result = discovery.connection("missing")
        self.assertIsNone(result.value)
        self.assertEqual("lookup.connection.missing", result.question["key"])
        self.assertIn("missing", result.question["question"])

    def test_write_methods_and_unapproved_az_queries_are_rejected(self) -> None:
        discovery = ReadOnlyDiscovery(FakeRunner())
        with self.assertRaisesRegex(ValueError, "GET"):
            discovery._assert_read_only(["az", "rest", "--method", "POST"])
        with self.assertRaisesRegex(ValueError, "only use GET"):
            discovery._assert_read_only(["fab", "api", "-X", "post", "workspaces"])
        with self.assertRaisesRegex(ValueError, "unsupported"):
            discovery._az("pipelines", "variable-group", "create", key="bad", question="bad", example="bad")


if __name__ == "__main__":
    unittest.main()
