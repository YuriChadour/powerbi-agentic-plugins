"""plan.py with a fake read-only tool layer (no Fabric, Azure or git access)."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SKILL = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("plan", SKILL / "scripts" / "plan.py")
plan = importlib.util.module_from_spec(spec)
sys.modules["plan"] = plan
spec.loader.exec_module(plan)

WS = {"DEV": "11111111-1111-4111-8111-111111111111", "TEST": "22222222-1111-4111-8111-111111111111"}
LAKE_ID, LAKE_LOGICAL = "aaaaaaaa-1111-4111-8111-111111111111", "bbbbbbbb-1111-4111-8111-111111111111"
UNKNOWN = "99999999-9999-4999-8999-999999999999"
CONNECTION = "cccccccc-1111-4111-8111-111111111111"


class FakeTools(plan.Tools):
    def __init__(self, known_connection_name: bool = True):
        self.known_connection_name = known_connection_name

    def fab(self, path: str):
        if path == "workspaces":
            return {"value": [{"id": WS[e], "displayName": f"WS {e}", "capacityId": "cap1"} for e in WS]}
        if path == "capacities":
            return {"value": [{"id": "cap1", "displayName": "Cap"}, {"id": "cap2", "displayName": "Other"}]}
        if path.startswith("workspaces/") and path.endswith("/items"):
            return {"value": [
                {"id": LAKE_ID, "type": "Lakehouse", "displayName": "Lake", "logicalId": LAKE_LOGICAL},
                {"id": "dddddddd-1111-4111-8111-111111111111", "type": "SQLEndpoint", "displayName": "Lake", "logicalId": None},
            ]}
        if "/lakehouses/" in path:
            return {"properties": {"sqlEndpointProperties": {"id": "dddddddd-1111-4111-8111-111111111111"}}}
        if path.startswith("workspaces/"):
            ws = path.split("/")[1]
            return {"id": ws, "displayName": "WS DEV", "capacityId": "cap1"}
        if path == f"connections/{CONNECTION}" and self.known_connection_name:
            return {"displayName": "Conn"}
        if path == f"connections/{CONNECTION}/roleAssignments":
            return {"value": [{"principal": {"id": "p1", "type": "User"}, "role": "Owner"}]}
        return None

    def az(self, *args):
        return {"tenantId": "t"} if args[:2] == ("account", "show") else {"id": "sp-object"} if args[:2] == ("ad", "sp") else None

    def remote(self, repo):
        return "https://org@dev.azure.com/org/Proj/_git/Repo"


class PlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        folder = self.repo / "fabric" / "Pipe.DataPipeline"
        folder.mkdir(parents=True)
        (folder / ".platform").write_text(json.dumps({"metadata": {"displayName": "Pipe"}}), encoding="utf-8")
        (folder / "pipeline-content.json").write_text(json.dumps({"a": {"connection": CONNECTION}, "b": LAKE_LOGICAL, "c": UNKNOWN}), encoding="utf-8")

    def run_plan(self, *extra: str, tools=None) -> int:
        argv = ["--repo", str(self.repo), "--no-prompt", "--app-id", "app", "--variable-group", "grp",
                "--dev-workspace", "WS DEV", "--test-workspace", "WS TEST", "--prod-workspace", "New PROD", "--hotfix-workspace", "New HOTFIX", *extra]
        return plan.main(argv, tools or FakeTools())

    def setup(self) -> dict:
        return yaml.safe_load((self.repo / "cicd/fabric/setup.yml").read_text(encoding="utf-8"))

    def test_missing_workspaces_ask_for_capacity_and_unknown_guid_is_a_gap(self) -> None:
        self.assertEqual(2, self.run_plan())
        setup = self.setup()
        self.assertEqual({"capacity.PROD", "capacity.HOTFIX"}, {q["key"] for q in setup["open_questions"]})
        self.assertEqual([UNKNOWN], [g["guid"] for g in setup["gaps"] if "guid" in g])
        self.assertEqual(["Pipe.DataPipeline"], [g["item"] for g in setup["gaps"] if "item" in g])
        self.assertIn("BLOCKED", (self.repo / "cicd/fabric/SETUP.md").read_text(encoding="utf-8"))

    def test_answers_are_recorded_and_rendering_is_deterministic(self) -> None:
        answers = ["--answer", "capacity.PROD=Cap", "--answer", "capacity.HOTFIX=Other", "--exclude-guid", UNKNOWN]
        self.assertEqual(0, self.run_plan(*answers))
        first = (self.repo / "cicd/fabric/setup.yml").read_text(encoding="utf-8")
        self.assertEqual(0, self.run_plan(*answers))
        self.assertEqual(first, (self.repo / "cicd/fabric/setup.yml").read_text(encoding="utf-8"))
        setup = self.setup()
        self.assertEqual("cap2", setup["environments"]["HOTFIX"]["workspace"]["capacity"]["id"])
        self.assertEqual({"capacity.HOTFIX": "Other", "capacity.PROD": "Cap"}, setup["answers"])
        self.assertIn("supplied by user", (self.repo / "cicd/fabric/SETUP.md").read_text(encoding="utf-8").lower())

    def test_failed_connection_lookup_asks_instead_of_guessing(self) -> None:
        self.run_plan("--answer", "capacity.PROD=Cap", "--answer", "capacity.HOTFIX=Cap", tools=FakeTools(known_connection_name=False))
        keys = {q["key"] for q in self.setup()["open_questions"]}
        self.assertEqual({f"connection_name.{CONNECTION}"}, keys)

    def test_dependency_and_rules_are_generated(self) -> None:
        self.run_plan("--answer", "capacity.PROD=Cap", "--answer", "capacity.HOTFIX=Cap", "--exclude-guid", UNKNOWN)
        rules = {(r["find_value"], r["replace_value"]["HOTFIX"]) for r in self.setup()["bindings"]["rules"]}
        self.assertIn((LAKE_LOGICAL, "$items.Lakehouse.Lake.$id"), rules)
        self.assertIn((CONNECTION, CONNECTION), rules)


if __name__ == "__main__":
    unittest.main()
