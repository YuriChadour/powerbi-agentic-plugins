"""Offline regressions for the failures recorded during the FIN-2101 adoption.

Copy Jobs outside the managed scope, missing connection permission and a committed but
unregistered pipeline are covered in test_ported_scripts.py / test_apply.py; the SQL
endpoint rule in test_bindings.py. This file holds the remaining cases.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
import zipfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
sys.path.insert(0, str(SKILL / "tests"))


def load(path: Path, name: str):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render = load(SKILL / "scripts" / "render_pipelines.py", "render_pipelines_fin")
runner = load(SKILL / "assets" / "cicd" / "fabric" / "deploy_runner.py", "deploy_runner_fin")
from test_pipelines import SETUP  # noqa: E402


class Fin2101Regressions(unittest.TestCase):
    def setUp(self) -> None:
        self.files = render.render_all(SETUP)

    def test_deployment_job_runs_scripts_from_the_verified_extracted_artifact(self) -> None:
        for name in ("fabric-dev.yml", "fabric-test.yml", "fabric-hotfix.yml", "fabric-prod.yml"):
            text = self.files[name]
            self.assertIn("checkout: none", text)
            self.assertIn("content-hashes.json", text)
            self.assertRegex(text, r"(?:extracted|\$\(promotedRoot\))/cicd/fabric/deploy_artifact\.py")
            self.assertIn("--extracted-root", text)
            self.assertNotIn("/verifier/deploy_artifact.py", text)
            self.assertNotIn("$(Build.SourcesDirectory)", text)
            self.assertLess(text.index("Verify every hash and extract"), text.index("--extracted-root"))

    def test_no_windows_only_launcher_ships_and_protected_jobs_use_private_pool(self) -> None:
        self.assertEqual([], [p.name for p in SKILL.rglob("*.ps1")])
        for name, text in self.files.items():
            if not name.startswith("fabric-"):
                continue
            self.assertIn("pool:\n  vmImage: ubuntu-latest", text)
            self.assertIn("name: 'BAM-IaC-CloudEng'", text)
            self.assertIn("task: AzureKeyVault@2", text)
            self.assertIn("pwsh: true", text)

    def test_deploy_fails_without_a_schema_enabled_lakehouse(self) -> None:
        cfg = SKILL / "tests" / "_cfg"
        folder = cfg / "fabric" / "Lake.Lakehouse"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / ".platform").write_text(json.dumps({"metadata": {"displayName": "Lake"}}), encoding="utf-8")
        (cfg / "cicd").mkdir(exist_ok=True)
        config = cfg / "cicd" / "config.yml"
        config.write_text("core:\n  repository_directory: ../fabric\n  workspace_id:\n    TEST: w1\n", encoding="utf-8")
        original = runner.list_items, runner.request_json
        try:
            runner.list_items = lambda cred, ws: []
            with self.assertRaises(SystemExit) as raised:
                runner.validate_lakehouses(config, "TEST", None, "w1")
            self.assertIn("missing", str(raised.exception))
            runner.list_items = lambda cred, ws: [{"type": "Lakehouse", "displayName": "Lake", "id": "l1"}]
            runner.request_json = lambda cred, method, url, body=None: {"properties": {}}
            with self.assertRaises(SystemExit) as raised:
                runner.validate_lakehouses(config, "TEST", None, "w1")
            self.assertIn("not schema-enabled", str(raised.exception))
        finally:
            runner.list_items, runner.request_json = original
            import shutil
            shutil.rmtree(cfg, ignore_errors=True)

    def test_every_generated_reference_form_resolves_through_the_real_library(self) -> None:
        from fabric_cicd._parameter._utils import extract_replace_value

        class Workspace:
            bulk_publish_enabled = False
            workspace_id = "target-ws"
            workspace_name = "Target"
            workspace_items = {"Lakehouse": {"Lake": {"id": "lake-id", "sqlendpointid": "sql-id"}}, "Notebook": {"Nb": {"id": "nb-id"}}}

            def _refresh_deployed_items(self) -> None:
                return None

        expected = {"$workspace.$id": "target-ws", "$items.Lakehouse.Lake.$id": "lake-id", "$items.Lakehouse.Lake.$sqlendpointid": "sql-id", "$items.Notebook.Nb.$id": "nb-id"}
        for expression, value in expected.items():
            self.assertEqual(value, extract_replace_value(Workspace(), expression), expression)

    def test_each_pipeline_triggers_only_from_its_own_branch_not_dev(self) -> None:
        import yaml
        for name, branch in (("fabric-test.yml", "TEST"), ("fabric-prod.yml", "PROD"), ("fabric-hotfix.yml", "hotfix/*")):
            self.assertEqual([branch], yaml.safe_load(self.files[name])["trigger"]["branches"]["include"])

    def test_artifact_contains_the_deployment_scripts(self) -> None:
        shipped = {p.name for p in (SKILL / "assets" / "cicd" / "fabric").glob("*.py")}
        self.assertLessEqual({"deploy_runner.py", "deploy_artifact.py", "release_contract.py", "auth_check.py", "record_release.py", "select_artifact.py"}, shipped)


if __name__ == "__main__":
    unittest.main()
