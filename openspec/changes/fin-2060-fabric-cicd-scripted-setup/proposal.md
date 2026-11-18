## Why

The first live adoption of `fabric-cicd` (Servicing Oversight, FIN-2101) needed sixteen corrections and repeated lookups in Analytics Reporting, because the skill leaves too much to the agent and its templates still use a deploy path the reference had abandoned. Setup should instead be: the user names the DEV, TEST and PROD workspaces, a script shows exactly what will be built, the user approves, and scripts execute it the same way every time, including on small models such as Haiku.

## What Changes

- Add a `plan` script: from the repository and the DEV, TEST, PROD and HOTFIX workspace names or IDs, it discovers everything else it can (workspace and capacity IDs, managed items, Lakehouses, Copy Jobs, connections, Azure DevOps repository) and writes `cicd/fabric/setup.yml` (every resolved value and assumed default) and `cicd/fabric/SETUP.md` (a readable summary of what will be created, granted, generated and registered per environment, plus any blocking gaps).
- Add an `approve` script that records the hash of the reviewed `setup.yml`; the `apply` script refuses to run if `setup.yml` changed after approval.
- Add an `apply` script that runs a fixed sequence of idempotent steps from the approved `setup.yml`: generate files, prepare each target workspace, check connection permissions, check and register pipelines. Each step stops with a plain message saying what to fix.
- **BREAKING**: replace the PowerShell + `fab` deploy path and its templates with the Analytics Reporting Python deployment scripts, packaged in the release artifact and run on hosted Linux, plus the Servicing Oversight fixes: Copy Jobs, connection bindings, the SQL endpoint parameter rule and per-environment branch triggers.
- Generate `parameter.yml` from the source definitions instead of writing it by hand.
- Generalize Analytics Reporting's UAT-only bootstrap so the same workspace, role, schema-enabled Lakehouse and pipeline-authorization steps work for DEV, TEST, PROD and HOTFIX.
- Implement the hotfix route: `hotfix/*` branches build once, deploy to a dedicated HOTFIX workspace, and PROD deploys that same artifact after the reviewed merge.
- Rewrite `SKILL.md` as a short numbered command list.
- Add one regression test per FIN-2101 failure.
- Carry over the release-topology, hotfix and live-evidence tasks of the archived `fin-2060-reference-fabric-bootstrap` change; the separate setup/verification records task is replaced by `SETUP.md`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fabric/reference-cicd-bootstrap`: setup becomes plan → approve → apply scripts driven by a generated `setup.yml` and `SETUP.md`; protected deployment uses the packaged Python path; promotion branches are configured per environment; adds generated bindings, Copy Jobs, connection and Lakehouse readiness, and the same bootstrap for every environment.

## Impact

- `plugins/fabric/skills/fabric-cicd/`: scripts, templates, tests and `SKILL.md`. `Initialize-FabricCicd.ps1` and `bootstrap-config.json` are retired.
- `powerbi-cicd` and Power BI bindings are out of scope; they will be handled by a separate follow-up change.
- Existing adopters: Analytics Reporting and Servicing Oversight are re-generated as the migration check.
- Dependencies: pinned `fabric-cicd`, `azure-identity`, `PyYAML`, `requests`; developer `fab` and `az` sessions for setup only.
- Provenance: Analytics Reporting `cicd/fabric/` (`dfaa945`, base), Servicing Oversight `cicd/fabric/` (`e78fe32`, FIN-2101 fixes).
