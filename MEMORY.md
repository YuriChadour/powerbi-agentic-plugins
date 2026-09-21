# Project Memory

## Codex agent adapters

- Codex projects all packaged agent adapters into the shared user directory `%USERPROFILE%\.codex\agents`.
- Every checked-in agent adapter MUST therefore have a globally unique TOML `name` and filename across all plugins. Matching the filename to the `name` is the repository convention.
- Before adding an adapter, check the complete plugin catalog for name and filename collisions. Do not rely on a plugin directory as a Codex namespace.
- Adapter parity validation must normalize CRLF/LF line endings and trailing whitespace before comparing `developer_instructions`; otherwise Windows checkouts can be falsely reported as stale.
