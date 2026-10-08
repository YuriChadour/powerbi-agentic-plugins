## Purpose

This capability ensures Jira-driven development begins with an explicit architecture or OpenSpec planning outcome, so implementation is traceable to reviewed intent and does not start from an unrefined ticket alone.

## ADDED Requirements

### Requirement: Jira work SHALL pass a planning gate before implementation

When a Jira ticket is started for development, the workflow MUST identify whether architecture or OpenSpec planning is required. If planning is required, the workflow MUST prevent implementation actions until the required planning artifact or architect decision is complete.

#### Scenario: Ticket requires OpenSpec planning

- **WHEN** a started Jira ticket requests an OpenSpec proposal or describes a cross-cutting workflow change
- **THEN** the workflow creates or resumes the corresponding OpenSpec change and reports that implementation is gated until the required artifacts are complete

#### Scenario: Ticket requires architect review

- **WHEN** a started Jira ticket has unresolved architectural scope or a change spanning multiple agents, services, or integrations
- **THEN** the workflow records an architect-review requirement and prevents implementation until the review outcome is available

#### Scenario: Planning is complete

- **WHEN** the required OpenSpec artifacts are complete or the architect review has an approved outcome
- **THEN** the workflow marks the planning gate satisfied and allows the implementation workflow to be started explicitly

### Requirement: The planning gate SHALL be visible and resumable

The workflow MUST report the gate state, the required planning action, and the artifact or review location. A later invocation MUST be able to resume an existing planning effort instead of silently creating a duplicate.

#### Scenario: Existing planning change is found

- **WHEN** a Jira ticket already has a matching local OpenSpec change
- **THEN** the workflow reports the existing change and resumes or asks the user to select it before implementation proceeds

#### Scenario: Planning is incomplete

- **WHEN** required planning artifacts are missing or not approved
- **THEN** the workflow reports the missing planning work and stops before code, configuration, or documentation implementation changes

### Requirement: Jira status and branch setup SHALL not imply implementation authorization

Assignment, transition to In Progress, and creation of a valid ticket branch MUST remain separate from satisfying the planning gate. Those actions MUST NOT be treated as approval to modify implementation files.

#### Scenario: Ticket is In Progress but planning is incomplete

- **WHEN** Jira reports In Progress and the ticket branch is valid but planning is incomplete
- **THEN** the workflow allows planning artifacts only and refuses implementation actions

#### Scenario: User explicitly starts implementation after planning

- **WHEN** the planning gate is satisfied and the user explicitly requests implementation
- **THEN** the workflow may hand off to the implementation workflow using the completed planning artifacts as context
