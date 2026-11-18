"""Plan Power BI CI/CD setup through read-only local, Fabric, Power BI and az discovery."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from discovery_adapters import ReadOnlyDiscovery  # noqa: E402
from setup_contract import dump_setup, load_setup, validate_setup  # noqa: E402
from source_discovery import discover_source  # noqa: E402

GUID = re.compile(r"(?i)^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
TARGETS = ("DEV", "TEST", "PROD", "HOTFIX")
OPTIONAL_TARGETS = ("UAT", "REHEARSAL")
DEFAULT_BRANCHES = {"DEV": "dev", "TEST": "test", "PROD": "main", "HOTFIX": "hotfix/*", "UAT": "uat", "REHEARSAL": "rehearsal"}
QUESTIONS = {
    "tenant_id": ("What is the Entra tenant ID?", "00000000-0000-4000-8000-000000000001"),
    "ado": ("What is the Azure DevOps organization URL, project, and repository?", "org=https://dev.azure.com/contoso project=Finance repository=analytics"),
    "sp_object_id": ("What is the service-principal object ID for application {app_id}?", "00000000-0000-4000-8000-000000000001"),
    "workspace_id": ("What is the approved workspace ID for {target} workspace '{name}'?", "00000000-0000-4000-8000-000000000001"),
    "capacity_id": ("What is the approved capacity ID for {name}?", "00000000-0000-4000-8000-000000000001"),
    "capacity": ("Which Fabric capacity should {target} workspace '{name}' use?", "Finance Capacity"),
    "binding": ("Which connection IDs bind semantic model '{model}' in {target}? Separate multiple IDs with commas.", "00000000-0000-4000-8000-000000000001"),
    "variable_group": ("Which variable group is approved for {target}?", "powerbi-test"),
    "private_pool": ("Which Windows private Azure DevOps pool is approved for {target}?", "Power BI Protected Windows"),
    "key_vault_connection": ("Which WIF Key Vault service connection is approved for {target}?", "Power BI Key Vault WIF"),
    "key_vault_name": ("Which Key Vault is approved for {target}?", "finance-powerbi-prod"),
    "key_vault_secret_reference": ("Which Key Vault secret-name reference holds the protected runtime client secret for {target}?", "powerbi-client-secret"),
    "runtime_app_id": ("Which application ID is approved for the {target} protected runtime identity?", "00000000-0000-4000-8000-000000000001"),
    "runtime_object_id": ("Which object ID is approved for the {target} protected runtime identity?", "00000000-0000-4000-8000-000000000001"),
    "target_owner": ("Which owner group or reference owns the {target} target?", "Power BI Engineering"),
}


class Asker:
    def __init__(self, answers: dict[str, str], prompt: bool):
        self.answers = dict(answers)
        self.prompt = prompt
        self.open: list[dict[str, str]] = []
        self.supplied: dict[str, str] = {}

    def ask(self, key: str, kind: str, **fields: str) -> str | None:
        if key in self.answers:
            value = self.answers[key]
            if isinstance(value, str) and value.strip():
                self.supplied[key] = value
                return value
        question, example = QUESTIONS[kind]
        question = question.format(**fields)
        if self.prompt:
            value = input(f"{question} (e.g. {example}): ").strip()
            if value:
                self.answers[key] = value
                self.supplied[key] = value
                return value
        record = {"key": key, "question": question, "example": example}
        if record not in self.open:
            self.open.append(record)
        return None

    def add_lookup(self, question: dict[str, str] | None) -> None:
        if question and question not in self.open:
            self.open.append(question)


class LocalDiscovery:
    def __init__(self, repo: Path):
        self.repo = repo

    @staticmethod
    def remote(repo: Path) -> str | None:
        done = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"], capture_output=True, text=True, check=False)
        return done.stdout.strip() if done.returncode == 0 else None


def parse_remote(url: str | None) -> dict[str, str] | None:
    match = re.match(r"https://(?:[^@/]+@)?dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/]+)/?$", url or "")
    if not match:
        return None
    organization, project, repository = (part.replace("%20", " ") for part in match.groups())
    return {"organization": f"https://dev.azure.com/{organization}", "project": project, "repository": repository}


def lookup_by_name(values: object, field: str, name: str) -> dict[str, Any] | None:
    if not isinstance(values, dict):
        return None
    return next((item for item in values.get("value", []) if isinstance(item, dict) and item.get(field) == name), None)


def source_answers(previous: dict[str, Any]) -> dict[str, str]:
    return {str(key): str(value) for key, value in previous.get("answers", {}).items() if isinstance(value, str)}


def parse_connection_ids(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def plan_setup(args, discovery: ReadOnlyDiscovery | Any, ask: Asker) -> dict[str, Any]:
    repo = Path(args.repo).resolve(strict=True)
    provenance: dict[str, str] = {}
    configured_targets = list(TARGETS) + [target for target in OPTIONAL_TARGETS if getattr(args, f"{target.lower()}_workspace")]

    account = discovery.account()
    ask.add_lookup(account.question)
    tenant_id = (account.value or {}).get("tenantId") or ask.ask("tenant_id", "tenant_id")
    provenance["tenant_id"] = "discovered" if account.value else "user"

    azure = parse_remote(LocalDiscovery.remote(repo))
    if azure:
        provenance["repository.azure_devops"] = "discovered"
    else:
        raw = ask.ask("ado", "ado")
        parsed = dict(part.split("=", 1) for part in (raw or "").split() if "=" in part)
        azure = {
            "organization": parsed.get("org") or "",
            "project": parsed.get("project") or "",
            "repository": parsed.get("repository") or "",
        }
        provenance["repository.azure_devops"] = "user"

    capacities = discovery.capacities()
    ask.add_lookup(capacities.question)
    workspace_lookup = discovery.workspaces()
    ask.add_lookup(workspace_lookup.question)
    workspace_values = workspace_lookup.value or {}
    capacity_values = capacities.value or {}

    app_id = args.app_id.lower()
    service_principal = discovery.service_principal(app_id)
    ask.add_lookup(service_principal.question)
    object_id = (service_principal.value or {}).get("id") or ask.ask("sp_object_id", "sp_object_id", app_id=app_id)

    environments: dict[str, Any] = {}
    branches: dict[str, str] = {}
    for target in configured_targets:
        workspace_name = getattr(args, f"{target.lower()}_workspace")
        found = next((item for item in workspace_values.get("value", []) if item.get("displayName") == workspace_name), None)
        workspace_id = (found or {}).get("id")
        create = found is None
        if not workspace_id and not create:
            workspace_id = ask.ask(f"workspace_id.{target}", "workspace_id", target=target, name=workspace_name)
        if target == "DEV" and found is None and workspace_lookup.value is not None:
            provenance[f"environments.{target}.workspace"] = "generated"
        else:
            provenance[f"environments.{target}.workspace"] = "discovered" if found else "user"
        capacity_id = (found or {}).get("capacityId")
        capacity = next((item for item in capacity_values.get("value", []) if item.get("id") == capacity_id), None)
        capacity_name = (capacity or {}).get("displayName") or ask.ask(f"capacity.{target}", "capacity", target=target, name=workspace_name)
        if capacity_name:
            by_name = next((item for item in capacity_values.get("value", []) if item.get("displayName") == capacity_name), None)
            capacity_id = capacity_id or (by_name or {}).get("id")
        if not capacity_id:
            capacity_id = ask.ask(f"capacity_id.{target}", "capacity_id", name=capacity_name or workspace_name)
        variable_group = getattr(args, f"variable_group_{target.lower()}") or args.variable_group or ask.ask(f"variable_group.{target}", "variable_group", target=target)
        group_lookup = discovery.variable_group(variable_group, azure["organization"], azure["project"]) if variable_group and azure["organization"] else None
        if group_lookup:
            ask.add_lookup(group_lookup.question)
        pool = getattr(args, f"private_pool_{target.lower()}") or args.private_pool or ask.ask(f"private_pool.{target}", "private_pool", target=target)
        endpoint_name = getattr(args, f"key_vault_service_connection_{target.lower()}") or args.key_vault_service_connection or ask.ask(f"key_vault_service_connection.{target}", "key_vault_service_connection", target=target)
        vault_name = getattr(args, f"key_vault_name_{target.lower()}") or args.key_vault_name or ask.ask(f"key_vault_name.{target}", "key_vault_name", target=target)
        reference = getattr(args, f"key_vault_secret_reference_{target.lower()}") or args.key_vault_secret_reference or ask.ask(f"key_vault_secret_reference.{target}", "key_vault_secret_reference", target=target)
        runtime_app = getattr(args, f"runtime_app_id_{target.lower()}") or app_id
        runtime_object = getattr(args, f"runtime_object_id_{target.lower()}") or object_id or ask.ask(f"runtime_object_id.{target}", "runtime_object_id", target=target)
        target_owner = getattr(args, f"target_owner_{target.lower()}") or args.target_owner or ask.ask(f"target_owner.{target}", "target_owner", target=target)
        pipeline_name = f"{azure.get('repository') or 'Power BI'} {target}"
        environments[target] = {
            "workspace": {"name": workspace_name, "id": workspace_id, "create": create},
            "capacity": {"id": capacity_id, "name": capacity_name},
            "runtime_identity": {"reference": f"kv:powerbi-{target.lower()}", "app_id": runtime_app, "object_id": runtime_object},
            "variable_group": variable_group,
            "private_pool": pool,
            "key_vault": {"service_connection": endpoint_name, "service_connection_id": None, "name": vault_name, "secret_reference": reference},
            "ado_environment": f"powerbi-{target.lower()}",
            "pipeline_name": pipeline_name,
            "pipeline_yaml": f"{args.ci_folder}/azure-pipelines.yml",
            "branch": DEFAULT_BRANCHES[target],
            "target_owner": target_owner,
            "approval_policy": "required",
            "artifact_route": "immutable",
            "verification_profile": "full",
            "git_connected": False,
            "direct_roles": ([{"object_id": runtime_object, "principal_type": "ServicePrincipal", "role": "Contributor"}] if runtime_object else []),
        }
        branches[target] = DEFAULT_BRANCHES[target]
        if variable_group and azure["organization"]:
            provenance[f"environments.{target}.variable_group"] = "discovered" if group_lookup and group_lookup.question is None else "user"
        provenance[f"environments.{target}"] = "generated"

    source_result = discover_source(repo, args.source_root)
    managed_items = []
    for item in source_result["managed_items"]:
        item = dict(item)
        item.pop("name", None)
        managed_items.append(item)
    gaps = list(source_result["gaps"])

    semantic_models = [item for item in managed_items if item["type"] == "SemanticModel"]
    bindings: dict[str, dict[str, list[str]]] = {}
    connections: list[dict[str, str]] = []
    seen_connections: set[str] = set()
    previous_bindings = (yaml.safe_load((repo / args.out / "setup.yml").read_text(encoding="utf-8")) if (repo / args.out / "setup.yml").exists() else {}).get("semantic_model_bindings", {})
    for model in semantic_models:
        bindings[model["id"]] = {}
        for target in configured_targets:
            if target == "HOTFIX":
                continue
            key = f"binding.{model['id']}.{target}"
            default = previous_bindings.get(model["id"], {}).get(target)
            raw = ask.ask(key, "binding", model=model["id"], target=target) if not default else ",".join(default)
            ids = parse_connection_ids(raw or "")
            if ids:
                bindings[model["id"]][target] = ids
                for connection_id in ids:
                    if connection_id not in seen_connections:
                        detail = discovery.connection(connection_id)
                        ask.add_lookup(detail.question)
                        display = (detail.value or {}).get("displayName") or ask.ask(f"connection_name.{connection_id}", "target_owner", target=f"connection {connection_id}") or connection_id
                        connections.append({"id": connection_id, "display_name": display, "required_permission": "User"})
                        seen_connections.add(connection_id)

    roles: list[dict[str, str]] = []
    for target, environment in environments.items():
        roles.extend({"target": target, **role} for role in environment["direct_roles"])

    setup = {
        "version": 1,
        "repository": {
            "source_root": args.source_root,
            "ci_folder": args.ci_folder,
            "azure_devops": azure,
            "branches": branches,
        },
        "tenant_id": tenant_id or "",
        "service_principal": {"app_id": app_id, "object_id": object_id or ""},
        "environments": environments,
        "managed_items": managed_items,
        "semantic_model_bindings": bindings,
        "connections": connections,
        "roles": roles,
        "excluded": source_result["excluded"],
        "gaps": gaps,
        "answers": dict(sorted(ask.supplied.items())),
        "open_questions": ask.open,
        "provenance": provenance,
    }
    return setup


def render_markdown(setup: dict[str, Any]) -> str:
    return render_setup_markdown(setup)


def render_setup_markdown(setup: dict[str, Any]) -> str:
    blocked = bool(setup["open_questions"] or setup["gaps"])
    repository = setup["repository"]
    ado = repository["azure_devops"]
    out = [
        "# Power BI CI/CD setup review", "",
        "Review this generated contract, correct `setup.yml`, and re-run plan before approval.", "",
        "## Status", "", "BLOCKED: resolve every question and gap before approval." if blocked else "Ready for explicit review and approval.", "",
    ]
    if setup["open_questions"]:
        out += ["## Open questions", ""]
        out += [f"- `{question['key']}`: {question['question']} (example: `{question['example']}`)" for question in setup["open_questions"]] + [""]
    if setup["gaps"]:
        out += ["## Blocking gaps", ""]
        out += [f"- `{gap.get('path', 'setup')}`: {gap['reason']}" for gap in setup["gaps"]] + [""]
    out += [
        "## Repository and scope", "",
        f"- Azure DevOps: `{ado['organization']}` / `{ado['project']}` / `{ado['repository']}`",
        f"- Source: `{repository['source_root']}`; generated files: `{repository['ci_folder']}`",
        f"- Branch route: " + ", ".join(f"{target}=`{branch}`" for target, branch in repository["branches"].items()),
        "", "## Managed items in dependency order", "",
    ]
    for item in setup["managed_items"]:
        detail = f"- `{item['id']}` ({item['type']}): `{item['path']}`"
        if item["dependencies"]:
            detail += "; dependencies " + ", ".join(f"`{dependency}`" for dependency in item["dependencies"])
        if item["binding"]:
            detail += f"; binding `{item['binding']['kind']}` -> `{item['binding']['target']}`"
        out.append(detail)
        for rule in item["substitutions"]["rules"]:
            targets = ", ".join(rule["values"])
            out.append(f"  - `{rule['type']}` at `{rule['path']}`; exact find is approved in order; values for {targets}")
    out += ["", "## Targets and protected resources", ""]
    for target, config in setup["environments"].items():
        workspace = config["workspace"]
        capacity = config["capacity"]
        runtime = config["runtime_identity"]
        vault = config["key_vault"]
        out += [
            f"### {target}", "",
            f"- Workspace: {'create' if workspace['create'] else 'reuse'} `{workspace['name']}` (`{workspace['id']}`) on capacity `{capacity['name']}` (`{capacity['id']}`); Git-disconnected and owned by `{config['target_owner']}`",
            f"- Runtime identity: `{runtime['reference']}` / application `{runtime['app_id']}` / object `{runtime['object_id']}`",
            f"- Direct roles: " + (", ".join(f"`{role['object_id']}` {role['principal_type']} {role['role']}" for role in config["direct_roles"]) or "none"),
            f"- Azure DevOps: variable group `{config['variable_group']}`, private pool `{config['private_pool']}`, environment `{config['ado_environment']}`",
            f"- Key Vault: WIF service connection `{vault['service_connection']}` (`{vault['service_connection_id']}`), vault `{vault['name']}`, secret reference `{vault['secret_reference']}`",
            f"- Pipeline: `{config['pipeline_name']}` from `{config['pipeline_yaml']}` on `{config['branch']}`; approval `{config['approval_policy']}`, route `{config['artifact_route']}`, verification `{config['verification_profile']}`",
            "",
        ]
    out += ["## Semantic-model bindings", ""]
    for model, values in setup["semantic_model_bindings"].items():
        out.append(f"- `{model}`: " + ", ".join(f"{target}={','.join(connection_ids)}" for target, connection_ids in values.items()))
        if "HOTFIX" in setup["environments"] and "PROD" in values:
            out.append("  - HOTFIX resolves this model through the approved PROD binding.")
    out += ["", "## Apply actions and prerequisites", "",
        "- Generate compatibility config/manifest, bindings, substitutions, pipeline YAML, and packaged validation/deployment helpers.",
        "- Create or reuse only the reviewed workspaces and reconcile only the reviewed direct roles.",
        "- Validate service-principal and connection access, model connections, and protected invocation identities before the affected write.",
        "- Validate variable groups, private pools, WIF Key Vault endpoint authorization, Azure DevOps environments, named pipelines, and pipeline permissions.",
        "- Apply emits non-secret readiness evidence and never runs a deployment or workload.",
        "", "## Generated files", "",
        f"- `{repository['ci_folder']}/bootstrap-config.json` (generated compatibility input)",
        f"- `{repository['ci_folder']}/powerbi-assets.yml` (generated compatibility manifest)",
        f"- `{repository['ci_folder']}/bindings.yml` and `{repository['ci_folder']}/azure-pipelines.yml`",
        "- Packaged Power BI validation and protected deployment helpers under the reviewed CI/CD folder.", "",
    ]
    if setup["answers"]:
        out += ["## User-supplied values", ""] + [f"- `{key}`: reviewed answer" for key in sorted(setup["answers"])] + [""]
    for source in ("discovered", "assumed", "user", "generated"):
        entries = sorted(key for key, provenance in setup["provenance"].items() if provenance == source)
        if entries:
            out += [f"## {source.title()} values", ""] + [f"- `{key}`" for key in entries] + [""]
    if setup["gaps"]:
        out += ["## Blocking values", ""] + [f"- `{gap.get('path', 'setup')}`" for gap in setup["gaps"]] + [""]
    out += ["## Rollback", "", "- Retain the previous installed skill and legacy release inputs until reviewed generated files are committed.", "- Existing committed immutable release artifacts remain valid; rollback is to reinstall the previous skill or redeploy a retained known-good artifact.", ""]
    return "\n".join(out) + "\n"


def add_target_arguments(parser: argparse.ArgumentParser, target: str) -> None:
    parser.add_argument(f"--{target.lower()}-workspace")
    parser.add_argument(f"--variable-group-{target.lower()}")
    parser.add_argument(f"--private-pool-{target.lower()}")
    parser.add_argument(f"--key-vault-service-connection-{target.lower()}")
    parser.add_argument(f"--key-vault-name-{target.lower()}")
    parser.add_argument(f"--key-vault-secret-reference-{target.lower()}")
    parser.add_argument(f"--runtime-app-id-{target.lower()}")
    parser.add_argument(f"--runtime-object-id-{target.lower()}")
    parser.add_argument(f"--target-owner-{target.lower()}")


def main(argv=None, discovery: ReadOnlyDiscovery | Any = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--source-root", default="pbi")
    parser.add_argument("--ci-folder", default="cicd/powerbi")
    parser.add_argument("--out", default="cicd/powerbi")
    for target in TARGETS:
        add_target_arguments(parser, target)
    for target in OPTIONAL_TARGETS:
        add_target_arguments(parser, target)
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--variable-group")
    parser.add_argument("--private-pool")
    parser.add_argument("--key-vault-service-connection")
    parser.add_argument("--key-vault-name")
    parser.add_argument("--key-vault-secret-reference")
    parser.add_argument("--target-owner")
    parser.add_argument("--no-prompt", action="store_true")
    parser.add_argument("--answer", action="append", default=[], metavar="key=value")
    args = parser.parse_args(argv)
    for target in TARGETS:
        if not getattr(args, f"{target.lower()}_workspace"):
            parser.error(f"--{target.lower()}-workspace is required")
    repo = Path(args.repo).resolve()
    out = repo / args.out
    previous = load_setup(out / "setup.yml") if (out / "setup.yml").exists() else {}
    answers = source_answers(previous)
    for answer in args.answer:
        if "=" not in answer:
            parser.error(f"--answer must be key=value: {answer}")
        key, value = answer.split("=", 1)
        answers[key] = value
    ask = Asker(answers, prompt=not args.no_prompt and sys.stdin.isatty())
    setup = plan_setup(args, discovery or ReadOnlyDiscovery(), ask)
    serialized = dump_setup(setup)
    schema_errors = validate_setup(setup)
    if setup["open_questions"] or setup["gaps"] or schema_errors:
        if schema_errors and not setup["gaps"]:
            setup["gaps"].extend({"path": "setup", "reason": error} for error in schema_errors)
    out.mkdir(parents=True, exist_ok=True)
    (out / "setup.yml").write_text(serialized, encoding="utf-8", newline="\n")
    (out / "SETUP.md").write_text(render_markdown(setup), encoding="utf-8", newline="\n")
    if setup["open_questions"]:
        print("Open questions (answer with --answer key=value and re-run plan):")
        for question in setup["open_questions"]:
            print(f"  {question['key']}: {question['question']} (e.g. {question['example']})")
        return 2
    if setup["gaps"]:
        print("Planning blocked; resolve the gaps in SETUP.md and re-run plan")
        return 2
    print(f"Wrote {out / 'setup.yml'} and {out / 'SETUP.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
