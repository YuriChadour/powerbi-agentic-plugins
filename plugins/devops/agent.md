# DevOps Agent Instructions

## Purpose
This devops package standardizes how the team works with Azure DevOps branch policies and local Git branch hygiene on Windows.

## Mandatory pre-development check
Before making any implementation changes, always run the `git-branch-guard` skill.

The current branch must satisfy all of the following:
1. It is **not** a protected or shared branch.
2. It includes a Jira ticket key in the branch name.
3. It follows the preferred naming pattern:
   - `drv/JIRA-123-short-description`

If the branch check fails:
- Stop immediately.
- Do not modify files.
- Explain the issue clearly.
- Suggest a compliant replacement branch name.
- Provide PowerShell commands to create or switch to the correct branch.

## Standard Azure DevOps branch policy setup
Use the `azure-devops-standard-branch-policy` skill when you need to apply team policy to a repository.

The standard policy behavior is:

### For non-production branches
Branches such as `dev`, `test`, `qa`, and other non-production branches should use:
- minimum approvers = 1
- self-approval allowed
- build validation only if a build definition ID is provided

### For production branches
Branches `main`, `master`, and `prod` should use:
- minimum approvers = 1
- self-approval not allowed
- build validation only if a build definition ID is provided

## Required confirmation rule
Before applying or changing any Azure DevOps repository policy:
1. Resolve the repository ID.
2. Show the full execution plan.
3. Ask the user for explicit confirmation.
4. Only proceed if the user answers `yes`.

## Windows execution convention
All helper scripts are stored with a `.txt` extension for portability.
Run them with PowerShell using:

```powershell
powershell -ExecutionPolicy Bypass -File <script>.txt
```

## Skills included
- `git-branch-guard`
- `azure-devops-standard-branch-policy`
