## 1. Import and adapt the Warehouse CLI guidance

- [x] 1.1 Create an attributed `sqldw-cli` Warehouse CLI reference from the upstream Warehouse guidance, and verify it documents Fabric CLI creation, inspection, browsing, bounded DuckDB Delta reads, supported loading paths, and clearly labelled deletion behavior.
- [x] 1.2 Adapt all examples to discover resource identifiers at runtime, use supported Azure CLI credential acquisition, omit secrets, and bound read queries; verify no hardcoded GUID, connection string, or token is introduced.
- [x] 1.3 Document Fabric CLI and DuckDB as optional external prerequisites without adding Python package installation; verify the reference distinguishes them from the MCP SQL execution path.

## 2. Integrate the workflow

- [x] 2.1 Link the Warehouse CLI reference from `sqldw-cli/SKILL.md` and preserve the authoring, consumption, and operations mode selection; verify the new link resolves locally.
- [x] 2.2 State the MCP-first T-SQL boundary and destructive-command confirmation requirement in the integrated guidance; verify a Warehouse inspection, a DuckDB read, and a deletion request each route to the correct safeguards.
- [x] 2.3 Review root attribution and update it only if required for the imported source; verify the reference itself identifies its upstream material.

## 3. Validate and document delivery

- [x] 3.1 Run repository Markdown-link validation and `git diff --check`; verify all changed links resolve and the diff has no whitespace errors.
- [x] 3.2 Review all added command examples for repository safety compliance; verify DuckDB reads are bounded and no destructive command is presented as automatic.
- [x] 3.3 Run `openspec validate fin-2167-merge-sqldw-cli --strict`; verify the implementation artifacts remain consistent with the approved change.
