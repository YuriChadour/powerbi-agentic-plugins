# Verification record

## Offline implementation evidence

- Reference commit `4a77113ec051907c3e10e6da9d4a89e62bfb58ea`: the retained wrapper, manifest, UAT/TEST/PROD YAML, validation, packaging, deployment, verification and focused-test paths resolved in the connected Analytics Reporting checkout.
- `py -3 -B -m unittest discover plugins/fabric/skills/fabric-cicd/tests -v`: passed 15 tests. Coverage includes a synthetic Fabric-folder adopter, read-only planning, manifest validation, source and secret scope, immutable packaging and digest gate, rendered YAML path filters, protected-deployment contract and no Power BI output.
- PowerShell parse check for `Initialize-FabricCicd.ps1`: passed.
- `openspec validate fin-2060-reference-fabric-bootstrap --type change --strict`: passed.

## Harness evidence

- Codex discovery: `C:\Users\IOURICHADOUR\.codex\skills\fabric-cicd` was not installed at verification time, so an installed-Codex routing test is unavailable.
- Copilot discovery: `copilot plugin list` reports `fabric@powerbi-agentic-plugins (v0.2.0)` installed. The repository source and its focused tests were validated; no installer mutation was performed.

## Deliberately unverified live behavior

No live `fab` or `az` command was run. Workspace creation/reuse, role reconciliation, Fabric Git-connection preflight, Azure Pipeline registration, protected deployment and runtime execution therefore remain unverified. A live exercise requires separately selected targets, developer permissions and protected resources.
