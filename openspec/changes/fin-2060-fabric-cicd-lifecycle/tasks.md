## 1. Discovery and repository contracts

- [ ] 1.1 Implement repository discovery for `fabric/`, `pbi/`, `cicd/`, Git remotes, target branches, Fabric Git connection state, initial synchronization evidence, and existing pipeline assets; verify the plan distinguishes Fabric-only, Power BI-only, mixed, and unconfigured repositories.
- [ ] 1.2 Define and validate `cicd/managed-items.yml` for Fabric source roots, DEV/PROD workspaces, item types, logical IDs, dependencies, data policy, exclusions, and non-secret deployment-identity references; verify malformed, duplicate, missing-path, unsupported-type, and missing-sync-evidence fixtures fail closed.
- [ ] 1.3 Define a separate `pbi-assets.yml` contract for Power BI source-to-workspace mappings and Fabric prerequisites; verify a `pbi/` folder alone does not trigger Power BI or Fabric deployment setup.
- [ ] 1.4 Add explicit cross-domain dependency validation so a Power BI release can require a successful Fabric release without sharing workspace credentials; verify invalid or cyclic dependency fixtures are rejected.

## 2. Repository bootstrap and templates

- [ ] 2.1 Add idempotent templates for manifest/configuration, dependency locks, validation entry points, release packaging, deployment guards, post-deployment checks, and lifecycle documentation; verify bootstrap produces a reviewable diff and preserves unrelated files.
- [ ] 2.2 Generate secretless Fabric source-validation assets and path-scoped pipeline definitions; verify they never request Fabric deployment credentials.
- [ ] 2.3 Generate the trusted DEV drift-validation template and adapter configuration; verify it consumes the shared drift report contract and fails closed on export or authentication errors.
- [ ] 2.4 Generate shared release-stage templates plus thin `fabric-dev.yml` and `fabric-prod.yml` wrappers; verify both wrappers consume the same immutable artifact without repository checkout or rebuild.
- [ ] 2.5 Generate immutable release and protected DEV rehearsal/PROD deployment templates for the Fabric scope; verify the artifact includes revision, manifest, dependency, and content-hash metadata.
- [ ] 2.6 Generate Power BI validation/release assets only when `pbi-assets.yml` contains an explicit approved mapping; verify Fabric-only repositories receive no Power BI pipeline files.
- [ ] 2.7 Generate target-specific DEV/PROD write guards, protected environment references, and post-deployment verification/audit assets; verify missing guards stop before writes and repeated DEV rehearsal is idempotent.
- [ ] 2.8 Provide plan, bootstrap, validate, drift, release, status, and rollback-oriented command modes; verify plan/status modes perform no repository or external writes.

## 3. Azure DevOps governance configuration

- [ ] 3.1 Implement read-only discovery and diff planning for path-scoped Azure Repos policies, environments, service connections, variable groups/Key Vault references, agent pools, and protected checks; verify the plan reports exact missing or conflicting resources and does not introduce Azure Boards policy by default.
- [ ] 3.2 Apply separate Fabric and Power BI DEV/PROD build-validation policies only after explicit confirmation; verify repeated configuration is idempotent, preserves path scopes, and does not duplicate policies.
- [ ] 3.3 Configure protected `fabric-dev` and `fabric-prod` environments, approved target-specific deployment identities, and agent-pool permissions without exposing secret values; verify unauthorized or missing protected resources block readiness.
- [ ] 3.4 Add protected variable-group and Key Vault connectivity preflight; verify the required secret can be retrieved by the approved identity without logging its value and that failures stop before deployment.
- [ ] 3.5 Keep Fabric and Power BI governance resources separately scoped; verify Power BI policy changes cannot grant Fabric deployment permissions and vice versa.
- [ ] 3.6 Provide manual recovery instructions when the user declines an external write or the Azure DevOps CLI/API is unavailable; verify repository files remain unchanged in that case.

## 4. Validation and DEV drift lifecycle

- [ ] 4.1 Extract the existing notebook, pipeline, and `.platform` semantic comparator into the reusable lifecycle boundary; verify local and trusted pipeline callers receive identical `PASS`, `DRIFT`, `ERROR`, and `UNKNOWN` results.
- [ ] 4.2 Implement read-only DEV export with temporary output, CLI/authentication checks, excluded-content protection, redacted diagnostics, and preserved report paths; verify missing CLI, workspace, item, or authentication fails closed.
- [ ] 4.3 Add the trusted server-side DEV drift pipeline and required build-validation policy with a pinned Fabric CLI and protected read-only identity; verify local helper success cannot mark release readiness when the trusted stage is missing.
- [ ] 4.4 Integrate the generic branch/Jira guard and DEV PR helper through a thin delegation hook; verify the helper contains no Fabric workspace, credential, parser, or deployment logic.
- [ ] 4.5 Block DEV PR creation and merge on drift, export failure, unknown status, or missing required policy; verify an integration fixture proves `az repos pr create` is not invoked on failure.
- [ ] 4.6 Keep pull-request validation read-only and separate from post-merge execution; verify a DEV PR does not write to Fabric and a successful DEV merge invokes the approved `fabric-dev` rehearsal only when its environment, identity, and write guard are present.
- [ ] 4.7 Verify the DEV rehearsal deploys metadata/definitions only, excludes rows/credentials/schedules/triggers/SQL endpoints, and publishes item-level verification/audit evidence.

## 5. Release, deployment, and evidence

- [ ] 5.1 Implement source, manifest, secret, dependency, and excluded-data validation before packaging; verify invalid or incomplete source cannot produce a release artifact.
- [ ] 5.2 Build an immutable Fabric artifact from the exact merged revision; verify the package records content hashes, resolved manifests, pinned dependencies, approved identity reference, and artifact identity without secret values.
- [ ] 5.3 Implement protected DEV rehearsal and DEV-to-PROD deployment preflight and identity checks; verify mismatched revisions, manifests, identities, guards, approvals, or inputs stop before any target write.
- [ ] 5.4 Add post-deployment checks and audit records for both DEV and PROD managed items, dependencies, generated companion availability, and policy state; verify partial failures stop dependent actions and retain item-level evidence.
- [ ] 5.5 Add rollback selection based on a prior known-good immutable artifact; verify rollback requires the same protected approval and target preflight as a normal release.
- [ ] 5.6 Add optional Power BI promotion ordering after successful Fabric prerequisites; verify Power BI-only releases remain independent and mixed releases respect the declared dependency graph.

## 6. Fabric orchestration and security integration

- [ ] 6.1 Route cross-workload CI/CD requests from `FabricDataEngineer` to the new lifecycle skill; verify existing specialist Fabric skills remain the owners of endpoint-specific implementation.
- [ ] 6.2 Keep the generic branch/Jira guard responsible only for branch and ticket rules; verify Fabric workspace, export, and credential logic remains outside the guard.
- [ ] 6.3 Enforce protected read-only DEV identities for drift and separate approved PROD identities for deployment; verify no fallback to developer credentials occurs.
- [ ] 6.4 Redact tokens, passwords, connection strings, and secret values from command output, reports, and build artifacts; verify secret-scan fixtures pass for normal and failure paths.

## 7. Tests, reference bootstrap, and rollout

- [ ] 7.1 Add unit fixtures for manifest parsing, mixed-scope routing, cross-domain dependency validation, notebook comparison, pipeline comparison, platform exceptions, and excluded content; verify the focused test suite passes.
- [ ] 7.2 Add integration fixtures for bootstrap idempotency, external-plan confirmation, DEV drift blocking, immutable artifact verification, protected deployment preflight, and rollback evidence; verify expected exit codes and reports.
- [ ] 7.3 Run the orchestrator in report-only mode against the reference Analytics Reporting `cicd/` asset map; verify existing assets are inventoried before any generated replacement is proposed.
- [ ] 7.4 Validate the generated secretless validation, trusted drift, shared release stages, DEV rehearsal, and PROD deployment templates on supported hosted/self-hosted agents; verify agent-pool authorization, protected-resource connectivity, and target guards before release.
- [ ] 7.5 Validate OpenSpec artifacts and document adoption, dry-run, confirmation, rollback, and separate Fabric/Power BI workspace procedures; verify the final status reports all planning artifacts complete.
