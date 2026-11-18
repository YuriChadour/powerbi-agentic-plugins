## 1. Setup Contract And Read-Only Planning

- [x] 1.1 Add the versioned Power BI `setup.yml` schema and deterministic serialization helpers; verify schema tests reject unsupported, duplicate, secret-bearing, incomplete, and target-inconsistent values.
- [x] 1.2 Add local PBIP/PBIR/TMDL/RDL source discovery and managed-item extraction; verify synthetic fixtures produce stable item IDs, dependency order, report model edges, RDL bindings, exclusions, and blocking errors for unsupported or ambiguous sources.
- [x] 1.3 Add read-only `fab`, Power BI, and `az` discovery through narrow adapters for workspaces, capacities, items, connections, identities, variable groups, private pools, Key Vault endpoints, environments, and pipelines; verify fake-tool tests make no write calls and turn lookup failures into named questions.
- [x] 1.4 Implement `plan.py` with terminal and `--no-prompt`/`--answer` behavior; verify repeat runs are byte-identical and unanswered inputs produce the expected exit code, question keys, `setup.yml`, and `SETUP.md` without external writes.
- [x] 1.5 Render discovered, assumed, user-supplied, generated, and blocking values into `SETUP.md`; verify the review fixture contains every planned action and prerequisite while secret candidate tests never appear.

## 2. Approval, Generation, And Idempotent Apply

- [x] 2.1 Implement `approve.py` and the `setup.approved` hash record; verify gaps block approval, valid approval succeeds, and one-byte setup changes invalidate the approval before any fake external call.
- [x] 2.2 Generate compatibility configuration, Power BI manifest, per-environment semantic-model bindings, RDL bindings, substitutions, pipeline YAML, and packaged helpers from `setup.yml`; verify two identical setups produce identical files, all generated inputs pass the existing validators, and substitution rule order, path or glob, exact find text, and string replacement values are preserved without normalization, sorting, coercion, or inference.
- [x] 2.3 Add explicit DEV, TEST, PROD, HOTFIX, and optional target entries to generated configuration and protected-resource maps; verify HOTFIX has its own workspace, identity, guard, and access values while semantic-model bindings and substitutions resolve through PROD and package and promotion behavior uses the existing HOTFIX policy.
- [x] 2.4 Implement `apply.py` generation and workspace steps; verify missing approval blocks all writes, approved apply creates or reuses only reviewed targets, reconciles direct roles idempotently, keeps deployment targets Git-disconnected, and never runs a workload.
- [x] 2.5 Implement apply identity and connection steps; verify service-principal and connection access mismatches, missing model target connections, personal-cloud connections, and unauthorized pipeline invocation identities stop before the affected write with the named resource.
- [x] 2.6 Implement apply Azure DevOps and protected-resource steps; verify variable-group identity checks, private-pool checks, WIF Key Vault endpoint authorization, environment creation, named pipeline registration, and pipeline permission scopes are idempotent and secretless.
- [x] 2.7 Emit non-secret apply/readiness evidence with completed and blocked step results; verify rerun after a fake failure continues from current external state without a separate hidden progress state machine.

## 3. Preserve Release And HOTFIX Behavior

- [ ] 3.1 Adapt `powerbi_cicd.py` and `deploy_adapter.py` validation to consume generated config and manifest values without changing immutable artifact structure; verify all existing Power BI lifecycle tests pass against generated fixtures.
- [ ] 3.2 Extend HOTFIX setup validation and release fixtures without replacing existing HOTFIX artifact resolution; verify HOTFIX cannot target TEST or PROD, PROD requires the successful HOTFIX artifact after merge, and a missing validated build blocks before a workspace write.
- [ ] 3.3 Verify generated Power BI pipelines retain offline PR/build validation, packaged pinned helpers, archive member/hash checks, protected Windows execution, runtime WIF Key Vault retrieval, target guards, dependency-aware deployment, evidence, and rollback; add one template-level test for each behavior if existing coverage is absent, including an assertion that successful `deploy_artifact.py` verification is followed by invocation of packaged `deploy_fabric.py` with authenticated read-only inventory.
- [ ] 3.4 Add round-trip tests for semantic-model ownership transfer, source-connection verification, RDL data-source binding, substitutions, artifact drift, and release-file drift using generated files; verify ordered substitutions change only the extracted staging payload consumed by the adapter, leave repository source and immutable ZIP bytes unchanged, record resolved values, and fail before a workspace write for a missing environment value, unmatched path or glob, or absent exact find text.
- [ ] 3.5 Add a complete content-environment matrix for DEV, TEST, PROD, HOTFIX, UAT, and REHEARSAL; verify same-named targets use their own binding and substitution values, HOTFIX uses PROD values without a HOTFIX value, and target-specific workspace, identity, guard, and protected-resource selection remains isolated.

## 4. Legacy Migration And Skill Surface

- [ ] 4.1 Add optional migration of legacy `bootstrap-config.json` and Power BI manifest inputs into `setup.yml`; verify valid values import, conflicts become gaps, secret-bearing values block, legacy files remain unchanged, generated release files are untouched during plan, and legacy substitution rules retain their original order and exact string values including numeric-looking, Boolean-looking, quoted, multiline, and special-character content.
- [ ] 4.2 Compare generated artifacts from at least two synthetic legacy-adopter fixtures with their reviewed legacy artifacts; verify managed items, dependency order, bindings, and substitutions are semantically identical rule-for-rule and that only documented setup-contract and HOTFIX-target differences remain.
- [ ] 4.3 Rewrite `SKILL.md` as the ordered plan, review, approve, apply, commit, and PR command list; verify the installed command paths resolve and script failures instruct the operator to stop.
- [ ] 4.4 Retire `Initialize-PowerBiCicd.ps1`, the bootstrap JSON template, and hand-edited `CICD-SETUP.json` approval handling after migration tests pass; verify installer, catalog, and harness projections package the new scripts and do not expose the retired operator path.
- [ ] 4.5 Add focused migration and user documentation for the one-time re-plan requirement and rollback to the previous installed skill; verify all affected paths and generated-file locations exist.

## 5. End-To-End Verification

- [ ] 5.1 Run the Power BI CI/CD unit suite and OpenSpec strict validation; verify all tests and `openspec validate fin-2060-powerbi-cicd-scripted-setup --strict` pass.
- [ ] 5.2 Exercise plan, approve, and apply once against a fully synthetic PBIP/PBIR/TMDL/RDL repository and fake external tool layer; verify deterministic files, hash invalidation, blocked-gap behavior, idempotent rerun, no setup-time deployment workload, and generated release assets that execute staged-only parameter replacement through the packaged adapter in a simulated protected deployment.
- [ ] 5.3 Exercise the numbered workflow from installed Copilot and Codex copies on a small synthetic model; verify equivalent routing and report any unavailable harness as unverified rather than passed.
- [ ] 5.4 Run installer/catalog validation and record the final `openspec status`; verify all required planning artifacts are complete and no project implementation was performed during proposal creation.
