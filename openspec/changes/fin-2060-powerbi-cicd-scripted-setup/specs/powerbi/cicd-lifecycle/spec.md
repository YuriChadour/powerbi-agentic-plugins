## MODIFIED Requirements

### Requirement: Power BI bootstrap shares the CI/CD operator contract

The Power BI lifecycle SHALL provide three fixed setup scripts run in order:
`plan`, `approve`, and `apply`. The plan script SHALL use the invoking
developer's existing authenticated `fab`, Power BI, and `az` sessions to perform
only read-only discovery and SHALL write `cicd/powerbi/setup.yml` and a readable
`cicd/powerbi/SETUP.md`. Missing required values SHALL be reported as fixed
questions instead of guessed. The approve script SHALL refuse while a blocking
question or gap remains. The apply script SHALL execute a fixed idempotent step
sequence from the approved setup and stop at the first failed step with an
actionable diagnostic. The scripts SHALL use the same setup semantics as
`fabric-cicd` while retaining the Power BI-only source, item, dependency, and
binding contract.

The setup scripts SHALL NOT accept or persist credentials, use a generic REST
automation layer for setup, fall back to a service principal, or require the
developer to choose step order. Protected deployment identities SHALL remain
reserved for trusted release execution.

#### Scenario: Fabric-compatible Power BI setup is invoked

- **WHEN** an adopter runs Power BI plan with repository and minimal workspace inputs
- **THEN** the skill discovers the remaining supported values, renders only Power BI CI/CD assets, and preserves the Fabric data-engineering exclusion

#### Scenario: Plan has a missing required value

- **WHEN** plan cannot resolve a required Power BI target, identity, repository, binding, or Azure DevOps value
- **THEN** plan records a named question with an example in `setup.yml` and `SETUP.md`, performs no external write, and exits without approval-ready status

#### Scenario: Apply is re-run after correction

- **WHEN** apply stops at one failed step and the developer corrects its cause
- **THEN** completed steps are no-ops and apply resumes through the same fixed sequence

#### Scenario: Plan or setup authorization is invalid

- **WHEN** plan is selected, or the developer `fab`, Power BI, or `az` session, target, repository binding, role mapping, or required approval is unavailable
- **THEN** plan performs no writes and apply stops before the affected external write, identifying the required authorization without attempting a credential fallback

#### Scenario: Optional target is configured

- **WHEN** an adopter configures UAT or REHEARSAL with its reviewed workspace, pipeline, protected resources, artifact route, and verification mapping
- **THEN** plan renders the optional target and apply registers its Power BI pipeline only after the complete setup is approved

### Requirement: Repository and target mappings require explicit approval

The lifecycle SHALL discover candidate Power BI source roots and supported items
without changing repository, Azure DevOps, Fabric, or Power BI state. The
planned setup SHALL require an explicit reviewed mapping for the selected PBIP,
PBIR, TMDL, and RDL source boundary, every supported item, report-to-model and
RDL dependencies, semantic-model target-connection bindings, environment
substitutions, DEV, TEST, PROD, and HOTFIX workspaces, optional UAT or REHEARSAL
workspaces, target protection and verification profiles, promotion branches,
Azure DevOps resources, and runtime input references. A discovered folder,
workspace, connection, or guessed environment SHALL NOT constitute approval.

The generated managed-item manifest SHALL be the complete Power BI deployment
scope. It SHALL preserve every item in dependency order, map every managed
semantic model in every required target, provide resolvable bindings for every
report and paginated report, and record unsupported or ambiguous references as
blocking gaps. Per-environment binding values SHALL remain deploy-time inputs
inside the immutable artifact and SHALL NOT be represented as environment
overlays that change the selected artifact.

The generated manifest SHALL also preserve each approved Power BI substitution
rule without reinterpretation: rule order, `find_replace` type, relative path or
glob, exact find text, and every replacement value as a string. Setup discovery
MAY identify substitution candidates, but SHALL NOT invent, normalize, sort,
coerce, or approve a rule. Every configured content environment SHALL have a
replacement value before approval. DEV, TEST, PROD, UAT, and REHEARSAL use their
same-named content environment; the isolated HOTFIX deployment target SHALL use
the approved PROD substitutions and semantic-model bindings and SHALL NOT
require or generate a separate HOTFIX content value.

At deployment, substitution preflight SHALL verify that every selected rule has
a replacement, matches at least one packaged file, and finds its exact source
text before a workspace write. Rules SHALL execute in their approved order only
against the extracted staging payload. They SHALL NOT modify the repository
source, immutable archive, content hashes, embedded manifest, or dependency
lock. The packaged Power BI deployment adapter SHALL consume that substituted
staging payload after artifact verification; artifact verification alone SHALL
NOT constitute deployment success.

#### Scenario: Complete mapping is supplied

- **WHEN** plan discovers supported Power BI assets and the developer supplies or approves every required value
- **THEN** `setup.yml` contains every resolved value and assumed default and `SETUP.md` shows the selected source, dependency, target, binding, and pipeline scope without secret values

#### Scenario: Mapping is absent or ambiguous

- **WHEN** a source root, target workspace, report-to-model dependency, RDL data-source binding, or required target connection is missing or ambiguous
- **THEN** plan records the unresolved mapping as a blocking gap before pipeline registration, protected identity use, or workspace write

#### Scenario: A generated binding is incomplete

- **WHEN** generated mappings contain an unresolved Power BI item or connection for DEV, TEST, PROD, HOTFIX, or another configured target
- **THEN** approval is refused and apply does not proceed

#### Scenario: A substitution rule is migrated or generated

- **WHEN** setup imports or renders an approved Power BI substitution rule
- **THEN** the generated manifest preserves its order, path or glob, exact find text, and string replacement values without inferred or normalized changes

#### Scenario: HOTFIX resolves environment-specific content

- **WHEN** an approved artifact is deployed to the isolated HOTFIX target
- **THEN** substitution and semantic-model binding resolution use the approved PROD content mapping while HOTFIX retains its own workspace, identity, guard, and protected resources

#### Scenario: Substitution preflight is incomplete

- **WHEN** a selected rule lacks the applicable environment value, matches no packaged file, or its exact find text is absent
- **THEN** deployment stops before a workspace write and identifies the failed rule

#### Scenario: Substitutions are applied for deployment

- **WHEN** artifact verification and substitution preflight pass
- **THEN** rules run in approved order on only the extracted staging payload, the packaged deployment adapter deploys that payload, and the repository source and immutable artifact remain byte-identical

### Requirement: Rendered review and approval records gate setup

Before an external setup write, plan SHALL render `cicd/powerbi/setup.yml` as the
single non-secret setup contract and `cicd/powerbi/SETUP.md` as its readable
review record. The contract SHALL identify resolved and assumed values for the
repository, Power BI source and managed items, dependency and binding maps,
DEV, TEST, PROD, HOTFIX and optional target workspaces, capacity and isolation,
branch promotion route, Azure DevOps repository, pipelines, environments,
private pool, Key Vault service connection, secret reference, runtime identity,
role and connection access, unresolved prerequisites, generated files, and
rollback route. `SETUP.md` SHALL distinguish discovered values, assumed
defaults, user-supplied answers, generated bindings, and blocking gaps.

The approve script SHALL record a SHA-256 approval marker only after the setup has
no blocking questions or gaps. Apply SHALL recompute the hash and refuse every
external write if the setup differs from the approved content. Credentials,
tokens, client secrets, connection credentials, and secret values SHALL NOT be
written to either review artifact or the approval marker.

#### Scenario: Rendered contract is awaiting review

- **WHEN** plan or render completes with a complete non-secret mapping
- **THEN** `SETUP.md` identifies unresolved prerequisites and apply refuses until the developer explicitly approves the exact setup

#### Scenario: Approved contract is applied

- **WHEN** the developer approves `setup.yml` and runs apply
- **THEN** apply verifies the recorded hash and performs only the external actions represented in the review contract

#### Scenario: Setup changed after approval

- **WHEN** `setup.yml` changes after approval
- **THEN** apply stops before any external write and requires a new review and approval

#### Scenario: Approval is requested with a blocking gap

- **WHEN** `setup.yml` or `SETUP.md` contains an unresolved required value or generated binding gap
- **THEN** approval is refused and the marker is not created or changed

### Requirement: Environment bootstrap is gated and isolated

Apply SHALL create or reuse only the explicitly reviewed DEV, TEST, PROD, and
HOTFIX workspaces, plus configured UAT or REHEARSAL workspaces, in idempotent
ordered steps. It SHALL validate exact workspace ID, name, approved capacity,
region when discoverable, owner, target guard, and Git-disconnected deployment
status before reuse. HOTFIX SHALL be represented as its own isolated workspace
and runtime target even though its content-to-binding mapping follows the
approved PROD mapping. Apply SHALL reconcile only approved direct workspace and
connection roles, protected Azure DevOps resources, and named pipelines; it
SHALL NOT deploy Power BI assets or run a workload.

Repository, generated-file, workspace, identity-and-secret, Power BI connection,
governance, and pipeline-registration gates SHALL retain non-secret readiness
evidence and block the next affected step on failure. The setup SHALL never
read or write secret values. Missing workspace or pipeline invocation
permissions, mismatched protected identities, unauthorized Key Vault service
connections, and unavailable target connections SHALL identify the resource
and corrective action.

#### Scenario: Git-disconnected targets are prepared

- **WHEN** the repository and workspace gates pass
- **THEN** DEV, TEST, PROD, HOTFIX, and each configured optional target are recorded as Git-disconnected protected targets and receive only an approved immutable `pbi/` artifact through the release pipeline

#### Scenario: Empty HOTFIX workspace is prepared

- **WHEN** the approved HOTFIX workspace contains no managed Power BI items
- **THEN** apply prepares only its workspace, access, and release registration and does not run a workload or deploy an item

#### Scenario: A target connection is unreadable or inaccessible

- **WHEN** plan or apply cannot confirm a required Power BI target connection for the protected identity
- **THEN** the affected step blocks with the connection and required access named, without reading or changing connection credentials

#### Scenario: A bootstrap gate fails

- **WHEN** repository, workspace, identity, connection, governance, or pipeline-registration validation fails
- **THEN** setup records non-secret evidence and stops before the next affected external step or artifact deployment

## ADDED Requirements

### Requirement: Legacy setup inputs migrate without silent reinterpretation

The scripted setup SHALL accept the prior Power BI bootstrap configuration and
manifest as migration inputs when they can be read and validated locally. It
SHALL populate `setup.yml` with their explicitly declared values, flag values
that could not be independently resolved, and require normal review and
approval. Invalid, conflicting, secret-bearing, or ambiguous legacy values
SHALL be reported as blocking gaps rather than silently translated or dropped.
Existing generated release files SHALL remain untouched until the migrated
setup is applied.

#### Scenario: Valid legacy files are migrated

- **WHEN** an adopter has valid legacy bootstrap JSON and Power BI manifest files
- **THEN** plan imports their explicit non-secret values into `setup.yml`, renders the resulting review contract, and performs no external write

#### Scenario: Legacy input conflicts with discovery

- **WHEN** a legacy workspace, identity, branch, pipeline, or binding differs from a value resolved by read-only discovery
- **THEN** plan reports the conflict as a blocking gap and requires the developer to choose or correct the value
