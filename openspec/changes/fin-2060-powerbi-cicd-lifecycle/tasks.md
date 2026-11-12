## 1. Establish ownership and the non-secret contract

- [ ] 1.1 Inventory the connected Glasslake environment-bootstrap assets alongside existing Power BI authoring, semantic-model, report-management, paginated-report, DAX-testing, DevOps, and `fabric-cicd` mapping assets; record the smallest reusable dependency set and verify every retained asset has one named owner.
- [ ] 1.2 Create the `plugins/powerbi/skills/powerbi-cicd/` skeleton and `Initialize-PowerBiCicd.ps1` with the same `Render|Plan|Apply|Status|Resume|Deploy`, configuration, manifest, repository, output, target, artifact, and write-guard parameters as `Initialize-FabricCicd.ps1`; verify each compatible invocation parses and a Power BI CI/CD request selects this skill rather than `fabric-cicd`.
- [ ] 1.3 Define and validate a Fabric-compatible non-secret configuration schema retaining repository, Azure DevOps, workspace, target, role, pipeline, and protected-resource sections while replacing the Fabric source and managed-item fields with `powerbi_source_folder`, supported item identities, dependencies, RDL bindings, required DEV/TEST/PROD mappings, optional UAT/REHEARSAL mappings, substitutions, and target metadata; verify absent, arbitrary, extra, unsafe, or ambiguous target fields fail closed.
- [ ] 1.4 Migrate or deprecate the existing `fabric-cicd` `pbi-assets.yml` mapping contract with a documented compatibility path; verify `fabric-cicd` retains its Power BI deployment exclusion and no Power BI deployment owner remains under the Fabric skill.

## 2. Implement read-only discovery and offline validation

- [ ] 2.1 Implement a read-only repository discovery command that reports candidate Power BI roots, existing CI/CD assets, and mapping gaps without remote URLs, credentials, local writes, Azure DevOps changes, or workspace calls; verify a synthetic mixed-workload repository is classified but not enabled.
- [ ] 2.2 Implement Power BI source-boundary validation for PBIP/PBIR/TMDL/RDL structure, logical identities, supported-item classification, source exclusions, and committed-secret safety; verify valid fixtures pass and malformed, duplicate, unsupported, escaped-path, and secret-bearing fixtures fail.
- [ ] 2.3 Implement dependency-manifest generation and validation using existing specialist validators where appropriate; verify semantic models precede dependent reports, unresolved references block validation, and a paginated report without an explicit binding cannot proceed.
- [ ] 2.4 Implement machine-readable, redacted PR validation output and Azure DevOps validation template behavior; verify the validation job has no protected variable group, service-principal secret, target write permission, or workspace-authentication step.

## 3. Build and verify immutable release artifacts

- [ ] 3.1 Implement packaging of only the approved Power BI source subset, reviewed non-secret configuration, dependency lock, manifest, revision identifier, and SHA-256 hashes; verify unrelated files, credentials, and Fabric data-engineering content are excluded.
- [ ] 3.2 Implement artifact integrity checks and deterministic deployment ordering for configured UAT, TEST, PROD, and REHEARSAL targets; verify a changed digest, revision mismatch, missing dependency, unresolved RDL binding, or unconfigured target stops before a deployment operation.
- [ ] 3.3 Produce retained non-secret release evidence for source revision, digest, environment, target, managed scope, approval, identity reference, and result; verify error and partial-result records do not expose secret values.

## 4. Implement the supported Power BI deployment adapter

- [ ] 4.1 Establish and test the supported-item matrix against the intended non-production tenant/API surface, documenting the approved Power BI/Fabric operation and least-privilege preflight for each supported item family; verify unsupported or unavailable operations remain blocking classifications with no fallback write path.
- [ ] 4.2 Implement adapter `preflight`, `deploy`, and `verify` operations that consume only validated artifacts and explicit environment mappings; verify unavailable identity, target mismatch, missing binding, or failed read-only preflight stops before a workspace write.
- [ ] 4.3 Implement dependency-aware deployment and post-deployment verification of item scope, semantic-model/report bindings, configured substitutions, semantic-model readiness, and applicable RDL data sources; verify report deployment cannot precede its model and a verification failure blocks promotion.
- [ ] 4.4 Implement managed-state drift reporting and known-good artifact recovery through the same protected path; verify unmanaged workspace items are neither deleted nor modified during failure handling or rollback.

## 5. Generate protected lifecycle assets and route work correctly

- [ ] 5.1 Implement plan/apply/status/resume behavior that renders reviewable scoped Azure DevOps templates and setup guidance, revalidates the approved configuration before an external write, and reports proposed external actions; verify plan mode performs no local or remote mutation.
- [ ] 5.2 Implement sequential repository, workspace, identity-and-secret, governance, and pilot gates using developer-authenticated `fab` and `az` for idempotent workspace/role reconciliation, DEV Power BI folder Git binding, and named pipeline registration for required TEST/PROD plus configured UAT/REHEARSAL targets; verify each failed gate prevents the next phase, every non-DEV target remains Git-disconnected, and protected runtime identities are not used during setup.
- [ ] 5.3 Generate and register pipeline templates for every configured UAT, TEST, PROD, or REHEARSAL target that build once, apply the target's explicit guard, approval policy, exclusive lock, and environment mapping, and require TEST verification of the matching digest before PROD; verify the pipeline never rebuilds or checks out a different revision after artifact creation and UAT/REHEARSAL cannot replace the TEST gate.
- [ ] 5.4 Integrate scope-first Jira/DevOps/branch-guard handoff for Power BI CI/CD implementation requests; verify Power BI, mixed, other, and unknown requests use normal Jira-keyed feature/bugfix validation and never receive the Fabric-data-engineering DEV exception.
- [ ] 5.5 Update Power BI agent, plugin, Fabric CI/CD, DevOps, repository, and installer-facing documentation to state the shared setup interface, Power BI-specific manifest fields, skill triggers, ownership boundaries, required approvals, and non-secret setup inputs; verify links, skill paths, and examples resolve in each supported harness.

## 6. Verify adoption and safety boundaries

- [ ] 6.1 Add focused unit and fixture tests for discovery, configuration, source validation, dependency locks, package hashes, deployment guards, promotion digest checks, drift handling, and recovery; verify the complete Power BI CI/CD test suite passes.
- [ ] 6.2 Run an end-to-end synthetic Power BI adopter through plan, offline PR validation, package, optional UAT and REHEARSAL deployment simulations, TEST evidence, PROD digest gate, and rollback simulation; verify no Fabric data-engineering item, secret, arbitrary target, or unrelated file enters the generated artifacts.
- [ ] 6.3 Independently exercise Codex, Copilot, and Claude discovery and lifecycle routing with Power BI, Fabric-data-engineering, mixed, and unresolved requests; record each supported result and mark unavailable harnesses or live tenant checks as unverified.
- [ ] 6.4 Validate the OpenSpec change strictly and review generated documentation against the approved lifecycle; verify existing adopter files and unrelated repository changes remain preserved.
