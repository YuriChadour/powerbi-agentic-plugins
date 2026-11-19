## MODIFIED Requirements

### Requirement: Rendered review and approval records gate setup
Before an external setup write, the capability SHALL generate a non-secret setup contract and readable review record from canonical environment profiles. The setup SHALL contain every resolved value and assumed default used by later steps, including each profile's name/key, lifecycle, source branch or branch pattern, resolved workspace and capacity, Azure DevOps pipeline name and YAML path, protected deployment environment, approved Key Vault credential source, variable-group reference, target bindings, verification requirements, promotion role, promotion eligibility and accepted upstream evidence. An ad hoc target SHALL be discovered, or created only by a separately approved realization step, and normalized before generation approval; the approved profile SHALL contain its fixed resolved identifiers rather than a runtime target-redirection mechanism. The records SHALL identify migration compatibility from the effective pipeline setup and every incompatible active asset. Credentials, tokens, client secrets and secret values SHALL NOT be written. Superseded ad hoc generator, contract, test and generated files SHALL be moved together into an isolated `archive/cicd/fabric/<migration-id>/` directory after compatibility validation and SHALL be excluded from active generation, packaging and validation. The developer SHALL approve the rendered setup revision, and setup SHALL refuse an external write if the approved setup changed.

#### Scenario: Rendered contract is awaiting review
- **WHEN** plan completes with a complete non-secret profile mapping or a recoverable unresolved input
- **THEN** generated records SHALL identify every resolved and unresolved value, and approval and apply SHALL remain blocked until the reviewed profile contract is approved

#### Scenario: Approved contract is applied
- **WHEN** the developer records approval and invokes apply
- **THEN** setup SHALL revalidate the approved revision and SHALL perform only actions covered by the approved profile records

#### Scenario: Four-profile legacy setup is rendered
- **WHEN** an existing adopter supplies the legacy DEV, TEST, PROD and HOTFIX configuration
- **THEN** the capability SHALL generate equivalent canonical profiles, preserve the established branch and workspace behavior, and render every resolved value for review

#### Scenario: Additional profile is rendered
- **WHEN** a developer requests a TEST2 or other complete environment profile with its own branch, resolved workspace, pipeline and protected environment
- **THEN** the capability SHALL render that profile without requiring a generator code or YAML-template change

#### Scenario: Ad hoc profile is realized
- **WHEN** an agent creates or discovers an ad hoc UAT target and resolves its workspace, Lakehouse and managed-item identities
- **THEN** the profile SHALL contain those fixed values for review and SHALL require re-approval before any later target change

#### Scenario: Profile is incomplete
- **WHEN** a profile lacks a required routing field, resolved workspace configuration, credential source, target binding or promotion policy
- **THEN** plan or validation SHALL fail with a profile-specific message before approval, artifact packaging or external write

#### Scenario: Setup file changed after approval
- **WHEN** the approved setup file is edited and setup is run
- **THEN** setup SHALL stop before any external write and require review and approval again

### Requirement: Reference-derived protected deployment
The capability SHALL package the selected revision and approved managed scope together with the approved profile configuration, deployment scripts, binding rules and pinned toolchain. Build and validation MAY run on hosted agents without secrets. Every profile SHALL use the same protected deployment path: the job SHALL run on its configured private pool, use its profile's approved WIF Azure Key Vault service connection and secret reference, verify every archive member path and file hash, verify the protected identity and the fixed approved target workspace, and apply only profile-specific bindings. Generated YAML, standard variable groups, setup files, artifacts and logs SHALL NOT contain secret values. Protected deployment SHALL reject missing Key Vault access and SHALL NOT fall back to a variable-group secret, environment variable secret from an unapproved source, interactive credential, developer credential or runtime target discovery.

#### Scenario: Isolated target is prepared
- **WHEN** an approved ad hoc or rehearsal profile is applied
- **THEN** the capability SHALL prepare only the profile-authorized target and managed resources, queue deployment only when requested, and preserve every other profile mapping

#### Scenario: Profile deployment runs without source checkout
- **WHEN** a protected environment job consumes its verified artifact
- **THEN** it SHALL retrieve credentials only from that profile's approved Key Vault configuration, verify and extract the artifact, and deploy only to the fixed workspace and bindings in the approved profile

#### Scenario: Target identity changes after approval
- **WHEN** a runtime input, artifact, or existing target identity differs from the approved profile
- **THEN** deployment SHALL stop before any write and require profile regeneration and approval

#### Scenario: Key Vault access is unavailable
- **WHEN** the approved Key Vault service connection, vault reference, or secret reference is missing or unauthorized
- **THEN** deployment SHALL stop before any target write and SHALL NOT fall back to a secret in a variable group or another source

#### Scenario: Artifact was altered
- **WHEN** a packaged member path is unsafe or a file hash differs from the artifact manifest
- **THEN** deployment SHALL stop before packaged code is run or Fabric is written

#### Scenario: Validation pipeline runs without secrets
- **WHEN** plan, generation, pull-request validation or artifact validation runs
- **THEN** the pipeline SHALL have no secret task, secret variable or protected credential requirement

### Requirement: Promote an eligible verified artifact
Each profile SHALL trigger only from its configured branch or branch pattern. A PROD profile SHALL accept an artifact only from profiles explicitly listed in its promotion policy, such as TEST, TEST2 and HOTFIX. PROD eligibility SHALL NOT be inferred from an environment name, branch shape or successful run alone. Before any PROD write, the capability SHALL validate the resolved source profile and branch, exact source revision, promotion-source eligibility, successful upstream deployment and required evidence, artifact source and member digests, managed-content equivalence and final target workspace. Failed, missing, mismatched or ambiguous upstream evidence SHALL block promotion.

#### Scenario: PROD artifact differs
- **WHEN** the candidate PROD digest or source-managed content differs from the selected promotion artifact
- **THEN** promotion SHALL stop before target writes

#### Scenario: No build exists for the promoted revision
- **WHEN** a PROD merge resolves to a revision or profile with no successful eligible upstream build and evidence
- **THEN** deployment SHALL stop before target writes

#### Scenario: Explicit TEST2 promotion is allowed
- **WHEN** PROD explicitly accepts TEST2 and the TEST2 revision has complete successful evidence and equivalent managed content
- **THEN** PROD MAY select and consume that exact TEST2 artifact

#### Scenario: Name is not a promotion grant
- **WHEN** a TEST2 artifact exists successfully but PROD does not explicitly list TEST2 as a promotion source
- **THEN** PROD SHALL reject the artifact even when branch and digest checks would otherwise pass

#### Scenario: Upstream evidence or digest differs
- **WHEN** required upstream evidence is missing, unsuccessful, belongs to another revision, or the candidate digest differs from the selected artifact
- **THEN** promotion SHALL stop before any target write

#### Scenario: Branch route is unsupported
- **WHEN** a branch or pull-request source does not match any declared profile route or is ambiguous across profiles
- **THEN** artifact selection SHALL fail with a clear unsupported or ambiguous routing message

### Requirement: Hotfixes use cherry-pick branches
A production fix SHALL be deliverable through an explicitly declared HOTFIX profile whose source branch pattern targets the approved hotfix route. The profile SHALL package once, deploy only to its mapped workspace and produce evidence eligible for PROD only when PROD explicitly lists that profile as a promotion source. After an eligible reviewed merge, PROD SHALL consume the exact verified HOTFIX artifact for the branch tip and SHALL NOT rebuild it. Forward-port requirements SHALL be rendered from the declared topology rather than assumed from environment names.

#### Scenario: Cherry-picked fix is promoted
- **WHEN** a HOTFIX profile artifact is successful, its branch route matches the merged pull request and PROD explicitly accepts HOTFIX
- **THEN** PROD SHALL deploy that exact artifact after source, evidence and digest validation

#### Scenario: Cherry-pick bypasses the hotfix branch
- **WHEN** a cherry-picked change reaches the PROD route from a source that does not match the declared HOTFIX branch pattern
- **THEN** deployment SHALL block rather than selecting an older or unrelated artifact

#### Scenario: Hotfix source is not eligible
- **WHEN** PROD does not explicitly accept HOTFIX or the pull request source does not match the HOTFIX profile route
- **THEN** deployment SHALL block before any target write

## ADDED Requirements

### Requirement: Environment profiles are the generation contract
The capability SHALL accept a list or map of uniquely keyed environment profiles and SHALL use those profiles as the source of truth for setup, generation, validation, deployment and release evidence. A profile key SHALL be a stable case-insensitive-safe identifier with an explicit display/name value. Each profile SHALL declare its lifecycle and source branch or branch pattern, Azure DevOps pipeline name and YAML path, protected deployment environment, approved Key Vault-backed credential source, resolved workspace and capacity, target bindings, promotion role, eligible accepted artifact sources when applicable, required upstream evidence and verification requirements. An ad hoc profile SHALL NOT be distinguishable to the runtime builder or deployer from a persistent profile; its special behavior is completed during setup and normalization. No supported-stage behavior SHALL depend on a fixed environment allow-list.

#### Scenario: TEST2 is configured
- **WHEN** a developer adds a complete TEST2 profile and approves the setup
- **THEN** generation SHALL produce TEST2 workspace routing, a dedicated protected environment, a dedicated pipeline and YAML path, profile-specific bindings, guards, validation and evidence without generator source changes

#### Scenario: Ad hoc UAT is configured
- **WHEN** an agent realizes an ad hoc UAT target and emits an approved canonical UAT profile
- **THEN** the normal generator, builder and deployer SHALL consume that profile exactly as they consume any other declared profile

#### Scenario: Profile keys are duplicated
- **WHEN** two profiles resolve to the same profile key or target duplicate routing owned by another profile
- **THEN** validation SHALL fail before generated files are written

#### Scenario: Runtime recognizes a declared profile
- **WHEN** an artifact or deployment target names a profile present in the approved profile set
- **THEN** every script SHALL validate and resolve it through the approved configuration without a fixed environment-name lookup

### Requirement: Ad hoc environments are normalized before deployment
An ad hoc environment lifecycle SHALL be a setup-time operation, not a runtime deployment mode. The agent or setup tooling MAY inspect the effective pipeline setup and discover an existing target during plan. After the developer approves a realization plan listing every resource to create, it MAY create or reuse an isolated workspace, create or validate a Lakehouse and managed item shells, and read back target identities. It SHALL convert those effective results into a canonical profile containing fixed workspace, capacity, Lakehouse, managed-item and binding values. The normalized profile SHALL be reviewed and approved before packaging or deployment. Runtime code SHALL reject target-redirection input rather than consume dynamic workspace or binding data.

#### Scenario: Existing pipeline setup is imported
- **WHEN** an existing ad hoc environment has an effective pipeline, protected resources, target mapping and verification requirements
- **THEN** the agent SHALL review that effective pipeline setup and map its results to canonical profile fields without treating the old generator implementation as an input contract

#### Scenario: Legacy artifacts are archived after migration
- **WHEN** the canonical profile and regenerated pipeline pass compatibility validation
- **THEN** the old generator, intermediate contracts, generator-specific tests and superseded UAT outputs SHALL move together to `archive/cicd/fabric/<migration-id>/`, and active tooling SHALL exclude that directory

#### Scenario: New ad hoc target is realized
- **WHEN** a developer requests a new UAT or similarly isolated environment
- **THEN** setup MAY create or discover the target, resolve its identities and emit a complete profile for approval without changing the normal release runtime

#### Scenario: Runtime attempts target redirection
- **WHEN** a build or deployment invocation supplies a dynamic target contract or workspace override that differs from the approved profile
- **THEN** runtime validation SHALL reject it before packaging or any target write

### Requirement: UAT consumers migrate to a canonical profile
Existing UAT behavior SHALL be preserved by migrating the effective pipeline result, not the old generator implementation. The importer SHALL review the UAT pipeline YAML and registered pipeline setup, protected resources, target workspace/Lakehouse/items, bindings, artifact/evidence behavior and manual-verification boundary, prove equivalence, and populate a canonical UAT profile. Old bootstrap code, intermediate target contracts/schemas, old generated UAT files and generator-specific tests SHALL be moved as one migration bundle into `archive/cicd/fabric/<migration-id>/` after validation, not retained in active paths. Shared release scripts SHALL become profile-aware and SHALL NOT require `--uat-contract` after migration. Deployment success SHALL NOT be reported as runtime verification success. Manual verification SHALL remain pending and tracked separately until explicitly completed.

#### Scenario: Existing UAT CLI input is migrated
- **WHEN** an existing UAT workflow invokes the shared builder with `--target UAT --uat-contract <path>`
- **THEN** migration SHALL convert that input into approved profile values before generation, preserve the existing pipeline name and YAML path unless the migration record lists the change as a manual reconciliation step, and the generated builder SHALL reject `--uat-contract`

#### Scenario: UAT deployment completes before manual verification
- **WHEN** UAT artifact deployment succeeds but manual verification is not recorded
- **THEN** release evidence SHALL report deployment succeeded and verification pending, not complete

#### Scenario: UAT equivalence cannot be proven
- **WHEN** the canonical profile or generated assets cannot preserve the existing UAT target, bindings, evidence or manual-verification boundary
- **THEN** regeneration compatibility validation SHALL fail with a clear UAT asset incompatibility before overwriting supported behavior

### Requirement: Managed-item binding metadata remains compatible
Generated `managed-items.yml` SHALL preserve each managed item's `logical_id` when a logical ID was discovered for its DEV item or already exists in compatible generated state. Binding generation, Copy Job dependency validation and repository-specific binding checks SHALL continue to accept direct item IDs, Fabric Git logical IDs, SQL endpoint IDs and declared explicit mappings. A future equivalent metadata mechanism SHALL NOT replace `logical_id` until it proves the same lookup, validation and migration coverage and existing logical-ID consumers have a documented migration or are removed under a deliberate compatibility gate.

#### Scenario: Managed item has a Fabric Git logical ID
- **WHEN** discovery returns a `logicalId` for a managed DEV item
- **THEN** generated `managed-items.yml` SHALL include the normalized `logical_id` with the item's folder, type and dependency metadata

#### Scenario: Legacy generated manifest lacks logical ID
- **WHEN** an existing repository has managed-item rules or tests that rely on logical IDs but its generated manifest omitted them
- **THEN** migration SHALL backfill logical IDs from read-only DEV discovery or fail with an unresolved mapping; generation SHALL NOT silently remove the legacy validation capability

#### Scenario: Equivalent mechanism is proposed
- **WHEN** an implementation proposes replacing `logical_id`
- **THEN** migration and validation SHALL identify the consuming checks, prove equivalent direct/logical/endpoint binding resolution, provide a transition that supports both forms, and prohibit legacy-check removal until consumer validation passes

### Requirement: Regeneration preserves supported environment behavior
Applying a profile-aware setup SHALL generate a compatibility inventory of existing managed and consumer-specific CI/CD assets before replacement. It SHALL add, update or remove generated files only where the approved profile set proves equivalent or intentionally migrated behavior. A setup SHALL fail before overwrite when a profile has an unresolved workspace or binding, invalid promotion source, missing Key Vault-backed credential source, unsupported custom setup, unapproved target change, or incompatible existing generated asset. The failure SHALL identify the profile, field or asset and the required remediation.

#### Scenario: New setup omits an existing supported route
- **WHEN** regeneration would remove a previously supported profile, pipeline, contract file or manual-verification asset not marked as intentionally retired in the approved migration
- **THEN** setup SHALL fail before replacing the asset

#### Scenario: Existing four-profile generated assets are upgraded
- **WHEN** an existing repository uses the current DEV, TEST, PROD and HOTFIX generated files
- **THEN** migration SHALL preserve their routing and artifact behavior through explicit legacy-compatible profile records and a versioned generated-schema transition

#### Scenario: Effective pipeline setup is incompatible
- **WHEN** the reviewed pipeline setup, protected resource binding, target mapping or verification requirement cannot be represented by the canonical profile
- **THEN** apply SHALL stop without overwriting active assets and identify the incompatible effective behavior

### Requirement: Backward compatibility is versioned and explicit
The capability SHALL continue to accept the current four-environment setup for a migration window by translating it to explicit DEV, TEST, PROD and HOTFIX canonical profiles. PROD defaults SHALL preserve the existing TEST and HOTFIX promotion sources only in the translated legacy profile set; a newly authored or edited profile set SHALL retain no implicit PROD eligibility. The migration record SHALL document source schema version, generated schema version, profile translation, changed files, retained custom assets, validation evidence and rollback commit or package version. The previous skill remains usable without automatically mutating consumer repositories.

#### Scenario: Legacy setup is migrated
- **WHEN** plan reads a current four-environment setup with no profile list
- **THEN** it SHALL deterministically translate the setup into four explicit profiles and render the migration for approval without changing behavior

#### Scenario: New profile set omits PROD sources
- **WHEN** a developer authors a profile-based PROD definition without promotion sources
- **THEN** validation SHALL pass only when the profile declares `deploy.enabled: false` or SHALL fail if deployment is enabled, and SHALL NOT add TEST or HOTFIX implicitly

### Requirement: Profile-aware offline regression matrix
The skill's offline suite SHALL cover the legacy DEV/TEST/PROD/HOTFIX profile set, a generated TEST2 profile, an imported/generated UAT profile, ad hoc target realization, missing or invalid profile fields, unsupported or ambiguous branch routing, unsupported PROD promotion sources, digest and upstream-evidence mismatch, Key Vault access and secret-fallback rejection, generated artifact and deployment validation, and managed-item logical-ID compatibility. The tests SHALL run without Fabric, Azure DevOps or secret values and SHALL assert that each failure stops before a protected write.

#### Scenario: Profile matrix passes
- **WHEN** the offline suite runs against legacy, TEST2 and imported/generated UAT fixtures
- **THEN** each generated configuration, pipeline, artifact and runner validation case SHALL pass deterministically without network credentials

#### Scenario: A safety regression is introduced
- **WHEN** a branch route, promotion source, digest, evidence, Key Vault fallback or binding metadata regression is introduced
- **THEN** the corresponding offline negative test SHALL fail and identify the violated profile contract
