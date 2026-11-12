## Purpose

Provide a separately discoverable, Power BI-only CI/CD lifecycle for approved
PBIP/PBIR, TMDL semantic-model, and paginated-report RDL assets, from
repository discovery through protected promotion and recovery.

## ADDED Requirements

### Requirement: Power BI CI/CD is explicitly routed and isolated

The system SHALL expose a Power BI CI/CD entry point for requests to set up,
operate, validate, release, promote, or recover CI/CD for Power BI projects.
It SHALL classify the selected scope before setup or implementation. A Power
BI, mixed, other, or unresolved scope SHALL use the existing Jira-keyed
feature/bugfix branch route and SHALL NOT receive the Fabric
data-engineering-only DEV-branch exception. The Power BI lifecycle SHALL NOT
deploy Fabric data-engineering items, and the Fabric data-engineering
lifecycle SHALL NOT deploy Power BI assets merely because they are present.

#### Scenario: Power BI CI/CD request is selected

- **WHEN** a user requests CI/CD for PBIP, PBIR, semantic-model, or paginated
  report assets
- **THEN** the system selects the Power BI CI/CD lifecycle and requires the
  normal Power BI branch and PR workflow before implementation work

#### Scenario: Repository contains both workload families

- **WHEN** a repository has Power BI assets and a separately configured
  Fabric data-engineering source root
- **THEN** each lifecycle handles only its explicit source and target mapping
  and neither lifecycle packages or deploys the other workload family

### Requirement: Power BI bootstrap shares the CI/CD operator contract

The Power BI lifecycle SHALL provide a PowerShell setup entry point with the
same modes and base parameters as `fabric-cicd`: `Render`, `Plan`, `Apply`,
`Status`, `Resume`, and `Deploy`; `ConfigPath`, `ManifestPath`, `RepoRoot`,
`OutputRoot`, `Target`, `ArtifactPath`, `AllowOverwrite`, and
`AllowTargetWrite`. Its non-secret configuration SHALL retain the common
repository, Azure DevOps, DEV workspace, required TEST/PROD target, role,
pipeline, and protected-resource fields, and SHALL optionally accept UAT and
REHEARSAL target profiles. It SHALL replace the Fabric source-folder and
managed-item values with an explicit Power BI source-folder, supported-item,
dependency, model/report, and RDL-binding mapping.

The setup entry point SHALL use the invoking developer's authenticated `fab`
and `az` sessions to plan or reconcile only the selected workspace topology,
direct role mappings, DEV Git connection, and named Azure DevOps pipelines.
It SHALL NOT accept or persist credentials, fall back to a service principal,
or use a generic REST automation layer for setup. Protected identities SHALL
be reserved for trusted deployments.

#### Scenario: Fabric-compatible Power BI setup is invoked

- **WHEN** an adopter invokes the Power BI setup entry point with a valid
  configuration and mapping
- **THEN** it accepts the shared operator parameters, renders only Power BI
  CI/CD assets, and preserves the Fabric bootstrap's Power BI exclusion

#### Scenario: Plan or setup authorization is invalid

- **WHEN** plan mode is selected, or the developer `fab`/`az` session, target,
  repository binding, role mapping, or required approval is unavailable
- **THEN** plan performs no writes and apply stops before the affected external
  write with an actionable diagnostic

#### Scenario: Optional target is configured

- **WHEN** an adopter configures a UAT or REHEARSAL target with its required
  workspace, pipeline, protection, artifact, and verification mapping
- **THEN** the setup renders and registers that target's Power BI pipeline
  alongside the required TEST and PROD pipelines

### Requirement: Repository and target mappings require explicit approval

The lifecycle SHALL discover candidate Power BI source roots and existing
CI/CD assets without changing local, Azure DevOps, Fabric, or Power BI state.
It SHALL require an explicit approved, non-secret mapping of each selected
Power BI source root, supported item, dependency, required DEV/TEST/PROD or
optional UAT/REHEARSAL target workspace, target owner, capacity, environment,
pipeline, protection, and verification profile before generating deployment
assets or performing a write. Folder presence, workspace discovery, or a
guessed environment SHALL NOT constitute approval.

#### Scenario: Complete mapping is supplied

- **WHEN** an adopter supplies an approved mapping for supported Power BI
  assets and all target environments
- **THEN** the lifecycle produces a reviewable plan identifying the selected
  source scope, dependencies, target workspaces, unresolved prerequisites,
  and proposed CI/CD assets without exposing credentials

#### Scenario: Mapping is absent or ambiguous

- **WHEN** a source root, target workspace, report-to-model dependency, or
  RDL data-source binding is missing or ambiguous
- **THEN** validation fails before pipeline registration, protected identity
  use, or workspace write

### Requirement: Environment bootstrap is gated and isolated

The bootstrap SHALL create or reuse only explicitly selected DEV, TEST, and
PROD workspaces, plus configured UAT or REHEARSAL workspaces, idempotently;
validate exact workspace IDs, capacity, region, owner, and isolation before
reuse; and retain non-secret readiness evidence. It SHALL attach only the
approved Power BI source folder from the protected DEV branch to DEV. TEST,
PROD, UAT, and REHEARSAL SHALL remain Git-disconnected for the scripted
deployment path and SHALL receive only an immutable validated artifact.
Repository, workspace, identity-and-secret, governance, and pilot validation
gates SHALL each record evidence and block the next phase on failure. A pilot
SHALL use isolated non-production targets and SHALL NOT alter enterprise
production workspaces.

#### Scenario: DEV Git and protected targets are prepared

- **WHEN** the repository and workspace gates pass
- **THEN** DEV is connected only to the approved Power BI folder and branch,
  while TEST, PROD, and each configured UAT or REHEARSAL target are recorded
  as Git-disconnected protected targets

#### Scenario: A bootstrap gate fails

- **WHEN** repository, workspace, identity, governance, or pilot validation
  fails
- **THEN** the bootstrap records the non-secret failure evidence and stops
  before the next setup phase or artifact deployment

### Requirement: Source validation is offline, secretless, and fail-closed

Pull-request validation SHALL run without protected deployment variables,
Key Vault secret values, or workspace write permissions. It SHALL validate
only the approved Power BI source boundary, including PBIP/PBIR/TMDL/RDL
structure, logical identities, supported-item classification, dependency
reachability, non-secret environment configuration, and committed-secret
safety. Unsupported or duplicate items and unresolved references SHALL fail
validation rather than be converted, ignored, or deployed partially.

#### Scenario: Valid source change is reviewed

- **WHEN** a pull request changes an approved Power BI source or lifecycle
  configuration
- **THEN** validation reports the affected item scope and machine-readable
  results without authenticating to a target workspace

#### Scenario: Unsafe source change is reviewed

- **WHEN** validation finds an unsupported item, malformed project,
  unresolved reference, duplicate identity, invalid mapping, or secret
- **THEN** the pull-request check fails and no workspace is modified

### Requirement: Releases use a dependency-aware immutable artifact

After the selected revision passes validation, the lifecycle SHALL package the
exact approved Power BI source subset, non-secret configuration, dependency
lock, manifest, revision identifier, and content hashes into one immutable
release artifact. Trusted deployment SHALL verify the artifact identity and
hashes before a target write, deploy semantic models before dependent reports,
and deploy paginated reports only after their configured bindings are
resolvable. No later environment stage SHALL rebuild from a branch or check
out a different revision.

#### Scenario: Artifact promotion succeeds

- **WHEN** the selected artifact has matching revision and content hashes and
  all required dependencies are ready
- **THEN** the stage deploys only the mapped Power BI items in dependency
  order to its selected workspace

#### Scenario: Artifact or dependency is invalid

- **WHEN** an artifact digest differs, a report lacks its model, or a
  paginated report lacks a configured binding
- **THEN** deployment stops before the affected workspace write and records
  the reason

### Requirement: Trusted deployments are protected and verifiable

Only trusted deployment stages SHALL resolve the approved protected runtime
identity, and they SHALL perform an authenticated read-only preflight before
writing. TEST and PROD SHALL require their configured approval controls.
Each configured UAT or REHEARSAL profile SHALL have an explicit target guard,
pipeline, verification profile, and configured approval policy. Concurrent
deployments to the same target SHALL be serialized. Each completed, failed, or
partial deployment SHALL retain non-secret evidence of the artifact, target,
managed items, identity reference, approval, timestamps, and verification
result. TEST verification and the matching artifact digest SHALL be required
before PROD writes; UAT or REHEARSAL evidence SHALL NOT replace that TEST
gate unless a future approved requirement changes the promotion policy.

#### Scenario: TEST-ready release is promoted

- **WHEN** the TEST deployment verifies the exact artifact and the required
  PROD approval is granted
- **THEN** PROD consumes that same artifact under the protected target guard
  and records its verification evidence

#### Scenario: Protected prerequisite fails

- **WHEN** the identity, target guard, approval, TEST verification, or
  artifact digest is absent, invalid, or mismatched
- **THEN** the affected deployment remains blocked and no target workspace
  item is changed

#### Scenario: UAT or Rehearsal deployment is requested

- **WHEN** a configured UAT or REHEARSAL pipeline receives a validated
  immutable artifact and satisfies its target guard and approval policy
- **THEN** it deploys only to its mapped workspace, retains verification
  evidence, and does not authorize a PROD deployment by itself

### Requirement: Live state is verified, drift-aware, and recoverable

Post-deployment verification SHALL confirm the selected item scope, intended
semantic-model/report bindings, configured environment substitutions, model
readiness, and applicable paginated-report data-source bindings. The
lifecycle SHALL detect unexpected managed-item metadata or binding drift and
block later promotion pending documented reconciliation. Rollback SHALL use
the normal protected path to redeploy a retained known-good artifact and
SHALL NOT delete unrelated workspace items.

#### Scenario: Managed target is healthy

- **WHEN** deployment and post-deployment checks pass
- **THEN** the release record identifies the verified target state and
  retains the artifact as a rollback candidate

#### Scenario: Drift or partial failure is found

- **WHEN** verification finds unexpected drift or a deployment fails after
  one or more managed items changed
- **THEN** promotion stops, the affected items are recorded, and recovery is
  limited to an approved known-good artifact without deleting unrelated items

### Requirement: Lifecycle behavior is consistently discoverable

The Power BI CI/CD entry point and its handoffs SHALL be discoverable in the
supported Codex, Copilot, and Claude harnesses. It SHALL provide equivalent
scope-first routing, explicit mappings, and plan-before-write behavior in
each harness; an unavailable harness test SHALL be reported as unverified.

#### Scenario: Supported harness receives a Power BI CI/CD request

- **WHEN** a user asks a supported harness to set up or operate Power BI
  CI/CD
- **THEN** the harness exposes the Power BI CI/CD lifecycle rather than the
  Fabric data-engineering bootstrap
