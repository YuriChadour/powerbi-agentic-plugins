## Why

The separate development repository contains expanded Fabric CLI and administration guidance that is absent from this plugin repository. Integrating the useful capabilities will make them available through the existing Fabric plugin while preserving its established workflows.

## What Changes

- Merge relevant updates, references and supporting scripts from the source `fabric-cli` skill into the existing Fabric plugin skill.
- Integrate the source `fabric-capacity` and `audit-tenant-settings` skills with their required resources into the Fabric plugin.
- Reconcile overlapping guidance, cross-skill routing, harness-specific assumptions and documentation; validate packaging and dependencies.
- Make only the newly integrated Python scripts uv-native, with self-declared runtime dependencies and uv-based invocation guidance.

## Capabilities

### New Capabilities

- `fabric/cli-admin-skills`: Fabric CLI and administration skill integration, routing and distributable supporting resources.

### Modified Capabilities

None.

## Impact

The `plugins/fabric/skills` tree and Fabric plugin documentation and packaging may change. The uv revision is limited to newly integrated Python scripts under `fabric-cli` and `audit-tenant-settings`; it does not modify pre-existing Fabric-plugin scripts. Source material is in `C:/Development/power-bi-agentic-development/plugins/fabric-cli` and `plugins/fabric-admin`. Existing specialist skills, supported harnesses, external CLI dependencies and authorization boundaries require compatibility review. No live Fabric operation is part of this proposal.
