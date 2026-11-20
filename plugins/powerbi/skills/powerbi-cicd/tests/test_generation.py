from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(TESTS.parent / "scripts"))
import deploy_adapter as adapter
import powerbi_cicd as cicd
from generation import compatibility_config, compatibility_manifest, generated_files
from legacy_migration import import_legacy
from powerbi_cicd import validate_config, validate_manifest
from test_setup_contract import valid_setup


class GenerationTests(unittest.TestCase):
    def test_generated_files_are_deterministic_valid_and_preserve_rules(self) -> None:
        setup = valid_setup()
        rule = setup["managed_items"][0]["substitutions"]["rules"][0]
        rule["path"] = "Sales.SemanticModel/*.tmdl"
        rule["find"] = "  exact\nquoted value  "
        rule["values"] = {"DEV": "001", "TEST": "true", "PROD": "@quoted value@"}

        first = generated_files(setup)
        second = generated_files(copy.deepcopy(setup))

        self.assertEqual(first, second)
        self.assertEqual([], validate_config(compatibility_config(setup)))
        self.assertEqual([], validate_manifest(compatibility_manifest(setup), "pbi"))
        manifest = json.loads(first["cicd/powerbi/powerbi-assets.yml"])
        generated_rule = manifest["items"][0]["substitutions"]["rules"][0]
        self.assertEqual([rule], manifest["items"][0]["substitutions"]["rules"])
        self.assertIsInstance(generated_rule["values"]["DEV"], str)
        self.assertIsInstance(generated_rule["values"]["TEST"], str)
        self.assertIn("cicd/powerbi/deployment/scripts/deploy_fabric.py", first)
        self.assertIn("cicd/powerbi/deployment/templates/deploy-stage.yml", first)
        self.assertIn("cicd/powerbi/scripts/powerbi_cicd.py", first)

    def test_generated_contract_round_trips_through_release_lifecycle(self) -> None:
        setup = valid_setup()
        config = compatibility_config(setup)
        manifest = compatibility_manifest(setup)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = root / "pbi" / "Sales.SemanticModel"
            model.mkdir(parents=True)
            (model / "model.tmdl").write_text("model Sales\nvalue TRUE", encoding="utf-8")
            report = root / "pbi" / "Sales.Report"
            report.mkdir()
            (report / "report.json").write_text("{}", encoding="utf-8")
            (root / "pbi" / "Sales.rdl").write_text("<Report />", encoding="utf-8")

            self.assertEqual("valid", cicd.validate_source(root, config, manifest)["status"])
            artifact = root / "release.zip"
            package = cicd.package(root, config, manifest, "TEST", artifact, "generated-revision")
            self.assertEqual(
                "verified",
                cicd.check_artifact(artifact, "TEST", "generated-revision", package["source_digest"], None)["status"],
            )
            preflight = adapter.preflight(root, config, manifest, "TEST", artifact, package["source_digest"])
            self.assertEqual("ready", preflight["status"])
            self.assertEqual("unverified until authenticated read-only preflight", preflight["live_target"])

    def test_two_legacy_adopters_round_trip_without_semantic_drift(self) -> None:
        fixtures = []
        first = valid_setup()
        first["managed_items"][0]["substitutions"]["rules"] = [{
            "type": "find_replace", "path": "Sales.SemanticModel/**/*.tmdl",
            "find": "source = true\n  001  ",
            "values": {"DEV": "001", "TEST": "true", "PROD": "\"quoted\""},
        }]
        fixtures.append(first)
        second = valid_setup()
        second["managed_items"][2]["binding"] = {"kind": "data_source", "target": "30000000-0000-4000-8000-000000000003"}
        second["managed_items"][0]["substitutions"]["rules"] = [
            {"type": "find_replace", "path": "Sales.SemanticModel/model.tmdl", "find": "@special?", "values": {"DEV": "A/B", "TEST": "false", "PROD": "prod,exact"}},
            {"type": "find_replace", "path": "Sales.SemanticModel/*.tmdl", "find": "line one\nline two", "values": {"DEV": "00.1", "TEST": "yes", "PROD": "$prod#value"}},
        ]
        fixtures.append(second)

        for index, reviewed in enumerate(fixtures):
            config = compatibility_config(reviewed)
            manifest = compatibility_manifest(reviewed)
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                config_path = root / "bootstrap-config.json"
                manifest_path = root / "powerbi-assets.yml"
                config_path.write_text(json.dumps(config), encoding="utf-8")
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                migrated = import_legacy(copy.deepcopy(reviewed), config_path, manifest_path)
            self.assertEqual([], migrated["gaps"], f"fixture {index}")
            self.assertEqual(config, compatibility_config(migrated), f"fixture {index}")
            self.assertEqual(manifest, compatibility_manifest(migrated), f"fixture {index}")
            self.assertEqual(manifest["items"], compatibility_manifest(migrated)["items"])
            self.assertEqual(manifest["semantic_model_bindings"], compatibility_manifest(migrated)["semantic_model_bindings"])
            self.assertNotIn("HOTFIX", compatibility_manifest(migrated)["semantic_model_bindings"]["SalesModel"])

    def test_generated_pipeline_preserves_protected_release_guards(self) -> None:
        generated = generated_files(valid_setup())
        pipeline = generated["cicd/powerbi/azure-pipelines.yml"]
        stage = generated["cicd/powerbi/deployment/templates/deploy-stage.yml"]
        text = pipeline + stage

        self.assertIn("vmImage: ubuntu-latest", text)
        self.assertIn("PowerShell@2", text)
        self.assertIn("name: '${{ parameters.privatePool }}'", text)
        self.assertIn("task: AzureKeyVault@2", text)
        self.assertIn("requirements-powerbi-cicd.lock", text)
        self.assertIn("validate_deployment_identity.py", text)
        self.assertIn("deploy_artifact.py", text)
        self.assertIn("deploy_fabric.py", text)
        self.assertIn("--live-inventory", text)
        self.assertIn("ALLOW_POWERBI_HOTFIX_WRITE", text)
        self.assertIn("write_deployment_metadata.py", text)
        self.assertIn("condition: always()", text)
        self.assertIn("known-good artifact", text)
        self.assertLess(stage.index("deploy_artifact.py"), stage.index("deploy_fabric.py"))
        self.assertNotIn("checkout: self", text)
        self.assertNotIn("{{POWERBI_", pipeline)
        self.assertIsInstance(yaml.safe_load(pipeline), dict)
        self.assertIsInstance(yaml.safe_load(stage), dict)

    def test_complete_content_environment_matrix_remains_isolated(self) -> None:
        setup = valid_setup()
        for index, target in enumerate(("UAT", "REHEARSAL"), start=5):
            environment = copy.deepcopy(setup["environments"]["TEST"])
            guid = f"{index:08d}-1111-4111-8111-111111111111"
            environment["workspace"] = {"name": f"Finance {target}", "id": guid, "create": False}
            environment["capacity"] = {"id": guid, "name": "Capacity A"}
            environment["runtime_identity"] = {"reference": f"kv:powerbi-{target.lower()}", "app_id": guid, "object_id": guid}
            environment["variable_group"] = f"powerbi-{target.lower()}"
            environment["ado_environment"] = f"powerbi-{target.lower()}"
            environment["pipeline_name"] = f"Power BI {target}"
            environment["branch"] = target.lower()
            environment["direct_roles"] = [{"object_id": guid, "principal_type": "ServicePrincipal", "role": "Contributor"}]
            setup["environments"][target] = environment
            setup["repository"]["branches"][target] = target.lower()
            connection_id = f"30000000-0000-4000-8000-00000000000{index - 1}"
            setup["semantic_model_bindings"]["SalesModel"][target] = [connection_id]
            setup["connections"].append({"id": connection_id, "display_name": f"{target} SQL", "required_permission": "User"})
            setup["managed_items"][0]["substitutions"]["rules"][0]["values"][target] = target.lower()

        config = compatibility_config(setup)
        manifest = compatibility_manifest(setup)
        self.assertEqual([], validate_config(config))
        self.assertEqual([], validate_manifest(manifest, "pbi"))
        for target in ("DEV", "TEST", "PROD", "UAT", "REHEARSAL"):
            expected_binding = setup["semantic_model_bindings"]["SalesModel"][target]
            expected_value = setup["managed_items"][0]["substitutions"]["rules"][0]["values"][target]
            self.assertEqual(expected_binding, manifest["semantic_model_bindings"]["SalesModel"][target])
            self.assertEqual(expected_value, manifest["items"][0]["substitutions"]["rules"][0]["values"][target])
        self.assertNotIn("HOTFIX", manifest["semantic_model_bindings"]["SalesModel"])
        self.assertEqual("PROD", adapter.binding_environment("HOTFIX"))
        self.assertEqual("kv:powerbi-hotfix", config["protected_resources"]["HOTFIX"]["identity_reference"])
        self.assertNotEqual(config["targets"]["HOTFIX"]["workspace_id"], config["targets"]["PROD"]["workspace_id"])

    def test_hotfix_has_isolated_target_but_prod_content_mapping(self) -> None:
        setup = valid_setup()
        config = compatibility_config(setup)
        manifest = compatibility_manifest(setup)

        self.assertEqual(
            setup["environments"]["HOTFIX"]["workspace"]["id"],
            config["targets"]["HOTFIX"]["workspace_id"],
        )
        self.assertEqual("ALLOW_POWERBI_HOTFIX_WRITE", config["protected_resources"]["HOTFIX"]["write_guard"])
        self.assertEqual("kv:powerbi-hotfix", config["protected_resources"]["HOTFIX"]["identity_reference"])
        self.assertNotIn("HOTFIX", manifest["semantic_model_bindings"]["SalesModel"])
        self.assertNotIn("HOTFIX", manifest["items"][0]["substitutions"]["rules"][0]["values"])
        self.assertIn("HOTFIX", config["targets"])
        self.assertEqual("ALLOW_POWERBI_DEV_WRITE", config["protected_resources"]["DEV"]["write_guard"])


if __name__ == "__main__":
    unittest.main()
