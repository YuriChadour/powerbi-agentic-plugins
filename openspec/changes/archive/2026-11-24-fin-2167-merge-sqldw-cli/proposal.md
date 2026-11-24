## Why

The Fabric CLI source collection includes Warehouse lifecycle, inspection, and
DuckDB-over-OneLake guidance that was not brought over with the initial
`fabric-cli` merge. The existing `sqldw-cli` skill is stronger for SQL endpoint
authoring, querying, and diagnostics, but lacks this CLI-specific workflow.

## What Changes

- Incorporate the upstream Fabric CLI Warehouse reference into `sqldw-cli` as a
  focused, attributed reference for Warehouse lifecycle inspection and
  read-only Delta access through DuckDB.
- Reconcile the upstream examples with this repository's safety conventions:
  MCP remains the preferred SQL execution surface; destructive operations stay
  explicit and guarded; and credentials are obtained through supported CLI
  authentication rather than stored in commands or files.
- Link the new reference from the `sqldw-cli` dispatcher without changing its
  existing authoring, consumption, and operations mode boundaries.
- Add validation that the imported reference is reachable and that its commands
  and links satisfy repository documentation checks.

## Capabilities

### New Capabilities

- `fabric/sqldw-cli`: Fabric Warehouse and SQL-endpoint guidance that includes
  safe Fabric CLI lifecycle inspection and DuckDB access to Warehouse Delta
  tables, alongside the existing MCP-first SQL workflow.

### Modified Capabilities

- None.

## Impact

- `plugins/fabric/skills/sqldw-cli/SKILL.md` and a new supporting reference
  under its `references/` directory.
- Fabric CLI (`fab`) and DuckDB remain optional local prerequisites for the
  added workflow; no Python package installation is introduced.
- README/source acknowledgements will be extended only if the imported content
  requires a new, distinct attribution beyond the existing source-repository
  acknowledgement.
