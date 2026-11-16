## Why

The reference Fabric bootstrap deliberately excludes Power BI, while the
Glasslake environment bootstrap establishes the Power BI setup shape that must
be generalized: governed Dev/Test/Prod workspaces, an artifact-only deployment
path, `fab`/`az` setup, protected identity, PR governance, and pilot gates.
A separately scoped lifecycle is needed so Power BI CI/CD can use the same
plan-and-recovery operator experience without incorrectly treating Power BI as
Fabric data-engineering content.

## What Changes

- Add a Power BI CI/CD lifecycle capability for explicitly approved PBIP,
  PBIR, TMDL semantic-model, and paginated-report RDL source roots.
- Generalize the smallest connected Glasslake bootstrap dependency set while
  preserving useful YAML compatibility. Provide `powerbi-cicd` the same
  PowerShell-led `Render`, `Plan`, `Apply`, `Status`, `Resume`, and `Deploy`
  interface and common non-secret CI/CD parameters as `fabric-cicd`, with a
  Power BI source mapping and dependency manifest in place of Fabric managed
  items.
- Configure `dev` as an unprotected integration branch that accepts direct
  commits for any workload, and `test` and `main` as pull-request-only
  promotion branches (one required reviewer, required validation, merge-commit
  completion). Configure Git-disconnected DEV/TEST/PROD Power BI targets, an
  isolated HOTFIX validation target, and explicitly configured optional UAT or
  Rehearsal targets. The pipeline deploys only the packaged `pbi/` artifact
  through sequential repository, workspace, identity, governance, and pilot
  readiness gates. Use developer-authenticated `fab` and `az` for setup;
  reserve protected runtime identity for deployment.
- Generate reviewable Azure DevOps assets and keep offline PR validation
  separate from trusted deployment. Render a populated, non-secret CI/CD review
  and verification record containing configured and resolved workspace IDs,
  source and promotion scope, Azure DevOps resources, service-connection and
  service-principal references, role mappings, supported item scope,
  prerequisites, and recovery guidance; require developer approval of that
  contract before `Apply` may register or reconcile external resources.
- Build a single immutable Power BI artifact once from a `dev` revision and
  promote that same artifact through reviewed `dev`-to-`test` and
  `test`-to-`main` pull requests; TEST and PROD locate it by revision lineage
  and never rebuild. Required PR review and validation are the manual release
  approvals; deployment environments supply only target guards and exclusive
  locks. Support a `hotfix/<Jira-key>` route from `main`: build once, validate
  in the isolated HOTFIX workspace with the PROD mapping, deploy PROD through a
  reviewed PR to `main`, then forward-port to `test` and `dev`. Include
  post-deployment verification, audit evidence, drift detection, and
  known-good rollback guidance.
- Route Power BI work through the existing scope-first Jira and branch-guard
  workflow: Power BI, mixed, other, and unknown work use normal Jira-keyed
  feature/bugfix rules; only explicit Fabric-data-engineering-only work may
  use the configured DEV exception.
- Keep the existing Fabric data-engineering bootstrap unchanged: its Fabric
  folder boundary remains exclusive, and a Power BI folder does not enable it.
- Fail closed for unsupported item types, unresolved report/model or RDL
  bindings, incomplete environment contracts, absent protected identities,
  missing or mismatched semantic-model connection bindings, or artifact-digest
  mismatches. Semantic-model source connections use approved, non-secret,
  target-specific connection identifiers and direct deployment-identity access;
  no generic REST automation layer or implicit migration is introduced.

## Capabilities

### New Capabilities

- `powerbi/cicd-lifecycle`: Explicit, Power BI-only repository bootstrap and
  immutable DEV/TEST/PROD release lifecycle, with optional UAT/Rehearsal
  deployment profiles, for supported PBIP/PBIR, TMDL, and RDL assets.

### Modified Capabilities

None.

## Impact

- New Power BI CI/CD skill, Fabric-compatible PowerShell template interface,
  non-secret configuration and mapping contracts, Azure DevOps YAML,
  validation/package/deployment wrappers, focused tests, and Power BI plugin
  documentation.
- Coordination points in existing DevOps routing and the Fabric CI/CD skill
  documentation, without changing their established branch-policy or
  Fabric-data-engineering deployment requirements.
- Azure DevOps YAML and environment resources, Fabric/Power BI workspace
  mappings, and protected runtime identity references only when a repository
  explicitly opts in and supplies approved targets.
