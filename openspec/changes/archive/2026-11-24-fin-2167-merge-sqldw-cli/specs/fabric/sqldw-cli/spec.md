## Purpose

Provide safe, discoverable Fabric Warehouse guidance that joins the existing
MCP-first SQL workflow with Fabric CLI inspection and DuckDB Delta access.

## ADDED Requirements

### Requirement: Warehouse CLI guidance is discoverable
The `sqldw-cli` skill SHALL expose a focused reference for Fabric Warehouse
lifecycle inspection and browsing through the Fabric CLI, without displacing
the existing mode-selected SQL guidance.

#### Scenario: User requests Warehouse inspection
- **WHEN** a user asks to inspect a Warehouse, its properties, schemas, or
  tables through the Fabric CLI
- **THEN** the skill routes the request to guidance that uses the Fabric CLI
  and identifies the relevant Warehouse resource safely.

### Requirement: Warehouse Delta reads protect credentials and scope
The skill SHALL describe DuckDB access to Warehouse Delta tables as a read-only
workflow that uses supported Azure CLI credential acquisition and a bounded
query.

#### Scenario: User reads a Warehouse table with DuckDB
- **WHEN** a user requests a DuckDB query against a Warehouse Delta table
- **THEN** the guidance obtains the workspace and Warehouse identifiers without
  hardcoding them, uses the supported credential chain, and includes a bounded
  read example.

### Requirement: CLI guidance preserves SQL and mutation boundaries
The Warehouse CLI reference SHALL retain the existing MCP-first path for T-SQL
execution, distinguish it from read-only Delta access, and require explicit
user intent before any destructive Fabric CLI command is run.

#### Scenario: User requests a Warehouse deletion
- **WHEN** a user asks to delete a Warehouse using the Fabric CLI
- **THEN** the guidance identifies the command as destructive and requires
  confirmation consistent with repository safety rules before execution.
