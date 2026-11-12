## Purpose

Provide a reusable, reference-based Fabric CI/CD bootstrap and protected release workflow.

## ADDED Requirements

### Requirement: Reference-compatible Fabric starter
The capability SHALL provide a lightweight, parameterized Fabric data-engineering starter based on the connected reference bootstrap, packaging, deployment and verification workflow. It SHALL accept the reference-style YAML managed-item mapping and SHALL require explicit adopter values for project-specific resources, Fabric source-folder scope and Azure DevOps repository binding.

#### Scenario: New adopter supplies inputs
- **WHEN** a user provides a valid source, target, managed scope and protected-resource configuration
- **THEN** the capability SHALL render a coherent starter and setup guide without embedding reference-project identifiers or secrets

### Requirement: Folder-scoped Fabric routing
The capability SHALL render and register only Fabric CI/CD assets for the configured Fabric source folder and generated CI folder. Its validation, package selection and Azure Pipeline path filters SHALL use those configured folders. A Power BI folder or files alone SHALL NOT enable, render or register a Power BI pipeline.

#### Scenario: Repository contains Fabric and Power BI folders
- **WHEN** an adopter configures a Fabric source folder and also has Power BI files without an approved Power BI bootstrap mapping
- **THEN** the capability SHALL create or register only the Fabric pipeline assets and SHALL exclude the Power BI folder from Fabric validation and packaging

### Requirement: Coordinated CLI setup with review
The capability SHALL expose a single PowerShell setup entry point with a read-only plan, coordinated authorized application, and status and recovery support. It SHALL use `fab` for selected Fabric workspace operations and `az` with the Azure DevOps extension for Fabric pipeline registration, both in the invoking developer's existing authenticated local session. It SHALL NOT accept or persist Fabric or Azure DevOps tokens, use a service principal for setup, require the operator to manually run every internal stage, or introduce a general-purpose Fabric or Azure DevOps REST client. Protected pipeline identities are reserved for TEST/PROD deployment.

#### Scenario: Plan is requested
- **WHEN** the user requests a plan
- **THEN** the capability SHALL identify changes and missing inputs without local or remote writes

#### Scenario: Target or authorization is invalid
- **WHEN** the target, source, permissions or required approval are missing or inconsistent
- **THEN** the capability SHALL stop before the affected external write and report the reason

#### Scenario: Developer setup session is unavailable
- **WHEN** the invoking developer is not authenticated to `fab` or `az`, or lacks the required workspace or Azure DevOps permission
- **THEN** setup SHALL stop before the affected write and identify the required developer authorization without attempting a credential fallback

### Requirement: Idempotent Fabric workspace roles and Azure Pipelines
The authorized setup SHALL create or reuse the explicitly selected Fabric workspace and reconcile only explicit user, group and service-principal object-ID role mappings. After rendered YAML is committed to the configured Azure Repos branch, it SHALL create a missing named Fabric YAML pipeline through `az pipelines create`. It SHALL read existing role assignments and pipeline bindings first; a conflicting workspace, role, repository, branch or YAML path SHALL stop before a write and unrelated assignments or pipelines SHALL be preserved.

#### Scenario: Fabric role mapping is applied
- **WHEN** the approved setup has an existing selected workspace and an explicit principal object ID, principal type and role
- **THEN** it SHALL use `fab` to inspect the role assignments, add only a missing mapping, and read the mapping back without exposing credentials

#### Scenario: Fabric pipeline is already registered differently
- **WHEN** a named pipeline exists but targets a different repository, branch or YAML path
- **THEN** setup SHALL report the mismatch and SHALL NOT replace or rebind that pipeline

### Requirement: Reference-derived protected deployment
The capability SHALL package the selected DEV revision and approved managed scope from the configured Fabric source folder, excluding data, schedules, secrets and Power BI source, and SHALL deploy only to the authorized target using protected credentials. Fabric release setup SHALL require a verified DEV Git connection and initial baseline.

#### Scenario: Isolated target is prepared
- **WHEN** an approved UAT or rehearsal setup is applied
- **THEN** the capability SHALL create or reuse only the selected workspace and managed resources, queue deployment only when requested, and preserve DEV, TEST and PROD mappings

### Requirement: Verification is distinct from deployment
The capability SHALL report deployment and verification separately. File checks SHALL NOT be presented as evidence of successful notebook execution; automated workload execution SHALL require explicit selection and authorization.

#### Scenario: Definitions deploy before verification
- **WHEN** deployment succeeds and developer verification has not occurred
- **THEN** the result SHALL show deployment success and verification pending with a usable manual checklist

### Requirement: Promote the TEST-verified artifact
Protected PROD promotion SHALL consume the exact artifact digest verified in TEST, after required approvals, rather than rebuild it. Failed or missing TEST verification SHALL block promotion.

#### Scenario: PROD artifact differs
- **WHEN** the candidate PROD digest differs from the TEST-verified digest
- **THEN** promotion SHALL stop before target writes

### Requirement: Independent Power BI scope
Power BI deployment SHALL be separately scoped and opt-in through a distinct future bootstrap; a Power BI folder alone SHALL NOT initiate Fabric or Power BI deployment setup.

#### Scenario: No approved Power BI mapping
- **WHEN** a repository has Power BI files but no approved Power BI mapping
- **THEN** the capability SHALL NOT generate or configure Power BI deployment

### Requirement: Evidence-based rollout
The capability SHALL distinguish offline test results, installed-skill tests and live Fabric or Azure DevOps verification. It SHALL provide installation and invocation checks for both Codex and Copilot, and SHALL report unavailable checks as unverified.

#### Scenario: Only offline tests ran
- **WHEN** no live deployment or runtime exercise has been performed
- **THEN** status SHALL NOT claim live deployment or runtime verification
