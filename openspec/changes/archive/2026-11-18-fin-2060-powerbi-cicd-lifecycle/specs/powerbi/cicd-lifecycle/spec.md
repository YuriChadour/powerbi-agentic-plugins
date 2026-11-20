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
REHEARSAL target profiles and a built-in HOTFIX validation profile. It SHALL
replace the Fabric source-folder and
managed-item values with an explicit Power BI source-folder, supported-item,
dependency, model/report, and RDL-binding mapping.

The setup entry point SHALL use the invoking developer's authenticated `fab`
and `az` sessions to plan or reconcile only the selected workspace topology,
direct role mappings, protected branch governance, and named Azure DevOps
pipelines.
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
pipeline, branch promotion path, target-specific runtime inputs, semantic-model
source-connection bindings, protection, and verification profile before
generating deployment assets or performing a write. Folder presence, workspace
discovery, or a guessed environment SHALL NOT constitute approval. Workspace,
Lakehouse/item, and connection binding IDs SHALL be per-environment keyed
entries inside the artifact or deploy-time inputs recorded as evidence; no
target-specific overlay SHALL change the artifact.

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

### Requirement: Rendered review and approval records gate setup
Before an external setup write, the lifecycle SHALL render populated,
non-secret `CICD-SETUP.md` and `CICD-VERIFICATION.md` records alongside the
configuration, manifest, and pipeline YAML. The setup record SHALL identify
the requested and resolved workspace names and IDs, source and promotion
branches, Azure DevOps repository/pipeline/environment references,
service-connection and service-principal references, direct role mappings,
supported item scope, target-specific runtime inputs, unresolved prerequisites,
and rollback route. The verification record SHALL identify required deployment,
binding, and runtime checks. Credentials, tokens, client secrets, connection
credentials, and secret values SHALL NOT be rendered. The developer SHALL
explicitly approve the reviewed non-secret contract before `Apply` creates or
changes an external resource.

#### Scenario: Rendered contract is awaiting review

- **WHEN** render or plan completes with a complete non-secret mapping
- **THEN** the generated records SHALL identify unresolved prerequisites and
  `Apply` SHALL stop before an external write until developer approval is
  recorded for the rendered contract revision

#### Scenario: Approved contract is applied

- **WHEN** the developer records approval for the reviewed contract and invokes
  `Apply`
- **THEN** setup SHALL revalidate that approved revision before reconciling
  only the mapped workspace roles, governance, and named pipelines

### Requirement: Environment bootstrap is gated and isolated

The bootstrap SHALL create or reuse only explicitly selected DEV, TEST, and
PROD workspaces, plus configured UAT or REHEARSAL workspaces, idempotently;
validate exact workspace IDs, capacity, region, owner, and isolation before
reuse; and retain non-secret readiness evidence. Every deployment target SHALL
remain Git-disconnected and SHALL receive only an immutable validated artifact
from the approved `pbi/` source boundary.
Repository, workspace, identity-and-secret, governance, and pilot validation
gates SHALL each record evidence and block the next phase on failure. A pilot
SHALL use isolated non-production targets and SHALL NOT alter enterprise
production workspaces.

#### Scenario: Git-disconnected targets are prepared

- **WHEN** the repository and workspace gates pass
- **THEN** DEV, TEST, PROD, and each configured UAT or REHEARSAL target are
  recorded as Git-disconnected protected targets, and only the pipeline may
  deploy the approved `pbi/` artifact to them

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
lock, manifest, target-specific semantic-model source-connection binding map,
connection verifier, revision identifier, and content hashes into one immutable
release artifact. Trusted deployment SHALL verify the artifact identity and
hashes before a target write, deploy semantic models before dependent reports,
bind models only to the approved target connections, and deploy paginated
reports only after their configured bindings are resolvable. No later
environment stage SHALL rebuild from a branch or check out a different
revision. The artifact SHALL include every deployment script a stage needs;
before any workspace write the stage SHALL reject a missing required script,
and a selected revision whose release files differ from the deployment
branch's.

Environment-specific substitutions (for example TMDL expression values and
notebook or report Lakehouse and model references) and semantic-model
connection bindings SHALL be per-environment keyed rules inside the artifact.
They SHALL be applied only after artifact verification and SHALL NOT be
re-hashed. Values resolved at deploy time SHALL be recorded in the release
evidence. Preflight SHALL block when a rule lacks a value for the target
environment or matches no packaged file.

#### Scenario: Artifact promotion succeeds

- **WHEN** the selected artifact has matching revision and content hashes and
  all required dependencies are ready
- **THEN** the stage deploys only the mapped Power BI items in dependency
  order to its selected workspace

#### Scenario: Artifact or dependency is invalid

- **WHEN** an artifact digest differs, a report lacks its model, a semantic
  model lacks an approved source-connection binding, or a paginated report
  lacks a configured binding
- **THEN** deployment stops before the affected workspace write and records
  the reason

### Requirement: Trusted deployments are protected and verifiable

Only trusted deployment stages SHALL resolve the approved protected runtime
identity, and they SHALL perform an authenticated read-only preflight before
writing. `dev` SHALL be an unprotected integration branch that permits direct
commits for any workload; a validated push to `dev` SHALL package one artifact
and deploy DEV. `test` and `main` SHALL accept changes only through pull
requests with one required reviewer and required validation; `test` SHALL
complete by merge commit and `main` SHALL permit merge commit or squash (branch
policy cannot vary by source branch); direct pushes SHALL be rejected by branch
policy. TEST SHALL deploy
only the artifact recorded for the `dev` revision promoted by its reviewed,
validated `dev`-to-`test` pull request; PROD SHALL deploy that same artifact
only after its reviewed, validated `test`-to-`main` pull request merges. TEST
and PROD SHALL locate that artifact from the promoted commit's revision
lineage (the merge-base with `dev`) or, for a hotfix, from the completed
pull-request metadata (second parent as fallback), and SHALL block when no
successful build exists for that revision. A squashed `test`-to-`main` pull
request has no resolvable `dev` build and SHALL block. PR review
and required validation are the manual release approvals; deployment stages
SHALL NOT require environment approval checks.
For every configured semantic-model source connection, preflight SHALL verify
the selected target connection identifier and direct deployment-identity access
before publication; it SHALL reject a missing, unexpected, or personal-cloud
connection and SHALL NOT require elevated connection-sharing access.
When the target workspace already contains a managed semantic model not owned
by the deployment identity, the deployment SHALL transfer ownership to that
identity before configuring bindings and SHALL fail the stage before binding or
a successful audit record if the transfer fails; a new model or one already
owned by the deployment identity SHALL skip the transfer.
Each configured UAT or REHEARSAL profile SHALL have an explicit target guard,
pipeline, promotion-eligibility policy, and verification profile; it SHALL NOT
use a deployment environment approval check. Concurrent deployments to the
same target SHALL be serialized. Each completed, failed, or partial deployment
SHALL retain non-secret evidence of the artifact, target, managed items,
identity reference, PR/validation evidence, timestamps, and verification
result. TEST verification and the matching artifact digest SHALL be required
before PROD writes; UAT or REHEARSAL evidence SHALL NOT replace that TEST
gate. HOTFIX verification of the same artifact SHALL satisfy that gate only for
a `hotfix/*` release.

#### Scenario: DEV deployment is authorized

- **WHEN** a revision is pushed to `dev` and passes required validation
- **THEN** the revision may package one artifact and deploy only to DEV after
  automated preflight and target guards, without an environment approval check

#### Scenario: TEST deployment is authorized

- **WHEN** a reviewed `dev`-to-`test` pull request passes required validation
  and merges to protected `test`
- **THEN** TEST may deploy only the recorded immutable DEV artifact after its
  automated preflight and target guards, without an environment approval check

#### Scenario: Unreviewed source is presented for TEST

- **WHEN** a direct push to `test` or `main` is attempted, or a TEST run has no
  successful `dev` build for its resolved revision
- **THEN** branch policy rejects the push or TEST deployment is blocked before
  any workspace write

#### Scenario: TEST-ready release is promoted

- **WHEN** the TEST deployment verifies the exact artifact and a reviewed,
  validated `test`-to-`main` pull request merges to protected `main`
- **THEN** PROD consumes that same artifact under the protected target guard,
  without an environment approval check, and records its verification evidence

#### Scenario: Protected prerequisite fails

- **WHEN** the identity, target guard, approval, TEST verification, or
  artifact digest is absent, invalid, or mismatched
- **THEN** the affected deployment remains blocked and no target workspace
  item is changed

#### Scenario: UAT or Rehearsal deployment is requested

- **WHEN** a configured UAT or REHEARSAL pipeline receives a validated
  immutable artifact and satisfies its target guard and promotion-eligibility
  policy
- **THEN** it deploys only to its mapped workspace, retains verification
  evidence, and does not authorize a PROD deployment by itself

#### Scenario: Existing model is owned by another principal

- **WHEN** the target workspace contains the managed semantic model and its
  owner is not the deployment identity
- **THEN** ownership is transferred before bindings are configured, or the
  stage fails before a successful audit record is written

#### Scenario: Model ownership is already correct

- **WHEN** the model is new or already owned by the deployment identity
- **THEN** the takeover is skipped and binding and verification continue

#### Scenario: Required deployment script is missing

- **WHEN** the selected artifact lacks a required deployment script, or its
  release files differ from the deployment branch
- **THEN** the stage fails before any workspace write

### Requirement: Hotfixes use an isolated validation route

A production defect SHALL be released from a `hotfix/<Jira-key>` branch that
starts from the current protected `main` revision; its fix MAY be authored on
`dev` and delivered by cherry-pick. The lifecycle SHALL package
the hotfix once, validate that artifact in an isolated HOTFIX workspace that
uses the PROD mapping and never writes PROD, and deploy PROD only after a
reviewed, validated pull request merges the hotfix into `main`; PROD SHALL
consume the same artifact, located from the completed pull-request metadata
(so a squash merge resolves) and requiring a successful HOTFIX validation. The resolved fix
SHALL be forward-ported through reviewed pull requests to `test` and `dev`.

#### Scenario: Hotfix is released

- **WHEN** a `hotfix/<Jira-key>` artifact passes HOTFIX verification and its
  pull request merges into `main`
- **THEN** PROD deploys that artifact without rebuilding and the forward-port
  pull requests to `test` and `dev` are recorded as open follow-ups

#### Scenario: Hotfix merge has no validated build

- **WHEN** a pull request into `main` carries a hotfix commit with no
  successful HOTFIX-verified build
- **THEN** PROD deployment is blocked before any workspace write

#### Scenario: Squash-merged hotfix is promoted

- **WHEN** a validated `hotfix/<Jira-key>` pull request is squash-merged to
  `main`
- **THEN** PROD resolves the HOTFIX release from the completed pull-request
  metadata and does not fall back to an unrelated `dev` artifact

### Requirement: Live state is verified, drift-aware, and recoverable

Post-deployment verification SHALL confirm the selected item scope, intended
semantic-model/report bindings, configured environment substitutions, model
readiness, and applicable paginated-report data-source bindings. For each
external paginated-report source, preflight SHALL require an approved
environment connection, gateway/data-source binding, and deployment-identity
access; verification SHALL confirm the resulting report binding. The
post-deployment verifier SHALL compare every managed semantic model's live
source connections with the immutable artifact's selected target binding map.
Any mismatch SHALL fail the stage and prevent a successful deployment audit
record. The
lifecycle SHALL detect unexpected managed-item metadata or binding drift and
block later promotion pending documented reconciliation. Rollback SHALL use
the normal protected path to redeploy a retained known-good artifact and
SHALL NOT delete unrelated workspace items.

#### Scenario: Managed target is healthy

- **WHEN** deployment and post-deployment checks pass
- **THEN** the release record identifies the verified target state, including
  applicable semantic-model and external paginated-report bindings, and
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
