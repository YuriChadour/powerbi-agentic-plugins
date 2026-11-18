## MODIFIED Requirements

### Requirement: Rendered review and approval records gate setup
Given the DEV, TEST, PROD and HOTFIX workspace names or IDs, the deployment service principal and the Azure DevOps variable group for each environment, the capability SHALL generate a setup file and a readable `SETUP.md` before any external write. The setup file SHALL contain every resolved value and every assumed default the later steps use: workspace and capacity IDs, source folder, promotion branches, managed items, Lakehouses, connections, protected identity and Azure DevOps references, role mappings and generated binding rules. `SETUP.md` SHALL state, per environment, what will be created, granted, generated and registered, and SHALL list any unresolved value as a blocking gap. Credentials, tokens, client secrets and secret values SHALL NOT be written. The developer SHALL approve the reviewed setup file; approval SHALL be bound to that file's content, and setup SHALL refuse to run if the file changed after approval.

#### Scenario: Rendered contract is awaiting review
- **WHEN** the developer supplies the DEV, TEST and PROD workspaces for a repository
- **THEN** the capability SHALL write the setup file and `SETUP.md` without any external write and SHALL list every assumed default for review

#### Scenario: Approved contract is applied
- **WHEN** the developer has approved the setup file and runs apply
- **THEN** apply SHALL confirm the file is unchanged since approval before performing only the actions listed in `SETUP.md`

#### Scenario: Setup file changed after approval
- **WHEN** the approved setup file is edited and setup is run
- **THEN** setup SHALL stop before any external write and ask for approval again

#### Scenario: Plan has a blocking gap
- **WHEN** a required value cannot be looked up
- **THEN** plan SHALL ask the user for it with a question and an example, record the answer in the setup file, and SHALL list it in `SETUP.md` as supplied by the user; approval SHALL be refused while any required value is still unanswered

### Requirement: Coordinated CLI setup with review
The capability SHALL provide three setup scripts run in order: plan, approve and apply. Apply SHALL execute a fixed sequence of idempotent steps from the approved setup file and SHALL stop at the first failing step with a message naming the cause and the fix. It SHALL use `fab` for Fabric workspace operations and `az` with the Azure DevOps extension for pipeline operations, both in the invoking developer's existing authenticated session. It SHALL NOT accept or persist tokens, use a service principal for setup, or require the developer to choose the order of steps. Protected pipeline identities are reserved for target deployment.

#### Scenario: Plan is requested
- **WHEN** the user runs the plan script
- **THEN** the capability SHALL identify what will change and any missing inputs without external writes

#### Scenario: Target or authorization is invalid
- **WHEN** the target, source, permissions or required approval are missing or inconsistent
- **THEN** the capability SHALL stop before the affected external write and report the reason

#### Scenario: Apply is re-run after a fix
- **WHEN** apply stopped at a failing step and the developer fixes the cause and re-runs apply
- **THEN** completed steps SHALL be no-ops and apply SHALL continue from the failed step

#### Scenario: Developer setup session is unavailable
- **WHEN** the invoking developer is not authenticated to `fab` or `az`, or lacks the required workspace or Azure DevOps permission
- **THEN** setup SHALL stop before the affected write and identify the required developer authorization without attempting a credential fallback

### Requirement: Reference-derived protected deployment
The capability SHALL package the selected revision and approved managed scope from the configured Fabric source folder, excluding data, schedules, secrets and Power BI source, together with the deployment scripts, generated binding rules and a pinned Python toolchain. Protected deployment SHALL run the packaged Python deployment on the hosted Linux agent through the `fabric-cicd` library, without a repository checkout, and only after safely extracting the artifact and verifying every file hash. It SHALL verify the protected identity and target workspace before writing, create only missing notebook shells through the notebook-specific API, and deploy only to the authorized target. Fabric release setup SHALL require a verified DEV Git connection and initial baseline.

#### Scenario: Isolated target is prepared
- **WHEN** an approved UAT or rehearsal setup is applied
- **THEN** the capability SHALL create or reuse only the selected workspace and managed resources, queue deployment only when requested, and preserve DEV, TEST and PROD mappings

#### Scenario: Deployment runs on a hosted agent
- **WHEN** a protected deployment job starts on the hosted Linux agent
- **THEN** it SHALL use only the verified artifact contents and pinned toolchain and SHALL NOT require a repository checkout or a Windows-only launcher

#### Scenario: Artifact was altered
- **WHEN** a packaged file's hash differs from the artifact's hash manifest or a member path is unsafe
- **THEN** deployment SHALL stop before running packaged code or writing to the target

#### Scenario: Protected identity does not match
- **WHEN** the runtime identity differs from the approved identity or cannot read the target workspace
- **THEN** deployment SHALL stop before any target write

### Requirement: Promote the TEST-verified artifact
Each release pipeline SHALL trigger only from its own configured promotion branch. TEST and PROD branches SHALL accept changes only through pull requests with one required reviewer, required validation and merge-commit completion; the reviewed pull request is the release approval and deployment environments SHALL NOT add an approval check. Protected PROD promotion SHALL consume the exact artifact verified in TEST, whose source digest matches the PROD branch's managed content, rather than rebuild it. Failed or missing TEST verification, a digest mismatch, or no successful TEST build for the resolved revision SHALL block promotion.

#### Scenario: PROD artifact differs
- **WHEN** the candidate PROD digest differs from the TEST-verified digest
- **THEN** promotion SHALL stop before target writes

#### Scenario: No build exists for the promoted revision
- **WHEN** a merge into the PROD branch resolves to a revision with no successful TEST build
- **THEN** deployment SHALL stop before target writes

#### Scenario: DEV merge reaches only the DEV pipeline
- **WHEN** a pull request merges into the configured DEV branch
- **THEN** no TEST or PROD release pipeline SHALL run for that merge

### Requirement: Hotfixes use cherry-pick branches
A production fix SHALL be delivered on a `hotfix/<Jira-key>` branch created from the PROD branch, carrying the fix authored on DEV as cherry-picked commits. The capability SHALL package that branch once and deploy it to a dedicated HOTFIX workspace, prepared by the same bootstrap as the other environments and resolving its bindings to its own items; the hotfix pipeline SHALL never write to TEST or PROD. After a reviewed pull request from the hotfix branch merges into the PROD branch, PROD SHALL deploy that same HOTFIX-verified artifact, located from the hotfix branch's successful build, without rebuilding. The fix SHALL then be forward-ported to the TEST and DEV branches through reviewed pull requests.

#### Scenario: Cherry-picked fix is promoted
- **WHEN** a hotfix artifact is verified in the HOTFIX workspace and its pull request merges into the PROD branch
- **THEN** PROD SHALL deploy that artifact without rebuilding and `SETUP.md`'s runbook SHALL list the forward-port pull requests to TEST and DEV

#### Scenario: Cherry-pick bypasses the hotfix branch
- **WHEN** a cherry-picked change merges into the TEST or PROD branch from a non-hotfix branch
- **THEN** deployment SHALL block rather than select an older artifact

#### Scenario: Hotfix merge has no verified build
- **WHEN** a `hotfix/*` pull request merges into the PROD branch and no successful HOTFIX deployment exists for its tip
- **THEN** PROD deployment SHALL stop before any target write

## ADDED Requirements

### Requirement: Same bootstrap for every environment
Apply SHALL prepare DEV, TEST, PROD and HOTFIX with the same steps: create or reuse the workspace on the approved capacity, reconcile the listed roles, create missing managed Lakehouses with schema support enabled, and confirm each release pipeline is authorized for its protected variable group and deployment environment. Lakehouse creation SHALL use the developer session, never the deployment identity. Bootstrap SHALL NOT run workloads.

#### Scenario: PROD workspace is empty
- **WHEN** the approved PROD workspace contains no managed Lakehouses
- **THEN** apply SHALL create them schema-enabled and SHALL NOT run any workload

#### Scenario: Pipeline is not authorized for protected resources
- **WHEN** a release pipeline is not authorized for its variable group or deployment environment
- **THEN** apply SHALL stop naming the pipeline and the missing authorization

### Requirement: Protected identity and variable groups
The setup file SHALL record, per environment, the deployment service principal (application ID and resolved object ID), the Azure DevOps variable group and the deployment environment, defaulting to one shared service principal and variable group for all three environments. Apply SHALL, without reading or writing secret values:
- grant the service principal `Contributor` on each target workspace and `User` on each listed connection;
- grant the owner of the Fabric pipeline-invocation connection `Contributor` on the TEST and PROD workspaces;
- confirm each variable group exists and defines the tenant ID, application ID and a secret-flagged client secret variable, and that its application ID variable names the recorded service principal;
- create a missing deployment environment, and authorize each release pipeline for its own variable group and environment only.
Creating the service principal, setting its secret and enabling service-principal access in the Fabric tenant SHALL remain manual prerequisites listed in `SETUP.md`. A missing variable group or secret variable SHALL stop apply with instructions to create it.

#### Scenario: Variable group lacks the secret variable
- **WHEN** the configured variable group has no secret-flagged client secret variable
- **THEN** apply SHALL stop naming the group and the missing variable and SHALL NOT create or read a secret

#### Scenario: Variable group names a different application
- **WHEN** the variable group's application ID differs from the service principal in the setup file
- **THEN** apply SHALL stop before granting any role or authorizing any pipeline

#### Scenario: Shared defaults
- **WHEN** the developer supplies one service principal and one variable group
- **THEN** the setup file SHALL apply them to DEV, TEST and PROD and `SETUP.md` SHALL show that sharing for review

### Requirement: Generated target binding rules
The plan step SHALL generate the deployment binding rules from the managed source and a read-only listing of the DEV workspace. Every workspace, Lakehouse, Lakehouse SQL endpoint, notebook, Copy Job and data pipeline identifier found in managed definitions, in both its direct and Fabric Git logical-ID forms, SHALL map to a target-resolved reference or an explicit exclusion in the setup file. An identifier that cannot be mapped SHALL be reported as a blocking gap.

#### Scenario: Notebook carries a SQL endpoint reference
- **WHEN** a managed notebook references the DEV Lakehouse SQL endpoint as its default warehouse
- **THEN** the generated rules SHALL resolve it to the target Lakehouse's SQL endpoint in every environment

#### Scenario: Unknown identifier is found
- **WHEN** a managed definition contains an identifier that matches no DEV item and no exclusion
- **THEN** `SETUP.md` SHALL list it as a blocking gap naming the file

### Requirement: Copy Jobs are managed with dependency order
The managed scope SHALL support Copy Jobs. Copy Jobs and notebooks SHALL deploy before the data pipelines that invoke them, and Copy Job destinations and pipeline Copy Job references SHALL be rewritten to target items through the generated binding rules.

#### Scenario: Pipeline invokes a Copy Job
- **WHEN** a managed data pipeline invokes a Copy Job
- **THEN** the plan SHALL require the Copy Job in the managed scope and deployment SHALL publish it before the pipeline

### Requirement: Connection readiness
The setup file SHALL list every connection referenced by managed items as a non-secret binding. Apply SHALL confirm that both the developer running the first Git update and the protected deployment identity hold the `User` role on each listed connection, matched by principal object ID. Connection credentials SHALL NOT be read or changed.

#### Scenario: Deployment identity lacks connection access
- **WHEN** the protected deployment identity is not a `User` of a listed connection
- **THEN** apply SHALL stop naming the connection and the missing role

### Requirement: FIN-2101 regressions remain covered
The skill's offline tests SHALL include one case for each failure recorded during the FIN-2101 adoption: Copy Jobs outside the managed scope, missing connection permission, committed but unregistered pipeline, deployment job without its scripts, Windows-only launcher, missing schema-enabled Lakehouse, unparameterized SQL endpoint, incomplete deployment-library test double, and TEST triggering from DEV.

#### Scenario: A recorded failure is reintroduced
- **WHEN** a change reintroduces one of the recorded FIN-2101 failure conditions
- **THEN** the corresponding offline test SHALL fail
