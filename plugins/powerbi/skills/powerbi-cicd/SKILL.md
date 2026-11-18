---
name: powerbi-cicd
description: Plan, validate, package, promote, and recover explicitly mapped Power BI CI/CD releases for PBIP, PBIR, TMDL semantic models, and paginated RDL reports. Use for Power BI CI/CD setup, offline PR validation, release artifacts, protected promotion, deployment evidence, drift, or rollback; do not use for Fabric data-engineering CI/CD.
---

# Power BI CI/CD lifecycle

This skill owns Power BI-only CI/CD. It coordinates the existing
`semantic-model-authoring`, `powerbi-report-authoring`,
`paginated-report-authoring`, and DevOps skills; it does not replace their
authoring boundaries. `fabric-cicd` remains Fabric data-engineering-only.

Start with explicit Jira/work-area/work-type intake and the normal Jira-keyed
feature or bugfix branch guard. Power BI, mixed, other, and unknown scope never
qualify for the Fabric-data-engineering DEV-branch exception.

Use `assets/templates/bootstrap-config.json` and
`assets/templates/powerbi-assets.yml` as non-secret adopter inputs. The
configuration requires DEV, TEST, and PROD and accepts only UAT and REHEARSAL
as optional targets. A discovered folder or workspace is never approval.

```powershell
$bootstrap = '<skill-path>/assets/templates/Initialize-PowerBiCicd.ps1'
& $bootstrap -Mode Plan -ConfigPath ./cicd/powerbi-bootstrap.json -ManifestPath ./cicd/powerbi-assets.yml -RepoRoot .
& $bootstrap -Mode Render -ConfigPath ./cicd/powerbi-bootstrap.json -ManifestPath ./cicd/powerbi-assets.yml -RepoRoot .
```

`Plan` and PR validation are offline and do not write locally or authenticate
to Fabric, Power BI, Azure DevOps, or a workspace. They emit redacted JSON.
`Apply`, `Resume`, and `Deploy` use the supported `fabric-cicd` adapter only
after target preflight and its protected write guard succeed. The supported
item matrix records the versioned Glasslake reference dry run; an unavailable
identity or unverified target remains fail-closed. The lifecycle never falls
back to developer credentials or a generic REST client.

Run focused checks before handoff:

```powershell
py -3 -B -m unittest discover <skill-path>/tests -v
```

These tests use synthetic sources only. They do not prove live tenant support,
Azure DevOps registration, protected identity access, or workspace deployment.

## HOTFIX route

Create `hotfix/<Jira-key>` from `main`. Its validated source is packaged once
and deployed only to the isolated HOTFIX workspace using the PROD mapping; it
never writes PROD directly. A reviewed pull request to `main` resolves the
same artifact from completed-PR metadata (with merge second-parent fallback),
and requires its `ValidateHotfix` stage to have succeeded before it may deploy
PROD. After production deployment, open forward-port pull requests to `test`
and `dev`. A missing validated hotfix build, or a non-`hotfix/*` source, blocks
promotion.
