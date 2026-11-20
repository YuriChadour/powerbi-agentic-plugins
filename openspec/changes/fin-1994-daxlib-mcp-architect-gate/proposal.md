## Why

Power BI specifications can describe DAX behavior that already exists in community user-defined function packages, but the architect currently has no required library-discovery step. A read-only DAX Lib review after a specification is fully drafted can identify reusable options before developer handoff, while keeping package selection and installation under explicit user control.

## What Changes

- Register DaxLib MCP for the Power BI plugin and expose only its read-only package search and inspection tools to the architect.
- Add a required architect research gate after the technical specification draft is complete and before it is presented as finalized.
- Record relevant package findings, recommendation or no-match result, version and compatibility evidence, licensing, and limitations in the specification.
- Define an explicit blocked/unavailable outcome when the MCP cannot be used; do not claim the review occurred or silently skip the gate.
- Keep package installation and model mutation outside architect authority; installation requires a separate user-authorized implementation action.

## Capabilities

### New Capabilities
- `powerbi/dax-library-research-gate`: Require a documented, read-only DAX Lib package review during architect specification finalization.

### Modified Capabilities
- None.

## Impact

- Power BI plugin MCP configuration and supported host projections.
- `plugins/powerbi/agents/powerbi-architect.agent.md` and its checked-in Codex adapter, which must remain behaviorally aligned.
- Power BI architect instructions, specification output, and relevant setup/configuration validation.
- The external `@daxlib/mcp` package and DAX Lib catalog. DaxLib covers community DAX UDF packages; it is not a general library optimizer and its recommendations do not establish runtime performance without model-specific validation.