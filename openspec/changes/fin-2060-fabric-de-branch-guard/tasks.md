## 1. Guard contract and validation

- [x] 1.1 Implement explicit exclusive Fabric data-engineering scope and configured DEV branch inputs in `check_git_branch_guard.ps1`; verify the exact configured DEV branch passes only for eligible scope and invalid DEV configuration fails closed.
- [x] 1.2 Preserve no-argument behavior and protected branch checks; verify feature/bugfix prefixes and uppercase Jira keys remain required for Power BI, other, mixed and unknown scope.
- [x] 1.3 Verify configured main/master/prod/production/test, mismatched branches, detached HEAD and Git errors cannot grant the exception; verify plugin implementation is not exempt.
- [x] 1.4 Update `git-branch-guard/SKILL.md` triggers and examples to require the guard while documenting explicit scope, DEV configuration, branch validation and independent Jira tracking; review examples against script behavior.

## 2. Agent and workflow routing

- [x] 2.1 Update `plugins/devops/agents/devops.agent.md` and `devops.toml` plus Jira intake so the user selects work area first, then bug/feature/story, before branch lookup or guard invocation; verify both definitions agree and the existing report subtype and planning gates remain.
- [x] 2.2 Update Jira and troubleshooting workflow guard handoffs and all other discovered callers to forward scope and DEV branch correctly; verify broad Fabric categories, unknown and mixed scope cannot automatically grant the exception.
- [ ] 2.3 Preserve local/remote branch reuse and confirmation for feature/bugfix flows and preserve applicable Jira traceability for DEV work; verify both routes using representative ticket scenarios.
- [ ] 2.3a Require a user-provided Jira ticket for every work area, preserve unrelated content while recording the current key in `RESUME.md`, and make it available for commit traceability, including when Jira integration is unavailable; verify missing-ticket and multiple-work-area scenarios.
- [ ] 2.4 Integrate the related `fin-2060-fabric-cicd-lifecycle` route using this guard contract; verify no duplicate guard implementation or unintended changes to Power BI release behavior.

## 3. Verification and documentation

- [x] 3.1 Add executable isolated Git/PowerShell coverage for DEV eligibility, alternate DEV names, absent or invalid configuration, protected branches, normal valid and invalid branches, no arguments, and detached HEAD; run the focused tests.
- [ ] 3.2 Independently exercise Codex, GitHub Copilot, and Claude discovery and workflow entry points with Fabric DE bug and story, Power BI, other, mixed and unresolved scope; verify selection order, text-prompt fallback, guard routing and Jira fallback. Record evidence for each harness or mark it unverified if unavailable.
- [ ] 3.3 Document configuration and the separate Git/Azure DevOps policy boundary; verify conflicting remote protections are reported without automatic bypass or policy changes.
- [ ] 3.4 Validate both related OpenSpec changes and check implementation ownership and references for consistency; record results.
- [ ] 3.5 Apply skill-creator guidance to guard and Jira skill changes: review trigger descriptions, input/output and handoff contracts, and evaluate representative prompts and failure cases; record results and unresolved harness limitations.
