## 1. Preserve the reference baseline

- [x] 1.1 Capture the compatible UAT PowerShell wrapper, manifest, Fabric YAML, packaging, deployment, verification and documentation dependencies from reference commit `4a77113ec051907c3e10e6da9d4a89e62bfb58ea`; document that its YAML was not provisioned by `az` and verify all retained paths resolve.
- [x] 1.2 Adapt a focused offline baseline for the PowerShell plan/apply boundary, manifest, folder scope, source checks and promotion contract before functional generalization; distinguish mocked command services from live evidence.
- [x] 1.3 Assess the checkpoint only for the few documentation or rendering helpers needed by the connected workflow; document each consumer and verify no broad Python REST adapter or helper is copied without one.

## 2. Generalize the connected UAT flow

- [x] 2.1 Parameterize workspace, capacity, Lakehouse, Fabric source and generated-CI folders, source revision, managed items and dependencies, principal object IDs/types/roles, Azure Repos organization/project/repository/branch, pipeline names and protected-resource references; verify different synthetic adopters have no reference IDs, names or secrets as defaults.
- [x] 2.2 Preserve the reference YAML managed-item interface and adapt its configuration and validation; verify the reference-shaped manifest and missing or inconsistent input cases.
- [x] 2.3 Provide one PowerShell setup entry point for read-only plan and coordinated authorized apply, with status and resume; use the invoking developer's authenticated `fab` session for selected workspace creation/reuse and explicit role reconciliation, and verify no writes on plan, target isolation, idempotent reuse, missing developer authorization and failure recovery.
- [x] 2.4 Render compatible Fabric UAT/TEST/PROD pipeline YAML, minimal PowerShell templates and `SETUP.md` under the configured CI folder; verify all rendered paths, inputs, permissions and commands resolve without the reference checkout and that a Power BI folder is not selected.
- [x] 2.5 After rendered Fabric YAML is committed to the configured Azure Repos branch, use the invoking developer's authenticated `az` session with the Azure DevOps extension to list and create only missing named Fabric pipelines; verify idempotent reuse and block missing developer authorization or a mismatched repository, branch or YAML path before writes.
- [x] 2.6 Preserve useful reference source and secret checks inside the Fabric pipeline; verify file checks do not claim Fabric execution and no separate source-only pipeline is required.
- [x] 2.7 Package only selected Fabric managed definitions and required deployment tooling from the exact revision; verify hashes, excluded data, secrets, Power BI files and unrelated files, and reject mismatches before deployment.
- [x] 2.8 Deploy with protected target identity, target guard and permissions; verify target mismatch and unauthorized inputs stop before writes and deployment does not run workloads by default.
- [x] 2.9 Generate the developer checklist and separate deployment and verification results; verify an incomplete checklist is reported as pending and optional runtime execution requires explicit selection.

## 3. Protected release and integration

- [x] 3.1 Require verified DEV Fabric Git connection and baseline and consume the existing scope-aware branch guard; test invalid baseline and non-Fabric scope routing.
- [x] 3.2 Adapt TEST and PROD release pipelines to build once and consume the identical TEST-verified artifact under protected identity, approval and locking; test changed digest, failed TEST and missing approval.
- [x] 3.3 Support known-good artifact selection and protected recovery guidance; verify rollback preserves unrelated items and reports remaining managed items.
- [x] 3.4 Preserve the boundary for a future independently scoped Power BI bootstrap; verify a Power BI folder without its approved mapping does not create Fabric or Power BI deployment, and that the Fabric pipeline triggers and package exclude it.

## 4. Validate and roll out

- [x] 4.1 Run the focused reference-derived and plugin tests plus an end-to-end synthetic Fabric-folder adopter setup; report failures, skips and checks that did not access live services rather than expanding into a broad adapter test suite.
- [ ] 4.2 Install and test the relevant skills separately in Codex and Copilot using their supported workflows; record discovery, routing, source revision and unavailable tests.
- [ ] 4.3 If a live exercise is separately selected, verify target, permissions and protected resources, then retain redacted deployment and verification results; otherwise report live behavior as unverified.
- [x] 4.4 Validate OpenSpec and setup documentation against the delivered workflow, and verify existing user files and unrelated repository scope are preserved.
