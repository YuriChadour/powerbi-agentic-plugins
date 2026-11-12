---
name: fabric-cicd
description: Plan and develop a reusable Fabric CI/CD lifecycle, including repository discovery, target-specific bootstrap, immutable releases, protected deployments and recovery. Use for setting up or operating Fabric data engineering CI/CD; coordinate endpoint-specific Fabric operations with the appropriate specialist skills.
---

# Fabric data-engineering CI/CD bootstrap

This skill provides a focused Fabric data-engineering bootstrap. It renders and
sets up only the configured Fabric source and CI folders; it does not set up
Power BI CI/CD, copy data, schedules, credentials, or a general-purpose REST
automation layer. Power BI remains a separately approved future bootstrap.

Use `assets/templates/bootstrap-config.json` and
`assets/templates/managed-items.yml` as non-secret adopter inputs. The
reference-derived manifest selects only managed Fabric definitions and records
dependencies and exclusions.

## Bootstrap a repository

The single setup entry point is
`assets/templates/Initialize-FabricCicd.ps1`. Copy the input templates into
the adopter repository's configured CI folder, replace all `REPLACE_*` values,
then render and review generated files before committing them.

```powershell
$bootstrap = '<skill-path>/assets/templates/Initialize-FabricCicd.ps1'
& $bootstrap -Mode Render -ConfigPath ./cicd/bootstrap-config.json -ManifestPath ./cicd/managed-items.yml -RepoRoot .
& $bootstrap -Mode Plan -ConfigPath ./cicd/bootstrap-config.json -ManifestPath ./cicd/managed-items.yml -RepoRoot .
& $bootstrap -Mode Apply -ConfigPath ./cicd/bootstrap-config.json -ManifestPath ./cicd/managed-items.yml -RepoRoot .
```

`Plan` is offline and reports no external writes. `Apply` uses the invoking
developer's existing `fab` and `az` sessions: it checks `fab auth status`,
`az account show`, and the Azure DevOps extension before any affected write.
It creates or reuses only configured workspaces, reconciles only explicit
direct role mappings, and registers only missing named Fabric YAML pipelines.
It rejects conflicting workspace IDs, roles, repository bindings, branches,
or YAML paths. It accepts no setup token, secret, or service-principal
credential.

`Status` reads the redacted setup state. `Resume` requires that state and
re-runs the approved reconciliation. The rendered TEST and PROD deployment
stages use protected pipeline identities; they require target guards and do
not execute workloads by default. PROD consumes the matching TEST-built
artifact rather than rebuilding it.

Run the focused offline checks before handoff:

```powershell
py -3 -B -m unittest discover <skill-path>/tests -v
```

These tests validate generated contracts and synthetic adoption only. They do
not prove live Fabric access, Azure DevOps registration, deployment, or
workload execution.

## Discover a repository

```powershell
py -3 <skill-path>/scripts/discover.py --repo <repository-path>
```

The JSON report identifies candidate source roots, existing CI/CD files, local
branch names and remote names. Folder presence is not approval to deploy.
Fabric Git connection, synchronization evidence and target mappings are
reported as unknown until established through authorized discovery. The command
never changes repository or external state and does not print remote URLs.

For an implementation request, consult the lifecycle OpenSpec change and its
task state before continuing. Resolve explicit work area and work type, Jira
traceability and the mandatory branch guard through the DevOps workflow.
Fabric work is authored in DEV; protected release targets and identities are
configured explicitly. Do not deploy to DEV, infer production mappings, include
secrets in generated files, or weaken remote branch protections.

`assets/reference-inventory.md` records the reference asset dispositions; it is
provenance, not a runtime dependency or authorization to deploy. The planned
bundle must work without the reference repository and must not contain its
project-specific defaults.

See `assets/pbi-mapping.md` for the separate optional mapping contract and `assets/dev-authoring.md` for DEV authoring guidance.
