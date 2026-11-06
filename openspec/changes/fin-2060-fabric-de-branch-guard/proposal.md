## Why

The current branch guard runs for Fabric development and rejects `dev`, while the related `fin-2060-fabric-cicd-lifecycle` change selects a shared DEV workspace and branch for Fabric data engineering. The guard and its callers must support this narrow workflow without relaxing branch rules for Power BI and other work.

## What Changes

- Ask the user to select the work area first, then its ticket type (bug, feature, or story), before branch handling; allow the configured DEV working branch only for explicitly exclusive Fabric data-engineering work, including bugs.
- Keep the guard mandatory and retain feature/bugfix branches with Jira keys for Power BI, other, mixed and unknown scope; preserve other protected branches.
- Update the guard skill and script, DevOps agent routing, Jira and troubleshooting handoffs, and discovered triggers consistently for Codex, GitHub Copilot, and Claude; verify each harness separately using its supported discovery and execution path.
- Keep Jira intake and traceability independent of the DEV branch name and leave remote branch policies and workspace permissions under their existing controls.
- Coordinate with `fin-2060-fabric-cicd-lifecycle`: this change owns the reusable guard behavior, and that change consumes it for DEV authoring and TEST/PROD release.

## Capabilities

### New Capabilities

- `devops/git-branch-guard`: Scope-aware branch validation and routing for Fabric data engineering and other development.

### Modified Capabilities

- None. Existing `devops/git-branch-reuse` requirements continue to apply whenever a feature or bugfix branch is to be created.

## Impact

- `plugins/devops/skills/git-branch-guard/` instructions and PowerShell guard; DevOps agent definitions, Jira and troubleshooting workflow handoffs, relevant routing and tests.
- Adopter configuration must identify the permitted DEV branch and project scope; no tenant, workspace, or branch policy is changed by planning.
