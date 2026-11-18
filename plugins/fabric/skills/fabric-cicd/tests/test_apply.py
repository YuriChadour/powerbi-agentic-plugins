"""approve.py and apply.py against a fake developer-session tool layer."""
from __future__ import annotations

import copy
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))


def load(name):
    spec = importlib.util.spec_from_file_location(name, SKILL / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


approve, ops_module, apply = load("approve"), load("ops"), load("apply")
StepError = ops_module.StepError

APP = "e4b14c44-12a7-4882-a5ed-dbcb036c9d7b"
SP = "97937f89-9a24-49f4-a3be-c757d283b03d"
DEV_USER = "13298c1e-421e-4dd8-9896-26342560504a"
OWNER = "abeda224-528f-4ff7-9219-fb2d0eb1817f"
CONNECTION = "28623ad9-a18e-4685-84ae-698a6dc23547"
ENVS = ("DEV", "TEST", "PROD", "HOTFIX")


def make_setup() -> dict:
    envs = {}
    for i, env in enumerate(ENVS, 1):
        envs[env] = {
            "workspace": {"name": f"WS {env}", "id": f"{i}{i}{i}{i}{i}{i}{i}{i}-1111-4111-8111-111111111111" if env != "HOTFIX" else None, "create": env == "HOTFIX", "capacity": {"id": "cap", "name": "Cap"}},
            "variable_group": {"name": "powerbi eot", "exists": True, "variables": None},
            "private_pool": {"name": "BAM-IaC-CloudEng", "exists": True},
            "key_vault": {"service_connection": "BAM-PROD Key Vault (WIF)", "service_connection_id": "endpoint-1", "service_connection_exists": True, "name": "BAM-KV-PBI-Prod", "secret": "powerbi-eot-secret"},
            "ado_environment": f"fabric-{env.lower()}", "pipeline_name": f"Repo Fabric {env}",
            "pipeline_yaml": f"cicd/fabric/fabric-{env.lower()}.yml", "branch": "hotfix/*" if env == "HOTFIX" else env,
        }
    return {
        "version": 1,
        "repository": {"source_root": "fabric", "ci_folder": "cicd/fabric", "azure_devops": {"organization": "https://dev.azure.com/org", "project": "Proj X", "repository": "Repo"}},
        "tenant_id": "t", "service_principal": {"app_id": APP, "object_id": SP}, "environments": envs,
        "managed_items": [{"folder": "Lake.Lakehouse", "type": "Lakehouse", "name": "Lake", "dependencies": []}],
        "excluded": [{"path": "pbi/**", "reason": "x"}],
        "connections": [{"id": CONNECTION, "display_name": "Service_1 - Service", "required_permission": "User", "roles": None}],
        "pipeline_invocation_connections": [CONNECTION],
        "bindings": {"rules": [{"find_value": "x", "item_type": "Notebook", "replace_value": {e: "$workspace.$id" for e in ENVS}}], "excluded_guids": []},
        "dev_items": [], "gaps": [], "answers": {}, "open_questions": [],
    }


class FakeOps:
    """In-memory Fabric and Azure DevOps; records every write."""

    def __init__(self):
        self.posts, self.workspaces, self.items, self.roles, self.conn_roles = [], {}, {}, {}, {}
        for i, env in enumerate(ENVS[:3], 1):
            wid = f"{i}{i}{i}{i}{i}{i}{i}{i}-1111-4111-8111-111111111111"
            self.workspaces[wid] = {"id": wid, "displayName": f"WS {env}"}
            self.items[wid] = [{"type": "Lakehouse", "displayName": "Lake"}]
            self.roles[wid] = []
        self.conn_roles[CONNECTION] = [{"principal": {"id": OWNER, "type": "User"}, "role": "Owner"}]
        self.deny_connection_grant = False
        self.groups = [{"id": 23, "variables": {"FABRIC_TENANT_ID": {"value": "t"}, "FABRIC_APP_ID": {"value": APP}}}]
        self.pools = [{"id": 7, "name": "BAM-IaC-CloudEng"}]
        self.queues = [{"id": 70, "name": "BAM-IaC-CloudEng"}]
        self.service_connections = [{"id": "endpoint-1", "name": "BAM-PROD Key Vault (WIF)", "type": "azurerm"}]
        self.environments, self.pipelines, self.authorized = [], {f"Repo Fabric {e}": {"id": 100 + i, "yaml": f"cicd/fabric/fabric-{e.lower()}.yml"} for i, e in enumerate(ENVS)}, set()

    def fab_get(self, path):
        parts = path.split("/")
        if path == "workspaces":
            return {"value": list(self.workspaces.values())}
        if parts[0] == "workspaces" and len(parts) == 2:
            return self.workspaces.get(parts[1])
        if path.endswith("/items"):
            return {"value": self.items.get(parts[1], [])}
        if path.endswith("/roleAssignments") and parts[0] == "workspaces":
            return {"value": self.roles.get(parts[1], [])}
        if path.endswith("/roleAssignments") and parts[0] == "connections":
            return {"value": self.conn_roles.get(parts[1])} if parts[1] in self.conn_roles else None
        return None

    def fab_post(self, path, body):
        if self.deny_connection_grant and path.startswith("connections/"):
            raise StepError("403 forbidden")
        self.posts.append((path, body))
        parts = path.split("/")
        if path == "workspaces":
            wid = "77777777-1111-4111-8111-111111111111"
            self.workspaces[wid] = {"id": wid, "displayName": body["displayName"]}
            self.items[wid], self.roles[wid] = [], []
            return {"id": wid}
        if path.endswith("/lakehouses"):
            self.items[parts[1]].append({"type": "Lakehouse", "displayName": body["displayName"]})
        if path.endswith("/roleAssignments"):
            target = self.roles if parts[0] == "workspaces" else self.conn_roles
            target[parts[1]].append({"principal": body["principal"], "role": body["role"]})
        return {}

    def developer_object_id(self):
        return DEV_USER

    def az_json(self, *args):
        if args[:2] == ("pipelines", "variable-group"):
            return self.groups
        if args[:2] == ("pipelines", "list"):
            name = args[args.index("--name") + 1]
            return [{"id": self.pipelines[name]["id"]}] if name in self.pipelines else []
        if args[:2] == ("pipelines", "show"):
            pid = int(args[args.index("--id") + 1])
            yaml_path = next(p["yaml"] for p in self.pipelines.values() if p["id"] == pid)
            return {"process": {"yamlFilename": yaml_path}}
        if args[:3] == ("pipelines", "pool", "list"):
            return self.pools
        if args[:3] == ("devops", "service-endpoint", "list"):
            return self.service_connections

    def ado_rest(self, method, url, body=None):
        if "/queues?" in url:
            return {"value": self.queues}
        if "/environments" in url:
            if method == "post":
                self.environments.append({"name": body["name"], "id": 40 + len(self.environments)})
                return self.environments[-1]
            return {"value": self.environments}
        if method == "patch":
            self.authorized.add((url, body["pipelines"][0]["id"]))
            return {}
        return {"pipelines": [{"id": pid, "authorized": True} for u, pid in self.authorized if u == url]}


class ApprovalTests(unittest.TestCase):
    def write(self, setup):
        self.dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        path = self.dir / "setup.yml"
        path.write_text(yaml.safe_dump(setup, sort_keys=True), encoding="utf-8")
        return path

    def test_approval_is_refused_with_gaps_or_questions(self):
        setup = make_setup()
        setup["gaps"] = [{"guid": "g", "file": "f", "reason": "r"}]
        path = self.write(setup)
        self.assertEqual(1, approve.main(["--setup", str(path)]))
        self.assertFalse((self.dir / "setup.approved").exists())

    def test_clean_setup_is_approved_and_edit_is_detected(self):
        path = self.write(make_setup())
        self.assertEqual(0, approve.main(["--setup", str(path)]))
        apply.load_setup(path)
        path.write_text(path.read_text(encoding="utf-8") + "# edit\n", encoding="utf-8")
        with self.assertRaises(StepError) as raised:
            apply.load_setup(path)
        self.assertIn("changed after approval", str(raised.exception))

    def test_unapproved_setup_is_refused(self):
        path = self.write(make_setup())
        with self.assertRaises(StepError):
            apply.load_setup(path)


class GenerateTests(unittest.TestCase):
    IDS = {e: f"{i}{i}{i}{i}{i}{i}{i}{i}-1111-4111-8111-111111111111" for i, e in enumerate(ENVS, 1)}

    def test_two_runs_are_identical_and_complete(self):
        first, second = apply.generate(make_setup(), self.IDS), apply.generate(make_setup(), self.IDS)
        self.assertEqual(first, second)
        for expected in ("cicd/fabric/config.yml", "cicd/fabric/parameter.yml", "cicd/fabric/managed-items.yml", "cicd/fabric/connection-bindings.yml",
                         "cicd/fabric/fabric-hotfix.yml", "cicd/fabric/deploy_runner.py", "cicd/shared/secret_scan.py", "cicd/fabric/requirements-fabric-cicd.lock"):
            self.assertIn(expected, first)
        config = yaml.safe_load(first["cicd/fabric/config.yml"])
        self.assertEqual(self.IDS, config["core"]["workspace_id"])

    def test_write_files_is_idempotent(self):
        repo = Path(self.enterContext(tempfile.TemporaryDirectory()))
        files = apply.generate(make_setup(), self.IDS)
        self.assertEqual(len(files), len(apply.write_files(repo, files)))
        self.assertEqual([], apply.write_files(repo, files))


class StepTests(unittest.TestCase):
    def setUp(self):
        self.ops, self.setup = FakeOps(), make_setup()

    def test_bootstrap_creates_missing_then_is_idempotent_and_runs_no_workload(self):
        ids = apply.bootstrap(self.setup, self.ops)
        created = [p for p, _ in self.ops.posts]
        self.assertEqual(["workspaces", "workspaces/77777777-1111-4111-8111-111111111111/lakehouses"], created)
        self.assertTrue(self.ops.posts[1][1]["creationPayload"]["enableSchemas"])
        self.ops.posts.clear()
        self.assertEqual(ids, apply.bootstrap(self.setup, self.ops))
        self.assertEqual([], self.ops.posts)
        self.assertFalse(any("jobs" in p or "run" in p.lower() for p, _ in self.ops.posts))

    def test_grants_are_idempotent_and_cover_owner_on_test_prod(self):
        ids = apply.bootstrap(self.setup, self.ops)
        apply.grants(self.setup, self.ops, ids)
        paths = [p for p, _ in self.ops.posts if p.endswith("roleAssignments")]
        self.assertEqual(4 + 2 + 2, len(paths))  # SP x4 workspaces, SP+developer on the connection, owner on TEST+PROD
        self.ops.posts.clear()
        apply.grants(self.setup, self.ops, ids)
        self.assertEqual([], self.ops.posts)

    def test_missing_connection_permission_stops_naming_the_connection(self):
        ids = apply.bootstrap(self.setup, self.ops)
        self.ops.deny_connection_grant = True
        with self.assertRaises(StepError) as raised:
            apply.grants(self.setup, self.ops, ids)
        self.assertIn(CONNECTION, str(raised.exception))

    def azure(self):
        repo = Path(self.enterContext(tempfile.TemporaryDirectory()))
        apply.write_files(repo, apply.generate(self.setup, GenerateTests.IDS))
        apply.azure_devops(self.setup, self.ops, repo)

    def test_azure_devops_creates_environments_authorizes_pipelines_and_is_idempotent(self):
        self.azure()
        self.assertEqual(4, len(self.ops.environments))
        self.assertEqual(16, len(self.ops.authorized))
        before = len(self.ops.environments)
        self.azure()
        self.assertEqual(before, len(self.ops.environments))
        self.assertEqual(16, len(self.ops.authorized))

    def test_missing_group_pool_service_connection_wrong_app_and_unregistered_pipeline_stop(self):
        cases = {
            "does not exist": lambda o: setattr(o, "groups", []),
            "private pool": lambda o: setattr(o, "pools", []),
            "Key Vault service connection": lambda o: setattr(o, "service_connections", []),
            "FABRIC_APP_ID": lambda o: o.groups[0]["variables"].pop("FABRIC_APP_ID"),
            "does not match service principal": lambda o: o.groups[0]["variables"]["FABRIC_APP_ID"].update(value="other"),
            "is not registered": lambda o: o.pipelines.pop("Repo Fabric PROD"),
        }
        for message, mutate in cases.items():
            self.ops, self.setup = FakeOps(), make_setup()
            mutate(self.ops)
            with self.subTest(message), self.assertRaises(StepError) as raised:
                self.azure()
            self.assertIn(message, str(raised.exception))


if __name__ == "__main__":
    unittest.main()
