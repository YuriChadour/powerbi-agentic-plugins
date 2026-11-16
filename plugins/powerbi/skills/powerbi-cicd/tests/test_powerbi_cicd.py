from __future__ import annotations

import json
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import powerbi_cicd as cicd
import deploy_adapter as adapter


class PowerBiCicdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "pbi"
        (self.source / "Sales.SemanticModel").mkdir(parents=True)
        (self.source / "Sales.SemanticModel" / "model.tmdl").write_text("model Sales", encoding="utf-8")
        (self.source / "Sales.Report").mkdir()
        (self.source / "Sales.Report" / "report.json").write_text("{}", encoding="utf-8")
        (self.source / "Sales.rdl").write_text("<Report />", encoding="utf-8")
        self.config = {"version": 1, "repository": {"powerbi_source_folder": "pbi", "ci_folder": "cicd", "dev_branch": "feature/FIN-2060", "prod_branch": "main"}, "azure_devops": {"organization": "contoso", "project": "Finance", "repository": "analytics"}, "dev_workspace": {"workspace_name": "Finance Dev", "workspace_id": "11111111-1111-4111-8111-111111111111", "git_connected": True}, "targets": {"TEST": self.target("Test", "22222222-2222-4222-8222-222222222222"), "PROD": self.target("Prod", "33333333-3333-4333-8333-333333333333")}, "roles": [], "pipelines": {"TEST": {"yaml_path": "cicd/powerbi-test.yml", "source_branch": "feature/FIN-2060"}, "PROD": {"yaml_path": "cicd/powerbi-prod.yml", "source_branch": "main"}}, "protected_resources": {"TEST": {"identity_reference": "kv:powerbi-test", "write_guard": "ALLOW_POWERBI_TEST_WRITE"}, "PROD": {"identity_reference": "kv:powerbi-prod", "write_guard": "ALLOW_POWERBI_PROD_WRITE"}}}
        self.manifest = {"version": 1, "source_root": "pbi", "items": [{"id": "SalesModel", "type": "SemanticModel", "path": "Sales.SemanticModel", "dependencies": [], "substitutions": {}}, {"id": "SalesReport", "type": "Report", "path": "Sales.Report", "dependencies": ["SalesModel"], "substitutions": {}}, {"id": "SalesRdl", "type": "PaginatedReport", "path": "Sales.rdl", "dependencies": ["SalesModel"], "binding": {"kind": "semantic_model", "target": "SalesModel"}, "substitutions": {}}], "excluded": []}

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def target(name: str, workspace_id: str) -> dict:
        return {"workspace_name": f"Finance {name}", "workspace_id": workspace_id, "capacity_name": "CapacityA", "target_owner": "Owner", "environment": name.upper(), "pipeline_name": f"Power BI {name}", "approval_policy": "required", "artifact_route": "immutable", "verification_profile": "full", "git_connected": False}

    def test_valid_source_orders_model_before_dependents(self) -> None:
        result = cicd.validate_source(self.root, self.config, self.manifest)
        self.assertEqual("valid", result["status"])
        self.assertEqual("SalesModel", result["ordered_items"][0])
        self.assertFalse(result["workspace_authentication"])

    def test_config_fails_closed_for_extra_target_and_secret(self) -> None:
        self.config["targets"]["TEST"]["arbitrary"] = "no"
        self.assertTrue(any("unsupported" in error for error in cicd.validate_config(self.config)))
        self.config["targets"]["TEST"].pop("arbitrary")
        self.config["azure_devops"]["access_token"] = "unsafe"
        errors = cicd.validate_config(self.config)
        self.assertTrue(any("secret-bearing" in error for error in errors))

    def test_required_and_optional_target_profiles_are_unambiguous(self) -> None:
        self.config["targets"].pop("PROD")
        self.assertTrue(any("include TEST and PROD" in error for error in cicd.validate_config(self.config)))
        self.config["targets"]["PROD"] = self.target("Prod", "33333333-3333-4333-8333-333333333333")
        self.config["targets"]["UAT"] = self.target("Uat", "44444444-4444-4444-8444-444444444444")
        self.config["pipelines"]["UAT"] = {"yaml_path": "cicd/powerbi-uat.yml", "source_branch": "main"}
        self.config["protected_resources"]["UAT"] = {"identity_reference": "kv:powerbi-uat", "write_guard": "ALLOW_POWERBI_UAT_WRITE"}
        self.assertEqual([], cicd.validate_config(self.config))
        self.config["targets"]["UAT"].pop("approval_policy")
        self.assertTrue(cicd.validate_config(self.config))

    def test_manifest_blocks_duplicate_unresolved_and_missing_rdl_binding(self) -> None:
        invalid = json.loads(json.dumps(self.manifest))
        invalid["items"][1]["id"] = "SalesModel"
        self.assertTrue(any("duplicated" in error for error in cicd.validate_manifest(invalid, "pbi")))
        invalid = json.loads(json.dumps(self.manifest))
        invalid["items"][2].pop("binding")
        errors = cicd.validate_manifest(invalid, "pbi")
        self.assertTrue(any("binding" in error for error in errors))
        invalid = json.loads(json.dumps(self.manifest))
        invalid["items"][0]["type"] = "Notebook"
        self.assertTrue(any("unsupported" in error for error in cicd.validate_manifest(invalid, "pbi")))

    def test_source_blocks_escaped_path_and_committed_secret(self) -> None:
        escaped = json.loads(json.dumps(self.manifest))
        escaped["items"][0]["path"] = "../outside.SemanticModel"
        self.assertNotEqual("valid", cicd.validate_source(self.root, self.config, escaped)["status"])
        (self.source / "Sales.Report" / "unsafe.json").write_text('client_secret: leaked', encoding="utf-8")
        result = cicd.validate_source(self.root, self.config, self.manifest)
        self.assertEqual("blocked", result["status"])
        self.assertTrue(any("secret candidate" in error for error in result["errors"]))

    def test_malformed_pbip_boundary_is_blocked(self) -> None:
        (self.source / "Sales.Report" / "report.json").unlink()
        (self.source / "Sales.Report" / "notes.txt").write_text("not a PBIR definition", encoding="utf-8")
        result = cicd.validate_source(self.root, self.config, self.manifest)
        self.assertEqual("blocked", result["status"])
        self.assertTrue(any("PBIR" in error for error in result["errors"]))

    def test_package_and_promotion_digest_gate(self) -> None:
        (self.root / "unrelated.txt").write_text("not a release input", encoding="utf-8")
        output = self.root / "release.zip"
        package = cicd.package(self.root, self.config, self.manifest, "TEST", output, "abc123")
        self.assertEqual("verified", cicd.check_artifact(output, "TEST", "abc123", package["source_digest"], None)["status"])
        self.assertEqual("blocked", cicd.check_artifact(output, "PROD", "abc123", package["source_digest"], "wrong")["status"])
        self.assertEqual("verified", cicd.check_artifact(output, "PROD", "abc123", package["source_digest"], package["source_digest"])["status"])
        with zipfile.ZipFile(output) as archive:
            archive_data = json.loads(archive.read("release.json"))
            self.assertNotIn("payload/unrelated.txt", archive.namelist())
        self.assertEqual(["SalesModel", "SalesRdl", "SalesReport"], archive_data["managed_scope"])

    def test_artifact_tampering_stops_before_a_write(self) -> None:
        output = self.root / "release.zip"
        cicd.package(self.root, self.config, self.manifest, "TEST", output, "abc123")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(output, "a") as archive:
                archive.writestr("payload/pbi/Sales.Report/report.json", "tampered")
        result = cicd.check_artifact(output, "TEST", "abc123", None, None)
        self.assertEqual("blocked", result["status"])
        self.assertFalse(result["external_writes"])

    def test_pr_template_is_offline_and_evidence_is_redacted(self) -> None:
        template = (Path(__file__).resolve().parents[1] / "assets" / "templates" / "powerbi-validation.yml").read_text(encoding="utf-8").casefold()
        for prohibited in ("variablegroup", "serviceconnection", "client_secret", "az login", "fab auth", "allow_powerbi"):
            self.assertNotIn(prohibited, template)
        redacted = cicd.redact({"result": "partial", "client_secret": "never-log", "nested": {"access_token": "never-log"}})
        self.assertEqual("<redacted>", redacted["client_secret"])
        self.assertEqual("<redacted>", redacted["nested"]["access_token"])
        evidence = self.root / "evidence" / "release.json"
        record = cicd.write_evidence(evidence, self.config, self.manifest, "TEST", "abc123", "digest")
        self.assertEqual("recorded", record["status"])
        self.assertNotIn("never-log", evidence.read_text(encoding="utf-8"))

    def test_supported_matrix_is_fabric_cicd_only_and_fail_closed(self) -> None:
        matrix = (Path(__file__).resolve().parents[1] / "assets" / "supported-item-matrix.md").read_text(encoding="utf-8")
        self.assertIn("fabric_cicd.deploy_with_config", matrix)
        self.assertIn("fabric-cicd` 1.3.0", matrix)
        self.assertIn("Block before target write", matrix)
        invalid = json.loads(json.dumps(self.manifest))
        invalid["items"][0]["type"] = "Dashboard"
        self.assertTrue(cicd.validate_manifest(invalid, "pbi"))

    def test_adapter_preflight_blocks_before_write_and_verifies_read_only_inventory(self) -> None:
        artifact = self.root / "release.zip"
        package = cicd.package(self.root, self.config, self.manifest, "TEST", artifact, "abc123")
        ready = adapter.preflight(self.root, self.config, self.manifest, "TEST", artifact, package["source_digest"], None)
        self.assertEqual("ready", ready["status"])
        self.assertFalse(ready["workspace_write"])
        self.config["protected_resources"]["TEST"]["identity_reference"] = ""
        blocked = adapter.preflight(self.root, self.config, self.manifest, "TEST")
        self.assertEqual("blocked", blocked["status"])
        self.assertEqual([["SemanticModel"], ["Report"], ["PaginatedReport"]], adapter.deployment_groups(self.manifest))
        inventory = {"target": "TEST", "items": [{"id": "SalesModel", "type": "SemanticModel", "ready": True}, {"id": "SalesReport", "type": "Report"}, {"id": "SalesRdl", "type": "PaginatedReport", "binding": {"kind": "semantic_model", "target": "SalesModel"}}, {"id": "Unmanaged", "type": "Report"}]}
        self.assertEqual("verified", adapter.verify(self.manifest, "TEST", inventory)["status"])
        self.assertEqual("none", adapter.drift(self.manifest, "TEST", inventory)["unmanaged_action"])
        inventory["items"].pop()
        inventory["items"].pop()
        self.assertEqual("blocked", adapter.verify(self.manifest, "TEST", inventory)["status"])

    def test_discovery_has_no_remote_or_enablement(self) -> None:
        report = cicd.discover(self.root)
        self.assertFalse(report["scope_approved"])
        self.assertFalse(report["external_writes"])
        self.assertNotIn("remote", json.dumps(report).casefold())


if __name__ == "__main__":
    unittest.main()
