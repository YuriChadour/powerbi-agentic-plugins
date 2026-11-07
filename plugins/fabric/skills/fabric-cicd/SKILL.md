---
name: fabric-cicd
description: Plan and develop a reusable Fabric CI/CD lifecycle, including repository discovery, target-specific bootstrap, immutable releases, protected deployments and recovery. Use for setting up or operating Fabric data engineering CI/CD; coordinate endpoint-specific Fabric operations with the appropriate specialist skills.
---

# Fabric CI/CD lifecycle

This skill is under development. The currently available executable is
`scripts/discover.py`, a read-only inventory, and an opt-in Power BI mapping validator; bootstrap, deployment, runtime
and recovery automation are not yet implemented. Do not claim those operations
are available or complete.

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
