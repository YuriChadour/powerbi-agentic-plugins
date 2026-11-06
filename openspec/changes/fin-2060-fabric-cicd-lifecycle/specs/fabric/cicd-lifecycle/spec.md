## Purpose

Establishes a reusable, idempotent Fabric CI/CD lifecycle for a new or existing repository, from scope discovery and validation through DEV drift control, immutable release packaging, protected deployment, and operational evidence.

## ADDED Requirements

### Requirement: Discover and classify the repository delivery scope

The capability SHALL inspect the repository and identify Fabric source roots, Power BI source roots, existing CI/CD assets, target branches, configured managed items, and any Fabric Git connection state before proposing changes. It SHALL classify the repository as Fabric-only, Power BI-only, mixed, or unconfigured and SHALL surface missing or ambiguous inputs before bootstrap. When Fabric Git reconciliation is in scope, it SHALL record the initial synchronization direction, result, source revision, and target branch before enabling promotion.

#### Scenario: New Fabric repository is discovered

- **WHEN** a repository contains Fabric source items but no complete CI/CD contract
- **THEN** the capability SHALL produce a bootstrap plan identifying the source root, candidate managed items, DEV/PROD workspace inputs, and required CI/CD assets

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

- **WHEN** the DEV workspace is connected to Git but the initial synchronization direction, result, or source revision is not recorded
- **THEN** the capability SHALL report the missing evidence and SHALL not mark Fabric reconciliation or promotion as ready

### Requirement: Bootstrap a repository CI/CD contract

After an approved bootstrap action, the capability SHALL create or update the repository-local CI/CD contract needed to validate and release the declared scope. The contract SHALL include managed-item mappings, source roots, dependencies, logical IDs, data exclusions, pinned runtime/dependency inputs, validation entry points, release packaging inputs, and explicit Power BI scope boundaries. Bootstrap SHALL be idempotent and SHALL show a diff before overwriting an existing file.

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

#### Scenario: DEV and PROD branch policies are established

- **WHEN** the user approves governance setup and the repository has declared DEV and PROD targets
- **THEN** the capability SHALL configure required validation policies with the appropriate path scopes and report the resulting policy identities and status

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
- **THEN** the capability SHALL create or validate separate required build-validation policies for each declared path scope and SHALL prevent an unrelated path change from invoking the other release scope

### Requirement: Validate source and produce an immutable release artifact

The lifecycle SHALL validate manifests, source definitions, supported item types, secret-like content, excluded data content, and required dependencies before release. A successful release build SHALL identify the exact source revision, resolved manifest, approved deployment-identity reference, dependency versions, content hashes, and package identity in an immutable artifact. Secret values SHALL never be included in the manifest or artifact.

#### Scenario: Repository validation passes

- **WHEN** all configured source files, manifests, exclusions, and dependency checks are valid
- **THEN** the capability SHALL return success and produce the release inputs required for packaging

#### Scenario: Validation detects unsafe or incomplete source

- **WHEN** source content is malformed, unsupported, secret-like, data-bearing, missing, or outside the declared managed scope
- **THEN** the capability SHALL fail closed and SHALL not produce a releasable artifact

#### Scenario: Release artifact is built

- **WHEN** source validation passes on a specific merged revision
- **THEN** the capability SHALL create an immutable artifact whose manifest and hashes can be verified without rebuilding from another revision

### Requirement: Enforce DEV reconciliation and definition drift

For a Fabric-scoped repository, the lifecycle SHALL provide a read-only DEV definition export and semantic comparison against canonical source before DEV PR creation and required DEV PR validation. The comparator SHALL expose a stable per-item result of `MATCH`, `DRIFT`, or `ERROR` and an overall result of `PASS`, `DRIFT`, `ERROR`, or `UNKNOWN` to local and trusted callers. Notebook comparison SHALL preserve cell type, order, and normalized source while ignoring IDs, execution counts, outputs, and notebook-level execution metadata. Pipeline comparison SHALL parse JSON and ignore only approved export identity fields; activities, expressions, dependencies, connections, parameters, and references remain significant. Lakehouse `.platform` comparison SHALL allow only manifest-verified environment identity exceptions and SHALL report those exceptions explicitly. Unsupported types, missing canonical files, malformed exports, ambiguous locations, or incomplete exports SHALL fail closed rather than be skipped. The gate SHALL preserve export/report evidence and SHALL never import Git content into DEV. A trusted server-side DEV drift stage with the approved protected identity SHALL be required for release readiness; the local PR helper MAY provide an earlier equivalent check but SHALL not replace the server-side policy.

The lifecycle SHALL also provide an explicitly invoked local reconciliation operation that treats DEV as authoritative and overwrites corresponding manifest-mapped repository source files with validated DEV definitions when drift exists. It SHALL convert supported exports to the canonical source format, preserve recoverable previous file contents including uncommitted edits, report affected files, and leave the resulting Git diff for review. It SHALL re-run semantic comparison after synchronization and block PR creation if the result is not `PASS`. It SHALL not change unrelated files, commit or push changes, or write to Fabric. The server-side PR gate SHALL compare only and SHALL NOT synchronize repository files.

#### Scenario: Managed DEV definitions differ from repository source

- **WHEN** the operator invokes local reconciliation and a complete, validated DEV export differs from a managed repository definition
- **THEN** the lifecycle SHALL overwrite the corresponding source with the canonical form of the DEV definition, retain recoverable prior contents, report the file and resulting diff, and revalidate before allowing PR creation

#### Scenario: Synchronization cannot complete safely

- **WHEN** export, conversion, mapping, validation, or a repository write fails during reconciliation
- **THEN** the lifecycle SHALL restore any affected source files to their prior contents, retain diagnostics, and block PR creation

#### Scenario: DEV changes after local synchronization

- **WHEN** trusted PR validation detects new drift after local synchronization
- **THEN** the server-side gate SHALL report drift and block merge without modifying source or DEV

#### Scenario: DEV definitions match source

- **WHEN** all managed DEV items export successfully and executable definitions match the repository source
- **THEN** the drift stage SHALL return `PASS` with a machine-readable report and allow the DEV PR workflow to continue

#### Scenario: Notebook serialization-only differences exist

- **WHEN** an exported notebook differs from canonical source only by line endings, trailing whitespace, final blank lines, cell IDs, execution counts, outputs, or notebook metadata
- **THEN** the comparator SHALL return `MATCH` for that item and SHALL not report executable drift

#### Scenario: Notebook behavior differs

- **WHEN** a notebook cell is added, removed, reordered, changes type, or changes normalized source text
- **THEN** the comparator SHALL return `DRIFT` for that item and identify the changed cell or source

#### Scenario: Pipeline serialization-only differences exist

- **WHEN** parsed pipeline JSON differs only in formatting or approved export identity fields such as IDs, etags, folder identity, or export timestamps
- **THEN** the comparator SHALL return `MATCH` and record the normalized fields as approved exceptions

#### Scenario: Pipeline behavior differs

- **WHEN** pipeline activities, expressions, dependencies, connections, source/sink definitions, parameters, notebook references, lakehouse references, or policies differ
- **THEN** the comparator SHALL return `DRIFT` and prevent the DEV workflow from continuing

#### Scenario: Approved platform identity differs

- **WHEN** a verified item mapping differs only in an approved `.platform` environment identity field such as `config.logicalId` or an approved empty-versus-null description
- **THEN** the comparator SHALL return `MATCH` and report the metadata exception explicitly

#### Scenario: Unexpected platform metadata differs

- **WHEN** a `.platform` difference is outside the approved manifest-verified identity exceptions
- **THEN** the comparator SHALL return `DRIFT` and prevent the DEV workflow from continuing

#### Scenario: Comparator input is unsupported or incomplete

- **WHEN** an item type is unsupported, a canonical file is missing, an export is malformed or incomplete, or an export location is ambiguous
- **THEN** the comparator SHALL return `ERROR` or `UNKNOWN`, preserve diagnostics, and SHALL not silently skip the item

#### Scenario: Drift report is emitted deterministically

- **WHEN** comparison completes or fails for any managed scope
- **THEN** the lifecycle SHALL write a machine-readable report containing workspace, source root, item, type, status, structured differences or errors, approved exceptions, overall result, and preserved export/report locations without secrets

#### Scenario: DEV definitions drift from source

- **WHEN** a managed notebook, pipeline, or non-approved platform field differs semantically
- **THEN** the comparison SHALL report the item and difference, and PR creation or merge SHALL remain blocked until local reconciliation completes and validation passes

#### Scenario: Drift export is unavailable

- **WHEN** the Fabric CLI, authentication, workspace, managed item, or parser is unavailable
- **THEN** the drift stage SHALL return `ERROR` or `UNKNOWN`, preserve diagnostics, and block the DEV PR workflow rather than treating the result as a pass

#### Scenario: Non-Fabric scope reaches the DEV workflow

- **WHEN** the repository or change is explicitly Power BI-only
- **THEN** the lifecycle SHALL skip Fabric export and leave the applicable Power BI validation path unchanged

#### Scenario: Trusted server-side drift validation is not configured

- **WHEN** local drift checks pass but the required Azure Repos build-validation stage, pinned Fabric CLI, or protected read-only DEV identity is unavailable
- **THEN** the lifecycle SHALL report the repository as not release-ready and SHALL block protected promotion

### Requirement: Protect the DEV-to-PROD promotion boundary

The lifecycle SHALL keep interactive DEV authoring/reconciliation separate from trusted deployment stages and PROD deployment. A PR SHALL never write to Fabric. After a successful merge to `DEV`, an explicitly configured `fabric-dev` environment MAY run a production-shaped DEV deployment rehearsal using the exact immutable artifact for the merged revision. The rehearsal SHALL use a DEV-specific write guard and identity, verify the managed inventory, and exclude rows, credentials, schedules, triggers, and generated SQL endpoints. A reviewed DEV-to-PROD promotion SHALL consume that same immutable artifact through a protected environment and an approved PROD deployment identity.

#### Scenario: DEV branch merge triggers rehearsal

- **WHEN** a DEV PR passes required validation and is merged and the repository has enabled the DEV rehearsal contract
- **THEN** the lifecycle SHALL build and verify the merged revision once, run the shared release stages against the DEV workspace through `fabric-dev`, publish verification/audit evidence, and never checkout or rebuild a different revision

#### Scenario: DEV merge has no rehearsal authorization

- **WHEN** a DEV PR passes validation but the DEV environment, identity, or `ALLOW_FABRIC_DEV_WRITE` guard is missing
- **THEN** the lifecycle SHALL stop before any DEV write, report the missing protected prerequisite, and leave the source-control merge intact

#### Scenario: DEV rehearsal excludes operational state

- **WHEN** the DEV rehearsal deploys the merged artifact
- **THEN** it SHALL process only declared metadata and definitions and SHALL not move data rows, credentials, schedules, triggers, run history, or SQL endpoints

#### Scenario: DEV rehearsal is idempotent

- **WHEN** the same immutable artifact is rehearsed in DEV more than once
- **THEN** repeated runs SHALL converge on the same managed definitions and produce comparable verification evidence without duplicating unmanaged resources

#### Scenario: Pull request validation runs

- **WHEN** a DEV PR is opened or updated before merge
- **THEN** the lifecycle SHALL perform source validation and read-only drift checks only and SHALL not import, publish, or overwrite DEV definitions

#### Scenario: PROD promotion is approved

- **WHEN** the DEV-to-PROD promotion is approved, the immutable artifact passes pre-deployment checks, and the PROD write guard is enabled
- **THEN** the deployment stage SHALL use only the approved protected identity, target the configured PROD workspace, and consume the same artifact that was verified in DEV

#### Scenario: PROD deployment prerequisites are invalid

- **WHEN** the artifact revision, manifest hash, identity, protected approval, or required input is missing or mismatched
- **THEN** the deployment SHALL stop before any PROD write and SHALL report the failed prerequisite

### Requirement: Verify deployment and retain recovery evidence

After a successful DEV rehearsal or PROD deployment, the lifecycle SHALL verify the configured managed items and dependencies in the target workspace, record artifact identity and outcomes, and provide rollback guidance based on a prior known-good immutable artifact. Partial failures SHALL stop subsequent dependent actions and retain item-level evidence. The generated pipeline contract SHALL support shared release stages with thin target wrappers and target-specific write guards.

#### Scenario: Post-deployment checks pass

- **WHEN** the deployed workspace contains the expected managed items and dependency references
- **THEN** the lifecycle SHALL record a successful release evidence record with artifact, revision, target, approver, environment, and verification results

#### Scenario: Target verification is unavailable

- **WHEN** the Fabric API cannot verify the managed inventory after a DEV rehearsal or PROD deployment
- **THEN** the lifecycle SHALL mark the stage failed or unknown, preserve diagnostics and the artifact identity, and SHALL not report the target as successfully released

#### Scenario: Post-deployment checks fail

- **WHEN** an item, dependency, generated companion check, or policy verification fails
- **THEN** the lifecycle SHALL report the affected items, stop later dependent actions, and identify the last known-good artifact for recovery

#### Scenario: Rollback is requested

- **WHEN** an authorized operator requests rollback after a partial or failed promotion
- **THEN** the lifecycle SHALL identify the selected known-good immutable artifact and require the normal protected deployment approval before writing it

### Requirement: Provide safe lifecycle modes and protect secrets

The capability SHALL expose distinct planning, bootstrap, configure, validate, drift comparison, local reconciliation, release, status, and rollback-oriented operations. Read-only modes SHALL not mutate repository or external state; mutating modes SHALL require explicit authorization, redact credentials from output, and fail closed when required secure inputs are unavailable. Secretless source validation SHALL not retrieve protected Fabric deployment credentials.

#### Scenario: Plan or status mode runs

- **WHEN** the user requests planning or status
- **THEN** the capability SHALL inspect and report current state without creating files, changing Azure DevOps resources, or calling Fabric write operations

#### Scenario: Protected credentials are unavailable

- **WHEN** a trusted export or deployment stage lacks its approved identity, variable group, or service connection
- **THEN** the capability SHALL stop with an actionable error and SHALL not fall back to a developer account or unprotected secret

#### Scenario: Shared pipeline stages use protected target guards

- **WHEN** a generated DEV or PROD wrapper invokes the shared release stages
- **THEN** the wrapper SHALL select the correct workspace, environment, audit scope, and target-specific write guard, and the shared stages SHALL consume the immutable artifact without repository checkout or rebuild

#### Scenario: Sensitive values appear in command output

- **WHEN** a command, error, or report could contain tokens, passwords, connection strings, or secret values
- **THEN** the capability SHALL redact or omit those values while retaining diagnostic context

#### Scenario: Generic branch guard remains in scope

- **WHEN** the lifecycle validates a feature or bugfix branch and Jira key
- **THEN** it SHALL delegate branch/Jira rules to the existing generic guard and SHALL not embed Fabric workspace, credential, or export logic in that guard

### Requirement: Bootstrap from a complete reusable starter bundle

The capability SHALL provide a versioned, self-contained bundle of reusable scripts, pipeline YAML templates, configuration templates, dependency inputs, and operator guidance derived from the reference CI/CD assets. It SHALL record the source revision and a disposition for every reference file, including Power BI and sample pipeline assets. Bootstrap SHALL render a coherent starter from explicit scope, target, identity-reference, branch, path, and protected-resource inputs, without requiring the reference repository. It SHALL validate rendered syntax, required values, unresolved placeholders, dependencies, and cross-file references. Reference-project identifiers, credentials, item lists, and operational records SHALL NOT be embedded as adopter defaults.

#### Scenario: A new adopter renders the starter

- **WHEN** the adopter supplies the required approved non-secret inputs for a supported Fabric scope
- **THEN** bootstrap SHALL produce compatible validation, drift, release, deployment, verification, and documentation assets and an offline validation entry point, without access to the reference repository

#### Scenario: Optional Power BI scope is absent

- **WHEN** no Power BI mapping is approved
- **THEN** bootstrap SHALL keep Power BI deployment disabled and SHALL NOT render enabled Power BI release assets

#### Scenario: Template inputs are incomplete or inconsistent

- **WHEN** required inputs or template references are missing, malformed, or unresolved
- **THEN** bootstrap SHALL identify the affected fields or files and SHALL NOT report a usable configuration

#### Scenario: Rendered assets already exist

- **WHEN** bootstrap is repeated or rendered content conflicts with an existing file
- **THEN** it SHALL provide a reviewable diff, preserve unrelated files, and require an explicit update decision before overwriting conflicts

### Requirement: Isolate trusted PR drift execution

Credentialed DEV drift validation SHALL execute only trusted pipeline definitions, scripts, comparator, and dependencies bound to a protected revision. It SHALL treat PR content as untrusted data and SHALL prevent PR changes from running code with the protected identity. If this boundary cannot be enforced, the trusted gate SHALL fail closed and release readiness SHALL be blocked.

#### Scenario: A PR modifies validation code

- **WHEN** a PR changes pipeline YAML, scripts, dependencies, or comparator code used by the drift gate
- **THEN** the credentialed stage SHALL use the protected trusted versions and SHALL NOT execute the PR versions with the protected identity

### Requirement: Protect DEV authoring during rehearsal

The lifecycle SHALL serialize managed deployments per target workspace and compare the current DEV managed definitions immediately before rehearsal with the recorded state validated for the merge. It SHALL use an atomic target version precondition when available; otherwise an independently enforced authoring freeze SHALL be required for release readiness. A changed or unverifiable target SHALL block the write and require reconciliation.

#### Scenario: DEV changes after validation

- **WHEN** a managed DEV definition changes between validation and rehearsal
- **THEN** rehearsal SHALL stop before overwriting that definition and report the reconciliation required

#### Scenario: No atomic concurrency control is available

- **WHEN** a target cannot enforce an atomic precondition and no independently enforced authoring freeze exists
- **THEN** the lifecycle SHALL report the race as unresolved and SHALL block release readiness

### Requirement: Bind promotion and rollback to trusted evidence

The lifecycle SHALL retain each release artifact and digest in an access-controlled store for the configured promotion and rollback window. It SHALL bind the trusted producer and run, source revision, DEV verification result, and approval to that digest. PROD SHALL consume the exact DEV-verified artifact and SHALL fail closed if provenance, verification evidence, approval, or retained artifact is unavailable or mismatched. Verification SHALL compare supported managed definitions and dependency references to the artifact. Recovery SHALL track managed ownership and explicitly approved deletions, preserve unmanaged items, and report residual managed items after rollback.

#### Scenario: A different artifact is selected for PROD

- **WHEN** the requested artifact digest, trusted producer, or DEV verification evidence does not match the approved release
- **THEN** PROD deployment SHALL stop before any write

#### Scenario: Failed release introduced a managed item

- **WHEN** rollback selects an earlier artifact that does not contain a managed item introduced by the failed release
- **THEN** the lifecycle SHALL preserve the item unless an explicit deletion plan is approved, report it as residual, and verify the resulting managed definitions

### Requirement: Exercise the lifecycle with PREQIN-1

The implementation SHALL include a live end-to-end exercise using `C:\Development\PREQIN-1` after offline template tests pass. The exercise SHALL inventory definitions and dependencies, explicitly select supported managed items, and report unsupported types and unresolved dependencies before deployment. It SHALL create dedicated DEV and PROD workspaces using the Fabric CLI and a selected capacity, and SHALL grant Power BI EOT (Service Principal), application ID `e4b14c44-12a7-4882-a5ed-dbcb036c9d7b` and service principal object ID `97937f89-9a24-49f4-a3be-c757d283b03d`, Contributor in both workspaces. The service principal SHALL be the test deployment identity; trusted drift SHALL use a separate protected read-only identity. Test-specific identifiers SHALL NOT become defaults in reusable assets.

The exercise SHALL bootstrap PREQIN-1, establish an explicit initial DEV baseline before DEV-authoritative reconciliation, run the applicable trusted validation, build one revision-bound artifact, deploy and verify it in DEV, and promote the same verified artifact to PROD through the protected release path. It SHALL retain workspace, role-assignment, artifact, approval, deployment, and verification evidence without secrets. Missing capacity, identities, permissions, protected resources, or required dependencies SHALL block the affected live step and be reported; plan/status and offline tests SHALL NOT create resources or run deployments.

#### Scenario: PREQIN-1 live deployment succeeds

- **WHEN** offline tests pass and the selected scope, capacity, identities, workspace role assignments, and protected release resources are available
- **THEN** the exercise SHALL create and verify the dedicated workspaces and Contributor assignments, deploy the artifact to DEV and PROD, and retain definition and dependency verification evidence linked to the same artifact digest

#### Scenario: PREQIN-1 contains an unsupported or unresolved item

- **WHEN** discovery finds an unsupported type or a dependency that cannot be resolved within the selected scope
- **THEN** the exercise SHALL report it explicitly and SHALL NOT claim that item or its dependent deployment was verified

#### Scenario: Newly created DEV workspace is empty

- **WHEN** a new DEV workspace does not yet contain the selected managed definitions
- **THEN** the exercise SHALL establish and verify the approved initial baseline before running DEV-to-repository reconciliation and SHALL NOT interpret the empty workspace as authority to erase source files
