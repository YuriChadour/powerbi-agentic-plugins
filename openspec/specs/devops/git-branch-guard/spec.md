# Git Branch Guard Specification

## Purpose

Ensure branch validation accommodates explicitly scoped Fabric data-engineering development while preserving existing branch protections for all other work.

## Requirements

### Requirement: Resolve scope before branch handling

Before invoking branch validation or selecting a branch-creation route, the system SHALL ask the user to select the work area first and then the independent work type: bug, feature, or story. The system SHALL determine whether the work is explicitly and exclusively Fabric data engineering. A broad Fabric category alone SHALL NOT establish this scope. Unknown, unresolved, or mixed scope SHALL NOT qualify for the DEV exception. Jira intake and applicable ticket traceability SHALL remain independent of the branch name.

#### Scenario: User selects a Fabric data-engineering bug

- **WHEN** the user selects Fabric data engineering as the work area and bug as the work type, and the scope is exclusive
- **THEN** the system SHALL use the same DEV-branch guard route as an eligible feature or story

#### Scenario: An intake selection is unresolved

- **WHEN** the user declines, cancels, or leaves work area or work type unresolved
- **THEN** the system SHALL stop before branch creation, validation, planning, or implementation and report that routing is unresolved

#### Scenario: Explicit Fabric data-engineering work

- **WHEN** the work is identified as Fabric data engineering only
- **THEN** the system SHALL pass that scope and the adopter's configured DEV branch to branch validation

#### Scenario: Mixed or ambiguous work

- **WHEN** the work includes Power BI or other work, or its scope is unclear
- **THEN** the system SHALL apply the existing feature/bugfix branch rules rather than the DEV exception

### Requirement: Record the user's Jira ticket for every work area

For work in every area, the system SHALL obtain the Jira ticket key from the user and record the current ticket key in `RESUME.md` for commit traceability, independently of the branch name. If the user has not provided a ticket key, the system SHALL ask for it and SHALL NOT invent one or infer it from the branch. If Jira integration is unavailable, the system SHALL still record the user-provided ticket key. Updating the current ticket SHALL preserve unrelated existing content in the record.

#### Scenario: Fabric data engineering on a shared DEV branch

- **WHEN** the user supplies a Jira ticket for Fabric data-engineering work on the configured DEV branch
- **THEN** the system SHALL record that key in `RESUME.md` so it is available for the commit workflow

#### Scenario: Other work areas

- **WHEN** the user supplies a Jira ticket for Power BI, other, mixed, or another work area
- **THEN** the system SHALL record that key in `RESUME.md` for commit traceability

#### Scenario: Ticket is missing or Jira is unavailable

- **WHEN** a ticket key has not been supplied or Jira integration is unavailable
- **THEN** the system SHALL ask the user for the key when needed and record the supplied key without inventing one

### Requirement: Validate the DEV working branch for Fabric data engineering

The branch guard SHALL run before implementation, including Fabric development. It SHALL permit the explicitly configured DEV working branch only for Fabric data-engineering-only work, without a feature/bugfix prefix or Jira key in that branch name. The exception SHALL NOT apply to implementation of the plugin itself. If the DEV exception is requested and its configured branch is missing, invalid, or cannot be determined, the guard SHALL fail closed with an actionable diagnostic. The exception SHALL NOT authorize main, master, prod, production, or test as a DEV working branch.

#### Scenario: Configured DEV branch is current

- **WHEN** explicitly scoped Fabric data-engineering-only work is on its configured DEV branch
- **THEN** the guard SHALL pass without requiring a Jira key or feature/bugfix prefix in that branch name

#### Scenario: DEV branch does not match

- **WHEN** a DEV exception is requested but the current branch differs from the configured DEV branch
- **THEN** the guard SHALL NOT grant the exception and SHALL apply normal branch checks

#### Scenario: Protected branch is configured as DEV

- **WHEN** the configured DEV branch names main, master, prod, production, or test
- **THEN** the guard SHALL reject the configuration and stop before implementation

#### Scenario: Branch cannot be determined

- **WHEN** Git cannot identify the current branch, including detached HEAD
- **THEN** the guard SHALL fail with an actionable diagnostic

### Requirement: Preserve ordinary branch validation and reuse

For Power BI, other, mixed, and unknown work the guard SHALL reject protected and shared branches and require a `feature/` or `bugfix/` branch containing an uppercase Jira key. Existing branch-reuse behavior SHALL remain in effect whenever a working branch must be created. A missing scope or DEV configuration SHALL NOT silently authorize direct work on DEV.

#### Scenario: Power BI on DEV

- **WHEN** a Power BI task starts on DEV
- **THEN** the guard SHALL reject DEV and direct the user to a compliant feature or bugfix branch

#### Scenario: Valid ordinary branch

- **WHEN** non-exempt work starts on `feature/FIN-123-description`
- **THEN** the guard SHALL pass branch validation

#### Scenario: No explicit context

- **WHEN** an existing caller invokes the guard without scope or DEV configuration
- **THEN** the guard SHALL retain the existing protected-branch, prefix and Jira-key checks

### Requirement: Coordinate guard callers without claiming remote enforcement

Agent and workflow entry points that invoke the guard SHALL apply the same scope and branch contract before implementation. The lifecycle SHALL report conflicts with Git permissions or Azure DevOps branch policies; passing the local guard SHALL NOT be represented as permission to bypass those controls or as path-level protection for direct commits.

#### Scenario: Existing DEV policy blocks a commit

- **WHEN** the guard passes but remote Git permissions or policies reject a direct DEV commit
- **THEN** the system SHALL report the conflict and SHALL NOT silently weaken or bypass the remote protection

### Requirement: Support equivalent behavior across agent harnesses

The skill and its handoffs SHALL support equivalent scope-first intake, ticket-type selection, branch validation, and Jira fallback behavior in Codex, GitHub Copilot, and Claude. Each harness SHALL have a supported prompt and discovery route, including a plain-text fallback where a structured selection control is unavailable. Compatibility SHALL be verified separately for each harness; unavailable harnesses SHALL be reported as unverified.

#### Scenario: A harness lacks a structured selection control

- **WHEN** a supported harness cannot display a structured multiple-choice prompt
- **THEN** the workflow SHALL present the same choices in text and wait for an explicit response without changing the route

#### Scenario: A harness cannot be tested

- **WHEN** a harness or its required integration is unavailable during verification
- **THEN** the result SHALL identify that harness and integration as unverified rather than claim cross-harness success
