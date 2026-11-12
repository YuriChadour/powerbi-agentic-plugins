"""Offline coverage for the focused Fabric CI/CD bootstrap contract."""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
HELPER = SKILL / "scripts" / "bootstrap.py"
SPEC = importlib.util.spec_from_file_location("fabric_cicd_bootstrap", HELPER)
bootstrap = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(bootstrap)


def configuration() -> dict:
    return {
        "version": 1,
        "repository": {"fabric_source_folder": "fabric", "ci_folder": "cicd", "dev_branch": "DEV", "prod_branch": "PROD"},
        "azure_devops": {"organization": "contoso", "project": "Data Engineering", "repository": "lakehouse-platform"},
        "dev_workspace": {"workspace_name": "Data Dev", "workspace_id": "33333333-3333-4333-8333-333333333333"},
        "targets": {
            "TEST": {"workspace_name": "Data Test", "workspace_id": None, "capacity_name": "Fabric Capacity", "environment": "fabric-test", "variable_group": "fabric-test-protected"},
            "PROD": {"workspace_name": "Data Prod", "workspace_id": "11111111-1111-4111-8111-111111111111", "capacity_name": None, "environment": "fabric-prod", "variable_group": "fabric-prod-protected"},
        },
        "roles": [{"target": "TEST", "object_id": "22222222-2222-4222-8222-222222222222", "principal_type": "ServicePrincipal", "role": "Contributor"}],
        "pipelines": {
            "TEST": {"name": "Fabric TEST", "yaml_path": "cicd/fabric-test.yml", "source_branch": "DEV"},
            "PROD": {"name": "Fabric PROD", "yaml_path": "cicd/fabric-prod.yml", "source_branch": "PROD"},
        },
        "protected_resources": {
            "TEST": {"service_connection": "fabric-test-wif", "write_guard": "ALLOW_FABRIC_TEST_WRITE"},
            "PROD": {"service_connection": "fabric-prod-wif", "write_guard": "ALLOW_FABRIC_PROD_WRITE"},
        },
    }


def manifest() -> str:
    return """version: 1
source_root: fabric
managed_items:
  - folder: Ingest.Notebook
    type: Notebook
    dependencies: []
  - folder: Orchestrate.DataPipeline
    type: DataPipeline
    dependencies: [Ingest.Notebook]
excluded:
  - path: fabric/**/Files/**
    reason: Data is not deployment content.
  - path: pbi/**
    reason: Power BI has a separate bootstrap.
"""


class BootstrapContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config_path = self.root / "bootstrap-config.json"
        self.manifest_path = self.root / "managed-items.yml"
        self.config_path.write_text(json.dumps(configuration()), encoding="utf-8")
        self.manifest_path.write_text(manifest(), encoding="utf-8")
        (self.root / "fabric" / "Ingest.Notebook").mkdir(parents=True)
        (self.root / "fabric" / "Ingest.Notebook" / "notebook-content.py").write_text("print('ingest')\n", encoding="utf-8")
        (self.root / "fabric" / "Orchestrate.DataPipeline").mkdir()
        (self.root / "fabric" / "Orchestrate.DataPipeline" / "pipeline-content.json").write_text('{"activities": []}\n', encoding="utf-8")
        (self.root / "pbi").mkdir()
        (self.root / "pbi" / "report.pbip").write_text("not Fabric deployment content\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_plan_is_offline_and_parameterized(self) -> None:
        result = bootstrap.plan(bootstrap.load_json(self.config_path), bootstrap.load_manifest(self.manifest_path))
        self.assertEqual("planned", result["status"])
        self.assertFalse(result["external_writes"])
        self.assertEqual(["Ingest.Notebook", "Orchestrate.DataPipeline"], result["managed_items"])

    def test_invalid_placeholder_and_missing_dependency_are_rejected(self) -> None:
        invalid = configuration()
        invalid["azure_devops"]["repository"] = "REPLACE_REPOSITORY"
        self.assertTrue(bootstrap.validate_config(invalid))
        invalid = configuration()
        invalid["dev_workspace"]["workspace_id"] = "not-a-guid"
        self.assertTrue(bootstrap.validate_config(invalid))
        bad_manifest = bootstrap.load_manifest(self.manifest_path)
        bad_manifest["managed_items"][1]["dependencies"] = ["Missing.Notebook"]
        self.assertTrue(bootstrap.validate_manifest(bad_manifest, "fabric"))

    def test_package_contains_only_selected_fabric_definitions(self) -> None:
        output = self.root / "fabric-release.zip"
        packaged = bootstrap.package(self.root, bootstrap.load_json(self.config_path), bootstrap.load_manifest(self.manifest_path), "TEST", output, "abc123")
        with zipfile.ZipFile(output) as archive:
            contents = archive.namelist()
            self.assertIn("payload/fabric/Ingest.Notebook/notebook-content.py", contents)
            self.assertIn("payload/fabric/Orchestrate.DataPipeline/pipeline-content.json", contents)
            self.assertNotIn("payload/pbi/report.pbip", contents)
        digest, _ = bootstrap.source_digest(self.root, "fabric", bootstrap.load_manifest(self.manifest_path))
        self.assertEqual("verified", bootstrap.release_gate(output, digest)["status"])
        self.assertEqual("blocked", bootstrap.release_gate(output, "0" * 64)["status"])
        self.assertEqual("TEST", packaged["target"])

    def test_secret_scan_is_a_source_gate_not_runtime_evidence(self) -> None:
        self.assertEqual([], bootstrap.scan_sources(self.root, "fabric"))
        (self.root / "fabric" / "unmanaged.txt").write_text("client_secret=not-a-real-secret", encoding="utf-8")
        self.assertEqual(["fabric/unmanaged.txt"], bootstrap.scan_sources(self.root, "fabric"))

    def test_render_is_offline_and_excludes_power_bi(self) -> None:
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if not shell:
            self.skipTest("PowerShell is unavailable")
        output = self.root / "cicd"
        result = subprocess.run(
            [shell, "-NoProfile", "-File", str(SKILL / "assets" / "templates" / "Initialize-FabricCicd.ps1"), "-Mode", "Render", "-ConfigPath", str(self.config_path), "-ManifestPath", str(self.manifest_path), "-RepoRoot", str(self.root), "-OutputRoot", str(output)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        test_yaml = (output / "fabric-test.yml").read_text(encoding="utf-8")
        self.assertIn("include: [fabric/**, cicd/**]", test_yaml)
        self.assertIn("exclude: [pbi/**]", test_yaml)
        parsed = bootstrap.yaml.safe_load(test_yaml)
        self.assertEqual(["DEV"], parsed["trigger"]["branches"]["include"])
        self.assertEqual(["pbi/**"], parsed["trigger"]["paths"]["exclude"])
        self.assertEqual(["PROD"], bootstrap.yaml.safe_load((output / "fabric-prod.yml").read_text(encoding="utf-8"))["trigger"]["branches"]["include"])
        self.assertFalse((output / "pbi-assets.yml").exists())
        checklist = (output / "verification-checklist.md").read_text(encoding="utf-8")
        self.assertIn("Deployment success is not runtime verification", checklist)

    def test_setup_uses_developer_sessions_and_protected_deploy_identity(self) -> None:
        setup = (SKILL / "assets" / "templates" / "Initialize-FabricCicd.ps1").read_text(encoding="utf-8")
        self.assertIn("Assert-DeveloperSetupSessions", setup)
        self.assertIn("fab' @('auth', 'status')", setup)
        self.assertIn("az' @('account', 'show'", setup)
        self.assertIn("az' @('extension', 'show', '--name', 'azure-devops'", setup)
        self.assertNotIn("client_secret", (SKILL / "assets" / "templates" / "bootstrap-config.json").read_text(encoding="utf-8").lower())
        for name in ("fabric-test.yml", "fabric-prod.yml"):
            pipeline = (SKILL / "assets" / "templates" / name).read_text(encoding="utf-8")
            self.assertIn("AzureCLI@2", pipeline)
            self.assertIn("FAB_SPN_FEDERATED_TOKEN", pipeline)
        self.assertIn("verification = 'pending'", setup)
        self.assertIn("fab' @('import'", setup)
        self.assertNotIn("fab' @('rm'", setup)


if __name__ == "__main__":
    unittest.main()
