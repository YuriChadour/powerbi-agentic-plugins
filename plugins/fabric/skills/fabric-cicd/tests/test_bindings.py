"""Binding-rule generation: synthetic cases plus a read-only check against the reference repository."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SKILL = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bindings", SKILL / "scripts" / "bindings.py")
bindings = importlib.util.module_from_spec(spec)
sys.modules["bindings"] = bindings
spec.loader.exec_module(bindings)

WORKSPACE = "dbc878fb-b457-426a-ac9f-f495dae2c13a"
REFERENCE = Path(r"C:\Development\Analytics Reporting")


def summarize(rules: list[dict]) -> set[tuple[str, str, str]]:
    return {(rule["find_value"], rule["item_type"], rule["replace_value"]["DEV"]) for rule in rules}


class SyntheticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.source = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def write(self, folder: str, name: str, content: str) -> None:
        path = self.source / folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_sql_endpoint_resolves_to_target_endpoint(self) -> None:
        self.write("Nb.Notebook", "notebook-content.py", "# default_warehouse 1f29c809-5c51-4cfe-8ace-aee50f8a1224\n")
        items = [{"type": "Lakehouse", "name": "Gold", "id": "aaaaaaaa-1111-4111-8111-111111111111", "logicalId": None, "sqlendpointid": "1f29c809-5c51-4cfe-8ace-aee50f8a1224"}]
        result = bindings.generate_rules(self.source, [{"folder": "Nb.Notebook", "type": "Notebook", "name": "Nb"}], WORKSPACE, items)
        self.assertEqual({("1f29c809-5c51-4cfe-8ace-aee50f8a1224", "Notebook", "$items.Lakehouse.Gold.$sqlendpointid")}, summarize(result["rules"]))
        self.assertEqual(set(bindings.ENVIRONMENTS), set(result["rules"][0]["replace_value"]))

    def test_unknown_guid_is_a_gap_naming_the_file(self) -> None:
        self.write("Nb.Notebook", "notebook-content.py", "x = '99999999-9999-4999-8999-999999999999'\n")
        result = bindings.generate_rules(self.source, [{"folder": "Nb.Notebook", "type": "Notebook", "name": "Nb"}], WORKSPACE, [])
        self.assertEqual([{"guid": "99999999-9999-4999-8999-999999999999", "file": "Nb.Notebook/notebook-content.py"}], result["gaps"])
        self.assertEqual([], result["rules"])

    def test_mapped_guid_resolves_to_the_given_reference(self) -> None:
        self.write("Nb.Notebook", "notebook-content.py", "x = '99999999-9999-4999-8999-999999999999'\n")
        result = bindings.generate_rules(self.source, [{"folder": "Nb.Notebook", "type": "Notebook", "name": "Nb"}], WORKSPACE, [], set(), {"99999999-9999-4999-8999-999999999999": "$workspace.$id"})
        self.assertEqual([], result["gaps"])
        self.assertEqual({("99999999-9999-4999-8999-999999999999", "Notebook", "$workspace.$id")}, summarize(result["rules"]))

    def test_excluded_guid_is_not_a_gap(self) -> None:
        self.write("Nb.Notebook", "notebook-content.py", "x = '99999999-9999-4999-8999-999999999999'\n")
        result = bindings.generate_rules(self.source, [{"folder": "Nb.Notebook", "type": "Notebook", "name": "Nb"}], WORKSPACE, [], {"99999999-9999-4999-8999-999999999999"})
        self.assertEqual([], result["gaps"])

    def test_pipeline_connection_maps_to_itself_and_dependency_is_recorded(self) -> None:
        notebook_logical = "bbbbbbbb-2222-4222-8222-222222222222"
        connection = "cccccccc-3333-4333-8333-333333333333"
        self.write("Pipe.DataPipeline", "pipeline-content.json", json.dumps({"a": {"connection": connection}, "b": {"notebookId": notebook_logical}}))
        items = [{"type": "Notebook", "name": "Nb", "id": "dddddddd-4444-4444-8444-444444444444", "logicalId": notebook_logical}]
        managed = [{"folder": "Pipe.DataPipeline", "type": "DataPipeline", "name": "Pipe"}, {"folder": "Nb.Notebook", "type": "Notebook", "name": "Nb"}]
        self.write("Nb.Notebook", "notebook-content.py", "pass\n")
        result = bindings.generate_rules(self.source, managed, WORKSPACE, items)
        self.assertIn((connection, "DataPipeline", connection), summarize(result["rules"]))
        self.assertIn((notebook_logical, "DataPipeline", "$items.Notebook.Nb.$id"), summarize(result["rules"]))
        self.assertEqual(["Nb.Notebook"], result["dependencies"]["Pipe.DataPipeline"])
        self.assertEqual([], result["gaps"])


@unittest.skipUnless((REFERENCE / "fabric").is_dir(), "reference repository not available")
class ReferenceRepositoryTests(unittest.TestCase):
    """Read-only: nothing is written under the reference repository."""

    def test_reproduces_committed_parameter_rules(self) -> None:
        manifest = yaml.safe_load((REFERENCE / "cicd/fabric/managed-items.yml").read_text(encoding="utf-8"))
        managed, items = [], []
        for entry in manifest["managed_items"]:
            platform = json.loads((REFERENCE / "fabric" / entry["folder"] / ".platform").read_text(encoding="utf-8"))
            name = entry["folder"].rsplit(".", 1)[0]
            managed.append({"folder": entry["folder"], "type": entry["type"], "name": name})
            items.append({"type": entry["type"], "name": name, "id": entry["logical_id"], "logicalId": platform["config"]["logicalId"]})
        items.append({"type": "SQLEndpoint", "name": "BAM_SH_LH", "id": "b3757728-044b-489e-b6e8-446ebe1daadc"})  # from the live DEV listing
        result = bindings.generate_rules(REFERENCE / "fabric", managed, manifest["dev_workspace"]["id"], items)
        committed = yaml.safe_load((REFERENCE / "cicd/fabric/parameter.yml").read_text(encoding="utf-8"))["find_replace"]
        expected = {(r["find_value"], r["item_type"], r["replace_value"]["DEV"]) for r in committed}
        self.assertEqual([], result["gaps"])
        # The committed file lacks the SQL endpoint rule (the FIN-2101 gap) and relies on fabric-cicd's
        # native logical-ID rewrite for intra-repository item references; the generator states both.
        self.assertEqual(
            {
                ("b3757728-044b-489e-b6e8-446ebe1daadc", "Notebook", "$items.Lakehouse.BAM_SH_LH.$sqlendpointid"),
                ("f47bf0b6-9331-aa50-4907-09c6feef2906", "DataPipeline", "$items.DataPipeline.GL Snapshot Ingestion.$id"),
                ("bdf29a01-8368-8271-407e-0f7c731c94e3", "DataPipeline", "$items.Notebook.SH_SD_Data Run.$id"),
                ("fecb7997-b4b7-add7-43eb-13e879f0ad73", "DataPipeline", "$items.Notebook.SH_SD_Data Test.$id"),
            },
            summarize(result["rules"]) - expected,
        )
        self.assertEqual(set(), expected - summarize(result["rules"]))


if __name__ == "__main__":
    unittest.main()
