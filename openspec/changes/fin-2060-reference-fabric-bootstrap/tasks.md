## 1. Preserve the reference baseline

- [ ] 1.1 Capture the compatible UAT bootstrap, wrapper, manifest, pipeline, packaging, deployment, verification and dependency files from reference commit `4a77113ec051907c3e10e6da9d4a89e62bfb58ea`; document each required file and verify all referenced paths resolve.
- [ ] 1.2 Adapt the reference bootstrap tests to the plugin bundle and verify the reference behavior passes offline before functional generalization; distinguish mocked services from live evidence.
- [ ] 1.3 Assess the checkpoint only for specific missing functionality, document reused files and dependencies, and verify no helper is copied without a workflow consumer.

## 2. Generalize the connected UAT flow

- [ ] 2.1 Parameterize workspace, capacity, Lakehouse, source revision, managed items and dependencies, principal roles and Azure DevOps protected resources; verify different synthetic adopters have no reference IDs, names or secrets as defaults.
- [ ] 2.2 Preserve the reference YAML managed-item interface and adapt its configuration and validation; verify the reference-shaped manifest and missing or inconsistent input cases.
- [ ] 2.3 Provide one setup entry point for read-only plan and coordinated authorized apply, with status and resume; verify no writes on plan, target isolation, idempotent reuse and failure recovery.
- [ ] 2.4 Render compatible UAT pipeline and dependency files and generate `SETUP.md`; verify all rendered paths, inputs, permissions and commands resolve without the reference checkout.
- [ ] 2.5 Preserve useful reference source and secret checks inside the pipeline; verify file checks do not claim Fabric execution and no separate source-only pipeline is required.
- [ ] 2.6 Package only selected managed definitions and required deployment tooling from the exact revision; verify hashes, excluded data, secrets and unrelated files, and reject mismatches before deployment.
- [ ] 2.7 Deploy with protected target identity, target guard and permissions; verify target mismatch and unauthorized inputs stop before writes and deployment does not run workloads by default.
- [ ] 2.8 Generate the developer checklist and separate deployment and verification results; verify an incomplete checklist is reported as pending and optional runtime execution requires explicit selection.

## 3. Protected release and integration

- [ ] 3.1 Require verified DEV Fabric Git connection and baseline and consume the existing scope-aware branch guard; test invalid baseline and non-Fabric scope routing.
- [ ] 3.2 Adapt TEST and PROD release pipelines to build once and consume the identical TEST-verified artifact under protected identity, approval and locking; test changed digest, failed TEST and missing approval.
- [ ] 3.3 Support known-good artifact selection and protected recovery guidance; verify rollback preserves unrelated items and reports remaining managed items.
- [ ] 3.4 Preserve opt-in, independently scoped Power BI setup; verify a folder without an approved mapping does not create Fabric or Power BI deployment.

## 4. Validate and roll out

- [ ] 4.1 Run reference-derived and plugin tests plus an end-to-end synthetic adopter setup; report failures, skips and checks that did not access live services.
- [ ] 4.2 Install and test the relevant skills separately in Codex and Copilot using their supported workflows; record discovery, routing, source revision and unavailable tests.
- [ ] 4.3 If a live exercise is separately selected, verify target, permissions and protected resources, then retain redacted deployment and verification results; otherwise report live behavior as unverified.
- [ ] 4.4 Validate OpenSpec and setup documentation against the delivered workflow, and verify existing user files and unrelated repository scope are preserved.
