from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from setup_contract import dump_setup, validate_setup


def valid_setup() -> dict:
    target_names = ("DEV", "TEST", "PROD", "HOTFIX")
    environments = {}
    for index, target in enumerate(target_names, start=1):
        guid = f"{index:08d}-1111-4111-8111-111111111111"
        environments[target] = {
            "workspace": {"name": f"Finance {target}", "id": guid, "create": False},
            "capacity": {"id": guid, "name": "Capacity A"},
            "runtime_identity": {"reference": f"kv:powerbi-{target.lower()}", "app_id": guid, "object_id": guid},
            "variable_group": f"powerbi-{target.lower()}",
            "private_pool": "Private Windows",
            "key_vault": {
                "service_connection": "Power BI Key Vault WIF",
                "service_connection_id": guid,
                "name": "powerbi-prod",
                "secret_reference": "powerbi-client-secret",
            },
            "ado_environment": f"powerbi-{target.lower()}",
            "pipeline_name": f"Power BI {target}",
            "pipeline_yaml": "cicd/powerbi/azure-pipelines.yml",
            "branch": {"DEV": "dev", "TEST": "test", "PROD": "main", "HOTFIX": "hotfix/*"}[target],
            "target_owner": "Power BI Engineering",
            "approval_policy": "required",
            "artifact_route": "immutable",
            "verification_profile": "full",
            "git_connected": False,
            "direct_roles": [{"object_id": guid, "principal_type": "ServicePrincipal", "role": "Contributor"}],
        }
    return {
        "version": 1,
        "repository": {
            "source_root": "pbi",
            "ci_folder": "cicd/powerbi",
            "azure_devops": {"organization": "https://dev.azure.com/contoso", "project": "Finance", "repository": "analytics"},
            "branches": {"DEV": "dev", "TEST": "test", "PROD": "main", "HOTFIX": "hotfix/*"},
        },
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "service_principal": {"app_id": "10000000-0000-4000-8000-000000000001", "object_id": "20000000-0000-4000-8000-000000000001"},
        "environments": environments,
        "managed_items": [
            {"id": "SalesModel", "type": "SemanticModel", "path": "Sales.SemanticModel", "dependencies": [], "binding": None, "substitutions": {"rules": [
                {"type": "find_replace", "path": "Sales.SemanticModel/model.tmdl", "find": "TRUE", "values": {"DEV": "001", "TEST": "true", "PROD": "@quoted value@"}}
            ]}},
            {"id": "SalesReport", "type": "Report", "path": "Sales.Report", "dependencies": ["SalesModel"], "binding": None, "substitutions": {"rules": []}},
            {"id": "SalesRdl", "type": "PaginatedReport", "path": "Sales.rdl", "dependencies": ["SalesModel"], "binding": {"kind": "semantic_model", "target": "SalesModel"}, "substitutions": {"rules": []}},
        ],
        "semantic_model_bindings": {"SalesModel": {
            "DEV": ["30000000-0000-4000-8000-000000000001"],
            "TEST": ["30000000-0000-4000-8000-000000000002"],
            "PROD": ["30000000-0000-4000-8000-000000000003"],
        }},
        "connections": [
            {"id": "30000000-0000-4000-8000-000000000001", "display_name": "DEV SQL", "required_permission": "User"},
            {"id": "30000000-0000-4000-8000-000000000002", "display_name": "TEST SQL", "required_permission": "User"},
            {"id": "30000000-0000-4000-8000-000000000003", "display_name": "PROD SQL", "required_permission": "User"},
        ],
        "roles": [],
        "excluded": [{"path": "**/*.pbix", "reason": "PBIX is not an approved source artifact"}],
        "gaps": [],
        "answers": {},
        "open_questions": [],
        "provenance": {"repository.source_root": "assumed", "managed_items": "discovered"},
    }


class SetupContractTests(unittest.TestCase):
    def test_valid_contract_accepts_secret_reference_and_exact_string_values(self) -> None:
        setup = valid_setup()
        self.assertEqual([], validate_setup(setup))
        serialized = dump_setup(setup)
        self.assertIn("DEV: '001'", serialized)
        self.assertIn("TEST: 'true'", serialized)
        self.assertIn("PROD: '@quoted value@'", serialized)
        self.assertEqual(serialized, dump_setup(setup))

    def test_rejects_secret_bearing_value_fields(self) -> None:
        setup = valid_setup()
        setup["answers"]["client_secret"] = "not-allowed"
        self.assertTrue(any("secret-bearing" in error for error in validate_setup(setup)))

    def test_rejects_duplicate_items_and_incomplete_target_bindings(self) -> None:
        setup = valid_setup()
        setup["managed_items"].append(copy.deepcopy(setup["managed_items"][0]))
        self.assertTrue(any("duplicated" in error for error in validate_setup(setup)))
        setup = valid_setup()
        setup["semantic_model_bindings"]["SalesModel"].pop("TEST")
        self.assertTrue(any("every content environment" in error for error in validate_setup(setup)))

    def test_rejects_hotfix_content_mapping_and_target_mismatch(self) -> None:
        setup = valid_setup()
        setup["semantic_model_bindings"]["SalesModel"]["HOTFIX"] = setup["semantic_model_bindings"]["SalesModel"]["PROD"]
        self.assertTrue(any("omit HOTFIX" in error for error in validate_setup(setup)))
        setup = valid_setup()
        setup["environments"]["HOTFIX"]["workspace"]["id"] = setup["environments"]["PROD"]["workspace"]["id"]
        self.assertTrue(any("cannot target the PROD workspace" in error for error in validate_setup(setup)))
        setup = valid_setup()
        setup["environments"]["TEST"]["branch"] = "main"
        self.assertTrue(any("differs" in error for error in validate_setup(setup)))

    def test_unresolved_distinct_creation_targets_are_not_workspace_aliases(self) -> None:
        setup = valid_setup()
        for target in ("TEST", "PROD", "HOTFIX"):
            setup["environments"][target]["workspace"] = {
                "name": f"Create Finance {target}", "id": None, "create": True,
            }
        self.assertEqual([], validate_setup(setup))

    def test_rejects_unsupported_fields_and_incomplete_setup(self) -> None:
        setup = valid_setup()
        setup["unexpected"] = True
        self.assertTrue(any("unsupported fields" in error for error in validate_setup(setup)))
        setup = valid_setup()
        setup["managed_items"] = []
        self.assertTrue(any("nonempty" in error for error in validate_setup(setup)))


if __name__ == "__main__":
    unittest.main()
