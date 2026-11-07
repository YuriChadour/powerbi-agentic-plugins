---
name: git-branch-guard
description: Validate the Git branch before implementation, including Fabric development; allow the configured DEV branch only for explicit exclusive Fabric data engineering and require Jira-keyed feature/bugfix branches otherwise.
---

# Git Branch Guard (Windows)

## Purpose and inputs

Run the guard before implementation, including Fabric development. Before branch
lookup or validation, obtain the user's work area and then independent work type
(bug, feature, or story). Clarify broad Fabric scope; if either selection is
unresolved, stop. Use plain-text choices if the harness has no selection control.
Do not infer exclusive scope from a ticket, path, or branch name.

For explicit **exclusive** Fabric data engineering in an adopter repository,
pass `-Scope fabric-data-engineering-only` and the adopter's explicitly
configured `-DevBranch` (the exact local branch name). Missing, malformed or
prohibited configuration fails closed. The plugin implementation repository is
not eligible. A different current branch receives normal checks. Jira intake
and ticket traceability remain independent of the DEV branch name.

For Power BI, other, mixed, or unknown scope, run with the corresponding
`-Scope power-bi`, `other`, `mixed`, or `unknown`, or omit arguments. Normal
validation requires `feature/` or `bugfix/` and an uppercase Jira key; it
rejects main, master, prod, production, dev, develop and test. When a working
branch is needed, preserve the DevOps agent's local/remote branch reuse and
user confirmation flow. Always validate after switching or creating a branch.

## Invocation and result

From the target Git repository, use the installed script's actual path:

```powershell
powershell -ExecutionPolicy Bypass -File <skill-path>/check_git_branch_guard.ps1
powershell -ExecutionPolicy Bypass -File <skill-path>/check_git_branch_guard.ps1 -Scope fabric-data-engineering-only -DevBranch dev
```

Exit code 0 permits implementation on the current branch; a nonzero exit
stops it. Detached HEAD, Git errors, invalid DEV configuration and prohibited
DEV names (`main`, `master`, `prod`, `production`, `test`) fail. Exact branch
matching is case-sensitive. A valid normal example is
`feature/FIN-123-description`; `feature/fin-123-description` is invalid.

The guard validates locally; Git permissions and Azure DevOps policies remain
independent. Report a rejected commit or policy conflict and do not bypass or
change remote protections automatically. It does not create branches or talk to
Jira. Invoke `jira-workflow` for applicable ticket intake and tracking.
## Note: assets/pbip-pr-summary/

This folder holds a standalone PBIP/PBIR change-summary tool (not part of
branch validation). It lives here only because skills are the unit that
gets distributed on install — a top-level repo `assets/` folder is not
scanned by the skill-loading mechanism, so tooling has to live inside a
skill's own folder to travel with it.

The tool is consumed in two ways:

1. **Automatic workflow** (jira-workflow Step 4.3.2): After a commit, when
   the user approves posting a summary comment to Jira, the tool generates
   a deterministic PBIP change summary.
   
2. **Explicit trigger** (devops agent Step 4): When the user requests
   "generate commit summary" or "generate PR summary" (case-insensitive),
   the devops agent routes to `.github/prompts/pbip-commit-or-pr-message.prompt.md`,
   which invokes this tool to synthesize a Jira-prefixed commit message
   or PR description. The user must explicitly request the generation
   or explicitly approve posting — no auto-posting in this mode.

See `plugins/devops/skills/jira-workflow/SKILL.md` for the automatic flow
and `devops.agent.md` Step 4 for the explicit trigger.

## Note: assets/azure-devops-cli-setup.md

One-time, per-machine setup steps for the Azure CLI (`az`) + `azure-devops`
extension that PR-creation tooling in this skill depends on (extension
install, `az login`, `az devops configure --defaults organization=...`).
It lives here — not in a top-level repo `plans/` folder — for the same
distribution reason as `assets/pbip-pr-summary/` above: only files inside a
skill's own folder travel with the plugin when installed elsewhere. The
accompanying `assets/setup_azure_cli.ps1` automates it end to end.

## Dependency: Azure DevOps CLI

PR creation (`assets/create_pr.ps1`) requires the Azure DevOps CLI to be
installed and ready:
- The `az` CLI itself, plus the `azure-devops` extension (`az extension add
  --name azure-devops`).
- An authenticated session (`az login`).
- Default `organization`/`project` configured (`az devops configure
  --defaults organization=... project=...`), or the equivalent `-Org`/
  `-Project` values passed explicitly to `create_pr.ps1`.

This is a one-time, per-machine setup — see
`assets/azure-devops-cli-setup.md` for the manual steps and
`assets/setup_azure_cli.ps1` for an idempotent script that automates all of
them. Branch validation (`check_git_branch_guard.ps1`) does not
depend on the Azure DevOps CLI; only PR creation does.
