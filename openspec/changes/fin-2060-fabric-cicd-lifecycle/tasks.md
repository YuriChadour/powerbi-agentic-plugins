## 1. Discovery and repository contracts

- [ ] 1.1 Implement repository discovery for `fabric/`, `pbi/`, `cicd/`, Git remotes, target branches, Fabric Git connection state, initial synchronization evidence, and existing pipeline assets; verify the plan distinguishes Fabric-only, Power BI-only, mixed, and unconfigured repositories.
- [ ] 1.2 Define and validate `cicd/managed-items.yml` for DEV/TEST/PROD workspaces, DEV branch mapping, protected resources, items, dependencies and exclusions; validate the initial workspace-to-branch baseline.
- [x] 1.3 Define a separate `pbi-assets.yml` contract for Power BI source-to-workspace mappings and Fabric prerequisites; verify a `pbi/` folder alone does not trigger Power BI or Fabric deployment setup.
- [ ] 1.4 Add explicit cross-domain dependency validation so a Power BI release can require a successful Fabric release without sharing workspace credentials; verify invalid or cyclic dependency fixtures are rejected.

## 2. Repository bootstrap and templates

- [x] 2.1 Inventory all 29 tracked files in Analytics Reporting `cicd/` at commit `db118e88dff09f5c422a4351eeb024d8ba539cf0`, record each file's disposition and provenance, and verify the inventory matches the source tree.
- [ ] 2.2 Port and generalize all applicable reference Python scripts, dependency inputs, and guidance into a versioned skill bundle; verify no project-specific identity, workspace, item list, secret, or operational record becomes a default.
- [ ] 2.3 Parameterize the reference pipeline YAML and four configuration files, adapting the DEV release wrapper to TEST while preserving independent Power BI and Key Vault examples; verify each of the nine YAML references has a documented disposition and all rendered cross-file paths resolve.
- [ ] 2.4 Implement a minimal-input offline bootstrap with a single validation entry point; verify a synthetic adopter can render and validate without the reference checkout or network access, and missing placeholders fail with actionable errors.
- [ ] 2.5 Add idempotent templates for manifest/configuration, dependency locks, validation entry points, release packaging, deployment guards, post-deployment checks, and lifecycle documentation; verify bootstrap produces a reviewable diff and preserves unrelated files.
- [ ] 2.6 Generate secretless Fabric source-validation assets and path-scoped pipeline definitions; verify they never request Fabric deployment credentials.
- [x] 2.7 Document Data Engineering extension authoring, review and commit to DEV, initial workspace-to-branch synchronization, and deliberate DEV revision selection for release.
- [ ] 2.8 Generate shared release-stage templates plus thin `fabric-test.yml` and `fabric-prod.yml` wrappers with target-specific configuration; verify both consume the same immutable artifact without repository checkout or rebuild and no DEV deployment wrapper is generated.
- [ ] 2.9 Generate immutable release and protected TEST/PROD deployment templates for the Fabric scope; verify the artifact includes revision, manifest, dependency, and content-hash metadata.
- [ ] 2.10 Generate Power BI validation/release assets only when `pbi-assets.yml` contains an explicit approved mapping; verify Fabric-only repositories receive no Power BI pipeline files.
- [ ] 2.11 Generate target-specific TEST/PROD write guards, protected environment and service-connection references, and verification/audit assets; verify missing guards stop before writes and repeated TEST deployment is idempotent.
- [ ] 2.12 Provide plan, bootstrap, validate, release, status, and rollback modes; verify plan/status do not mutate repository or external state.

## 3. Azure DevOps governance configuration

- [ ] 3.1 Implement read-only discovery and diff planning for path-scoped Azure Repos policies, environments, service connections, variable groups/Key Vault references, agent pools, and protected checks; verify the plan reports exact missing or conflicting resources and does not introduce Azure Boards policy by default.
- [ ] 3.2 Plan and, after confirmation, configure direct DEV commit permissions and policies for Fabric data engineering and retain feature/bugfix branch and PR policies for Power BI and other work; verify idempotency and scope.
- [ ] 3.3 Configure protected `fabric-test` and `fabric-prod` environments, approved target-specific deployment identity/service-connection references, and agent-pool permissions without exposing secret values; verify unauthorized or missing protected resources block readiness.
- [ ] 3.4 Add protected variable-group and Key Vault connectivity preflight; verify the required secret can be retrieved by the approved identity without logging its value and that failures stop before deployment.
- [ ] 3.5 Keep Fabric and Power BI governance resources separately scoped; verify Power BI policy changes cannot grant Fabric deployment permissions and vice versa.
- [ ] 3.6 Provide manual recovery instructions when the user declines an external write or the Azure DevOps CLI/API is unavailable; verify repository files remain unchanged in that case.

## 4. DEV authoring and release validation

- [ ] 4.1 Establish and validate the DEV workspace-to-branch integration and initial baseline.
- [ ] 4.2 Exercise extension authoring in DEV and committing resulting definitions to the DEV branch.
- [ ] 4.3 Integrate the branch-guard change’s scope-first intake and DEV exception; verify work area precedes bug/feature/story and Power BI, other and mixed work retain their applicable rules.
- [ ] 4.4 Review pending workspace changes, commit selected supported items to DEV, and validate a deliberately selected DEV commit; verify validation failures block release and validation never writes to Fabric.
- [ ] 4.5 Verify packaging uses the exact selected DEV commit and release pipelines reject DEV as a target.
- [ ] 4.6 Verify TEST deployment excludes operational state and publishes verification and integration evidence.

## 5. Release, deployment, and evidence

- [ ] 5.1 Implement source, manifest, secret, dependency, and excluded-data validation before packaging; verify invalid or incomplete source cannot produce a release artifact.
- [ ] 5.2 Build an immutable Fabric artifact from the exact selected DEV revision; verify the package records content hashes, resolved manifests, pinned dependencies, approved TEST/PROD identity references, and artifact identity without secret values.
- [ ] 5.3 Implement protected TEST and PROD deployment preflight and identity checks; verify mismatched revisions, manifests, identities, guards, approvals, or inputs stop before any target write and PROD requires successful TEST.
- [ ] 5.4 Add post-deployment checks and audit records for both TEST and PROD managed definitions, dependencies, generated companion availability, and policy state, including configured TEST execution/integration checks; verify partial failures stop dependent actions and retain item-level evidence.
- [ ] 5.5 Add rollback selection based on a prior known-good immutable artifact and digest with target verification history; verify rollback requires the same protected approval and target preflight as a normal release.
- [ ] 5.6 Add optional Power BI promotion ordering after successful Fabric prerequisites; verify Power BI-only releases remain independent and mixed releases respect the declared dependency graph.
- [ ] 5.7 Bind trusted producer/run, artifact digest, TEST verification, approval, and PROD consumption in retained access-controlled evidence; verify TEST failure, mismatches, missing evidence, or expired artifacts block PROD and no second build occurs.
- [ ] 5.8 Compare deployed supported definitions and dependencies to the artifact and track managed inventory and approved deletions; verify rollback reports introduced residual items and preserves unmanaged resources.
- [ ] 5.9 Extend release status and recovery evidence with TEST and PROD target identities, artifact digests, verification outcomes, and promotion linkage; verify a known-good rollback selection shows its digest and prior verification history.

## 6. Fabric orchestration and security integration

- [ ] 6.1 Route cross-workload CI/CD requests from `FabricDataEngineer` to the new lifecycle skill; verify existing specialist Fabric skills remain the owners of endpoint-specific implementation.
- [ ] 6.2 Consume the `fin-2060-fabric-de-branch-guard` capability rather than duplicating its implementation; verify scope, selected work type, Jira handoff and DEV branch configuration reach the guard.
- [ ] 6.3 Enforce approved TEST/PROD deployment identities; verify no fallback to developer credentials occurs.
- [ ] 6.4 Redact tokens, passwords, connection strings, and secret values from command output, reports, and build artifacts; verify secret-scan fixtures pass for normal and failure paths.

## 7. Tests, reference bootstrap, and rollout

- [ ] 7.1 Add unit fixtures for manifest parsing, mixed-scope routing, dependencies, source validation, excluded content and reports.
- [ ] 7.2 Test bootstrap idempotency, scoped branch routing, DEV commit selection and validation, immutable artifacts, protected deployment and rollback; verify TEST failure blocks PROD and PROD receives the TEST-verified digest.
- [ ] 7.3 Run the orchestrator in report-only mode against the reference Analytics Reporting `cicd/` asset map; verify existing assets are inventoried before any generated replacement is proposed.
- [ ] 7.4 Validate templates offline and validate secretless source checks, release stages, TEST and PROD on authorized agents, including protected-resource connectivity and TEST-gated promotion.
- [ ] 7.5 Validate OpenSpec artifacts and document adoption, dry-run, confirmation, rollback, and separate Fabric/Power BI workspace procedures; verify the final status reports all planning artifacts complete.

- [ ] 7.6 Apply skill-creator guidance to the Fabric lifecycle skill triggers, inputs and handoffs; test Codex, GitHub Copilot, and Claude independently for discovery, scope-first intake, DEV routing and release entry points, including plain-text fallback. Record unavailable harnesses as unverified.

## 8. PREQIN-1 live end-to-end exercise

- [ ] 8.1 After offline tests pass, inventory `C:\Development\PREQIN-1` source items and dependencies, select explicit supported managed scope, and report unsupported types and unresolved dependencies; verify the test manifest accounts for each selected item and does not silently include unsupported assets.
- [ ] 8.2 Resolve DEV/TEST/PROD workspaces, capacity, branch mappings, permissions and TEST/PROD protected resources; report missing prerequisites.
- [ ] 8.3 Create the dedicated DEV authoring, TEST and PROD workspaces with Fabric CLI using the selected capacity; verify workspace IDs, capacity assignments, and creation evidence.
- [ ] 8.4 Grant Power BI EOT (Service Principal), application ID `e4b14c44-12a7-4882-a5ed-dbcb036c9d7b` and object ID `97937f89-9a24-49f4-a3be-c757d283b03d`, Contributor on all three workspaces; verify role assignments using the service principal object ID and retain redacted evidence.
- [ ] 8.5 Bootstrap PREQIN-1 and establish the DEV workspace-to-branch baseline; exercise extension authoring, review and commit of selected items, and DEV revision selection with source validation without allowing an empty workspace to erase source.
- [ ] 8.6 Build one revision-bound immutable artifact and deploy it to TEST using the approved deployment principal; verify supported definitions, dependencies, configured execution/integration checks, identity, guards, and artifact digest and retain evidence.
- [ ] 8.7 Promote the exact TEST-verified artifact through the protected PROD path using the approved deployment principal; verify PROD definitions and dependencies, both target digests and approvals, and retain evidence without secrets.
- [ ] 8.8 Confirm PREQIN-specific workspace and service-principal identifiers are confined to adopter configuration and test evidence; verify reusable templates contain no PREQIN or Power BI EOT defaults.

## 9. Target-neutral bootstrap and recovery

- [ ] 9.1 Add explicit target name/ID and capacity inputs, isolated rehearsal target planning and target-ID alias checks; verify existing DEV/TEST/PROD mappings remain unchanged and plan/status make no writes.
- [ ] 9.2 Generate target-specific deployment configuration from versioned plugin scripts/templates and package selected revision definitions without rebuilding business logic; verify idempotency, diffs and preservation of unrelated files.
- [ ] 9.3 Verify schema-enabled Lakehouse, endpoint, identities, managed shells, notebook Lakehouse bindings and pipeline workspace/Lakehouse/connection destinations; test missing, mismatched and encoded references.
- [ ] 9.4 Enforce an exclusive lock for deployment through verification and require explicit selection of data-writing runtime checks; verify schedules remain disabled and unexpected target writes fail closed.
- [ ] 9.5 Document and validate Spark-first data engineering, protected artifact rollback, separately reviewed Delta recovery and residual-item handling.
- [ ] 9.6 Require an approved evidence location and retention period, record provenance-bound redacted results and revalidate mutable state on resume; test target and permission changes.
