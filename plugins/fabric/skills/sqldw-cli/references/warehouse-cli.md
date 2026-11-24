# Fabric Warehouse CLI and DuckDB Reference

> **Source attribution:** Adapted from the Warehouse reference in
> [Yuri Chadour's power-bi-agentic-development repository](https://github.com/YuriChadour/power-bi-agentic-development),
> whose relevant Fabric CLI history credits [Kurt Buhler](https://github.com/data-goblin).
> Adapted for this repository's MCP-first SQL and destructive-operation safety
> boundaries.

Use this reference for Fabric CLI (`fab`) Warehouse discovery and lifecycle
operations, and for bounded, read-only DuckDB access to a Warehouse's Delta
tables in OneLake. It does **not** replace the `authoring`, `consumption`, or
`operations` mode references: run T-SQL through
`fabric-sqlendpoint-execute_query` whenever that MCP tool is available.

## Prerequisites and boundaries

- `fab` and DuckDB are external command-line prerequisites. They are not Python
  dependencies and are not installed by `uv`.
- Before running the first `fab` command, verify authentication with
  `fab auth status`; if needed, ask the user to run `fab auth login`.
- Before using a `fab` command for the first time, inspect `fab --help` and
  `fab <command> --help` to confirm the installed version's syntax.
- DuckDB is a local, read-only Delta-file path. It does not provide Warehouse
  T-SQL semantics, Query Insights diagnostics, or a write path.
- Do not put access tokens, client secrets, connection strings, or resolved
  identifiers in scripts or documentation. Resolve identifiers at runtime.

## Create and inspect a Warehouse

Creating a Warehouse changes Fabric state. Confirm the target workspace and
Warehouse name with the user before executing this command.

```bash
fab mkdir "MyWorkspace.Workspace/MyWarehouse.Warehouse"
```

Inspect its properties and browse its schemas or tables:

```bash
fab get "MyWorkspace.Workspace/MyWarehouse.Warehouse" -q "properties"
fab ls "MyWorkspace.Workspace/MyWarehouse.Warehouse"
fab ls "MyWorkspace.Workspace/MyWarehouse.Warehouse/Tables/dbo"
fab table schema "MyWorkspace.Workspace/MyWarehouse.Warehouse/Tables/dbo/orders"
```

`fab get` can return endpoint-related properties, but do not use those values
as a substitute for the Warehouse item ID required by the SQL Endpoint MCP
tool. For T-SQL, use the existing `sqldw-cli` mode workflow and discover the
item ID as documented there.

## Read Warehouse Delta tables with DuckDB

Use this only when the user wants a bounded, read-only Delta-file query. First
confirm that the user is authenticated with both `fab auth status` and the
Azure CLI session used by DuckDB's `credential_chain` provider (for example,
`az account show`).

Discover IDs at runtime rather than copying them into a script:

```bash
WS_ID=$(fab get "MyWorkspace.Workspace" -q "id" | tr -d '"')
WH_ID=$(fab get "MyWorkspace.Workspace/MyWarehouse.Warehouse" -q "id" | tr -d '"')
```

Then run a bounded query. Replace `dbo/orders` with the schema and table the
user identified; retain `LIMIT` or add a selective `WHERE` predicate.

```bash
duckdb -c "
INSTALL delta; INSTALL azure;
LOAD delta; LOAD azure;
CREATE SECRET (TYPE azure, PROVIDER credential_chain, CHAIN 'cli');
SELECT *
FROM delta_scan('abfss://${WS_ID}@onelake.dfs.fabric.microsoft.com/${WH_ID}/Tables/dbo/orders')
LIMIT 10;
"
```

If the Azure extension or CLI credential chain is unavailable in the installed
DuckDB version, stop and report the prerequisite failure. Do not ask the user
to paste a token or save credentials to a local file.

## Supported data-loading paths

Fabric Warehouses do not support `fab cp` to a `Files` area or `fab table load`.
For writes, select the `authoring` mode and use the SQL Endpoint MCP tool for
supported Warehouse T-SQL. Other documented ingestion paths include a Fabric
notebook with `notebookutils.data.connect_to_artifact` or a PySpark notebook
with `synapsesql`; those are outside this CLI reference and must follow their
own workload guidance.

Lakehouse differences that matter here:

| Capability | Warehouse | Lakehouse |
|---|---|---|
| `fab cp` to `Files` | Not supported | Supported |
| `fab table load` | Not supported | Supported where applicable |
| T-SQL DDL/DML | Supported on Warehouse through SQL Endpoint MCP | SQL analytics endpoint is read-only |
| DuckDB `delta_scan` | Bounded, read-only access | Bounded, read-only access |

## Delete a Warehouse — destructive

Deletion is irreversible except where tenant Item Recovery is available. Do
not run this command automatically. First show the exact resolved Warehouse
path, explain the impact, and obtain the user's explicit confirmation for that
specific target. Then run:

```bash
fab rm "MyWorkspace.Workspace/MyWarehouse.Warehouse" -f
```

After deletion, report the exact target and whether recovery depends on the
tenant's Item Recovery setting. Do not assume recovery is enabled.
