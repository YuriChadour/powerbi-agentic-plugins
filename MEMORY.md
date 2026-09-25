# Project Memory

## Codex agent adapters

- Codex projects all packaged agent adapters into the shared user directory `%USERPROFILE%\.codex\agents`.
- Every checked-in agent adapter MUST therefore have a globally unique TOML `name` and filename across all plugins. Matching the filename to the `name` is the repository convention.
- Before adding an adapter, check the complete plugin catalog for name and filename collisions. Do not rely on a plugin directory as a Codex namespace.
- Adapter parity validation must normalize CRLF/LF line endings and trailing whitespace before comparing `developer_instructions`; otherwise Windows checkouts can be falsely reported as stale.

## End-of-session workflow

- Update `MEMORY.md` and `SESSION_RESUME.md` before publishing session state.
- Run `scripts/end-session.ps1` with the active OpenSpec change. It validates OpenSpec, reports unchecked tasks without marking them complete, stages only declared handoff files, commits, pushes the Jira branch, creates a PR targeting `DEV`, and prints a Jira-ready update.
- Post the generated commit/PR summary through the configured Jira workflow and transition the ticket only when the actual Jira transition is available.
