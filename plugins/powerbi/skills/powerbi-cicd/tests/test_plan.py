from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import yaml

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(TESTS.parent / "scripts"))
import plan
from discovery_adapters import Lookup
from generation import compatibility_config, compatibility_manifest


class FakeDiscovery:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.workspaces_value = {"value": [
            {"displayName": f"Finance {target}", "id": f"{index:08d}-1111-4111-8111-111111111111", "capacityId": "99999999-9999-4999-8999-999999999999"}
            for index, target in enumerate(("DEV", "TEST", "PROD", "HOTFIX"), start=1)
        ]}

    def account(self) -> Lookup:
        self.calls.append("account")
        return Lookup({"tenantId": "aaaaaaaa-1111-4111-8111-111111111111"})

    def service_principal(self, app_id: str) -> Lookup:
        self.calls.append("sp")
        return Lookup({"id": "bbbbbbbb-1111-4111-8111-111111111111"})

    def capacities(self) -> Lookup:
        self.calls.append("capacities")
        return Lookup({"value": [{"id": "99999999-9999-4999-8999-999999999999", "displayName": "Finance Capacity"}]})

    def workspaces(self) -> Lookup:
        self.calls.append("workspaces")
        return Lookup(self.workspaces_value)

    def variable_group(self, name: str, organization: str, project: str) -> Lookup:
        self.calls.append("variable_group")
        return Lookup([{"name": name, "variables": {}}])

    def connection(self, connection_id: str) -> Lookup:
        self.calls.append("connection")
        return Lookup({"displayName": f"Connection {connection_id[-1]}"})


class PlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        source = self.root / "pbi" / "Sales.SemanticModel"
        source.mkdir(parents=True)
        (source / ".platform").write_text(json.dumps({"metadata": {"displayName": "SalesModel"}}), encoding="utf-8")
        (source / "model.tmdl").write_text("model Sales", encoding="utf-8")
        self.args = [
            "--repo", str(self.root), "--no-prompt",
            "--app-id", "cccccccc-1111-4111-8111-111111111111",
            "--dev-workspace", "Finance DEV", "--test-workspace", "Finance TEST",
            "--prod-workspace", "Finance PROD", "--hotfix-workspace", "Finance HOTFIX",
            "--variable-group", "powerbi-shared", "--private-pool", "Protected Windows",
            "--key-vault-service-connection", "Power BI Key Vault WIF",
            "--key-vault-name", "finance-powerbi-prod",
            "--key-vault-secret-reference", "powerbi-client-secret",
            "--target-owner", "Power BI Engineering",
            "--answer", "ado=org=https://dev.azure.com/contoso project=Finance repository=analytics",
        ]

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_unanswered_no_prompt_writes_deterministic_review_and_exits_two(self) -> None:
        discovery = FakeDiscovery()
        with redirect_stdout(io.StringIO()) as output:
            first_status = plan.main(self.args, discovery)
        setup_path = self.root / "cicd/powerbi/setup.yml"
        review_path = self.root / "cicd/powerbi/SETUP.md"
        first_setup = setup_path.read_bytes()
        first_review = review_path.read_bytes()
        with redirect_stdout(io.StringIO()):
            second_status = plan.main(self.args, discovery)
        self.assertEqual(2, first_status)
        self.assertEqual(2, second_status)
        self.assertEqual(first_setup, setup_path.read_bytes())
        self.assertEqual(first_review, review_path.read_bytes())
        self.assertIn("binding.SalesModel.DEV", output.getvalue())
        setup = yaml.safe_load(first_setup)
        self.assertEqual(3, len(setup["open_questions"]))
        self.assertNotIn("c", discovery.calls)

    def answered_args(self) -> list[str]:
        return self.args + [
            "--answer", "binding.SalesModel.DEV=30000000-1111-4111-8111-111111111111",
            "--answer", "binding.SalesModel.TEST=30000000-2222-4222-8222-222222222222",
            "--answer", "binding.SalesModel.PROD=30000000-3333-4333-8333-333333333333",
        ]

    def test_fully_answered_plan_is_ready_without_external_writes(self) -> None:
        discovery = FakeDiscovery()
        args = self.answered_args()
        with redirect_stdout(io.StringIO()):
            status = plan.main(args, discovery)
        self.assertEqual(0, status)
        setup = yaml.safe_load((self.root / "cicd/powerbi/setup.yml").read_text(encoding="utf-8"))
        self.assertEqual([], setup["gaps"])
        self.assertEqual([], setup["open_questions"])
        self.assertNotIn("HOTFIX", setup["semantic_model_bindings"]["SalesModel"])
        self.assertIn("connection", discovery.calls)
        self.assertFalse(any(call.startswith(("create", "post", "patch", "deploy")) for call in discovery.calls))
        review = (self.root / "cicd/powerbi/SETUP.md").read_text(encoding="utf-8")
        for expected in (
            "Managed items in dependency order", "Targets and protected resources",
            "variable group", "private pool", "Key Vault", "Apply actions and prerequisites",
            "Generated files", "User-supplied values", "Rollback", "HOTFIX resolves",
            "never runs a deployment or workload",
        ):
            self.assertIn(expected, review)
        setup["answers"]["client_secret_candidate"] = "NEVER-RENDER-THIS-VALUE"
        redacted_review = plan.render_setup_markdown(setup)
        self.assertNotIn("NEVER-RENDER-THIS-VALUE", redacted_review)

    def test_legacy_migration_preserves_exact_rules_and_release_files(self) -> None:
        discovery = FakeDiscovery()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(0, plan.main(self.answered_args(), discovery))
        setup_path = self.root / "cicd/powerbi/setup.yml"
        setup = yaml.safe_load(setup_path.read_text(encoding="utf-8"))
        rule = {
            "type": "find_replace", "path": "Sales.SemanticModel/*.tmdl",
            "find": "  exact\nvalue  ",
            "values": {"DEV": "001", "TEST": "true", "PROD": "\"quoted\" # value"},
        }
        setup["managed_items"][0]["substitutions"]["rules"] = [rule, {**rule, "find": "second", "values": {"DEV": "00.1", "TEST": "false", "PROD": "@$%"}}]
        legacy_config = self.root / "legacy-bootstrap.json"
        legacy_manifest = self.root / "legacy-assets.yml"
        legacy_config.write_text(json.dumps(compatibility_config(setup), indent=2) + "\n", encoding="utf-8")
        legacy_manifest.write_text(json.dumps(compatibility_manifest(setup), indent=2) + "\n", encoding="utf-8")
        generated_config = self.root / "cicd/powerbi/bootstrap-config.json"
        generated_manifest = self.root / "cicd/powerbi/powerbi-assets.yml"
        generated_config.write_text("retained generated config\n", encoding="utf-8")
        generated_manifest.write_text("retained generated manifest\n", encoding="utf-8")
        originals = {path: path.read_bytes() for path in (legacy_config, legacy_manifest, generated_config, generated_manifest)}

        args = self.answered_args() + ["--legacy-config", str(legacy_config), "--legacy-manifest", str(legacy_manifest)]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(0, plan.main(args, discovery))
        migrated = yaml.safe_load(setup_path.read_text(encoding="utf-8"))
        self.assertEqual([rule, {**rule, "find": "second", "values": {"DEV": "00.1", "TEST": "false", "PROD": "@$%"}}], migrated["managed_items"][0]["substitutions"]["rules"])
        self.assertEqual([], migrated["gaps"])
        self.assertEqual([], migrated["open_questions"])
        for path, content in originals.items():
            self.assertEqual(content, path.read_bytes())

    def test_legacy_migration_blocks_conflicts_and_secrets_without_leaking(self) -> None:
        discovery = FakeDiscovery()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(0, plan.main(self.answered_args(), discovery))
        setup = yaml.safe_load((self.root / "cicd/powerbi/setup.yml").read_text(encoding="utf-8"))
        config = compatibility_config(setup)
        manifest = compatibility_manifest(setup)
        config["targets"]["PROD"]["workspace_id"] = "77777777-7777-4777-8777-777777777777"
        config["client_secret"] = "DO-NOT-COPY-THIS-SECRET"
        legacy_config = self.root / "legacy-bootstrap.json"
        legacy_manifest = self.root / "legacy-assets.yml"
        legacy_config.write_text(json.dumps(config), encoding="utf-8")
        legacy_manifest.write_text(json.dumps(manifest), encoding="utf-8")

        args = self.answered_args() + ["--legacy-config", str(legacy_config), "--legacy-manifest", str(legacy_manifest)]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(2, plan.main(args, discovery))
        migrated = yaml.safe_load((self.root / "cicd/powerbi/setup.yml").read_text(encoding="utf-8"))
        self.assertTrue(any("secret-bearing" in gap["reason"] for gap in migrated["gaps"]))
        self.assertNotIn("DO-NOT-COPY-THIS-SECRET", (self.root / "cicd/powerbi/setup.yml").read_text(encoding="utf-8"))
        self.assertNotIn("DO-NOT-COPY-THIS-SECRET", (self.root / "cicd/powerbi/SETUP.md").read_text(encoding="utf-8"))

        config.pop("client_secret")
        legacy_config.write_text(json.dumps(config), encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(2, plan.main(args, discovery))
        conflict = yaml.safe_load((self.root / "cicd/powerbi/setup.yml").read_text(encoding="utf-8"))
        self.assertTrue(any("conflicts" in gap["reason"] for gap in conflict["gaps"]))


if __name__ == "__main__":
    unittest.main()
