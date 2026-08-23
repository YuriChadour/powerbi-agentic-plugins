---
name: jira-workflow
description: Fetches, assigns, and transitions Jira tickets via the Atlassian MCP when a user starts or finishes work, and offers to post a commit summary comment. Falls back to a manual prompt when no Jira MCP is available.
---

# Jira Workflow (MCP-driven)

## Purpose

Automate the Jira side of starting and finishing ticket work, and posting
progress comments, using whatever Atlassian/Jira MCP server is connected in
the current session. This skill is written as a **strict numbered algorithm**.
Follow the steps in order, exactly as written. Do not skip steps. Do not
invent tool names. Do not guess status/transition IDs.

This skill does **not** create or validate git branches — that is the job of
the separate `git-branch-guard` skill. This skill only supplies
`ticket_key` and `short_description` to it (see Step 2.6).

## Dependencies

| Dependency | Purpose | Required When |
|---|---|---|
| `atlassian-rovo-mcp` MCP server (primary) | Fetch/assign/transition Jira tickets, add comments | Preferred — try first in Step 0 |
| `com.atlassian/atlassian-mcp-server` MCP server (secondary) | Same as above | Fallback candidate if `atlassian-rovo-mcp` is not connected |
| `git` / `git-branch-guard` skill | Creates the branch using `ticket_key` + `short_description` | Always, after Step 2 |

Both MCP server identifiers above are already used elsewhere in this repo
(`plugins/powerbi/agents/powerbi-architect.agent.md`), so they are the
first things to look for — see Step 0. If neither is connected, this skill
degrades automatically to the **Fallback algorithm** — this is expected,
non-error behavior, not a failure to work around.

---

## Step 0 — Discover the real MCP tool names (always do this first)

This repo already has a known, working Atlassian MCP integration configured
in `plugins/powerbi/agents/powerbi-architect.agent.md`, which lists these
exact MCP server identifiers:
```
atlassian-rovo-mcp/search
com.atlassian/atlassian-mcp-server/search
```
Try these two concrete server names **first**, in this order:

1. Call `tool_search_tool` with pattern `atlassian-rovo-mcp` (case-insensitive).
   - IF this returns one or more tools → this is the server to use. Skip to
     Step 0.3.
2. ELSE call `tool_search_tool` with pattern `com.atlassian.*atlassian-mcp-server`
   (case-insensitive).
   - IF this returns one or more tools → this is the server to use. Continue
     to Step 0.3.
   - IF this also returns zero tools → call `tool_search_tool` once more
     with the broader pattern `jira|atlassian` as a last resort, in case a
     differently-named Jira/Atlassian MCP server is connected instead.
     - IF that also returns zero tools → go directly to the **Fallback
       algorithm** at the bottom of this document, and stop. Do not attempt
       Steps 1-4.
3. Read the returned tool list from whichever search above succeeded. Match
   tools **by function** to the 7 jobs below — the exact tool names can
   still vary by MCP server version, so confirm each one exists before using
   it (example names shown in parentheses are hints from
   `Fabric Admin\.github\prompts\weekly_status_report.md`, not guaranteed):
   - List accessible Atlassian sites / get `cloudId` (e.g.
     `getAccessibleAtlassianResources`)
   - Get a single issue by key (e.g. `getJiraIssue`)
   - Search issues by JQL (e.g. `searchJiraIssuesUsingJql`)
   - List valid transitions for an issue (e.g. `getTransitionsForJiraIssue`)
   - Execute a transition (e.g. `transitionJiraIssue`)
   - Edit an issue's fields, including assignee (e.g. `editJiraIssue`)
   - Add a comment (e.g. `addCommentToJiraIssue`)
   - Resolve the current signed-in user's account id (any "who am I" /
     current-user tool; if none exists, plan to ask the user for their
     Atlassian email and use a user-lookup tool instead)
4. Record which concrete tool name fills each of the 7 jobs above. Reuse
   those exact discovered names for the rest of this session — never call a
   tool name you have not confirmed exists.
5. **Decision point:**
   - IF no tool was found in Steps 0.1-0.2 for **any** of the 7 jobs → go
     directly to the **Fallback algorithm** at the bottom of this document,
     and stop. Do not attempt Steps 1-4.
   - ELSE → continue to Step 1.

## Step 1 — Resolve the Atlassian `cloudId` (once per session)

1. Call the site-discovery tool found in Step 0.
2. IF it errors, times out, or returns no site → go to the **Fallback
   algorithm** and stop.
3. ELSE → store the returned `cloudId` value in memory for this session.
   Reuse it in every subsequent Jira MCP call below — do not re-resolve it
   each time.

## Step 2 — Start-ticket trigger

**Trigger phrases** (case-insensitive match against the user's message; the
ticket key is any token matching the regex `[A-Z]+-\d+`):
- "I want to work on <KEY>"
- "let's work on <KEY>"
- "start <KEY>"
- "pick up <KEY>"
- "I'm starting <KEY>"

When one of these matches, extract `<KEY>` and do the following, in order:

1. Call the get-issue tool from Step 0 with `{ cloudId, issue_key: <KEY> }`.
   - IF it errors (not found, permission denied, call fails) → tell the user
     the exact error text returned, then go to the **Fallback algorithm** and
     stop.
   - ELSE → store the issue's `summary`, `status`, and `issuetype` fields.
2. Resolve the current user's Atlassian account id using the current-user
   tool found in Step 0.
   - IF no such tool exists, or it errors → ask the user directly: "What is
     your Atlassian account email?" Then call a user-lookup tool (found in
     Step 0) with that email to get the account id.
   - IF that also fails → tell the user: "I couldn't resolve your Atlassian
     account automatically — you'll need to assign this ticket to yourself
     manually in Jira." Continue to Step 2.4 anyway (do not treat this as a
     full MCP failure / do not go to Fallback).
3. IF an account id was resolved in Step 2.2 → call the edit-issue tool with
   `{ cloudId, issue_key: <KEY>, assignee: <account_id> }` to assign the
   ticket to the current user.
   - IF it errors → tell the user the exact error text, but continue (do not
     stop the whole flow over an assignment failure).
4. Call the list-transitions tool with `{ cloudId, issue_key: <KEY> }`.
   - Search the returned list, case-insensitively, for an entry whose target
     status name is exactly **"In Progress"**.
   - IF found → call the transition tool with `{ cloudId, issue_key: <KEY>,
     transition_id: <the matched id> }`.
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
6. Hand off `ticket_key = <KEY>` and `short_description` (from Step 2.5) to
   the `git-branch-guard` skill so it can create/validate the
   `feature/<KEY>-<short_description>` or `bugfix/<KEY>-<short_description>`
   branch. Ask the user which of `feature` or `bugfix` applies if the
   ticket's `issuetype` (from Step 2.1) does not make it obvious (e.g.
   `issuetype` containing "Bug" → `bugfix`; anything else → `feature`).

## Step 3 — Finish-ticket trigger

**Trigger phrases** (case-insensitive):
- "I'm done with this ticket"
- "I'm finished working on this"
- "finished with <KEY>"
- "done with <KEY>"
- "ready to test <KEY>"
- "ready to test this ticket" (no key given)

When one of these matches:

1. Determine `<KEY>`:
   - IF the message contains a token matching `[A-Z]+-\d+` → use that as
     `<KEY>`.
   - ELSE → extract the ticket key from the current git branch name using
     the same regex `[A-Z]+-\d+` (this matches how `git-branch-guard` names
     branches: `feature/<KEY>-...` or `bugfix/<KEY>-...`). Run
     `git branch --show-current` if needed to read the branch name.
   - IF no key can be determined either way → ask the user: "Which ticket
     key should I transition?" and use their answer.
2. Call the list-transitions tool with `{ cloudId, issue_key: <KEY> }`.
   - Search case-insensitively for a transition whose target status name is
     exactly **"Ready to Test"**.
   - IF found → call the transition tool with that transition id.
   - IF not found → use the same explicit message pattern as Step 2.4,
     substituting "Ready to Test" for "In Progress".

## Step 4 — Post-commit comment trigger

Run this after **every** `git commit` the agent performs during this
session, in order:

1. Ask the user directly, verbatim: "Add a summary comment to the Jira
   ticket for this commit?"
2. IF the user answers no / declines → do nothing further; continue with
   whatever comes next.
3. IF the user answers yes:
   1. Determine `<KEY>` using the exact same procedure as Step 3.1.
   2. Write a 1-3 sentence **plain-English summary** of what the commit
      changed and why — a human-readable explanation, not the raw commit
      message or diff pasted verbatim.
   3. Call the add-comment tool with `{ cloudId, issue_key: <KEY>, body:
      <the plain-English summary> }`.
      - IF it errors → tell the user the exact error text and that they
        should add the comment manually in Jira. Do not retry silently and
        do not fail the rest of the task over this.

---

## Fallback algorithm (used whenever a step above says "go to Fallback")

1. Tell the user plainly: "The Jira/Atlassian MCP isn't available, so I
   can't fetch, assign, or transition the ticket automatically."
2. Ask the user two explicit questions:
   1. "What type of ticket is this — feature or bugfix?"
   2. "Give me a short kebab-case description for the branch name."
3. Hand off the user's two answers directly to `git-branch-guard` to
   create/validate the branch, exactly as it works today. Do not attempt any
   further Jira MCP calls for the rest of this flow (Steps 1-4 above are
   skipped entirely in fallback mode; Step 4's post-commit prompt should
   still be offered, but if the user says yes, tell them the comment can't
   be posted automatically and they should add it manually in Jira).

---

## Worked example (Steps 0-2, MCP available)

```
User: I want to work on FIN-1740

Agent (Step 0): [calls tool_search_tool("jira|atlassian")]
  -> finds: getAccessibleAtlassianResources, getJiraIssue,
     getTransitionsForJiraIssue, transitionJiraIssue, editJiraIssue,
     addCommentToJiraIssue, atlassianUserInfo

Agent (Step 1): [calls getAccessibleAtlassianResources]
  -> cloudId = "abc-123-bayview"

Agent (Step 2.1): [calls getJiraIssue(cloudId, "FIN-1740")]
  -> summary = "Update Agentic tooling for developers to automatically
     link to relevant jira and create latest comments on jira ticket"
  -> status = "To Do", issuetype = "Story"

Agent (Step 2.2): [calls atlassianUserInfo] -> accountId = "abc123"

Agent (Step 2.3): [calls editJiraIssue(cloudId, "FIN-1740",
  assignee: "abc123")] -> success

Agent (Step 2.4): [calls getTransitionsForJiraIssue(cloudId, "FIN-1740")]
  -> finds transition "In Progress" (id=21)
  [calls transitionJiraIssue(cloudId, "FIN-1740", 21)] -> success

Agent (Step 2.5): slugify summary ->
  "update-agentic-tooling-for-developers-to-autom" (truncated to 40 chars)

Agent (Step 2.6): hands off ticket_key="FIN-1740",
  short_description="update-agentic-tooling-for-developers-to-autom" to
  git-branch-guard, asks: "This looks like a Story — should the branch be
  feature/ or bugfix/?" -> user says feature ->
  git-branch-guard creates feature/FIN-1740-update-agentic-tooling-for-developers-to-autom
```
