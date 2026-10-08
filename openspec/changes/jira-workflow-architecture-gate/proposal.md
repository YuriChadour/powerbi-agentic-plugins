## Why

The Jira workflow currently allows implementation to begin immediately after a ticket is assigned and moved to In Progress, even when the work requires architectural discovery or an OpenSpec proposal. This can produce unreviewed implementation work and makes the planning boundary inconsistent across agents and harnesses.

## What Changes

- Add a pre-implementation planning gate to the Jira workflow for tickets that require architecture or OpenSpec work.
- Require the workflow to identify the planning artifact or architect review needed before implementation begins.
- Make the gate state explicit so implementation can continue only after the required planning work is complete or the user explicitly directs an approved exception.
- Preserve the existing Jira assignment, status-transition, and branch-guard behavior.

## Capabilities

### New Capabilities

- `devops/jira-workflow-architecture-gate`: Defines how Jira-start workflows detect and enforce completion of required architecture or OpenSpec planning before implementation.

### Modified Capabilities

- None.

## Impact

- Affected workflow documentation and agent orchestration under `plugins/devops/`.
- OpenSpec planning artifacts and any future architecture-review handoff used by the DevOps workflow.
- No Jira API contract changes; the existing Jira MCP operations remain unchanged.
