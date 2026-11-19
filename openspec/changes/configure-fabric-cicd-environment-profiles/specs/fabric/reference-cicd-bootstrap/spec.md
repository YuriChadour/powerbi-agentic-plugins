## MODIFIED Requirements

### Requirement: Promote the TEST-verified artifact
Each profile SHALL trigger only from its configured source branch, and a branch matching no profile or more than one profile SHALL fail with a clear routing error. A profile consumes another profile's artifact only when that profile appears in its `promotion.accepts_from`; PROD eligibility SHALL NOT be inferred from an environment name. Protected PROD promotion SHALL consume the exact artifact digest verified in the accepted source profile rather than rebuild it, located by revision lineage (or the branch tip for a hotfix branch). Before any PROD write the capability SHALL validate the source profile and branch, exact revision, successful upstream deployment and required evidence, artifact and member digests, and the fixed target workspace. Failed, missing, mismatched or ambiguous evidence, or no successful build for the resolved revision, SHALL block promotion.

#### Scenario: PROD artifact differs
- **WHEN** the candidate PROD digest differs from the verified source digest
- **THEN** promotion SHALL stop before target writes

#### Scenario: No build exists for the promoted revision
- **WHEN** a merge resolves to a revision with no successful eligible build
- **THEN** deployment SHALL stop before target writes

#### Scenario: Unlisted source is rejected
- **WHEN** a TEST2 or UAT artifact is successful but PROD does not list it in `accepts_from`
- **THEN** PROD SHALL reject the artifact

#### Scenario: Listed source is accepted
- **WHEN** PROD lists a source profile and that profile's revision has complete successful evidence and a matching digest
- **THEN** PROD MAY consume that exact artifact

#### Scenario: Branch route is unsupported or ambiguous
- **WHEN** a source branch matches no profile or more than one profile
- **THEN** artifact selection SHALL fail before any target write

## ADDED Requirements

### Requirement: Environments are configured profiles
The capability SHALL read an ordered list of uniquely keyed environment profiles from `setup.yml` and use it as the only source of environments for setup, generation, validation, deployment and evidence. A profile key SHALL match `^[A-Za-z][A-Za-z0-9_-]{0,31}$` and be unique case-insensitively. Each profile SHALL declare source branch, workspace and capacity, Azure DevOps pipeline name and YAML path, protected environment, variable group, Key Vault credential reference, deploy enablement, optional manual-verification boundary and `promotion.accepts_from`. Generation SHALL not branch on a profile name. A deploy-enabled profile with a non-empty `accepts_from` is the only kind that may consume another profile's artifact, and a deploy-enabled PROD-like profile with an empty list SHALL fail validation. Duplicate or conflicting keys, branch routes, pipeline paths, protected environments or workspace ownership SHALL fail before any write.

#### Scenario: Additional environment is added by configuration
- **WHEN** a developer adds a complete UAT, GO-LIVE or TEST2 profile to an existing DEV/TEST/PROD setup and approves the plan
- **THEN** generation SHALL produce its pipeline, workspace configuration, bindings, guards and evidence without any generator source or template change

#### Scenario: Profile is incomplete or unsafe
- **WHEN** a profile lacks a required field or a key or value contains YAML or PowerShell metacharacters
- **THEN** validation SHALL fail with a profile-specific message before approval or any write

#### Scenario: Legacy four-environment setup
- **WHEN** plan reads a v1 setup with DEV, TEST, PROD and HOTFIX
- **THEN** it SHALL translate to explicit profiles with PROD `accepts_from: [TEST, HOTFIX]`, preserving branches, workspaces, pipeline names and paths, environments and credential references

### Requirement: Existing custom environments are imported as profiles by the agent
When a repository already contains a custom environment such as UAT, the agent SHALL read the existing pipeline definition, YAML, target workspace, protected environment and verification practice and write an equivalent profile entry into `setup.yml` so the environment fits the standard template. Creating a new target workspace SHALL use existing Fabric skills rather than generator code. The plan SHALL list every existing `cicd/fabric` file that regeneration would overwrite and SHALL block on files the generator did not create until the user acknowledges them. The generated release builder SHALL reject `--uat-contract` and any runtime target override. Regeneration SHALL not run before the profile is approved.

#### Scenario: Custom UAT is imported
- **WHEN** an agent imports an existing UAT pipeline as a profile and the user approves it
- **THEN** regeneration SHALL produce UAT through the standard renderer and builder with `--target UAT`

#### Scenario: Unrecognized existing file would be overwritten
- **WHEN** regeneration would replace a `cicd/fabric` file the generator did not create
- **THEN** apply SHALL stop until the user acknowledges the file in the reviewed setup

#### Scenario: Stale contract invocation
- **WHEN** a build invocation passes `--uat-contract` or a runtime workspace override
- **THEN** the builder SHALL fail before packaging

### Requirement: Managed-item binding metadata keeps logical identity
Generated `managed-items.yml` SHALL include each item's normalized `logical_id` alongside id, name, folder, type and dependencies, backfilled from read-only DEV discovery when absent. Binding generation SHALL accept direct IDs, Fabric Git logical IDs, reversed IDs and SQL endpoint IDs. An unresolved required `logical_id` SHALL fail rather than be guessed.

#### Scenario: Logical ID is discovered
- **WHEN** discovery returns a logical ID for a managed DEV item
- **THEN** `managed-items.yml` SHALL record it

#### Scenario: Required logical ID is unresolved
- **WHEN** a consumer check requires a logical ID that discovery cannot resolve
- **THEN** generation SHALL fail with the item named

### Requirement: Credentials come only from the profile's Key Vault reference
Protected deployment SHALL obtain its credential only from the profile's approved Key Vault reference and SHALL NOT fall back to a variable-group secret, environment variable, developer credential or interactive login. Validation and build SHALL remain secretless, and generated files, artifacts and logs SHALL contain no secret values. When a profile has a manual-verification boundary, release evidence SHALL report deployment succeeded and verification pending until verification is explicitly recorded.

#### Scenario: Key Vault access is unavailable
- **WHEN** the Key Vault reference is missing or unauthorized
- **THEN** deployment SHALL stop before any target write

#### Scenario: Deployment before manual verification
- **WHEN** a profile with a manual boundary deploys successfully
- **THEN** evidence SHALL show deployment succeeded and verification pending
