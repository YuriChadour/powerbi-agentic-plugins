from __future__ import annotations

import json
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(TESTS.parent / "scripts"))
import powerbi_cicd as cicd
import deploy_adapter as adapter
from generation import compatibility_config, compatibility_manifest
from test_setup_contract import valid_setup


class PowerBiCicdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "pbi"
        (self.source / "Sales.SemanticModel").mkdir(parents=True)
        (self.source / "Sales.SemanticModel" / "model.tmdl").write_text("model Sales\nvalue TRUE", encoding="utf-8")
        (self.source / "Sales.Report").mkdir()
        (self.source / "Sales.Report" / "report.json").write_text("{}", encoding="utf-8")
        (self.source / "Sales.rdl").write_text("<Report />", encoding="utf-8")
        setup = valid_setup()
        self.config = compatibility_config(setup)
        self.manifest = compatibility_manifest(setup)

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
        self.config["targets"]["HOTFIX"]["workspace_id"] = self.config["targets"]["TEST"]["workspace_id"]
        self.assertTrue(any("cannot target the TEST workspace" in error for error in cicd.validate_config(self.config)))
        self.config["azure_devops"]["access_token"] = "unsafe"
        errors = cicd.validate_config(self.config)
        self.assertTrue(any("secret-bearing" in error for error in errors))

    def test_required_and_optional_target_profiles_are_unambiguous(self) -> None:
        self.config["targets"].pop("PROD")
        self.assertTrue(any("include TEST, PROD, and HOTFIX" in error for error in cicd.validate_config(self.config)))
        self.config["targets"]["PROD"] = self.target("Prod", "33333333-3333-4333-8333-333333333333")
        self.config["targets"]["UAT"] = self.target("Uat", "44444444-4444-4444-8444-444444444444")
        self.config["pipelines"]["UAT"] = {"name": "Power BI Uat", "yaml_path": "cicd/azure-pipelines.yml", "source_branch": "uat"}
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

    def test_manifest_requires_explicit_per_environment_model_bindings(self) -> None:
        invalid = json.loads(json.dumps(self.manifest))
        invalid["semantic_model_bindings"]["SalesModel"].pop("TEST")
        self.assertTrue(any("include DEV, TEST, and PROD" in error for error in cicd.validate_manifest(invalid, "pbi")))
        invalid = json.loads(json.dumps(self.manifest))
        invalid["semantic_model_bindings"]["SalesModel"]["TEST"] = ["22222222-2222-4222-8222-222222222222"] * 2
        self.assertTrue(any("duplicate" in error for error in cicd.validate_manifest(invalid, "pbi")))

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
            self.assertIn("deployment/scripts/validate_semantic_model_connections.py", archive.namelist())
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

    def test_artifact_missing_deployment_script_blocks_before_a_write(self) -> None:
        output = self.root / "release.zip"
        cicd.package(self.root, self.config, self.manifest, "TEST", output, "abc123")
        replacement = self.root / "missing-script.zip"
        with zipfile.ZipFile(output) as source, zipfile.ZipFile(replacement, "x") as destination:
            for name in source.namelist():
                if name != "deployment/scripts/write_deployment_metadata.py":
                    destination.writestr(name, source.read(name))
        result = cicd.check_artifact(replacement, "TEST", "abc123", None, None)
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
        self.assertIn("30000000-0000-4000-8000-000000000002", evidence.read_text(encoding="utf-8"))

    def test_supported_matrix_is_fabric_cicd_only_and_fail_closed(self) -> None:
        matrix = (Path(__file__).resolve().parents[1] / "assets" / "supported-item-matrix.md").read_text(encoding="utf-8")
        self.assertIn("fabric_cicd.deploy_with_config", matrix)
        self.assertIn("fabric-cicd` 1.3.0", matrix)
        self.assertIn("Block before target write", matrix)
        invalid = json.loads(json.dumps(self.manifest))
        invalid["items"][0]["type"] = "Dashboard"
        self.assertTrue(cicd.validate_manifest(invalid, "pbi"))

    def test_dev_target_uses_explicit_dev_workspace_without_release_target_alias(self) -> None:
        artifact = self.root / "release.zip"
        package = cicd.package(self.root, self.config, self.manifest, "TEST", artifact, "abc123")
        ready = adapter.preflight(self.root, self.config, self.manifest, "DEV", artifact, package["source_digest"])
        self.assertEqual("ready", ready["status"])
        native, override = adapter.native_config(self.config, self.manifest, "DEV", self.root / "pbi")
        self.assertEqual(self.config["dev_workspace"]["workspace_id"], native["core"]["workspace_id"]["DEV"])
        self.assertEqual(self.config["dev_workspace"]["workspace_id"], override["core"]["workspace_id"]["DEV"])
        self.assertEqual("verified", cicd.check_artifact(artifact, "DEV", "abc123", package["source_digest"], None)["status"])

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
        inventory = {"target": "TEST", "items": [{"id": "SalesModel", "type": "SemanticModel", "ready": True, "connections": [{"id": "30000000-0000-4000-8000-000000000002", "direct_identity_access": True, "personal_cloud": False}], "substitutions": self.manifest["items"][0]["substitutions"]}, {"id": "SalesReport", "type": "Report"}, {"id": "SalesRdl", "type": "PaginatedReport", "binding": {"kind": "semantic_model", "target": "SalesModel"}}, {"id": "Unmanaged", "type": "Report", "substitutions": {"rules": []}}]}
        self.assertEqual("verified", adapter.verify(self.manifest, "TEST", inventory)["status"])
        self.assertEqual("none", adapter.drift(self.manifest, "TEST", inventory)["unmanaged_action"])
        inventory["items"][0]["connections"][0]["direct_identity_access"] = False
        self.assertEqual("blocked", adapter.verify(self.manifest, "TEST", inventory)["status"])
        inventory["items"][0]["connections"][0]["direct_identity_access"] = True
        inventory["items"].pop()
        inventory["items"].pop()
        self.assertEqual("blocked", adapter.verify(self.manifest, "TEST", inventory)["status"])

    def test_existing_model_ownership_is_idempotent_and_write_requires_connection_preflight(self) -> None:
        class Credential:
            def get_token(self, _scope: str) -> object:
                return type("Token", (), {"token": "test-token"})()

        responses = [
            {"value": [{"id": "dataset-id", "name": "SalesModel"}]},
            {"configuredBy": "other-principal"},
            {},
        ]
        with patch.object(adapter, "power_bi_json", side_effect=responses) as request:
            self.assertEqual("ownership-transferred", adapter.take_over_semantic_model_if_present("workspace", "SalesModel", "deployment-principal", Credential()))
            self.assertEqual("POST", request.call_args_list[-1].kwargs["method"])
        artifact = self.root / "release.zip"
        package = cicd.package(self.root, self.config, self.manifest, "TEST", artifact, "abc123")
        blocked = adapter.deploy(self.root, self.config, self.manifest, "TEST", artifact, True, package["source_digest"], None)
        self.assertEqual("blocked", blocked["status"])
        self.assertFalse(blocked["workspace_write"])

    def test_substitutions_are_target_complete_and_only_apply_to_staged_payload(self) -> None:
        source = self.source / "Sales.SemanticModel" / "model.tmdl"
        source.write_text("server=ALPHA SECOND", encoding="utf-8")
        source_bytes = source.read_bytes()
        rules = [
            {"type": "find_replace", "path": "Sales.SemanticModel/model.tmdl", "find": "ALPHA", "values": {"DEV": "dev-a", "TEST": "BETA", "PROD": "prod-a"}},
            {"type": "find_replace", "path": "Sales.SemanticModel/model.tmdl", "find": "SECOND", "values": {"DEV": "dev-b", "TEST": "FINAL", "PROD": "prod-b"}},
        ]
        self.manifest["items"][0]["substitutions"] = {"rules": rules}
        artifact = self.root / "release.zip"
        package = cicd.package(self.root, self.config, self.manifest, "TEST", artifact, "abc123")
        archive_bytes = artifact.read_bytes()
        coverage = adapter.validate_substitution_coverage(artifact, self.manifest, "TEST")
        self.assertEqual("ready", coverage["status"])
        with tempfile.TemporaryDirectory() as staged:
            release_root = Path(staged)
            with zipfile.ZipFile(artifact) as archive:
                archive.extractall(release_root)
            resolved = adapter.apply_substitutions(release_root, self.manifest, "TEST")
            staged_source = release_root / "payload" / "pbi" / "Sales.SemanticModel" / "model.tmdl"
            self.assertEqual("server=BETA FINAL", staged_source.read_text(encoding="utf-8"))
        self.assertEqual([rule["values"]["TEST"] for rule in rules], [item["value"] for item in resolved])
        self.assertEqual(source_bytes, source.read_bytes())
        self.assertEqual(archive_bytes, artifact.read_bytes())
        self.assertEqual(package["source_digest"], cicd.check_artifact(artifact, "TEST", "abc123", None, None)["source_digest"])

    def test_substitution_preflight_blocks_missing_match_and_value_before_write(self) -> None:
        source = self.source / "Sales.SemanticModel" / "model.tmdl"
        cases = (
            ("missing-value", "Sales.SemanticModel/model.tmdl", "TRUE", {"DEV": "dev", "PROD": "prod"}),
            ("unmatched-path", "Sales.SemanticModel/*.missing", "TRUE", {"DEV": "dev", "TEST": "test", "PROD": "prod"}),
            ("absent-find", "Sales.SemanticModel/model.tmdl", "NOT_PRESENT", {"DEV": "dev", "TEST": "test", "PROD": "prod"}),
        )
        inventory = {"target": "TEST", "items": []}
        for index, (_, path, find, values) in enumerate(cases):
            manifest = json.loads(json.dumps(self.manifest))
            manifest["items"][0]["substitutions"] = {"rules": [{"type": "find_replace", "path": path, "find": find, "values": values}]}
            artifact = self.root / f"blocked-{index}.zip"
            cicd.package(self.root, self.config, manifest, "TEST", artifact, f"revision-{index}")
            result = adapter.deploy(self.root, self.config, manifest, "TEST", artifact, True, None, None, inventory)
            self.assertEqual("blocked", result["status"])
            self.assertEqual("substitution preflight failed", result["reason"])
            self.assertFalse(result["workspace_write"])
        self.assertIn("TRUE", source.read_text(encoding="utf-8"))

    def test_rdl_data_source_binding_round_trips_generated_manifest(self) -> None:
        rdl = self.manifest["items"][2]
        rdl["binding"] = {"kind": "data_source", "target": "30000000-0000-4000-8000-000000000002"}
        self.assertEqual([], cicd.validate_manifest(self.manifest, "pbi"))
        inventory = {"target": "TEST", "items": [
            {"id": "SalesModel", "type": "SemanticModel", "ready": True, "connections": [{"id": "30000000-0000-4000-8000-000000000002", "direct_identity_access": True, "personal_cloud": False}], "substitutions": self.manifest["items"][0]["substitutions"]},
            {"id": "SalesReport", "type": "Report"},
            {"id": "SalesRdl", "type": "PaginatedReport", "binding": rdl["binding"]},
        ]}
        self.assertEqual("verified", adapter.verify(self.manifest, "TEST", inventory)["status"])

    def test_hotfix_resolution_requires_successful_hotfix_validation(self) -> None:
        build = {"id": 42, "source_revision": "hotfix-revision", "source_branch": "hotfix/FIN-2060", "status": "succeeded", "validate_hotfix": "succeeded"}
        resolved = adapter.resolve_hotfix_release([{"merge_revision": "main-revision", "source_revision": "hotfix-revision", "source_branch": "hotfix/FIN-2060"}], "main-revision", None, [build])
        self.assertEqual("42", resolved["build_id"])
        artifact = self.root / "hotfix.zip"
        package = cicd.package(self.root, self.config, self.manifest, "HOTFIX", artifact, "hotfix-revision")
        promotion = cicd.check_artifact(artifact, "PROD", "hotfix-revision", package["source_digest"], package["source_digest"])
        self.assertEqual("verified", promotion["status"])
        build["validate_hotfix"] = "failed"
        with patch.object(adapter, "deploy") as workspace_write:
            with self.assertRaisesRegex(ValueError, "HOTFIX"):
                adapter.resolve_hotfix_release([], "main-revision", "hotfix-revision", [build])
            workspace_write.assert_not_called()

    def test_release_file_drift_blocks_before_a_write(self) -> None:
        artifact = self.root / "release.zip"
        package = cicd.package(self.root, self.config, self.manifest, "TEST", artifact, "abc123")
        with patch.object(adapter, "release_files_match", return_value=False):
            result = adapter.preflight(
                self.root, self.config, self.manifest, "TEST", artifact,
                package["source_digest"], None, deployment_revision="test-head",
            )
        self.assertEqual("blocked", result["status"])
        self.assertIn("drift", result["reason"])
        self.assertFalse(result["workspace_write"])

    def test_discovery_has_no_remote_or_enablement(self) -> None:
        report = cicd.discover(self.root)
        self.assertFalse(report["scope_approved"])
        self.assertFalse(report["external_writes"])
        self.assertNotIn("remote", json.dumps(report).casefold())

    def test_retired_hand_written_approval_surface_is_not_exposed(self) -> None:
        self.assertFalse(hasattr(cicd, "render"))
        with self.assertRaises(SystemExit):
            with patch.object(sys, "argv", ["powerbi_cicd.py", "render"]):
                cicd.main()


if __name__ == "__main__":
    unittest.main()
