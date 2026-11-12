# FIN-2060 branch guard verification

## Related changes and ownership

On 2026-11-09, `openspec validate <change> --strict` passed for both
`fin-2060-fabric-de-branch-guard` and `fin-2060-fabric-cicd-lifecycle`.
The branch-guard change owns intake and `check_git_branch_guard.ps1`; the
lifecycle change consumes that contract. Its current skill hands off ticket,
work area and work type, and calls the existing guard with the configured DEV
branch for eligible adopter work. Its release automation remains incomplete.
The lifecycle's Power BI mapping remains optional and separately scoped.

The isolated PowerShell/Git branch guard suite passed on 2026-11-09 after
correcting its expected Git-error case to capture the process exit code under
Windows PowerShell. It covers configured DEV, ordinary and protected branches,
invalid configuration, detached HEAD, Git errors and the plugin exclusion.

The Jira record helper's four isolated unit tests pass with `py -3 -m unittest
discover -s plugins/devops/skills/jira-workflow/tests -v`. They cover missing or
invalid keys, creation, switching keys while preserving unrelated content and
line endings, repeat invocation, and ambiguous or reversed markers. The helper
is independent of work area and Jira connectivity; actual interactive fallback
remains unverified.

## Instruction review

The DevOps agent definitions describe local and remote ticket-branch lookup,
confirmation, and guard validation for normal work. Jira intake describes a
uniquely marked current ticket in `RESUME.md`, preserving unrelated content,
and the same intake when Jira is unavailable. A missing ticket or unresolved
choice stops routing. Fabric DE bugs and stories use the same eligible DEV
route; mixed, Power BI and plugin implementation use normal branch rules.
These are instruction reviews, not independent interactive harness tests.

The guard and Jira skill descriptions were reviewed against their triggers,
inputs, outputs and handoffs. Representative cases include a Fabric DE bug on
configured DEV, a Power BI story, a mixed change, a missing ticket and an
unavailable Jira integration. The documented expected routes are described
above and in the skills; actual harness execution is still required.

On 2026-11-09, a read-only Codex CLI evaluation discovered the installed
`~/.codex/skills` copies, which are older than this change and still require a
ticket branch for Fabric DEV. `copilot skill list` likewise exposed older
installed descriptions. A Copilot run with `--plugin-dir plugins/devops`
reported that this directory has no `plugin.json` or `SKILL.md`; it did not
establish discovery of the changed plugin. These results are not validation of
the new instructions. The read-only Codex scenario run did not finish; the
Claude CLI scenario run produced no result before it was stopped. Claude
discovery and all three interactive workflows remain unverified. Do not update installed copies without following the
appropriate harness installation workflow. Remote policy conflict behavior is
documented but has not been exercised against a rejecting remote.

Later on 2026-11-09, the user requested updating DevOps for Codex and Copilot.
The registered Copilot DevOps copies and Codex DevOps skills/agent were updated
from this working tree, with per-harness backups. The Codex ownership manifest
was retained because it records only Power BI. Copilot `plugin list` reports
DevOps installed and `skill list` now discovers the revised guard and Jira
descriptions. Codex's installed guard, Jira skill and agent adapter match source
hashes. The installed Jira helper's four unit tests pass independently in both
locations. This verifies the files and Copilot discovery, not interactive
workflow execution; restart Codex for a new session to discover updated skills.
