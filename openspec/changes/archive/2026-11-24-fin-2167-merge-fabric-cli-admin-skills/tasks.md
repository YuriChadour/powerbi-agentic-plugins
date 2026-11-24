## 1. Reconcile source and destination

- [x] 1.1 Compare source and destination CLI guidance, references, assets and scripts; record the selected additions and conflict resolutions in the change record.
- [x] 1.2 Review the two admin skills and their scripts, metadata and dependencies; identify portable resources and verify each referenced dependency is accounted for.
- [x] 1.3 Review existing Fabric specialist routing and installation conventions; document ownership and harness adaptations in the change record.

## 2. Integrate skills

- [x] 2.1 Merge selected CLI guidance and resources into `plugins/fabric/skills/fabric-cli`; verify existing destination-specific assets and specialist routes remain available.
- [x] 2.2 Add capacity and tenant audit skills with their required resources; verify prerequisites, CLI cross-references and script paths resolve.
- [x] 2.3 Reconcile automatic upgrade, force flags, consent, configuration and harness-specific instructions with repository constraints; review resulting guidance for conflicting instructions.
- [x] 2.4 Update Fabric plugin discovery and documentation as needed; verify skill names and paths match the packaged files.

## 3. Validate integration

- [x] 3.1 Run focused offline checks for skill metadata, local links, referenced resources and packaging across supported harnesses; record results.
- [x] 3.2 Exercise included scripts using safe fixtures or mocks where feasible, check dependencies and sensitive output handling, and document any untested live operations.
- [x] 3.3 Review the final diff against the source comparison and scenarios in the spec; record remaining limitations and validation results.

## 4. Standardize newly integrated Python scripts on uv

- [x] 4.1 Add uv-compatible inline dependency metadata to newly integrated Fabric CLI and tenant-audit Python scripts, without changing pre-existing Fabric-plugin scripts.
- [x] 4.2 Update newly integrated script guidance to use `uv run` and distinguish uv-managed dependencies from external commands, authentication, and live-operation prerequisites.
- [x] 4.3 Run non-mutating uv-based checks for the updated scripts where feasible; record unavailable external dependencies and avoid live Fabric operations.
