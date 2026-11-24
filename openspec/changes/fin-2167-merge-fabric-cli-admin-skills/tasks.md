## 1. Reconcile source and destination

- [ ] 1.1 Compare source and destination CLI guidance, references, assets and scripts; record the selected additions and conflict resolutions in the change record.
- [ ] 1.2 Review the two admin skills and their scripts, metadata and dependencies; identify portable resources and verify each referenced dependency is accounted for.
- [ ] 1.3 Review existing Fabric specialist routing and installation conventions; document ownership and harness adaptations in the change record.

## 2. Integrate skills

- [ ] 2.1 Merge selected CLI guidance and resources into `plugins/fabric/skills/fabric-cli`; verify existing destination-specific assets and specialist routes remain available.
- [ ] 2.2 Add capacity and tenant audit skills with their required resources; verify prerequisites, CLI cross-references and script paths resolve.
- [ ] 2.3 Reconcile automatic upgrade, force flags, consent, configuration and harness-specific instructions with repository constraints; review resulting guidance for conflicting instructions.
- [ ] 2.4 Update Fabric plugin discovery and documentation as needed; verify skill names and paths match the packaged files.

## 3. Validate integration

- [ ] 3.1 Run focused offline checks for skill metadata, local links, referenced resources and packaging across supported harnesses; record results.
- [ ] 3.2 Exercise included scripts using safe fixtures or mocks where feasible, check dependencies and sensitive output handling, and document any untested live operations.
- [ ] 3.3 Review the final diff against the source comparison and scenarios in the spec; record remaining limitations and validation results.
