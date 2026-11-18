"""Plan Fabric CI/CD setup: read-only lookups, binding rules, then setup.yml and SETUP.md.

Nothing external is written. Missing values are asked (terminal prompt) or, with
--no-prompt, printed as questions to answer with --answer key=value.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bindings import ENVIRONMENTS, GUID, ITEM_TYPES, generate_rules  # noqa: E402

DEFAULT_BRANCHES = {"DEV": "DEV", "TEST": "TEST", "PROD": "PROD", "HOTFIX": "hotfix/*"}
DEFAULT_EXCLUDED = [
    {"path": "fabric/**/Files/**", "reason": "Lakehouse data rows are not deployed by CI/CD"},
    {"path": "fabric/**/Tables/**", "reason": "Lakehouse data rows are not deployed by CI/CD"},
    {"path": "**/*.schedules", "reason": "Schedules and triggers are separately approved operational state"},
    {"path": "pbi/**", "reason": "Power BI CI/CD has an independent scope"},
    {"path": "**/*credential*", "reason": "Credentials and secrets remain protected runtime inputs"},
]
QUESTIONS = {
    "capacity": ("Which Fabric capacity should workspace '{name}' use?", "my-fabric-capacity"),
    "tenant_id": ("What is the Entra tenant ID?", "00000000-0000-0000-0000-000000000000"),
    "ado": ("What is the Azure DevOps organization URL, project and repository?", "org=https://dev.azure.com/contoso project=Data repository=lakehouse"),
    "sp_object_id": ("What is the object ID of the service principal with application ID {app_id}?", "00000000-0000-0000-0000-000000000000"),
    "connection_name": ("What is the display name of Fabric connection {id}?", "Service_1 - Service"),
    "private_pool": ("What is the Windows private Azure DevOps agent pool used for Key Vault retrieval and deployment?", "BAM-IaC-CloudEng"),
    "key_vault_service_connection": ("What is the WIF Azure DevOps service connection for the protected Key Vault?", "BAM-PROD Key Vault (WIF)"),
    "key_vault_name": ("What is the protected Key Vault name?", "BAM-KV-PBI-Prod"),
    "key_vault_secret": ("What is the Key Vault secret name containing the service-principal client secret?", "powerbi-eot-secret"),
}


class Tools:
    """Read-only access to fab, az and git; every call returns None on failure."""

    def fab(self, path: str):
        executable = shutil.which("fab")
        if not executable:
            return None
        done = subprocess.run([executable, "api", path], capture_output=True, text=True)
        if done.returncode:
            return None
        try:
            body = json.loads(done.stdout)
        except json.JSONDecodeError:
            return None
        return body.get("text") if isinstance(body, dict) and body.get("status_code") == 200 else None

    def az(self, *args: str):
        executable = shutil.which("az")
        if not executable:
            return None
        done = subprocess.run([executable, *args, "--output", "json"], capture_output=True, text=True)
        if done.returncode:
            return None
        try:
            return json.loads(done.stdout)
        except json.JSONDecodeError:
            return None

    def remote(self, repo: Path) -> str | None:
        done = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"], capture_output=True, text=True)
        return done.stdout.strip() if done.returncode == 0 else None


class Asker:
    def __init__(self, answers: dict[str, str], prompt: bool):
        self.answers, self.prompt, self.open = dict(answers), prompt, []
        self.supplied: dict[str, str] = {}

    def __call__(self, key: str, kind: str, **fields) -> str | None:
        if key in self.answers:
            self.supplied[key] = self.answers[key]
            return self.answers[key]
        question, example = QUESTIONS[kind]
        question = question.format(**fields)
        if self.prompt:
            value = input(f"{question} (e.g. {example}): ").strip()
            if value:
                self.supplied[key] = self.answers[key] = value
                return value
        self.open.append({"key": key, "question": question, "example": example})
        return None


def parse_remote(url: str | None) -> dict | None:
    match = re.match(r"https://(?:[^@/]+@)?dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/]+?)/?$", url or "")
    if not match:
        return None
    org, project, repo = (part.replace("%20", " ") for part in match.groups())
    return {"organization": f"https://dev.azure.com/{org}", "project": project, "repository": repo}


def lookup_workspace(tools: Tools, spec: str, capacities: list[dict]) -> dict:
    found = None
    if GUID.fullmatch(spec):
        found = tools.fab(f"workspaces/{spec}")
    else:
        for workspace in (tools.fab("workspaces") or {}).get("value", []):
            if workspace.get("displayName") == spec:
                found = workspace
                break
    if not found:
        return {"name": spec, "id": None, "create": True, "capacity": None}
    capacity = next((c for c in capacities if c.get("id") == found.get("capacityId")), None)
    return {
        "name": found["displayName"], "id": found["id"], "create": False,
        "capacity": {"id": found.get("capacityId"), "name": (capacity or {}).get("displayName")},
    }


def dev_inventory(tools: Tools, workspace_id: str) -> list[dict]:
    items = []
    for item in (tools.fab(f"workspaces/{workspace_id}/items") or {}).get("value", []):
        entry = {"type": item["type"], "name": item["displayName"], "id": item["id"], "logicalId": item.get("logicalId")}
        if item["type"] == "Lakehouse":
            detail = tools.fab(f"workspaces/{workspace_id}/lakehouses/{item['id']}") or {}
            entry["sqlendpointid"] = detail.get("properties", {}).get("sqlEndpointProperties", {}).get("id")
        items.append(entry)
    return sorted(items, key=lambda i: (i["type"], i["name"]))


def scan_source(repo: Path, source_root: str) -> list[dict]:
    root = repo / source_root
    suffixes = tuple("." + t for t in ITEM_TYPES)
    managed = []
    for folder in sorted(p for p in root.rglob("*") if p.is_dir() and p.name.endswith(suffixes)):
        item_type = folder.name.rsplit(".", 1)[1]
        try:
            name = json.loads((folder / ".platform").read_text(encoding="utf-8"))["metadata"]["displayName"]
        except (OSError, KeyError, json.JSONDecodeError):
            name = folder.name.rsplit(".", 1)[0]
        managed.append({"folder": str(folder.relative_to(root)).replace("\\", "/"), "type": item_type, "name": name})
    return managed


def invocation_connections(source: Path, managed: list[dict]) -> list[str]:
    found: set[str] = set()

    def visit(value):
        if isinstance(value, dict):
            if value.get("type") == "InvokePipeline":
                found.update(m.lower() for m in GUID.findall(json.dumps(value.get("externalReferences", {}))))
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for item in managed:
        path = source / item["folder"] / "pipeline-content.json"
        if item["type"] == "DataPipeline" and path.exists():
            try:
                visit(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                pass
    return sorted(found)


def lookup_connection(tools: Tools, ask: Asker, connection_id: str) -> dict:
    detail = tools.fab(f"connections/{connection_id}") or {}
    roles = (tools.fab(f"connections/{connection_id}/roleAssignments") or {}).get("value")
    name = detail.get("displayName") or ask(f"connection_name.{connection_id}", "connection_name", id=connection_id)
    return {
        "id": connection_id, "display_name": name, "required_permission": "User",
        "roles": None if roles is None else sorted(
            ({"principal_id": r["principal"]["id"], "type": r["principal"]["type"], "role": r["role"]} for r in roles),
            key=lambda r: (r["principal_id"], r["role"]),
        ),
    }


def lookup_variable_group(tools: Tools, ado: dict, group: str) -> dict:
    found = tools.az("pipelines", "variable-group", "list", "--group-name", group, "--org", ado["organization"], "--project", ado["project"])
    if found is None:
        return {"name": group, "exists": None, "variables": None}
    if not found:
        return {"name": group, "exists": False, "variables": {}}
    variables = {k: bool(v.get("isSecret")) for k, v in sorted(found[0].get("variables", {}).items())}
    return {"name": group, "exists": True, "variables": variables}


def lookup_private_pool(tools: Tools, ado: dict, name: str | None) -> dict:
    if not name or not ado.get("organization"):
        return {"name": name, "exists": None}
    found = tools.az("pipelines", "pool", "list", "--org", ado["organization"])
    if found is None:
        return {"name": name, "exists": None}
    return {"name": name, "exists": any(pool.get("name") == name for pool in found)}


def lookup_key_vault_connection(tools: Tools, ado: dict, name: str | None) -> dict:
    if not name or not ado.get("organization"):
        return {"name": name, "id": None, "exists": None}
    found = tools.az("devops", "service-endpoint", "list", "--org", ado["organization"], "--project", ado["project"])
    if found is None:
        return {"name": name, "id": None, "exists": None}
    match = next((endpoint for endpoint in found if endpoint.get("name") == name), None)
    return {"name": name, "id": (match or {}).get("id"), "exists": match is not None}


def build_setup(args, tools: Tools, ask: Asker) -> dict:
    repo = Path(args.repo).resolve()
    tenant = (tools.az("account", "show") or {}).get("tenantId") or ask("tenant_id", "tenant_id", )
    ado = parse_remote(tools.remote(repo))
    if not ado:
        raw = ask("ado", "ado")
        ado = dict(part.split("=", 1) for part in (raw or "").split() if "=" in part) or {"organization": None, "project": None, "repository": None}
    capacities = (tools.fab("capacities") or {}).get("value", [])
    environments = {}
    shared_pool = args.private_pool or ask("private_pool", "private_pool")
    shared_kv_connection = args.key_vault_service_connection or ask("key_vault_service_connection", "key_vault_service_connection")
    shared_kv_name = args.key_vault_name or ask("key_vault_name", "key_vault_name")
    shared_kv_secret = args.key_vault_secret or ask("key_vault_secret", "key_vault_secret")
    for env in ENVIRONMENTS:
        spec = getattr(args, f"{env.lower()}_workspace")
        workspace = lookup_workspace(tools, spec, capacities)
        if env == "DEV" and workspace["create"]:
            raise SystemExit(f"DEV workspace '{spec}' must exist and be readable")
        if workspace["create"]:
            capacity_name = ask(f"capacity.{env}", "capacity", name=spec)
            match = next((c for c in capacities if c.get("displayName") == capacity_name), None)
            workspace["capacity"] = {"id": (match or {}).get("id"), "name": capacity_name}
        group = getattr(args, f"variable_group_{env.lower()}") or args.variable_group
        pool_name = getattr(args, f"private_pool_{env.lower()}") or shared_pool
        connection_name = getattr(args, f"key_vault_service_connection_{env.lower()}") or shared_kv_connection
        vault_name = getattr(args, f"key_vault_name_{env.lower()}") or shared_kv_name
        secret_name = getattr(args, f"key_vault_secret_{env.lower()}") or shared_kv_secret
        endpoint = lookup_key_vault_connection(tools, ado, connection_name)
        environments[env] = {
            "workspace": workspace, "variable_group": lookup_variable_group(tools, ado, group) if ado.get("organization") else {"name": group, "exists": None, "variables": None},
            "private_pool": lookup_private_pool(tools, ado, pool_name),
            "key_vault": {
                "service_connection": connection_name,
                "service_connection_id": endpoint["id"],
                "service_connection_exists": endpoint["exists"],
                "name": vault_name,
                "secret": secret_name,
            },
            "ado_environment": f"fabric-{env.lower()}", "pipeline_name": f"{ado.get('repository') or 'repo'} Fabric {env}",
            "pipeline_yaml": f"cicd/fabric/fabric-{env.lower()}.yml", "branch": DEFAULT_BRANCHES[env],
        }
    dev_id = environments["DEV"]["workspace"]["id"]
    dev_items = dev_inventory(tools, dev_id)
    managed = scan_source(repo, args.source_root)
    by_key = {(i["type"], i["name"]): i for i in dev_items}
    gaps = [{"item": m["folder"], "reason": "not found in the DEV workspace"} for m in managed if (m["type"], m["name"]) not in by_key]
    excluded_guids = sorted(set(args.exclude_guid))
    mapped = dict(pair.split("=", 1) for pair in args.map_guid)
    generated = generate_rules(repo / args.source_root, managed, dev_id, dev_items, set(excluded_guids), mapped)
    gaps += [{"guid": g["guid"], "file": f"{args.source_root}/{g['file']}", "reason": "matches no DEV item and no exclusion"} for g in generated["gaps"]]
    connections = [lookup_connection(tools, ask, c) for c in generated["connection_ids"]]
    app_id = args.app_id.lower()
    sp = (tools.az("ad", "sp", "show", "--id", app_id) or {}).get("id") or ask("sp_object_id", "sp_object_id", app_id=app_id)
    return {
        "version": 1,
        "repository": {"source_root": args.source_root, "ci_folder": "cicd/fabric", "azure_devops": ado},
        "tenant_id": tenant,
        "service_principal": {"app_id": app_id, "object_id": sp},
        "environments": environments,
        "managed_items": [
            {"folder": m["folder"], "type": m["type"], "name": m["name"], "dependencies": generated["dependencies"][m["folder"]]} for m in managed
        ],
        "excluded": DEFAULT_EXCLUDED,
        "connections": connections,
        "pipeline_invocation_connections": invocation_connections(repo / args.source_root, managed),
        "bindings": {"rules": generated["rules"], "excluded_guids": excluded_guids, "mapped_guids": dict(sorted(mapped.items()))},
        "dev_items": dev_items,
        "gaps": gaps,
        "answers": dict(sorted(ask.supplied.items())),
        "open_questions": ask.open,
    }


def render_markdown(setup: dict) -> str:
    out = ["# Fabric CI/CD setup", "", "Review this file, edit `setup.yml` if anything is wrong, then run `approve.py`.", ""]
    blocking = setup["gaps"] or setup["open_questions"]
    out += ["## Status", "", "BLOCKED: resolve the items below, then re-run plan." if blocking else "Ready for review: no blocking gaps.", ""]
    if setup["open_questions"]:
        out += ["### Open questions", ""] + [f"- `{q['key']}`: {q['question']} (e.g. `{q['example']}`)" for q in setup["open_questions"]] + [""]
    if setup["gaps"]:
        out += ["### Blocking gaps", ""] + [f"- {g.get('file') or g['item']}: {g.get('guid', '')} {g['reason']}".replace("  ", " ") for g in setup["gaps"]] + [""]
    sp = setup["service_principal"]
    out += ["## Protected identity", "", f"- Application ID `{sp['app_id']}`, object ID `{sp['object_id']}`", ""]
    for env, cfg in setup["environments"].items():
        ws, vg = cfg["workspace"], cfg["variable_group"]
        out += [f"## {env}", ""]
        out.append(f"- Workspace: {'create' if ws['create'] else 'reuse'} `{ws['name']}`" + (f" (`{ws['id']}`)" if ws["id"] else "") + f" on capacity `{(ws['capacity'] or {}).get('name')}`")
        out.append(f"- Roles: service principal `Contributor`" + ("; pipeline-invocation connection owner `Contributor`" if env in ("TEST", "PROD") else ""))
        out.append(f"- Lakehouses: create any missing, schema-enabled, with the developer session")
        out.append(f"- Pipeline: `{cfg['pipeline_name']}` from `{cfg['pipeline_yaml']}`, trigger branch `{cfg['branch']}`")
        out.append(f"- Variable group `{vg['name']}` ({'found' if vg['exists'] else 'missing' if vg['exists'] is False else 'not checked'}); environment `{cfg['ado_environment']}`")
        pool = cfg["private_pool"]
        vault = cfg["key_vault"]
        out.append(f"- Protected job pool `{pool['name']}` ({'found' if pool['exists'] else 'missing' if pool['exists'] is False else 'not checked'})")
        out.append(f"- WIF Key Vault connection `{vault['service_connection']}`, vault `{vault['name']}`, secret reference `{vault['secret']}`")
        out.append("")
    out += ["## Managed items", ""] + [f"- {m['type']}: `{m['folder']}`" for m in setup["managed_items"]] + [""]
    out += ["## Connections (service principal and developer need `User`)", ""] + [f"- `{c['id']}` {c['display_name']}" for c in setup["connections"]] + [""]
    out += ["## Binding rules", "", f"{len(setup['bindings']['rules'])} rules generated into `parameter.yml`.", ""]
    if setup["answers"]:
        out += ["## Supplied by user", ""] + [f"- `{k}` = `{v}`" for k, v in setup["answers"].items()] + [""]
    out += [
        "## Manual prerequisites", "",
        "- Create the service principal and store its client secret in the configured Key Vault; do not place it in the variable group.",
        "- Create and authorize the WIF Key Vault service connection and confirm the Windows private pool can reach the vault.",
        "- Enable service-principal access in the Fabric tenant settings.", "",
        "## Hotfix runbook", "",
        "1. Create `hotfix/<Jira-key>` from the PROD branch and cherry-pick the fix from DEV.",
        "2. The hotfix pipeline deploys it to the HOTFIX workspace; verify there.",
        "3. Open a reviewed pull request from the hotfix branch into the PROD branch; PROD deploys the HOTFIX artifact.",
        "4. Forward-port the fix to the TEST and DEV branches through reviewed pull requests.", "",
    ]
    return "\n".join(out)


def main(argv=None, tools: Tools | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--source-root", default="fabric")
    parser.add_argument("--out", default="cicd/fabric")
    for env in ENVIRONMENTS:
        parser.add_argument(f"--{env.lower()}-workspace", required=True, help=f"{env} workspace name or ID")
        parser.add_argument(f"--variable-group-{env.lower()}")
        parser.add_argument(f"--private-pool-{env.lower()}")
        parser.add_argument(f"--key-vault-service-connection-{env.lower()}")
        parser.add_argument(f"--key-vault-name-{env.lower()}")
        parser.add_argument(f"--key-vault-secret-{env.lower()}")
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--variable-group", required=True)
    parser.add_argument("--private-pool")
    parser.add_argument("--key-vault-service-connection")
    parser.add_argument("--key-vault-name")
    parser.add_argument("--key-vault-secret")
    parser.add_argument("--exclude-guid", action="append", default=[])
    parser.add_argument("--map-guid", action="append", default=[], metavar="guid=reference", help="map an identifier from another workspace, e.g. <guid>='$workspace.$id'")
    parser.add_argument("--no-prompt", action="store_true")
    parser.add_argument("--answer", action="append", default=[], metavar="key=value")
    args = parser.parse_args(argv)

    out = Path(args.repo).resolve() / args.out
    answers = {}
    if (out / "setup.yml").exists():
        answers.update((yaml.safe_load((out / "setup.yml").read_text(encoding="utf-8")) or {}).get("answers", {}))
    answers.update(a.split("=", 1) for a in args.answer)
    ask = Asker(answers, prompt=not args.no_prompt and sys.stdin.isatty())
    setup = build_setup(args, tools or Tools(), ask)
    out.mkdir(parents=True, exist_ok=True)
    (out / "setup.yml").write_text(yaml.safe_dump(setup, sort_keys=True, default_flow_style=False), encoding="utf-8")
    (out / "SETUP.md").write_text(render_markdown(setup), encoding="utf-8")
    if setup["open_questions"]:
        print("Open questions (answer with --answer key=value and re-run plan):")
        for q in setup["open_questions"]:
            print(f"  {q['key']}: {q['question']} (e.g. {q['example']})")
        return 2
    print(f"Wrote {out / 'setup.yml'} and {out / 'SETUP.md'}" + ("; blocking gaps remain" if setup["gaps"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
