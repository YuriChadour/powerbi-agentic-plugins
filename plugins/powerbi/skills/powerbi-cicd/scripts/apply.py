"""Apply an approved Power BI setup through fixed, resumable, non-deployment steps."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from approve import verify_approval  # noqa: E402
from generation import generated_files, write_files  # noqa: E402
from powerbi_cicd import validate_config, validate_manifest  # noqa: E402
from setup_contract import load_setup, validate_setup  # noqa: E402

ADO_RESOURCE = "499b84ac-1321-427f-aa17-267ca6975798"
TARGET_ORDER = ("DEV", "TEST", "PROD", "HOTFIX", "UAT", "REHEARSAL")
RANK = {"Viewer": 0, "Contributor": 1, "Member": 2, "Admin": 3}


class StepError(Exception):
    """A fail-closed apply step with an actionable operator message."""


class ApplyOps:
    """Developer-session operations for the reviewed setup sequence only."""

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        executable = shutil.which(command[0])
        if not executable:
            raise StepError(f"'{command[0]}' is not installed or not on PATH; install it and sign in as the developer")
        return subprocess.run([executable, *command[1:]], capture_output=True, text=True, check=False)

    def fab_get(self, path: str) -> Any:
        done = self._run(["fab", "api", path])
        try:
            body = json.loads(done.stdout)
        except json.JSONDecodeError:
            return None
        return body.get("text") if done.returncode == 0 and body.get("status_code") == 200 else None

    def fab_post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        done = self._run(["fab", "api", "-X", "post", path, "-i", json.dumps(body)])
        try:
            reply = json.loads(done.stdout)
        except json.JSONDecodeError:
            reply = {}
        status = reply.get("status_code")
        if done.returncode or status not in (200, 201, 202):
            raise StepError(f"POST {path} failed ({status or done.returncode}); check the developer's reviewed authorization")
        return reply.get("text") or {}

    def az_json(self, *args: str) -> Any:
        done = self._run(["az", *args, "--output", "json"])
        if done.returncode:
            return None
        try:
            return json.loads(done.stdout)
        except json.JSONDecodeError:
            return None

    def ado_rest(self, method: str, url: str, body: dict[str, Any] | None = None) -> Any:
        command = ["az", "rest", "--resource", ADO_RESOURCE, "--method", method, "--url", url]
        temp_dir: Path | None = None
        if body is not None:
            temp_dir = Path(tempfile.mkdtemp(prefix="powerbi-apply-"))
            body_path = temp_dir / "body.json"
            body_path.write_text(json.dumps(body), encoding="utf-8")
            command += ["--body", f"@{body_path}", "--headers", "Content-Type=application/json"]
        try:
            done = self._run(command)
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
        if done.returncode:
            if method.casefold() == "get":
                return None
            raise StepError(f"Azure DevOps {method} failed for {url}; check the reviewed project permission")
        return json.loads(done.stdout) if done.stdout.strip() else {}


def target_names(setup: dict[str, Any]) -> list[str]:
    return [target for target in TARGET_ORDER if target in setup["environments"]]


def workspace_git_state(value: dict[str, Any]) -> bool | None:
    for key in ("git_connected", "gitConnected"):
        if key in value:
            return bool(value[key])
    git = value.get("git") if isinstance(value.get("git"), dict) else {}
    if "connected" in git:
        return bool(git["connected"])
    return None


def workspace_steps(setup: dict[str, Any], ops: ApplyOps | Any) -> dict[str, str]:
    """Create or reuse only reviewed workspaces, then enforce the reviewed state."""
    ids: dict[str, str] = {}
    listed = ops.fab_get("workspaces")
    values = listed.get("value", []) if isinstance(listed, dict) else []
    for target in target_names(setup):
        config = setup["environments"][target]
        workspace = config["workspace"]
        current = ops.fab_get(f"workspaces/{workspace['id']}") if workspace.get("id") else None
        if current is None and workspace["create"] is True:
            current = next((item for item in values if item.get("displayName") == workspace["name"]), None)
            if current is None:
                capacity_id = config["capacity"].get("id")
                if not capacity_id:
                    raise StepError(f"{target}: workspace '{workspace['name']}' needs an approved capacity ID before creation")
                current = ops.fab_post("workspaces", {"displayName": workspace["name"], "capacityId": capacity_id})
                values.append(current)
        if not isinstance(current, dict) or not current.get("id"):
            raise StepError(f"{target}: reviewed workspace '{workspace['name']}' is unavailable; confirm the exact workspace mapping and developer access")
        if workspace.get("id") and str(current["id"]).casefold() != str(workspace["id"]).casefold():
            raise StepError(f"{target}: workspace '{workspace['name']}' ID changed; re-run plan and approval")
        if current.get("displayName", workspace["name"]) != workspace["name"]:
            raise StepError(f"{target}: workspace ID resolves to a different name than '{workspace['name']}'")
        if workspace_git_state(current) is not False:
            raise StepError(f"{target}: workspace '{workspace['name']}' is not confirmed Git-disconnected")
        ids[target] = str(current["id"])
    return ids


def role_at_least(assignments: list[dict[str, Any]], principal: str, minimum: str) -> bool:
    return any(
        str(item.get("principal", {}).get("id", "")).casefold() == principal.casefold()
        and RANK.get(item.get("role"), -1) >= RANK[minimum]
        for item in assignments
    )


def role_steps(setup: dict[str, Any], ids: dict[str, str], ops: ApplyOps | Any) -> int:
    """Reconcile only direct roles explicitly present in the setup contract."""
    writes = 0
    for target in target_names(setup):
        assignments = ops.fab_get(f"workspaces/{ids[target]}/roleAssignments")
        if not isinstance(assignments, dict) or not isinstance(assignments.get("value"), list):
            raise StepError(f"{target}: cannot read roles for workspace '{setup['environments'][target]['workspace']['name']}'; request reviewed Admin access")
        for role in setup["environments"][target]["direct_roles"]:
            if role_at_least(assignments["value"], role["object_id"], role["role"]):
                continue
            ops.fab_post(
                f"workspaces/{ids[target]}/roleAssignments",
                {"principal": {"id": role["object_id"], "type": role["principal_type"]}, "role": role["role"]},
            )
            writes += 1
            assignments["value"].append({"principal": {"id": role["object_id"], "type": role["principal_type"]}, "role": role["role"]})
    return writes


def _service_principal(ops: ApplyOps | Any, app_id: str, label: str) -> dict[str, Any]:
    value = ops.az_json("ad", "sp", "show", "--id", app_id)
    if not isinstance(value, dict) or not value.get("id"):
        raise StepError(f"{label}: service principal {app_id} is unreadable; grant the developer the reviewed directory read permission")
    return value


def identity_and_connection_steps(setup: dict[str, Any], ids: dict[str, str], ops: ApplyOps | Any) -> None:
    service_principal = setup["service_principal"]
    discovered = _service_principal(ops, service_principal["app_id"], "setup identity")
    if str(discovered["id"]).casefold() != service_principal["object_id"].casefold():
        raise StepError("setup identity: application and object ID do not match; re-run plan")

    bindings = setup["semantic_model_bindings"]
    by_connection = {connection["id"]: connection for connection in setup["connections"]}
    for target in target_names(setup):
        runtime = setup["environments"][target]["runtime_identity"]
        principal = _service_principal(ops, runtime["app_id"], f"{target} runtime identity")
        if str(principal["id"]).casefold() != runtime["object_id"].casefold():
            raise StepError(f"{target}: runtime identity {runtime['app_id']} resolves to the wrong object; re-run plan")
        content_target = "PROD" if target == "HOTFIX" else target
        required = sorted({connection_id for values in bindings.values() for connection_id in values[content_target]})
        for connection_id in required:
            connection = ops.fab_get(f"connections/{connection_id}")
            if not isinstance(connection, dict) or str(connection.get("id", connection_id)).casefold() != connection_id.casefold():
                raise StepError(f"{target}: approved Power BI connection {connection_id} is missing or unreadable")
            if connection.get("personal_cloud") is True or connection.get("personalCloud") is True:
                raise StepError(f"{target}: Power BI connection {connection_id} is a personal-cloud connection")
            assignments = ops.fab_get(f"connections/{connection_id}/roleAssignments")
            roles = assignments.get("value") if isinstance(assignments, dict) else None
            if not isinstance(roles, list):
                raise StepError(f"{target}: cannot read roles for Power BI connection {connection_id}; ask its owner for reviewed access")
            permitted = any(
                str(role.get("principal", {}).get("id", "")).casefold() == runtime["object_id"].casefold()
                and role.get("role") in {"Owner", "User"}
                for role in roles
            )
            if not permitted:
                raise StepError(f"{target}: runtime identity {runtime['reference']} lacks direct access to Power BI connection {connection_id}")
            listed = by_connection.get(connection_id)
            if not listed or listed["required_permission"] not in {"Owner", "User"}:
                raise StepError(f"{target}: Power BI connection {connection_id} has an unsupported reviewed permission")


def _one_named(values: Any, name: str) -> dict[str, Any] | None:
    if not isinstance(values, list):
        return None
    return next((value for value in values if isinstance(value, dict) and value.get("name") == name), None)


def _identity_value(variables: dict[str, Any]) -> str:
    for name in ("AZURE_CLIENT_ID", "POWERBI_APP_ID", "FABRIC_APP_ID"):
        value = variables.get(name)
        if isinstance(value, dict) and isinstance(value.get("value"), str):
            return value["value"].casefold()
        if isinstance(value, str):
            return value.casefold()
    return ""


def _endpoint_authorized(endpoint: dict[str, Any]) -> bool:
    if endpoint.get("authorized") is False or endpoint.get("isReady") is False:
        return False
    data = endpoint.get("data") if isinstance(endpoint.get("data"), dict) else {}
    authorization = endpoint.get("authorization") if isinstance(endpoint.get("authorization"), dict) else {}
    scheme = data.get("scheme") or authorization.get("scheme") or endpoint.get("authorizationScheme")
    return endpoint.get("authorized") is True or endpoint.get("isReady") is True or (
        isinstance(scheme, str) and scheme.replace("_", "").casefold() in {"workloadidentityfederation", "wif"}
    )


def azure_devops_steps(setup: dict[str, Any], repo: Path, ops: ApplyOps | Any) -> None:
    ado = setup["repository"]["azure_devops"]
    organization, project = ado["organization"].rstrip("/"), ado["project"]
    base = f"{organization}/{quote(project, safe='')}/_apis"
    pools = ops.az_json("pipelines", "pool", "list", "--org", organization) or []
    pool_names = {pool.get("name") for pool in pools if isinstance(pool, dict)}
    endpoints = ops.az_json("devops", "service-endpoint", "list", "--org", organization, "--project", project) or []
    endpoint_names = {endpoint.get("name"): endpoint for endpoint in endpoints if isinstance(endpoint, dict)}
    environment_body = ops.ado_rest("get", f"{base}/distributedtask/environments?api-version=7.1") or {}
    environments = {item.get("name"): item for item in environment_body.get("value", []) if isinstance(item, dict)}

    context: dict[str, dict[str, Any]] = {}
    for target in target_names(setup):
        config = setup["environments"][target]
        groups = ops.az_json(
            "pipelines", "variable-group", "list", "--group-name", config["variable_group"],
            "--org", organization, "--project", project,
        ) or []
        group = _one_named(groups, config["variable_group"])
        if group is None:
            raise StepError(f"{target}: variable group '{config['variable_group']}' is missing or unreadable")
        if _identity_value(group.get("variables", {})) != config["runtime_identity"]["app_id"].casefold():
            raise StepError(f"{target}: variable group '{config['variable_group']}' runtime identity does not match the approved application")
        if config["private_pool"] not in pool_names:
            raise StepError(f"{target}: private pool '{config['private_pool']}' is unavailable")
        queues = ops.ado_rest("get", f"{base}/distributedtask/queues?queueName={quote(config['private_pool'])}&api-version=7.1") or {}
        queue = next((item for item in queues.get("value", []) if item.get("name") == config["private_pool"]), None)
        if queue is None:
            raise StepError(f"{target}: private pool queue '{config['private_pool']}' is not authorized")
        key_vault = config["key_vault"]
        endpoint = endpoint_names.get(key_vault["service_connection"])
        if endpoint is None or not _endpoint_authorized(endpoint):
            raise StepError(f"{target}: WIF Key Vault service connection '{key_vault['service_connection']}' is missing or unauthorized")
        if key_vault.get("service_connection_id") and str(endpoint.get("id")) != key_vault["service_connection_id"]:
            raise StepError(f"{target}: WIF Key Vault service connection ID changed; re-run plan")
        environment = environments.get(config["ado_environment"])
        if environment is None:
            environment = ops.ado_rest("post", f"{base}/distributedtask/environments?api-version=7.1", {"name": config["ado_environment"]})
            if not isinstance(environment, dict) or not environment.get("id"):
                raise StepError(f"{target}: could not create Azure DevOps environment '{config['ado_environment']}'")
            environments[config["ado_environment"]] = environment
        context[target] = {"group": group, "queue": queue, "endpoint": endpoint, "environment": environment}

    for target in target_names(setup):
        config = setup["environments"][target]
        if not (repo / config["pipeline_yaml"]).is_file():
            raise StepError(f"{target}: generated pipeline YAML '{config['pipeline_yaml']}' is missing")
        pipelines = ops.az_json("pipelines", "list", "--name", config["pipeline_name"], "--org", organization, "--project", project) or []
        pipeline = _one_named(pipelines, config["pipeline_name"])
        if pipeline is None:
            branch = "main" if "*" in config["branch"] else config["branch"]
            pipeline = ops.az_json(
                "pipelines", "create", "--name", config["pipeline_name"], "--yml-path", config["pipeline_yaml"],
                "--branch", branch, "--org", organization, "--project", project, "--skip-first-run",
            )
        if not isinstance(pipeline, dict) or not pipeline.get("id"):
            raise StepError(f"{target}: pipeline '{config['pipeline_name']}' could not be registered; ask for Build Administrate permission")
        detail = ops.az_json("pipelines", "show", "--id", str(pipeline["id"]), "--org", organization, "--project", project) or {}
        if detail.get("process", {}).get("yamlFilename") != config["pipeline_yaml"]:
            raise StepError(f"{target}: pipeline '{config['pipeline_name']}' is registered to a different YAML path")
        resources = context[target]
        for kind, resource in (
            ("variablegroup", resources["group"]),
            ("queue", resources["queue"]),
            ("endpoint", resources["endpoint"]),
            ("environment", resources["environment"]),
        ):
            url = f"{base}/pipelines/pipelinePermissions/{kind}/{resource['id']}?api-version=7.1-preview.1"
            current = ops.ado_rest("get", url) or {}
            authorized = current.get("allPipelines", {}).get("authorized") or any(
                item.get("id") == pipeline["id"] and item.get("authorized") for item in current.get("pipelines", [])
            )
            if not authorized:
                result = ops.ado_rest("patch", url, {"pipelines": [{"id": pipeline["id"], "authorized": True}]})
                if result is None:
                    raise StepError(f"{target}: pipeline '{config['pipeline_name']}' cannot use {kind} '{resource['id']}'")


def evidence_path(setup_path: Path) -> Path:
    return setup_path.parent / "apply-readiness.json"


def record_evidence(path: Path, completed: list[dict[str, Any]], blocked: dict[str, str] | None = None) -> None:
    evidence = {"version": 1, "status": "blocked" if blocked else "completed", "completed_steps": completed}
    if blocked:
        evidence["blocked_step"] = blocked
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")


def apply_setup(repo: Path, setup_path: Path, ops: ApplyOps | Any) -> dict[str, Any]:
    verify_approval(setup_path)
    try:
        setup = load_setup(setup_path)
        problems = [*validate_setup(setup), *[f"open question: {question['key']}" for question in setup.get("open_questions", [])]]
        problems += [f"gap: {gap.get('path', 'setup')}" for gap in setup.get("gaps", [])]
        if problems:
            raise StepError("approved setup is incomplete; review and approve it again: " + "; ".join(sorted(set(problems))))
        files = generated_files(setup)
        config = json.loads(files[f"{setup['repository']['ci_folder']}/bootstrap-config.json"])
        manifest = json.loads(files[f"{setup['repository']['ci_folder']}/powerbi-assets.yml"])
        errors = validate_config(config) + validate_manifest(manifest, setup["repository"]["source_root"])
        if errors:
            raise StepError("generated setup is invalid: " + "; ".join(errors))
        changed = write_files(repo, files)
    except StepError as error:
        record_evidence(evidence_path(setup_path), [], {"step": "generation", "status": "blocked", "reason": str(error)})
        raise
    completed = [{"step": "generation", "status": "completed", "files_written": len(changed)}]
    active_step = "workspaces"
    try:
        ids = workspace_steps(setup, ops)
        completed.append({"step": "workspaces", "status": "completed", "targets": list(ids)})
        active_step = "direct_roles"
        role_writes = role_steps(setup, ids, ops)
        completed.append({"step": "direct_roles", "status": "completed", "writes": role_writes})
        active_step = "identities_and_connections"
        identity_and_connection_steps(setup, ids, ops)
        completed.append({"step": "identities_and_connections", "status": "completed", "workloads_run": 0})
        active_step = "azure_devops"
        azure_devops_steps(setup, repo, ops)
        completed.append({"step": "azure_devops", "status": "completed", "secret_values_read": 0})
    except StepError as error:
        blocked = {"step": active_step, "status": "blocked", "reason": str(error)}
        record_evidence(evidence_path(setup_path), completed, blocked)
        raise
    record_evidence(evidence_path(setup_path), completed)
    return {"status": "completed", "completed_steps": completed, "workspace_writes": "workspace and direct-role reconciliation only", "workloads_run": 0, "secret_values_read": 0}


def main(argv=None, ops: ApplyOps | Any | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--setup", default="cicd/powerbi/setup.yml")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    setup_path = (repo / args.setup).resolve()
    try:
        result = apply_setup(repo, setup_path, ops or ApplyOps())
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, StepError) as error:
        print(json.dumps({"status": "blocked", "reason": str(error)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
