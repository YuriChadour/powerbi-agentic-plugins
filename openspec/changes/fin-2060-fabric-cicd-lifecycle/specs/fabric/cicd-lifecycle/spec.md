## Purpose

Establishes a reusable, idempotent Fabric CI/CD lifecycle for a new or existing repository, from scope discovery and validation through DEV authoring and Git review, immutable release packaging, protected deployment, and operational evidence.

## ADDED Requirements

### Requirement: Discover and classify the repository delivery scope

The capability SHALL inspect the repository and identify Fabric source roots, Power BI source roots, existing CI/CD assets, target branches, configured managed items, and any Fabric Git connection state before proposing changes. It SHALL classify the repository as Fabric-only, Power BI-only, mixed, or unconfigured and SHALL surface missing or ambiguous inputs before bootstrap. When Fabric Git synchronization is in scope, it SHALL record the initial synchronization direction, result, source revision, and target branch before enabling promotion.

#### Scenario: New Fabric repository is discovered

- **WHEN** a repository contains Fabric source items but no complete CI/CD contract
- **THEN** the capability SHALL produce a bootstrap plan identifying the source root, candidate managed items, distinct DEV/TEST/PROD workspace inputs, and required CI/CD assets

#### Scenario: Existing CI/CD implementation is discovered

- **WHEN** the repository already contains manifests, validation, release, or deployment assets
- **THEN** the capability SHALL inventory them, preserve compatible assets, and identify only missing or conflicting pieces rather than replacing them silently

#### Scenario: Power BI-only repository is discovered

- **WHEN** no Fabric-managed items are in scope and the repository is explicitly Power BI-only
- **THEN** the capability SHALL not create Fabric export, deployment, or drift assets and SHALL report the Fabric lifecycle as not applicable

#### Scenario: Required scope input is ambiguous

- **WHEN** the source root, workspace mapping, managed item type, or target branch cannot be determined safely
- **THEN** the capability SHALL stop at planning and request the missing decision without writing external configuration

#### Scenario: Fabric Git synchronization evidence is missing

- **WHEN** Fabric Git integration is used and its initial synchronization direction, result, or source revision is not recorded
- **THEN** the capability SHALL report the missing evidence and SHALL not mark Fabric synchronization or promotion as ready

### Requirement: Bootstrap a repository CI/CD contract

After an approved bootstrap action, the capability SHALL create or update the repository-local CI/CD contract needed to validate and release the declared scope. For Fabric scope the contract SHALL include distinct DEV authoring, TEST and PROD workspace mappings, the DEV branch mapping, and protected TEST and PROD environment and deployment identity/service-connection references. It SHALL also include managed-item mappings, source roots, dependencies, logical IDs, data exclusions, pinned runtime/dependency inputs, validation entry points, release packaging inputs, and explicit Power BI scope boundaries. Power BI's separately mapped repository/PBIP source SHALL NOT be forced through a Fabric TEST workspace. Bootstrap SHALL be idempotent and SHALL show a diff before overwriting an existing file. The DEV workspace-to-branch mapping and initial synchronization SHALL be established for authoring.

#### Scenario: New Fabric CI/CD assets are scaffolded

- **WHEN** the user approves a bootstrap plan for a repository without the required contract
- **THEN** the capability SHALL create the manifest, validation configuration, release/deployment templates, dependency lock inputs, and documentation needed by later lifecycle stages

#### Scenario: Existing asset conflicts with the plan

- **WHEN** a repository file or configuration conflicts with the proposed contract
- **THEN** the capability SHALL report the conflict and require an explicit update decision rather than overwriting it automatically

#### Scenario: Managed scope excludes data and operational state

- **WHEN** the contract is generated or validated
- **THEN** it SHALL explicitly exclude Lakehouse data rows, generated SQL endpoints, schedules, run history, credentials, and secrets from source-controlled deployment scope

### Requirement: Establish Azure DevOps governance with explicit authorization

The capability SHALL be able to configure or validate path-scoped Azure DevOps build-validation policies, environments, service connections, protected variable groups, Key Vault references/connectivity checks, agent-pool permissions, and protected-resource approvals required by the lifecycle. Fabric and Power BI policy scopes SHALL remain independently configurable. Jira SHALL remain the default work-tracking integration; the capability SHALL not add Azure Boards work-item-link policy unless explicitly requested. External writes SHALL require a displayed plan and explicit user confirmation, SHALL be idempotent, and SHALL preserve user-owned configuration that is outside the requested scope.

#### Scenario: Branch governance supports the selected workflows

- **WHEN** the user approves governance setup
- **THEN** the capability SHALL verify that authorized Fabric workspace users can commit directly to DEV and that Power BI and other scopes retain their applicable PR policies, and SHALL report configured policy identities and status

#### Scenario: Branch policies conflict with direct DEV commits

- **WHEN** the existing DEV branch policy or permissions prevent Fabric Git integration from committing directly
- **THEN** the capability SHALL report the conflict and the required authorized policy decision; it SHALL NOT silently bypass or weaken existing protections

#### Scenario: Protected deployment resources are missing

- **WHEN** the release lifecycle requires an environment, service connection, variable group, or agent pool permission that is absent
- **THEN** the capability SHALL identify the missing protected resource and block release readiness until it is configured; required identity, protected approval, target guard, and agent authorization SHALL NOT be waived

#### Scenario: Governance configuration is already compliant

- **WHEN** existing policies and protected resources match the requested contract
- **THEN** the capability SHALL report them as compliant without recreating or duplicating resources

#### Scenario: User declines an external write

- **WHEN** the user does not confirm an Azure DevOps configuration change
- **THEN** the capability SHALL leave external state unchanged and SHALL provide the remaining manual steps

#### Scenario: Protected variable-group or Key Vault preflight fails

- **WHEN** a deployment stage requires a protected variable group or Key Vault-backed secret and its reference, connectivity, authorization, or required secret is missing
- **THEN** the capability SHALL block release readiness before secret retrieval or Fabric write and SHALL provide a redacted diagnostic

#### Scenario: Fabric and Power BI policies are path-scoped

- **WHEN** the repository contains both `fabric/` and `pbi/` source roots
- **THEN** the capability SHALL validate the applicable independent governance and release scope for each root, and SHALL report any inability to enforce the intended direct-commit and PR separation rather than treating path-scoped PR policies as protection against direct commits

### Requirement: Validate source and produce an immutable release artifact

The lifecycle SHALL validate manifests, source definitions, supported item types, secret-like content, excluded data content, and required dependencies before release. A successful release build SHALL identify the exact source revision, resolved manifest, approved TEST and PROD deployment-identity references, dependency versions, content hashes, and package identity in an immutable artifact. Secret values SHALL never be included in the manifest or artifact.

#### Scenario: Repository validation passes

- **WHEN** all configured source files, manifests, exclusions, and dependency checks are valid
- **THEN** the capability SHALL return success and produce the release inputs required for packaging

#### Scenario: Validation detects unsafe or incomplete source

- **WHEN** source content is malformed, unsupported, secret-like, data-bearing, missing, or outside the declared managed scope
- **THEN** the capability SHALL fail closed and SHALL not produce a releasable artifact

#### Scenario: Release artifact is built

- **WHEN** source validation passes on a specific selected DEV revision
- **THEN** the capability SHALL create an immutable artifact whose manifest and hashes can be verified without rebuilding from another revision

### Requirement: Author Fabric data engineering in DEV and review the release commit

For explicitly scoped Fabric data-engineering work, the lifecycle SHALL support authoring and testing in the shared DEV workspace using the Data Engineering extension. The operator SHALL review pending workspace changes and use Fabric Git integration to commit the selected supported managed definitions to the configured DEV branch. The operator SHALL deliberately select and validate the exact DEV commit for release, confirming its contents and accounting for unfinished or uncommitted workspace work. A feature or bugfix branch, PR, separate DEV export, repository overwrite reconciliation, or DEV drift gate SHALL NOT be required for this scope. The lifecycle SHALL report unsupported Git or deployment item types and unresolved dependencies before release.

The lifecycle SHALL consume the scope-first intake and mandatory branch guard contract owned by `fin-2060-fabric-de-branch-guard`: the user selects work area first and then bug, feature, or story before branch handling. A Fabric data-engineering bug follows the same eligible DEV route as a feature or story. The direct DEV branch exception SHALL apply only to explicitly identified Fabric data-engineering work. Power BI and other work SHALL retain their existing feature/bugfix branch and PR rules. For mixed work, each portion SHALL follow its applicable rules; ambiguous scope SHALL NOT qualify for the exception.

#### Scenario: DEV authoring is complete

- **WHEN** the operator completes Fabric data-engineering work in DEV
- **THEN** the operator SHALL review pending changes, commit the intended managed items to DEV, and select a validated DEV commit when ready to release

#### Scenario: Validation or scope review fails

- **WHEN** source validation fails or the selected commit contains unintended work
- **THEN** release SHALL stop until the problem is resolved and an appropriate DEV commit is selected

#### Scenario: Initial mapping is unavailable

- **WHEN** the DEV workspace-to-branch mapping, direct commit permissions or initial baseline is missing or ambiguous
- **THEN** the lifecycle SHALL report the missing setup and SHALL NOT claim the DEV release is ready

#### Scenario: Branch guard receives explicit Fabric data-engineering scope

- **WHEN** the mandatory branch guard runs for explicitly scoped Fabric data-engineering-only work on the configured DEV branch
- **THEN** it SHALL permit that branch without requiring a feature/bugfix prefix or Jira key in the branch name, while retaining applicable Jira intake and traceability

#### Scenario: Branch scope or target is unsafe

- **WHEN** scope is missing, ambiguous, mixed, or not Fabric data engineering, or the branch is a protected branch other than the configured DEV branch
- **THEN** the guard SHALL retain the existing feature/bugfix and protected-branch checks and SHALL NOT infer the DEV exception

#### Scenario: Work includes Power BI or another scope

- **WHEN** a change includes Power BI or other non-Fabric-data-engineering work
- **THEN** that work SHALL follow its existing feature/bugfix branch and PR rules even when the change also contains Fabric data engineering

### Requirement: Protect the TEST-to-PROD promotion boundary

Shared DEV SHALL remain available for interactive human and agent authoring and execution. PR validation and release pipelines SHALL NOT deploy, import, publish, or overwrite DEV definitions. After deliberate selection and successful validation of a DEV commit the lifecycle SHALL build one immutable artifact from that exact DEV revision, then deploy it to the distinct protected `fabric-test` environment using its configured TEST workspace, identity/service connection, parameters, and `ALLOW_FABRIC_TEST_WRITE` guard. TEST SHALL verify supported definitions, dependencies and configured execution/integration checks, publishing evidence bound to the artifact digest. PROD SHALL deploy only after successful TEST verification and required approvals and governance, and SHALL consume exactly that same artifact digest through its own protected environment, identity/service connection and guard without re-export or rebuild.

#### Scenario: Selected DEV commit builds once and deploys to TEST

- **WHEN** the intended DEV commit is selected for release, source validation passes, and TEST prerequisites are configured
- **THEN** the lifecycle SHALL build one artifact from that exact DEV revision, deploy that artifact to TEST, publish digest-bound verification evidence, and SHALL NOT deploy the artifact to DEV

#### Scenario: TEST prerequisites are missing

- **WHEN** the TEST workspace, protected environment, identity/service connection, write guard, or required input is unavailable
- **THEN** the lifecycle SHALL stop before TEST writes, report the missing prerequisite, and block PROD promotion

#### Scenario: A deployment target resolves to DEV

- **WHEN** a TEST or PROD deployment workspace resolves to the configured DEV authoring workspace ID
- **THEN** preflight SHALL reject the target before any release write

#### Scenario: TEST deployment excludes operational state

- **WHEN** TEST deploys the selected DEV artifact
- **THEN** it SHALL process only declared metadata and definitions and SHALL not move data rows, credentials, schedules, triggers, run history, or SQL endpoints as release content

#### Scenario: TEST deployment is idempotent

- **WHEN** the same immutable artifact is deployed to TEST more than once
- **THEN** repeated runs SHALL converge on the same managed definitions and produce comparable verification evidence without duplicating unmanaged resources

#### Scenario: TEST verification fails

- **WHEN** TEST deployment, definition verification, or a required execution or integration check fails or is unknown
- **THEN** the lifecycle SHALL retain failure evidence and block PROD promotion

#### Scenario: Source validation runs

- **WHEN** the selected DEV commit is validated for release
- **THEN** the lifecycle SHALL perform secretless source validation and SHALL not import, publish, or overwrite DEV definitions

#### Scenario: PROD promotion is approved

- **WHEN** TEST verification succeeds, applicable governance and PROD approval pass, and the PROD preflight and write guard succeed
- **THEN** the deployment stage SHALL use only the approved protected identity, target the configured PROD workspace, and consume the exact digest verified in TEST

#### Scenario: PROD deployment prerequisites are invalid

- **WHEN** the artifact revision, manifest hash, identity, protected approval, or required input is missing or mismatched
- **THEN** the deployment SHALL stop before any PROD write and SHALL report the failed prerequisite

### Requirement: Verify deployment and retain recovery evidence

After TEST or PROD deployment, the lifecycle SHALL verify configured managed definitions and dependencies in the target workspace, run configured TEST execution/integration checks, record the deployed artifact digest and outcomes, and provide rollback guidance based on a prior known-good immutable artifact. Partial failures SHALL stop subsequent dependent actions and retain item-level evidence. Status SHALL show the artifact digest and verification outcome in TEST and PROD and the promotion relationship. The generated pipeline contract SHALL support shared release stages with thin TEST and PROD wrappers and target-specific write guards.

#### Scenario: Post-deployment checks pass

- **WHEN** the deployed workspace contains the expected managed items and dependency references
- **THEN** the lifecycle SHALL record artifact digest, revision, target, approver where applicable, environment, and verification results and link PROD promotion to successful TEST evidence

#### Scenario: Target verification is unavailable

- **WHEN** the Fabric API cannot verify the managed inventory after a TEST or PROD deployment
- **THEN** the lifecycle SHALL mark the stage failed or unknown, preserve diagnostics and the artifact identity, and SHALL not report the target as successfully released

#### Scenario: Post-deployment checks fail

- **WHEN** an item, dependency, generated companion check, or policy verification fails
- **THEN** the lifecycle SHALL report the affected items, stop later dependent actions, and identify the last known-good artifact for recovery

#### Scenario: Rollback is requested

- **WHEN** an authorized operator requests rollback after a partial or failed promotion
- **THEN** the lifecycle SHALL identify the selected known-good artifact and digest, record its target and verification history, and require the normal protected deployment approval before writing it

### Requirement: Provide safe lifecycle modes and protect secrets

The capability SHALL expose distinct planning, bootstrap, configure, validate, release, status, and rollback-oriented operations. Read-only modes SHALL not mutate repository or external state; mutating modes SHALL require explicit authorization, redact credentials from output, and fail closed when required secure inputs are unavailable. Secretless source validation SHALL not retrieve protected Fabric deployment credentials.

#### Scenario: Plan or status mode runs

- **WHEN** the user requests planning or status
- **THEN** the capability SHALL inspect and report current state without creating files, changing Azure DevOps resources, or calling Fabric write operations

#### Scenario: Protected credentials are unavailable

- **WHEN** a trusted export or deployment stage lacks its approved identity, variable group, or service connection
- **THEN** the capability SHALL stop with an actionable error and SHALL not fall back to a developer account or unprotected secret

#### Scenario: Shared pipeline stages use protected target guards

- **WHEN** a generated TEST or PROD wrapper invokes the shared release stages
- **THEN** the wrapper SHALL select the correct workspace, environment, audit scope, and target-specific write guard, and the shared stages SHALL consume the immutable artifact without repository checkout or rebuild

#### Scenario: Sensitive values appear in command output

- **WHEN** a command, error, or report could contain tokens, passwords, connection strings, or secret values
- **THEN** the capability SHALL redact or omit those values while retaining diagnostic context

#### Scenario: Generic branch guard remains in scope

- **WHEN** the lifecycle handles Power BI or other non-Fabric-data-engineering work, including mixed work
- **THEN** it SHALL apply the existing feature/bugfix branch and Jira rules to that work; only explicitly scoped Fabric data-engineering work SHALL qualify for the DEV-branch exception

### Requirement: Bootstrap from a complete reusable starter bundle

The capability SHALL provide a versioned, self-contained bundle of reusable scripts, pipeline YAML templates, configuration templates, dependency inputs, and operator guidance derived from the reference CI/CD assets. It SHALL record the source revision and a disposition for every reference file, including Power BI and sample pipeline assets. Bootstrap SHALL render a coherent starter from explicit scope, target, identity-reference, branch, path, and protected-resource inputs, without requiring the reference repository. It SHALL validate rendered syntax, required values, unresolved placeholders, dependencies, and cross-file references. Reference-project identifiers, credentials, item lists, and operational records SHALL NOT be embedded as adopter defaults.

#### Scenario: A new adopter renders the starter

- **WHEN** the adopter supplies the required approved non-secret inputs for a supported Fabric scope
- **THEN** bootstrap SHALL produce compatible validation, release, deployment, verification, and documentation assets and an offline validation entry point, without access to the reference repository

#### Scenario: Optional Power BI scope is absent

- **WHEN** no Power BI mapping is approved
- **THEN** bootstrap SHALL keep Power BI deployment disabled and SHALL NOT render enabled Power BI release assets

#### Scenario: Template inputs are incomplete or inconsistent

- **WHEN** required inputs or template references are missing, malformed, or unresolved
- **THEN** bootstrap SHALL identify the affected fields or files and SHALL NOT report a usable configuration

#### Scenario: Rendered assets already exist

- **WHEN** bootstrap is repeated or rendered content conflicts with an existing file
- **THEN** it SHALL provide a reviewable diff, preserve unrelated files, and require an explicit update decision before overwriting conflicts



### Requirement: Bind promotion and rollback to trusted evidence

The lifecycle SHALL retain each release artifact and digest in an access-controlled store for the configured promotion and rollback window. It SHALL bind the trusted producer and run, source revision, TEST deployment and verification result, and approval to that digest. PROD SHALL consume the exact TEST-verified artifact and SHALL fail closed if provenance, verification evidence, approval, or retained artifact is unavailable or mismatched. Verification SHALL compare supported managed definitions and dependency references to the artifact. Recovery SHALL track managed ownership and explicitly approved deletions, preserve unmanaged items, and report residual managed items after rollback.

#### Scenario: A different artifact is selected for PROD

- **WHEN** the requested artifact digest, trusted producer, or successful TEST verification evidence does not match the approved release
- **THEN** PROD deployment SHALL stop before any write

#### Scenario: Failed release introduced a managed item

- **WHEN** rollback selects an earlier artifact that does not contain a managed item introduced by the failed release
- **THEN** the lifecycle SHALL preserve the item unless an explicit deletion plan is approved, report it as residual, and verify the resulting managed definitions

### Requirement: Exercise the lifecycle with PREQIN-1

The implementation SHALL include a live end-to-end exercise using `C:\Development\PREQIN-1` after offline template tests pass. The exercise SHALL inventory definitions and dependencies, explicitly select supported managed items, and report unsupported types and unresolved dependencies before deployment. It SHALL create dedicated DEV authoring, TEST and PROD workspaces using the Fabric CLI and a selected capacity, and SHALL grant Power BI EOT (Service Principal), application ID `e4b14c44-12a7-4882-a5ed-dbcb036c9d7b` and service principal object ID `97937f89-9a24-49f4-a3be-c757d283b03d`, Contributor in all three workspaces. The service principal SHALL be the TEST and PROD test deployment identity. Test-specific identifiers SHALL NOT become defaults in reusable assets.

The exercise SHALL bootstrap PREQIN-1, establish an initial DEV workspace-to-branch baseline without release-pipeline deployment to DEV, exercise DEV extension authoring, selected-item commit and source validation, select a DEV revision and build one revision-bound artifact, deploy and verify it in TEST, and promote the same verified artifact to PROD through the protected release path. It SHALL retain workspace, role-assignment, artifact digest, approval, deployment, and verification evidence without secrets. Missing capacity, identities, permissions, protected resources, or required dependencies SHALL block the affected live step and be reported; plan/status and offline tests SHALL NOT create resources or run deployments.

#### Scenario: PREQIN-1 live deployment succeeds

- **WHEN** offline tests pass and the selected scope, capacity, identities, workspace role assignments, and protected release resources are available
- **THEN** the exercise SHALL create and verify the three workspaces and Contributor assignments, deploy the artifact to TEST and PROD, and retain definition, dependency, and applicable integration verification evidence linked to the same artifact digest

#### Scenario: PREQIN-1 contains an unsupported or unresolved item

- **WHEN** discovery finds an unsupported type or a dependency that cannot be resolved within the selected scope
- **THEN** the exercise SHALL report it explicitly and SHALL NOT claim that item or its dependent deployment was verified

#### Scenario: Newly created DEV workspace is empty

- **WHEN** a new DEV workspace does not yet contain the selected managed definitions
- **THEN** the exercise SHALL establish and verify the approved initial baseline before DEV authoring and release and SHALL NOT interpret the empty workspace as authority to erase source files

### Requirement: Provide cross-harness lifecycle routing

The lifecycle SHALL provide equivalent scope-first intake, branch handoff, and release behavior through Codex, GitHub Copilot, and Claude using each harness’s supported discovery and interaction mechanisms. When structured choices are unavailable it SHALL support explicit plain-text responses. Verification SHALL identify the result for each harness separately and report unavailable harnesses as unverified.

#### Scenario: Fabric data-engineering bug is routed

- **WHEN** a user in any supported harness selects Fabric data engineering and then bug with exclusive scope
- **THEN** the lifecycle SHALL route to the configured DEV branch guard without requiring a feature or bugfix branch

#### Scenario: Harness interaction is unavailable

- **WHEN** the harness lacks a structured choice control
- **THEN** the lifecycle SHALL present equivalent choices in text and wait for the user response
