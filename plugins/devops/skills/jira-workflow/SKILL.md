---
name: jira-workflow
description: 'Use when starting work in any area or finishing Jira ticket work: capture the user-provided ticket, resolve work area then work type, hand off branch routing, and manage available Jira updates. Use a manual fallback when Jira integration is unavailable.'
---

# Jira Workflow (MCP-driven)

## Purpose

Automate the Jira side of starting and finishing ticket work, posting progress
comments, and selecting the correct downstream planning workflow, using
whatever Atlassian/Jira MCP server is connected in the current session. This
skill is written as a **strict numbered algorithm**.
Follow the steps in order, exactly as written. Do not skip steps. Do not
invent tool names. Do not guess status/transition IDs.

This skill does **not** create or validate git branches — that is the job of
the separate `git-branch-guard` skill. This skill resolves scope, work type and the user-provided ticket before handing branch routing to the caller.

## Dependencies

| Dependency | Purpose | Required When |
|---|---|---|
| `com.atlassian/atlassian-mcp-server` MCP server (primary, confirmed) | Fetch/assign/transition Jira tickets, add comments | Preferred — try first in Step 0 |
| `atlassian-rovo-mcp` MCP server (alternate name, some orgs) | Same as above | Only if the primary is not connected |
| `git` / `git-branch-guard` skill | Validates the selected branch after scope-first intake | Always before implementation |
| `git-branch-guard/assets/pbip-pr-summary/commit_diff_summary.ps1`/`.sh` | Grounded, structurally-diffed PBIP change summary for a single commit | Optional, Step 4.3.2 — only when the commit touches files under a `*.Report/` or `*.SemanticModel/` project folder |

Server availability and tool schemas vary by harness and session. Discover the
actual tools before using them; examples below do not override their schemas.
If Jira is unavailable, use the **Fallback algorithm**.

---

## Required intake before branch handling

Apply this intake when work starts, regardless of work area or Jira availability.
Obtain a ticket key directly from the user's request or ask for it; never infer
it from a branch or invent one. Require an uppercase key matching `[A-Z]+-\d+`;
if absent or unresolved, ask and stop until supplied. Record the current key in
repository-root `RESUME.md`, creating the file if absent and preserving all
unrelated content. Use the following uniquely delimited block; replace only its
contents when switching tickets, and fail with a diagnostic if markers are
ambiguous or the record cannot be written:

```markdown
<!-- jira-current-ticket:start -->
Current Jira ticket: FIN-123
<!-- jira-current-ticket:end -->
```

On Windows use `py -3 <skill-path>/scripts/record_current_ticket.py --repo
<repository-root> --ticket <user-provided-key>`; elsewhere use `python3` with
the same arguments. Run it in both the normal
and manual Jira paths and stop on a nonzero exit. Python 3 is required for this
operation; if it is unavailable, report the missing dependency and stop rather
than infer or silently omit the record.

The example is illustrative; use the user's actual key. This record is distinct
from `SESSION_RESUME.md`. When preparing a commit, use the current key from
this block; if absent or ambiguous, ask the user. Never infer it from the branch.

Then ask the work area first: **Fabric data engineering only**, **Power BI**,
**Other**, **Mixed**, or **Fabric (needs clarification)**. Ask for explicit
confirmation of exclusive Fabric data-engineering scope before granting the
exception. Broad Fabric does not qualify. Then ask the independent work type:
**bug**, **feature**, or **story**. If either selection is declined, cancelled,
or unresolved, stop before branch lookup, validation, planning or implementation.
Do not derive either answer from Jira metadata, ticket wording, paths, or branch.
Offer these choices as plain text when the harness has no structured selector.

Return `ticket_key`, selected `work_area`, `work_type`, exclusive scope, and
`short_description` (from Jira or the user's manual description) to the caller.
The caller validates the configured DEV branch only for explicit exclusive
Fabric DE in adopter projects; all other scopes use normal branch rules and
branch reuse. Pass `work_type` and `ticket_key` to the guard as `-WorkType` and
`-Ticket`, in addition to the selected scope and applicable `-DevBranch`.
If DEV configuration is missing or invalid, stop. The guard
validates but does not create branches. Never bypass remote Git permissions or
Azure DevOps policies; report any conflict.
## Step 0 — Discover Jira capabilities

Complete Required intake before branch handling even if Jira tools are missing.
Use the current harness's supported tool discovery to find Jira site discovery,
issue retrieval, user lookup, issue edit, transition listing and execution,
and comment tools. In a harness that provides `tool_search_tool`, search for
`getAccessible|atlassianUserInfo|getJiraIssue|transition|editJiraIssue|addComment`.
Use only discovered tools and their actual input schemas. If discovery or Jira
is unavailable, use the fallback algorithm; do not assume a specific MCP name.
## Step 1 — Resolve the Atlassian `cloudId` (once per session)

1. Call the site-discovery tool found in Step 0 with no arguments.
2. IF it errors, times out, or returns no site → go to the **Fallback
   algorithm** and stop.
3. The response is an array of resources; the same `id` (cloudId) commonly
   appears more than once with different `scopes` (e.g. one entry scoped to
   Confluence, another to `read:jira-work`/`write:jira-work`). Take the `id`
   value — it is the same cloudId regardless of which scoped entry you read,
   so the first entry is normally sufficient. Only ask the user which site
   to use if you see genuinely **different** `id` values (multiple distinct
   Atlassian sites).
4. Store the resolved `cloudId` value for this session. Reuse it in every
   subsequent Jira MCP call below — do not re-resolve it each time.

## Step 2 — Start-ticket trigger

**Trigger phrases** (case-insensitive match against the user's message; the
ticket key is any token matching the regex `[A-Z]+-\d+`):
- "I want to work on <KEY>"
- "let's work on <KEY>"
- "start <KEY>"
- "pick up <KEY>"
- "I'm starting <KEY>"

First complete Required intake before branch handling for all start-work requests, including when no trigger phrase or Jira tool is available. Use the user-provided `<KEY>` and do the following when Jira is available, in order.
**Parameter shapes below are confirmed from a live run — use them exactly,
do not invent alternate field names like `issue_key`, `assignee` (flat), or
`transition_id`:**

1. Call the get-issue tool with `{ cloudId, issueIdOrKey: <KEY> }`.
   - IF it errors (not found, permission denied, call fails) → tell the user
     the exact error text returned, then go to the **Fallback algorithm** and
     stop.
   - ELSE → store the issue's `fields.summary`, `fields.status.name`, and
     `fields.issuetype.name`.
2. Resolve the current user's Atlassian account id by calling the
   current-user tool (no arguments) → returns `account_id` (snake_case in
   this response).
   - IF no such tool exists, or it errors → ask the user directly: "What is
     your Atlassian account email?" Then call a user-lookup tool (found in
     Step 0) with that email to get the account id.
   - IF that also fails → tell the user: "I couldn't resolve your Atlassian
     account automatically — you'll need to assign this ticket to yourself
     manually in Jira." Continue to Step 2.4 anyway (do not treat this as a
     full MCP failure / do not go to Fallback).
3. IF an account id was resolved in Step 2.2 → call the edit-issue tool with
   `{ cloudId, issueIdOrKey: <KEY>, fields: { assignee: { accountId:
   <account_id> } } }` to assign the ticket to the current user. Note
   `assignee` is nested one level inside `fields`, and the key is
   `accountId` (camelCase) even though the lookup tool returned `account_id`.
   - IF it errors → tell the user the exact error text, but continue (do not
     stop the whole flow over an assignment failure).
4. Call the list-transitions tool with `{ cloudId, issueIdOrKey: <KEY> }`.
   - Search the returned `transitions[]` array, case-insensitively, for an
     entry whose `name` (or `to.name`) is exactly **"In Progress"**.
   - IF found → call the transition tool with `{ cloudId, issueIdOrKey:
     <KEY>, transition: { id: <the matched transitions[].id> } }`. Note the
     transition id is nested inside a `transition` object, not a flat
     `transition_id` field.
   - IF not found → tell the user, verbatim style: "No transition to 'In
     Progress' is available from the ticket's current status ('<current
     status>'). Available transitions are: <list the returned transition
     names>." Then ask the user to pick one of the listed names, or say
     "skip" to continue without transitioning. Never invent or force an
     unlisted transition id.
5. Take the issue's `summary` field (from Step 2.1) and slugify it: lowercase
   it, replace anything that is not `[a-z0-9]` with a single hyphen, collapse
   repeated hyphens, trim leading/trailing hyphens, and truncate to at most
   40 characters. This becomes `short_description`.
6. Return the intake state and description to the caller. The caller executes
   the scope-aware branch route and mandatory guard before implementation.

### Step 2.7 — Downstream planning gates

Use the user's already selected work area and independent work type; do not ask
another conflicting category question. The caller performs branch handling only
after both selections. Bug work follows troubleshooting. For Power BI report
work that is not a bug, apply the report subtype gate below. Fabric work follows
Fabric Development routing. Other investigative work follows Bug and Other
routing. Preserve all unresolved-state and explicit implementation gates.
#### Report Development Story subtype gate

For **Report Development Story**, ask the user to select exactly one subtype:

1. **New report or dashboard** → invoke `powerbi-report-planning`. Resume a
   matching `specs/<JIRA>-<slug>/` folder when present; otherwise let the
   planning skill create it. Require `brief.md` with `status: approved`, then
   hand off to `powerbi-architect` for the canonical `<Name>.spec.md`. Wait for
   an explicit implementation request before `powerbi-developer` acts.
2. **Existing report change** → route to `powerbi-report-design`,
   `powerbi-report-authoring`, or `powerbi-architect` according to the request.
   Do not force a new-report brief. A direct specialist request remains valid.
3. **Model-only work** → route to `semantic-model-authoring` (or the applicable
   model specialist). Do not require a new-report brief.
4. **Report publishing or management** → route to
   `powerbi-report-management` or the applicable Fabric resource workflow. Do
   not require a new-report brief.

If the subtype is declined or unresolved, stop before planning or
implementation and report that report routing remains unresolved.

#### Fabric Development routing

For development, architecture, migration, or cross-workload Fabric work,
derive a lowercase kebab-case slug and use the Jira-linked OpenSpec name
`<JIRA>-<slug>`. Before creating anything, search `openspec/changes/` (or
`openspec list --json`) for an existing change whose name starts with the Jira
key. Report its exact path and `openspec status --change <name> --json` state,
then resume it. Never create a duplicate and never run OpenSpec apply
automatically from this gate.

If no matching change exists, create one with `openspec new change
<JIRA>-<slug>`, report its path and status, and stop at planning. A completed
proposal, requirements/specification, design, and tasks record is a planning
handoff only. On a later explicit implementation request, hand off to
`FabricDataEngineer` or `FabricMigrationEngineer` and use
`openspec-apply-change` for the selected change.

Discovery, read-only querying, monitoring, or a simple operational Fabric
request may route directly to its applicable Fabric capability without
OpenSpec. If the user asks for a durable plan, use OpenSpec even for an
otherwise operational request.

#### Bug and Other routing

For **Bug**, invoke `troubleshooting-workflow`. For **Other**, ask whether the
request is investigative. Investigative Other follows the same troubleshooting
workflow; non-investigative Other pauses and asks the user to specify the
affected surface, desired workflow, required tools, and whether a durable
planning record is wanted. Do not invent a route.

Troubleshooting must read or bootstrap `TROUBLESHOOTING.md`, resume a matching
`## <JIRA>` section in place, and record evidence, blockers, unresolved root
causes, status, and actions. A confirmed root cause is not implementation
authorization. After resolution, extract reusable environment facts,
diagnostic shortcuts, known limitations, prevention rules, or remediation
patterns into the shared guidance section before the Jira findings handoff.

When the user chooses to fix a confirmed root cause, ask for the fix surface
(Power BI report, semantic model, Fabric, or Other) and the intended change.
Propose **substantial** when a reference scan finds dependents of a renamed or
removed object, or when the change adds a new object or structural element;
otherwise propose **surgical**. Ask when uncertain, let the user confirm or
override, and record the decision in the ticket section. A surgical fix goes
directly to the applicable specialist with the troubleshooting section as
context and no new planning record. A substantial fix resumes the existing
route for the selected surface. In either case, wait for a separate explicit
implementation request.

#### Route state and handoff contract

Always report the selected route, current state, required next planning action,
exact recovery-record path, and implementation handoff. Route recovery records
are `specs/<JIRA>-<slug>/` for new reports, `openspec/changes/<JIRA>-<slug>/`
for Fabric development, and the matching `## <JIRA>` section in
`TROUBLESHOOTING.md` for investigations and surgical fixes. Update that record's
status or task markers as work completes. Planning completion never starts
implementation automatically; a later explicit request is required.

The repository record roles are fixed: `MEMORY.md` contains only durable,
vendor-neutral facts; route records contain planned work and progress;
`TROUBLESHOOTING.md` contains investigation history and shared guidance;
`RESUME.md` records the user-provided current ticket for commit traceability;
`SESSION_RESUME.md` is a local, gitignored convenience only; Jira contains
external ticket status and comments. No workflow step may depend on
`SESSION_RESUME.md` existing.

## Step 3 — Finish-ticket trigger

**Trigger phrases** (case-insensitive):
- "I'm done with this ticket"
- "I'm finished working on this"
- "finished with <KEY>"
- "done with <KEY>"
- "ready to test <KEY>"
- "ready to test this ticket" (no key given)

When one of these matches:

1. Determine <KEY> from the user's current request or the uniquely marked current ticket in RESUME.md; if absent or ambiguous, ask the user. Never infer it from the branch.
2. Call the list-transitions tool with `{ cloudId, issueIdOrKey: <KEY> }`.
   - Search case-insensitively for a transition whose `name` is exactly
     **"Ready to Test"**.
   - IF found → call the transition tool with `{ cloudId, issueIdOrKey:
     <KEY>, transition: { id: <matched id> } }`.
   - IF not found → use the same explicit message pattern as Step 2.4,
     substituting "Ready to Test" for "In Progress".

## Step 4 — Post-commit comment trigger

Run this after **every** `git commit` the agent performs during this
session, in order:

1. Confirm that the local `SESSION_RESUME.md` was updated after the commit
   with the commit identifier, validation performed, current planning or
   implementation state, and next resume point. It is gitignored, untracked,
   and must not be staged. If validation failed or the handoff is incomplete,
   record that state before continuing.
2. Ask the user directly, verbatim: "Add a summary comment to the Jira
   ticket for this commit?"
3. IF the user answers no / declines → do nothing further; continue with
   whatever comes next.
4. IF the user answers yes:
   1. Determine `<KEY>` using the exact same procedure as Step 3.1.
   2. IF the commit touched any files under a `*.Report/` or
      `*.SemanticModel/` project folder → run
      `../git-branch-guard/assets/pbip-pr-summary/commit_diff_summary.ps1`
      (or `.sh`) with no arguments (it defaults to `HEAD~1..HEAD`) to get a
      grounded, structurally-diffed bullet list instead of reading the raw
      JSON yourself — UI/JSON changes (slicer field order, formatting,
      filters) are unreliable to summarize by eye. Use its output as the
      basis for the summary below; if the script errors or isn't available,
      fall back to reading the diff directly.
   3. Write a 1-3 sentence **plain-English summary** of what the commit
      changed and why — a human-readable explanation, not the raw commit
      message or diff pasted verbatim.
   4. Call the add-comment tool with `{ cloudId, issueIdOrKey: <KEY>,
      commentBody: <the plain-English summary> }`. Note the body parameter
      is named `commentBody`, not `body`.
      - IF it errors → tell the user the exact error text and that they
        should add the comment manually in Jira. Do not retry silently and
        do not fail the rest of the task over this.

---

## Fallback algorithm

Tell the user Jira is unavailable and automatic ticket updates cannot run.
Complete Required intake before branch handling, including obtaining the
user-provided key, updating `RESUME.md`, and asking work area then work type.
Ask for a short description if needed; return the same scope, type and ticket
contract to the caller. The caller performs branch selection and validation.
Offer the post-commit Jira comment prompt when applicable; if accepted, explain
that the user must add the comment manually. Do not invent Jira tool names.

---
## Worked example

For FIN-1740, record the user-provided key, ask work area then work type, and route explicit exclusive Fabric DE through the configured DEV guard. A Power BI story instead uses a Jira-keyed feature branch and the report subtype gate. If Jira is unavailable, preserve the same intake and use the manual fallback.
