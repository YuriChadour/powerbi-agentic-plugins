## Why

The repository currently has Fabric workload skills and a DevOps PR helper, but no reusable capability that can establish the complete CI/CD operating model for a new Fabric-enabled project. The DEV definition drift check is necessary, but it is only one control inside a larger lifecycle spanning repository bootstrap, validation, release packaging, protected deployment, governance, and rollback evidence.

## What Changes

- Introduce a Jira-linked `fabric-cicd-lifecycle` capability for net-new Fabric CI/CD setup and ongoing operation.
- Discover a repository's Fabric and Power BI scope and generate or validate the repository CI/CD contract, including managed-item manifest, source roots, Fabric Git connection and initial-sync evidence, exclusions, pinned dependencies, and validation entry points.
- Scaffold secretless source-validation, DEV drift-validation, immutable release-packaging, protected DEV rehearsal and PROD deployment, post-deployment verification, and rollback evidence assets from reusable templates.
- Configure and validate path-scoped Azure DevOps build-validation policies, environments, service connections, protected variable groups/Key Vault references, and agent-pool permissions through explicit user-confirmed operations. Keep Jira as the work-tracking system unless the adopter explicitly chooses another integration.
- Keep interactive DEV authoring/reconciliation distinct from trusted post-merge deployment rehearsal and PROD deployment. A DEV merge may trigger an explicitly configured rehearsal through the protected `fabric-dev` environment, but a PR must never write to Fabric.
- Run the DEV definition drift gate as one lifecycle stage before DEV PR creation/merge, with the existing read-only, semantic comparison, report, and fail-closed behavior. The merged revision may then flow through the same immutable artifact stages used by PROD, targeting DEV first.
- Preserve a stable drift result contract across local and trusted callers: type-aware normalization for notebooks, pipelines, and Lakehouse platform metadata; structured item-level differences and approved exceptions; deterministic reports on pass and failure; and no silent skips for unsupported or incomplete exports.
- Reuse the reference project's shared release-stage topology (thin `fabric-dev.yml`/`fabric-prod.yml` wrappers, target-specific write guards, and post-deployment verification) as an adapter pattern rather than hard-coding that project's paths, IDs, or secrets.
- Require a trusted server-side DEV drift stage and protected identity before treating the lifecycle as release-ready; a local pre-PR helper is an immediate safeguard, not a replacement for required Azure Repos validation.
- Route the capability through the existing Fabric data-engineering orchestration while preserving generic branch/Jira guard ownership and separate Power BI release scope.
- Provide plan, bootstrap, configure, validate, drift, release, status, and rollback-oriented operating modes with idempotent checks and clear recovery evidence.

## Capabilities

### New Capabilities

- `fabric/cicd-lifecycle`: Establish and operate a complete Fabric CI/CD lifecycle, including repository bootstrap, Azure DevOps governance, validation, drift control, immutable release packaging, protected deployment, and operational evidence.

### Modified Capabilities

- None.

## Impact

- New reusable Fabric CI/CD skill, templates, adapters, tests, and documentation under `plugins/fabric`.
- Integration with `FabricDataEngineer` routing from the existing Fabric orchestration capability.
- Integration points in the DevOps PR helper for DEV-targeted validation without moving Fabric logic into the generic branch guard.
- Fabric CLI export/authentication and Azure DevOps CLI/API dependencies.
- Protected Azure DevOps resources: path-scoped build policies, `fabric-dev`/`fabric-prod` environments, service connections, variable groups/Key Vault references, and agent-pool permissions.
- No DEV mutation during pull-request validation, no data-row export, and no change to existing Power BI release behavior unless a repository explicitly opts into a separate Power BI scope. Any post-merge DEV rehearsal requires its protected environment, identity, and write guard.
