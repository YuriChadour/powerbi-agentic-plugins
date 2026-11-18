from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(TESTS.parent / "scripts"))
from generation import compatibility_config, compatibility_manifest, generated_files
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
