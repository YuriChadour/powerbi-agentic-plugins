from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(TESTS.parent / "scripts"))
import apply
import approve
from setup_contract import dump_setup
from test_setup_contract import valid_setup


class FakeOps:
    def __init__(self, setup: dict[str, Any]):
        self.setup = setup
        self.calls: list[tuple[str, ...]] = []
        self.writes: list[tuple[str, ...]] = []
        self.workspaces = {
            config["workspace"]["id"]: {
                "id": config["workspace"]["id"],
                "displayName": config["workspace"]["name"],
                "capacityId": config["capacity"]["id"],
                "gitConnected": False,
            }
            for config in setup["environments"].values()
        }
        self.workspace_roles = {
            target: [
                {"principal": {"id": role["object_id"], "type": role["principal_type"]}, "role": role["role"]}
                for role in config["direct_roles"]
            ]
            for target, config in setup["environments"].items()
        }
        self.connection_roles: dict[str, list[dict[str, Any]]] = {}
        for target in apply.target_names(setup):
            content_target = "PROD" if target == "HOTFIX" else target
            principal = setup["environments"][target]["runtime_identity"]["object_id"]
            for connection_id in setup["semantic_model_bindings"]["SalesModel"][content_target]:
                self.connection_roles.setdefault(connection_id, []).append(
                    {"principal": {"id": principal, "type": "ServicePrincipal"}, "role": "User"}
                )
        self.personal_cloud: set[str] = set()
        self.pipelines: dict[str, dict[str, Any]] = {}
        for index, target in enumerate(apply.target_names(setup), start=1):
            config = setup["environments"][target]
            self.pipelines[config["pipeline_name"]] = {
                "id": 8000 + index,
                "name": config["pipeline_name"],
                "process": {"yamlFilename": config["pipeline_yaml"]},
            }
        self.environments = {
            config["ado_environment"]: {"id": 9000 + index, "name": config["ado_environment"]}
            for index, config in enumerate(setup["environments"].values(), start=1)
        }
        self.group_mismatch: str | None = None
        self.endpoint_authorized = True
        self.permission_authorized = True

    def target_for_workspace(self, workspace_id: str) -> str:
        return next(target for target, config in self.setup["environments"].items() if config["workspace"]["id"] == workspace_id)

    def fab_get(self, path: str) -> Any:
        self.calls.append(("fab_get", path))
        if path == "workspaces":
            return {"value": list(self.workspaces.values())}
        if path.startswith("workspaces/") and path.endswith("/roleAssignments"):
            workspace_id = path.split("/")[1]
            return {"value": list(self.workspace_roles[self.target_for_workspace(workspace_id)])}
        if path.startswith("workspaces/"):
            return self.workspaces.get(path.split("/")[1])
        if path.startswith("connections/") and path.endswith("/roleAssignments"):
            return {"value": list(self.connection_roles.get(path.split("/")[1], []))}
        if path.startswith("connections/"):
            connection_id = path.split("/")[1]
            return {"id": connection_id, "personalCloud": connection_id in self.personal_cloud}
        return None

    def fab_post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("fab_post", path))
        self.writes.append(("fab_post", path))
        if path == "workspaces":
            return {"id": "50000000-0000-4000-8000-000000000001", "displayName": body["displayName"], "gitConnected": False}
        if path.startswith("workspaces/") and path.endswith("/roleAssignments"):
            workspace_id = path.split("/")[1]
            target = self.target_for_workspace(workspace_id)
            self.workspace_roles[target].append({"principal": body["principal"], "role": body["role"]})
            return {}
        raise AssertionError(f"unexpected Fabric write: {path}")

    @staticmethod
    def argument(args: tuple[str, ...], name: str) -> str:
        return args[args.index(name) + 1]

    def az_json(self, *args: str) -> Any:
        self.calls.append(("az_json", *args))
        if args[:3] == ("ad", "sp", "show"):
            app_id = self.argument(args, "--id")
            return {"id": app_id if app_id in {item["runtime_identity"]["app_id"] for item in self.setup["environments"].values()} else self.setup["service_principal"]["object_id"]}
        if args[:3] == ("pipelines", "variable-group", "list"):
            name = self.argument(args, "--group-name")
            target = next(item for item, config in self.setup["environments"].items() if config["variable_group"] == name)
            app_id = self.group_mismatch or self.setup["environments"][target]["runtime_identity"]["app_id"]
            return [{"id": 7000 + list(self.setup["environments"]).index(target), "name": name, "variables": {"AZURE_CLIENT_ID": {"value": app_id}}}]
        if args[:3] == ("pipelines", "pool", "list"):
            return [{"id": 6001, "name": "Private Windows"}]
        if args[:3] == ("devops", "service-endpoint", "list"):
            return [
                {"id": config["key_vault"]["service_connection_id"], "name": config["key_vault"]["service_connection"], "authorized": self.endpoint_authorized}
                for config in self.setup["environments"].values()
            ]
        if args[:2] == ("pipelines", "list"):
            name = self.argument(args, "--name")
            return [self.pipelines[name]] if name in self.pipelines else []
        if args[:2] == ("pipelines", "show"):
            pipeline_id = int(self.argument(args, "--id"))
            return next(item for item in self.pipelines.values() if item["id"] == pipeline_id)
        if args[:2] == ("pipelines", "create"):
            self.writes.append(("pipelines_create", self.argument(args, "--name")))
            name = self.argument(args, "--name")
            pipeline = {"id": 10000 + len(self.pipelines), "name": name, "process": {"yamlFilename": self.argument(args, "--yml-path")}}
            self.pipelines[name] = pipeline
            return pipeline
        return None

    def ado_rest(self, method: str, url: str, body: dict[str, Any] | None = None) -> Any:
        self.calls.append(("ado_rest", method, url))
        if method.casefold() != "get":
            self.writes.append(("ado_rest", method, url))
        if "distributedtask/environments" in url and method.casefold() == "get":
            return {"value": list(self.environments.values())}
        if "distributedtask/environments" in url and method.casefold() == "post":
            value = {"id": 10000 + len(self.environments), "name": body["name"]}
            self.environments[value["name"]] = value
            return value
        if "distributedtask/queues" in url:
            pool = self.argument_from_url(url, "queueName=").replace("%20", " ")
            return {"value": [{"id": 5000, "name": pool}]}
        if "pipelinePermissions" in url:
            if method.casefold() == "patch":
                self.permission_authorized = True
            return {"allPipelines": {"authorized": self.permission_authorized}, "pipelines": []}
        return {"value": []}

    @staticmethod
    def argument_from_url(url: str, key: str) -> str:
        return url.split(key, 1)[1].split("&", 1)[0]


class ApplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        self.setup_path = self.repo / "cicd/powerbi/setup.yml"
        self.setup_path.parent.mkdir(parents=True)
        self.setup = valid_setup()
        for target, config in self.setup["environments"].items():
            config["key_vault"]["service_connection"] = f"Power BI {target} WIF"
        self.write_setup()
        self.ops = FakeOps(self.setup)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_setup(self) -> None:
        self.setup_path.write_text(dump_setup(self.setup), encoding="utf-8", newline="\n")

    def approve(self) -> None:
        self.write_setup()
        self.assertEqual(0, approve.main(["--setup", str(self.setup_path)]))

    def test_missing_approval_blocks_generation_and_all_external_calls(self) -> None:
        self.assertEqual(2, apply.main(["--repo", str(self.repo)], ops=self.ops))
        self.assertEqual([], self.ops.calls)
        self.assertFalse((self.repo / "cicd/powerbi/bootstrap-config.json").exists())
        self.assertFalse((self.repo / "cicd/powerbi/apply-readiness.json").exists())

    def test_approved_apply_is_idempotent_and_runs_no_workload(self) -> None:
        self.approve()
        self.assertEqual(0, apply.main(["--repo", str(self.repo)], ops=self.ops))
        self.assertEqual([], self.ops.writes)
        evidence = json.loads((self.repo / "cicd/powerbi/apply-readiness.json").read_text(encoding="utf-8"))
        self.assertEqual("completed", evidence["status"])
        self.assertIn("workloads_run", evidence["completed_steps"][-2])
        evidence_text = (self.repo / "cicd/powerbi/apply-readiness.json").read_text(encoding="utf-8")
        self.assertNotIn("secret_reference", evidence_text)
        self.assertNotIn("powerbi-client-secret", evidence_text)
        before = list(self.ops.writes)
        self.assertEqual(0, apply.main(["--repo", str(self.repo)], ops=self.ops))
        self.assertEqual(before, self.ops.writes)

    def test_role_reconciliation_adds_only_an_approved_direct_role(self) -> None:
        self.approve()
        self.ops.workspace_roles["TEST"] = []
        self.assertEqual(0, apply.main(["--repo", str(self.repo)], ops=self.ops))
        self.assertEqual([("fab_post", f"workspaces/{self.setup['environments']['TEST']['workspace']['id']}/roleAssignments")], self.ops.writes)
        self.ops.writes.clear()
        self.assertEqual(0, apply.main(["--repo", str(self.repo)], ops=self.ops))
        self.assertEqual([], self.ops.writes)

    def test_connected_or_unreviewed_workspace_blocks_before_workspace_write(self) -> None:
        self.approve()
        workspace_id = self.setup["environments"]["TEST"]["workspace"]["id"]
        self.ops.workspaces[workspace_id]["gitConnected"] = True
        self.assertEqual(2, apply.main(["--repo", str(self.repo)], ops=self.ops))
        self.assertFalse(any(kind == "fab_post" for kind, *_ in self.ops.writes))
        evidence = json.loads((self.repo / "cicd/powerbi/apply-readiness.json").read_text(encoding="utf-8"))
        self.assertEqual("blocked", evidence["status"])
        self.assertIn("Git-disconnected", evidence["blocked_step"]["reason"])

    def test_connection_failure_names_resource_and_precedes_ado_write(self) -> None:
        self.approve()
        connection_id = self.setup["semantic_model_bindings"]["SalesModel"]["TEST"][0]
        self.ops.connection_roles[connection_id] = []
        self.assertEqual(2, apply.main(["--repo", str(self.repo)], ops=self.ops))
        self.assertFalse(any("az_json" == call[0] and len(call) > 1 and call[1] == "pipelines" for call in self.ops.calls))
        evidence = json.loads((self.repo / "cicd/powerbi/apply-readiness.json").read_text(encoding="utf-8"))
        self.assertIn(connection_id, evidence["blocked_step"]["reason"])

    def test_personal_cloud_connection_blocks_without_write(self) -> None:
        self.approve()
        connection_id = self.setup["semantic_model_bindings"]["SalesModel"]["PROD"][0]
        self.ops.personal_cloud.add(connection_id)
        self.assertEqual(2, apply.main(["--repo", str(self.repo)], ops=self.ops))
        self.assertEqual([], self.ops.writes)

    def test_variable_group_identity_mismatch_stops_before_ado_write(self) -> None:
        self.approve()
        self.ops.group_mismatch = "99999999-9999-4999-8999-999999999999"
        self.assertEqual(2, apply.main(["--repo", str(self.repo)], ops=self.ops))
        self.assertFalse(self.ops.writes)
        evidence = json.loads((self.repo / "cicd/powerbi/apply-readiness.json").read_text(encoding="utf-8"))
        self.assertIn("runtime identity", evidence["blocked_step"]["reason"])

    def test_pipeline_registration_and_rerun_follow_external_state(self) -> None:
        self.approve()
        missing = self.setup["environments"]["TEST"]["pipeline_name"]
        self.ops.pipelines.pop(missing)
        self.assertEqual(0, apply.main(["--repo", str(self.repo)], ops=self.ops))
        self.assertEqual([("pipelines_create", missing)], self.ops.writes)
        self.ops.writes.clear()
        self.assertEqual(0, apply.main(["--repo", str(self.repo)], ops=self.ops))
        self.assertEqual([], self.ops.writes)

    def test_protected_resource_failure_resumes_from_current_state(self) -> None:
        self.approve()
        self.ops.endpoint_authorized = False
        self.assertEqual(2, apply.main(["--repo", str(self.repo)], ops=self.ops))
        evidence = json.loads((self.repo / "cicd/powerbi/apply-readiness.json").read_text(encoding="utf-8"))
        self.assertEqual("azure_devops", evidence["blocked_step"]["step"])
        self.ops.endpoint_authorized = True
        self.assertEqual(0, apply.main(["--repo", str(self.repo)], ops=self.ops))
        self.assertFalse(any(write[0] == "pipelines_create" for write in self.ops.writes))

    def test_pipeline_permissions_are_granted_once_and_then_become_noops(self) -> None:
        self.approve()
        self.ops.permission_authorized = False
        self.assertEqual(0, apply.main(["--repo", str(self.repo)], ops=self.ops))
        patches = [write for write in self.ops.writes if len(write) > 1 and write[1] == "patch"]
        self.assertEqual(1, len(patches))
        self.ops.writes.clear()
        self.assertEqual(0, apply.main(["--repo", str(self.repo)], ops=self.ops))
        self.assertEqual([], self.ops.writes)


if __name__ == "__main__":
    unittest.main()
