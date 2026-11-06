## Context

The existing Fabric plugin provides workload-specific skills and the DevOps plugin provides generic branch/Jira and PR behavior. The reference Analytics Reporting `cicd/README.md` and its `configure-fabric-cicd` OpenSpec demonstrate the desired operating model: a managed-item manifest, secretless source validation, DEV definition reconciliation, a shared immutable release-stage template with thin DEV/PROD wrappers, a production-shaped DEV rehearsal after merge, protected PROD deployment, post-deployment checks, target-specific write guards, and Azure DevOps governance. The local repository does not yet provide a reusable orchestrator that can establish this model for a new adopter.

See `proposal.md` and `specs/fabric/cicd-lifecycle/spec.md` for the motivation and behavior contract. The narrower `fabric-dev-definition-drift-gate` change remains a reference for the semantic comparator and is not the parent lifecycle.

## Goals / Non-Goals

**Goals:**

- Provide one orchestrator with safe, explicit modes for planning, bootstrap, configuration, validation, drift, release, status, and rollback guidance.
- Separate reusable lifecycle code from repository-local manifests, source layouts, workspace mappings, Fabric Git connection evidence, and identity references.
- Reuse the same validation/comparison contract locally and in trusted Azure Pipelines.
- Make repository and Azure DevOps setup idempotent, diffable, and recoverable.
- Preserve the boundary between interactive DEV source reconciliation, the explicitly authorized DEV rehearsal, and protected PROD deployment.

**Non-Goals:**

- Automatically deciding workspace IDs, service principals, branch-policy scope, or production approvals.
- Writing to DEV during pull-request validation. A post-merge DEV rehearsal is in scope only when its protected environment, identity, and target guard are explicitly configured.
- Moving data rows, schedules, credentials, or generated companion artifacts through Git.
- Replacing specialist Fabric workload skills or the generic branch/Jira guard.

## Decisions

### Architecture Diagram

```mermaid
flowchart TD
    U[User requests Fabric CI/CD setup] --> P[Plan and discover repository]
    P --> R{Scope and existing assets resolved?}
    R -->|No| Q[Request missing decisions]
    R -->|Yes| B[Bootstrap repository contract]
    B --> C[Configure Azure DevOps resources]
    C --> V[Validate source and pipeline configuration]
    V --> D[DEV drift stage]
    D -->|Fail or unknown| X[Preserve report; reconcile; stop]
    D -->|Pass| G[DEV PR + required build policy]
    G --> M[Merge to DEV branch]
    M --> A[Build immutable release artifact once]
    A --> E[DEV rehearsal via fabric-dev wrapper]
    E --> V2[DEV verify and audit]
    V2 --> H[Protected DEV-to-PROD approval]
    H --> W[Deploy same artifact via fabric-prod wrapper]
    W --> Z[PROD verification and release evidence]
    Z --> K[Known-good artifact for rollback]
    S[FabricDataEngineer] --> O[fabric-cicd orchestrator]
    O --> P
    O --> B
    O --> C
    O --> D
    O --> A
    O --> W
```

### 1. Make `fabric-cicd` a staged orchestrator, not a single drift command

The skill will expose a stable command/mode contract while keeping each stage independently testable:

- **Plan/status:** read repository files and Azure DevOps/Fabric metadata; produce a plan or compliance report without writes.
- **Bootstrap:** render missing repository assets from versioned templates and show file diffs before replacing existing content.
- **Configure:** apply only approved Azure DevOps policies, environments, protected resources, and permissions; return resource IDs and status.
- **Validate:** run manifest, source, secret, dependency, and pipeline checks.
- **Drift:** export and compare live DEV definitions using the existing semantic comparator contract.
- **Release:** create a revision-bound immutable artifact after validation.
- **Rollback guidance:** identify and, only after normal approval, redeploy a known-good artifact.

The orchestrator delegates workload-specific implementation to existing Fabric skills and delegates branch/Jira rules to `git-branch-guard`. This avoids creating a second general Fabric agent or embedding CI/CD policy in endpoint skills.

**Alternative rejected:** a single all-or-nothing setup command. It would make read-only discovery impossible, mix repository writes with external writes, and make partial recovery difficult.

### 2. Use a manifest as the repository adapter boundary

Each adopter supplies a `cicd/managed-items.yml` contract describing source root, DEV/PROD workspaces, item folders/types, logical IDs, dependencies, data policy, explicit exclusions, and a non-secret reference to the approved deployment identity. The repository adapter also records the Fabric Git connection, branch/path, initial synchronization direction/result, and source revision when workspace reconciliation is used. The orchestrator validates this contract before creating pipelines and passes it to the comparator, release builder, and deployment runner. Templates must not contain the reference project's workspace names, IDs, service-principal values, or item list.

The bootstrap stage may create a starter manifest only when the user supplies or confirms the workspace and managed-item mapping. It cannot infer a production identity from a display name or silently include all workspace items.

**Alternative rejected:** scanning the workspace and automatically managing every item. That creates an unsafe deployment scope and makes generated SQL endpoints, schedules, and data rows indistinguishable from deployable definitions.

### 3. Separate repository generation from Azure DevOps control-plane configuration

Repository setup renders CI/CD YAML, validation/release scripts, dependency locks, and documentation. Azure DevOps setup uses a separate adapter for path-scoped build-validation policies, environments, service connections, protected variable groups/Key Vault references, agent-pool authorization, and protected checks. The adapter first reads current state, displays a plan, and applies only a minimal idempotent diff after confirmation. Fabric and Power BI policies remain separately scoped, and Jira remains the default work-tracking integration rather than Azure Boards.

Secret values are never generated, copied into Git, or printed. The adapter accepts references to protected resources and verifies their existence/authorization without exposing values. If the user declines an external write, the repository plan remains usable and manual configuration steps are returned.

**Alternative rejected:** encoding Azure DevOps resource IDs or secret values in repository templates. That would couple the reusable skill to one tenant and create credential leakage risk.

### 4. Implement the reference pipeline topology as distinct trust zones

The generated lifecycle follows the README's separation of duties:

1. Secretless Git/source validation for ordinary PR checks.
2. Local/pre-PR DEV drift reconciliation using read-only export.
3. A trusted DEV drift build with protected read-only DEV identity, pinned Fabric CLI, and required Azure Repos branch policy. A local helper is an immediate pre-PR check, not the release-readiness control.
4. DEV merge starts a production-shaped rehearsal only through the protected `fabric-dev` environment; no DEV write occurs during the PR.
5. Immutable release packaging from the exact merged revision, consumed by both targets without checkout or rebuild.
6. DEV verification/audit followed by protected DEV-to-PROD promotion using an approved identity and environment approval.
7. Post-deployment verification, evidence recording, and rollback selection.

The reference adapter uses `fabric-release-stages.yml` for shared build/package/deploy/verify/audit behavior, with thin `fabric-dev.yml` and `fabric-prod.yml` wrappers. The lifecycle must generate equivalent contracts without copying project-specific paths or IDs. Each wrapper supplies its target workspace, environment, audit scope, and write guard (`ALLOW_FABRIC_DEV_WRITE` or `ALLOW_FABRIC_PROD_WRITE`). The release stages verify the immutable artifact and install pinned dependencies before invoking the deployment runner. DEV rehearsal is metadata/definition-only and should be safe to run repeatedly.

The same adapter/report contract is used by local and trusted drift stages. The secretless validation stage never obtains the protected Fabric identity merely to run source checks.

**Alternative rejected:** adding Fabric authentication to all PR validation or using PROD credentials for DEV export. Both violate least privilege and blur the source-validation/deployment boundary.

### 5. Treat release artifacts as the deployment source of truth

The release builder packages the merged revision, resolved manifest, dependency versions, source definitions, and content hashes. The deployment runner verifies those hashes and the approved target identity before writing. It does not checkout a newer revision or rebuild from a mutable workspace. DEV and PROD wrappers consume the same artifact. Partial deployment records affected items and stops dependent work so that rollback can use the last known-good artifact.

**Alternative rejected:** deploying directly from the Git working tree on the agent. That makes retries non-reproducible and prevents proving which source revision reached PROD.

### 6. Keep the drift comparator as a reusable child stage

The existing drift design remains the child implementation for notebook, pipeline, and `.platform` semantic comparison. The lifecycle consumes its stable per-item `MATCH`, `DRIFT`, and `ERROR` results plus overall `PASS`, `DRIFT`, `ERROR`, and `UNKNOWN` result contract and report. Notebook handlers compare cell type/order/normalized source while ignoring serialization metadata; pipeline handlers parse JSON and ignore only approved export identity fields; `.platform` handlers allow only manifest-verified environment identity exceptions. Unsupported types, malformed or incomplete exports, missing canonical files, and ambiguous locations fail closed. Drift is mandatory for Fabric-scoped DEV PRs but does not own release packaging, policy setup, or deployment.

**Alternative rejected:** duplicating drift logic in each generated pipeline. Duplication would cause local and server-side validation to disagree and make normalization fixes unsafe to roll out.

### 7. Integrate with the existing Fabric orchestrator and DevOps helper

`FabricDataEngineer` routes cross-workload CI/CD requests to `fabric-cicd`. The generic branch/Jira guard continues to validate branch shape and ticket identity. The PR helper performs only manifest detection and stage delegation for DEV targets; it does not own Fabric parsers, workspace IDs, credentials, or deployment rules.

### 8. Co-locate source while separating workspaces and release scopes

The standard repository layout may contain both `fabric/` and `pbi/` source roots, but those roots map to separate DEV/PROD workspace pairs, manifests, protected identities, and release pipelines. Fabric assets use the Fabric managed-item contract; Power BI assets require a separate explicit mapping such as `pbi-assets.yml` before the lifecycle generates Power BI validation or release assets.

The lifecycle will model cross-domain dependencies explicitly: a Power BI release may depend on a successful Fabric release when the semantic model or report consumes Fabric-managed data, but the two pipelines remain independently approvable and independently scoped. A repository containing `pbi/` alone does not cause Fabric or Power BI deployment configuration to be inferred from folder presence.

**Alternative rejected:** one shared workspace or one combined credentialed pipeline. That would couple release permissions, make rollback ambiguous, and allow an unrelated Power BI change to mutate Fabric deployment state.

### 9. Keep runtime configuration protected and target-specific

Repository configuration may declare non-secret references to the approved service connections, protected variable groups, Key Vault-backed variables, pinned tool versions, agent queue, and target workspace IDs. A preflight must verify the protected resource can retrieve the required secret without logging its value before release readiness is granted. Secret values remain in protected Azure DevOps resources. The DEV and PROD wrappers use separate environments and write guards, while the shared stages accept only the resolved artifact and target contract. Verification and audit scripts must work for both targets and must fail closed when the target guard, protected identity, or required agent authorization is absent.

## Risks / Trade-offs

- **Bootstrap changes differ from a repository's conventions** → Render to a temporary plan, show diffs, validate existing assets, and require explicit confirmation before replacement.
- **Azure DevOps permissions vary by tenant/project** → Separate read/plan/apply phases and report exact missing protected resources instead of guessing permissions.
- **Workspace metadata is incomplete or ambiguous** → Stop at planning and require explicit mappings; never infer PROD from DEV or by display name alone.
- **A pipeline stage is unavailable** → Fail the affected gate closed, preserve reports, and keep unrelated source validation diagnosable rather than claiming overall readiness.
- **CLI and export formats change** → Pin the trusted CLI dependency, keep type handlers version-aware, and fail on unsupported definitions.
- **Large managed scopes make bootstrap or drift slow** → Process manifest items independently, provide item-level progress/results, and allow explicit scope selection without bypassing required checks.
- **Rollback artifact is valid but target state has changed** → Re-run target preflight and protected approval before rollback; never treat artifact validity as authorization to write.

## Migration Plan

1. Extract the existing drift comparator/report contract into the reusable Fabric CI/CD skill boundary.
2. Add manifest/configuration schema validation and repository template rendering using the reference README asset map.
3. Add plan/diff/apply adapters for Azure DevOps policies and protected resources, starting with read-only discovery and dry-run output.
4. Generate secretless validation, trusted DEV drift, immutable release, protected PROD deployment, and post-deployment templates; validate them against synthetic fixtures.
5. Integrate `FabricDataEngineer` routing and the existing DEV PR helper with thin delegation hooks.
6. Bootstrap the reference Analytics Reporting project in report-only mode, reconcile the generated plan with its existing `cicd/` assets (including shared release stages, DEV rehearsal, target guards, and verification), and record any intentional deviations.
7. Enable external governance writes and blocking path-scoped branch policies only after a user-approved plan, protected-resource connectivity checks, and successful end-to-end smoke validation, including the trusted server-side DEV drift stage.
8. Roll back by disabling generated policy references and removing only lifecycle-owned templates/configuration; retain existing source definitions and unrelated DevOps/Fabric skills.

## Open Questions

- Which Azure DevOps organization/project/repository defaults should the reusable configure adapter accept when the adopting repository has multiple remotes?
- Which supported Fabric CLI version and agent pool should be pinned for the trusted drift and release templates?
