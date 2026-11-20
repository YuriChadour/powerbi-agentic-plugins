## 1. MCP Availability and Tool Boundaries

- [ ] 1.1 Pin a reviewed `@daxlib/mcp` release in the Power BI plugin MCP configuration and verify the configuration parses and the pinned package launches.
- [ ] 1.2 Expose only package search, metadata, and README inspection to the architect in supported host projections; verify `install_package` is absent from the architect's available tools.
- [ ] 1.3 Document and validate Node.js 18+ and Windows x64 availability; verify unsupported hosts report the DAX Lib gate as unavailable without failing unrelated plugin setup.

## 2. Architect Research Gate

- [ ] 2.1 Update `powerbi-architect.agent.md` to run the applicability check after the technical draft is complete and, when applicable, search and inspect candidates using generic functional queries; verify the gate occurs before final handoff.
- [ ] 2.2 Define the `DAX Library Review` output with package/version, links, functional fit, compatibility evidence, license evidence or `unknown`, limitations, and recommendation; verify no-match and not-applicable outcomes are explicitly represented.
- [ ] 2.3 Specify unresolved behavior for an unavailable MCP, requiring setup or explicit user exception; verify the architect does not claim a bypass is a completed review, install packages, modify models, or assert unmeasured performance gains.
- [ ] 2.4 Update the checked-in Codex architect adapter to match the source agent instructions and verify instruction parity with the repository's validation tooling.

## 3. Integration Validation

- [ ] 3.1 Add or update validation for MCP configuration, supported-host projection, read-only tool exposure, and architect-adapter parity; run the focused validation successfully.
- [ ] 3.2 Run a bounded MCP initialization, catalog search, and package inspection on supported Windows x64 with Node.js 18+; verify the architect can record evidence without invoking model installation.
- [ ] 3.3 Exercise unavailable-MCP, unsupported-host, no-match, and not-applicable outcomes; verify each is recorded correctly and only an explicit user exception can unblock an unresolved review.