# DevOps

Team devops package for branch hygiene and Azure DevOps policy workflows.

## What it does

Activated when a user needs to start development on a safe branch or apply standard Azure DevOps branch policies to a repository.

|  |  |
|--|--|
| Branch guardrails | "Check my current branch before I start coding" |
| Azure DevOps policies | "Apply the standard branch policy to dev and main" |

## Agent

### `devops`

Activated for branch hygiene and Azure DevOps policy tasks. Uses the `git-branch-guard` and `azure-devops-standard-branch-policy` skills to validate branch names, enforce repository policy standards, and guide safe team workflows.

## Skills

### `git-branch-guard`

Validates that development starts on a `drv/` branch with a Jira key and avoids protected branches.

### `azure-devops-standard-branch-policy`

Applies the team standard Azure DevOps policy settings for non-production and protected branches.
