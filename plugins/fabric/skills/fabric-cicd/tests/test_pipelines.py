"""Rendered pipeline topology and PROD artifact selection (offline)."""
from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

import yaml

SKILL = Path(__file__).resolve().parents[1]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(module)
    return module


render = load(SKILL / "scripts" / "render_pipelines.py", "render_pipelines")
select = load(SKILL / "assets" / "cicd" / "fabric" / "select_artifact.py", "select_artifact")

SETUP = {
    "branches": {"DEV": "DEV", "TEST": "TEST", "PROD": "PROD", "HOTFIX": "hotfix/*"},
    "environments": {
        env: {
            "workspace_id": f"{i}{i}{i}{i}{i}{i}{i}{i}-1111-4111-8111-111111111111",
            "variable_group": "grp",
            "ado_environment": f"fabric-{env.lower()}",
            "pipeline_name": f"Fabric {env}",
            "private_pool": "BAM-IaC-CloudEng",
            "key_vault_service_connection": "BAM-PROD Key Vault (WIF)",
            "key_vault_name": "BAM-KV-PBI-Prod",
            "key_vault_secret": "powerbi-eot-secret",
        }
        for i, env in enumerate(("DEV", "TEST", "PROD", "HOTFIX"), 1)
    },
}


class RenderedTopologyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.files = render.render_all(SETUP)

    def test_each_pipeline_triggers_only_from_its_own_branch(self) -> None:
        for env, name in render.FILES.items():
            doc = yaml.safe_load(self.files[name])
            self.assertEqual([SETUP["branches"][env]], doc["trigger"]["branches"]["include"], name)
            self.assertEqual("none", doc["pr"] if isinstance(doc["pr"], str) else str(doc["pr"]).lower().replace("false", "none"))

    def test_rendering_is_deterministic(self) -> None:
        self.assertEqual(self.files, render.render_all(SETUP))

    def test_deploy_jobs_use_private_pool_key_vault_verified_artifact_and_audit(self) -> None:
        for name in ("fabric-dev.yml", "fabric-test.yml", "fabric-hotfix.yml", "fabric-prod.yml"):
            text = self.files[name]
            self.assertIn("vmImage: ubuntu-latest", text)
            self.assertIn("name: 'BAM-IaC-CloudEng'", text)
            self.assertIn("task: AzureKeyVault@2", text)
            self.assertIn("azureSubscription: 'BAM-PROD Key Vault (WIF)'", text)
            self.assertIn("KeyVaultName: 'BAM-KV-PBI-Prod'", text)
            self.assertIn("SecretsFilter: 'powerbi-eot-secret'", text)
            self.assertIn("checkout: none", text)
            self.assertIn("requirements-fabric-cicd.lock", text)
            self.assertIn("auth_check.py", text)
            self.assertRegex(text, r"ALLOW_FABRIC_[A-Z]+_WRITE: true")
            self.assertIn("condition: always()", text)
            self.assertIn("PowerShell@2", text)
            self.assertIn("pwsh: true", text)
            self.assertNotIn("unzip -j", text)
            self.assertNotIn("/verifier/deploy_artifact.py", text)

    def test_hotfix_pipeline_cannot_target_test_or_prod(self) -> None:
        text = self.files["fabric-hotfix.yml"]
        self.assertNotRegex(text, r"--(environment|target) (TEST|PROD)")
        self.assertNotIn("ALLOW_FABRIC_TEST_WRITE", text)
        self.assertNotIn("ALLOW_FABRIC_PROD_WRITE", text)
        self.assertIn("ALLOW_FABRIC_HOTFIX_WRITE", text)

    def test_prod_compares_digest_before_deploying(self) -> None:
        text = self.files["fabric-prod.yml"]
        self.assertLess(text.index("compare_release.py"), text.index("Deploy the verified artifact to PROD"))
        self.assertIsNone(re.search(r"\{\{", text))

    def test_unresolved_placeholder_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            render.substitute("{{MISSING}}", {})


class ArtifactSelectionTests(unittest.TestCase):
    def test_test_branch_uses_test_artifact(self) -> None:
        self.assertEqual(("TEST", "Fabric TEST", "TEST"), select.choose("TEST", "TEST", "Fabric TEST", "Fabric HOTFIX"))

    def test_hotfix_branch_uses_hotfix_artifact(self) -> None:
        self.assertEqual(("HOTFIX", "Fabric HOTFIX", "hotfix/FIN-1"), select.choose("hotfix/FIN-1", "TEST", "Fabric TEST", "Fabric HOTFIX"))

    def test_other_source_blocks(self) -> None:
        for branch in ("feature/x", "DEV", "hotfixes"):
            with self.assertRaises(SystemExit):
                select.choose(branch, "TEST", "Fabric TEST", "Fabric HOTFIX")

    def test_missing_hotfix_build_blocks(self) -> None:
        original = select.api
        select.api = lambda url, token: {"value": [{"id": 1, "definition": {"name": "Fabric HOTFIX"}, "sourceVersion": "other"}]}
        try:
            with self.assertRaises(SystemExit):
                select.successful_build("https://x/", "p", "Fabric HOTFIX", "hotfix/FIN-1", "abc", "t")
        finally:
            select.api = original


if __name__ == "__main__":
    unittest.main()
