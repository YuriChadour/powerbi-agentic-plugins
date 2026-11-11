## Purpose

Provide a reusable, reference-based Fabric CI/CD bootstrap and protected release workflow.

## ADDED Requirements

### Requirement: Reference-compatible starter
The capability SHALL provide a parameterized starter based on the connected reference bootstrap, packaging, deployment and verification workflow. It SHALL accept the reference-style YAML managed-item mapping and SHALL require explicit adopter values for project-specific resources and scope.

#### Scenario: New adopter supplies inputs
- **WHEN** a user provides a valid source, target, managed scope and protected-resource configuration
- **THEN** the capability SHALL render a coherent starter and setup guide without embedding reference-project identifiers or secrets

### Requirement: Coordinated setup with review
The capability SHALL expose a single setup entry point with a read-only plan, coordinated authorized application, and status and recovery support. It SHALL NOT require the operator to manually run every internal stage.

#### Scenario: Plan is requested
- **WHEN** the user requests a plan
- **THEN** the capability SHALL identify changes and missing inputs without local or remote writes

#### Scenario: Target or authorization is invalid
- **WHEN** the target, source, permissions or required approval are missing or inconsistent
- **THEN** the capability SHALL stop before the affected external write and report the reason

### Requirement: Reference-derived protected deployment
The capability SHALL package the selected DEV revision and approved managed scope, excluding data, schedules and secrets, and SHALL deploy only to the authorized target using protected credentials. Fabric release setup SHALL require a verified DEV Git connection and initial baseline.

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
Power BI deployment SHALL be separately scoped and opt-in; a Power BI folder alone SHALL NOT initiate Fabric or Power BI deployment setup.

#### Scenario: No approved Power BI mapping
- **WHEN** a repository has Power BI files but no approved Power BI mapping
- **THEN** the capability SHALL NOT generate or configure Power BI deployment

### Requirement: Evidence-based rollout
The capability SHALL distinguish offline test results, installed-skill tests and live Fabric or Azure DevOps verification. It SHALL provide installation and invocation checks for both Codex and Copilot, and SHALL report unavailable checks as unverified.

#### Scenario: Only offline tests ran
- **WHEN** no live deployment or runtime exercise has been performed
- **THEN** status SHALL NOT claim live deployment or runtime verification
