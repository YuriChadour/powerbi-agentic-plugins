## 1. Workflow contract and planning-state model

- [ ] 1.1 Update the Jira workflow skill to define the planning-gate states, required inputs, OpenSpec/architect routing, and explicit implementation handoff; verify the documented flow matches every requirement scenario in the delta spec.
- [ ] 1.2 Add resumable change discovery and duplicate-prevention guidance for Jira-linked OpenSpec planning; verify an existing matching change is surfaced before `openspec new change` is invoked.
- [ ] 1.3 Document that Jira assignment, In Progress transition, and branch validation do not authorize implementation; verify the workflow stops before implementation when planning is incomplete.

## 2. Agent orchestration

- [ ] 2.1 Update the DevOps agent orchestration to invoke the planning gate after Jira/branch setup and before implementation handoff; verify the agent reports the gate state and planning location.
- [ ] 2.2 Add the explicit post-planning implementation handoff and preserve the existing Jira and branch workflow; verify planning completion does not automatically invoke the apply or implementation workflow.

## 3. Validation

- [ ] 3.1 Add or update workflow fixtures/tests for OpenSpec-required, architect-required, existing-change, incomplete-planning, and completed-planning paths; verify all scenarios pass.
- [ ] 3.2 Run OpenSpec validation and repository-local documentation/agent checks; verify `openspec validate --change jira-workflow-architecture-gate --strict` and relevant checks succeed.
