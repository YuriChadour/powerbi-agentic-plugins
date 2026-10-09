## 1. Jira classification gate

- [ ] 1.1 Add a mandatory post-branch category prompt with exactly Bug, Report Development Story, Fabric Development, and Other; verify the workflow never selects a category solely from Jira metadata
- [ ] 1.2 Add cancellation and unresolved-routing behavior; verify a declined category prompt stops before planning or implementation
- [ ] 1.3 Add Report Development Story subtype routing for new report/dashboard, existing report change, model-only, and publish/manage; verify each subtype reaches the documented downstream owner

## 2. Route-specific planning workflows

- [ ] 2.1 Route new report/dashboard work to `powerbi-report-planning`, `powerbi-architect`, and the canonical specification handoff; verify an approved `brief.md` and architect specification are required before implementation
- [ ] 2.2 Route existing report, model-only, and report-management subtypes to their specialist workflows without forcing the new-report planning brief; verify direct specialist requests remain available
- [ ] 2.3 Add Fabric Development OpenSpec create/resume routing and explicit apply handoff; verify matching Jira-linked changes are resumed and new changes are not duplicated
- [ ] 2.4 Preserve direct routing for read-only or simple operational Fabric requests; verify those requests do not require OpenSpec unless the user asks for a durable plan

## 3. Troubleshooting and Other routing

- [ ] 3.1 Route Bug and investigative Other work through `TROUBLESHOOTING.md` read/bootstrap/resume behavior; verify existing ticket sections are updated in place
- [ ] 3.2 Add evidence and blocker handling for troubleshooting investigations; verify unresolved or unverified root causes remain explicitly unresolved
- [ ] 3.3 Add post-resolution reusable-guidance extraction to the troubleshooting workflow; verify new environment facts, diagnostic shortcuts, prevention rules, or remediation patterns are written to the shared guidance section
- [ ] 3.4 Add non-investigative Other prompting for affected surface, desired workflow, required tools, and planning-record preference; verify the agent pauses without inventing a route
- [ ] 3.5 Add the post-diagnosis fix gate (surface question, two blast-radius triggers with reference scan and user confirmation, surgical direct handoff, substantial escalation); verify no new planning record is required for surgical fixes and implementation still needs an explicit request

## 4. Planning state and implementation handoff

- [ ] 4.1 Define and expose route-specific states, handoff paths, and completion criteria; verify planning completion never automatically invokes implementation
- [ ] 4.2 Add route-specific duplicate detection for Power BI work folders, Fabric OpenSpec changes, and troubleshooting ticket sections; verify exact paths and current status are reported
- [ ] 4.3 Preserve Jira assignment, status-transition, branch-guard, Jira-comment, and independent PR-offer behavior; verify MCP payloads and transition discovery remain unchanged
- [ ] 4.4 Require local `SESSION_RESUME.md` updates after every agent-created commit, before Jira-comment or PR handling; verify commit, validation, current state, and next resume point are recorded and the file is never staged
- [ ] 4.5 Add `SESSION_RESUME.md` to `.gitignore` and untrack it with `git rm --cached` in its own commit; verify the file remains on disk and `git status` ignores later edits
- [ ] 4.6 Update `scripts/end-session.ps1` to stage only `MEMORY.md` and declared OpenSpec files, keep `-ResumePath` local-only, and not fail when nothing publishable is staged; verify with updated script tests
- [ ] 4.7 Update the `MEMORY.md` end-of-session workflow section for the local handoff; verify it matches the script behavior
- [ ] 4.8 Restructure `MEMORY.md` with a cold-start orientation and vendor-neutral wording, excluding ticket status and next steps; verify a new harness can reconstruct key project facts from it
- [ ] 4.9 Document the record-roles table and `MEMORY.md` criteria in `jira-workflow/SKILL.md` and `devops.agent.md`, and add a pointer at the top of `MEMORY.md`; verify the `/memories/repo/` pointer only references `MEMORY.md`
- [ ] 4.10 Require progress-marker updates in each route's recovery record as work completes, and extend `scripts/end-session.ps1` to stage the Power BI `specs/<JIRA>-<slug>/` folder for report work; verify script tests cover it
- [ ] 4.11 Name Fabric OpenSpec changes `<JIRA>-<slug>` and match resume lookup on the Jira key prefix; verify no duplicate change is created

## 5. Documentation and validation

- [ ] 5.1 Update `plugins/devops/skills/jira-workflow/SKILL.md`, `plugins/devops/agents/devops.agent.md`, `plugins/devops/README.md`, and `.github/prompts/jira-workflow.md`; verify the category gate and all routes are documented consistently
- [ ] 5.2 Update `plugins/devops/skills/troubleshooting-workflow/SKILL.md` with the reusable-guidance and post-resolution handoff rules; verify it remains compatible with the existing Jira and branch handoffs
- [ ] 5.3 Add or update validation fixtures for every top-level category, report subtype, Fabric OpenSpec state, troubleshooting resume/update path, Other cancellation path, `SESSION_RESUME.md` local commit handoff, and `end-session.ps1` staging behavior
- [ ] 5.4 Run `openspec validate jira-workflow-architecture-gate --strict` and repository-local documentation/agent checks; verify all revised artifacts and referenced paths are valid
