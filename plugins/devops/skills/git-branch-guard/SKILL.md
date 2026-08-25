---
name: git-branch-guard
description: Ensures development starts on a valid bugfix/ or feature/ branch that includes a Jira ticket number. Also bundles a PBIP PR change-summary tool (assets/pbip-pr-summary) that posts plain-English PR comments summarizing Power BI project changes.
---

# Git Branch Guard (Windows)

## Purpose
Validate that development starts on a separate working branch and not on a protected branch.

## Mandatory rule
This check must run before:
- code changes
- SQL / DAX changes
- Fabric development
- semantic model updates
- notebook or pipeline edits
- documentation changes tied to implementation work

## Branch requirements
A valid development branch must:
1. Not be a protected or shared branch:
   - main
   - master
   - prod
   - production
   - dev
   - develop
2. Follow the preferred pattern:
   - `bugfix/JIRA-123-short-description`
   - `feature/JIRA-123-short-description`
3. Include a Jira ticket key in uppercase format:
   - `ABC-123`

## Expected behavior
1. Detect the current Git branch.
2. Fail if the branch is protected.
3. Fail if the branch does not contain a Jira ticket.
4. Fail if the branch does not start with `bugfix/` or `feature/`.
5. Suggest a compliant replacement branch name.
6. Do not proceed to implementation until the branch check passes.

## Script to run

```powershell
powershell -ExecutionPolicy Bypass -File check_git_branch_guard.txt
```

## Example valid branches
- bugfix/BI-123-fix-allocation-bug
- feature/DATA-456-add-audit-table

## Example invalid branches
- dev
- main
- feature/test
- drv/no-ticket

## Related skill: jira-workflow

This skill only validates/creates branch names — it does not talk to Jira.
When a user starts work on a ticket (e.g. "I want to work on FIN-1740"), the
`devops` agent invokes the `jira-workflow` skill **first** to
fetch/assign/transition the ticket via the `atlassian-rovo-mcp` or
`com.atlassian/atlassian-mcp-server` MCP server (see
`plugins/devops/skills/jira-workflow/SKILL.md` Step 0), then hands this
skill the resulting `ticket_key` + `short_description` to build the branch
name. If neither MCP server is connected, `jira-workflow` falls back to
asking the user directly for ticket type + description, which are passed to
this skill unchanged.

## PBIP PR change-summary tool

`assets/pbip-pr-summary/` bundles a GitHub Actions workflow and Python
script that post a sticky, plain-English PR comment summarizing PBIP/PBIR
changes (JSON, TMDL, M) whenever a pull request touches a Power BI project.
This is unrelated to branch validation, but lives here as the shared
"PR hygiene" toolset for teams using this skill.

| File | Purpose |
|---|---|
| `pbip_change_reviewer.py` | Diffs the PR base vs. head PBIP folders and renders a human-readable markdown summary (new/deleted/modified, grouped by page/visual/table, with friendly labels for positions, colors, field roles, filters, TMDL objects, and Power Query steps). Host-agnostic; `--platform {github,azure-devops}` (default `auto`, inferred from `--repo-url`) controls how file links are built. |
| `pbip-summary.yml` | GitHub Actions workflow: checks out base + head, runs the script, and posts/updates a single sticky PR comment via `gh api` (marked with `<!-- pbip-change-summary-marker -->`). |
| `pbip-summary.azure-pipelines.yml` | Azure Pipelines equivalent: same base/head diffing, but posts the sticky comment via `post_pr_comment_ado.py` against the Azure DevOps REST API. |
| `post_pr_comment_ado.py` | Stdlib-only (`urllib`) helper that finds-or-creates a marked PR thread comment via the Azure DevOps Pull Request Threads API and PATCHes it in place on re-runs, mirroring the GitHub workflow's sticky-comment behavior. |

### GitHub

1. Copy `pbip_change_reviewer.py` to `.github/scripts/pbip_change_reviewer.py`.
2. Copy `pbip-summary.yml` to `.github/workflows/pbip-summary.yml`.
3. No secrets to configure — it only needs the default `GITHUB_TOKEN`.

### Azure DevOps

1. Copy `pbip_change_reviewer.py` and `post_pr_comment_ado.py` to `.azuredevops/scripts/` in the target repo.
2. Copy `pbip-summary.azure-pipelines.yml` in as a new PR-validation pipeline (e.g. `.azuredevops/pipelines/pbip-summary.yml`), and create/enable it as a build pipeline with a PR trigger against the branches you want covered.
3. Grant the project's **Build Service** identity "Contribute to pull requests" on the repo (Project Settings → Repositories → *repo* → Security) — without this the sticky-comment POST/PATCH calls get `403`.
4. `$(System.AccessToken)` is available by default in YAML pipelines; no extra secret needed, but classic (non-YAML) pipelines must explicitly enable "Allow scripts to access the OAuth token".
5. Azure Repos has no per-file diff anchor like GitHub's `#diff-<sha>`, so file links point at the PR's Files tab (or a `?path=` blob view when there's no open PR) instead of a precise diff hunk.

**UI-change readability:** the script detects list *reordering* (not just
add/remove) and collapses it into one line, e.g.
`Field parameter values reordered: A, B, C -> B, A, C`, instead of a wall of
per-index "changed" noise. This matters most for slicer field-parameter
order, legend/tooltip/axis field order, and other UI arrangements where the
same elements just moved — the most common source of "hard to parse" PR
summaries for UI-only changes. See `json_diff_summary` /
`_detect_list_reorder` in the script if extending this further (e.g. new
friendly labels belong in `JSON_VALUE_PATTERNS` / `PBIP_PATH_LABELS`).

