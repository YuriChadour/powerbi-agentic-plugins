## 1. Profile Schema And Legacy Translation

- [ ] 1.1 Add a versioned profile model and strict normalization/validation for profile key/name, lifecycle, source branch or pattern, resolved workspace/capacity, Azure DevOps pipeline/environment, Key Vault credential source, variable group, private pool, bindings, verification, deploy enablement, promotion role/evidence and promotion-source fields (role-enforced: only `production` may accept sources); verify valid fixtures normalize deterministically, each invalid field fails with a profile-specific message, and keys or values containing YAML/PowerShell metacharacters are rejected.
- [ ] 1.2 Replace `ENVIRONMENTS` and fixed plan/apply argument loops with profile iteration and profile-aware CLI/config input; verify a complete TEST2 profile is accepted without a Python source or YAML-template edit.
- [ ] 1.3 Implement the deterministic v1 four-environment adapter to explicit DEV/TEST/PROD/HOTFIX profiles, including legacy PROD sources TEST and HOTFIX, and verify the translated setup preserves every legacy branch, workspace, pipeline, environment and credential reference.
- [ ] 1.4 Add an ad hoc profile realization/import input that can inspect effective registered/YAML pipeline setup, discover an existing target during read-only plan, and create a target only in a separate realization step after approval of a plan listing every resource to create; resolve workspace/Lakehouse/item identities and emit unresolved gaps plus a canonical profile for a second approval; verify plan performs no write, the old generator implementation is not treated as a contract, no secret is read, and resolved identities are revalidated before approval.
- [ ] 1.5 Add duplicate/ambiguous profile-key, branch-route, pipeline-path, protected-environment and workspace ownership validation; verify duplicate and conflicting fixtures are rejected before write or external action.
- [ ] 1.6 Add a mixed/unsupported schema-version guard and a rendered migration record containing source version, target version, translation, compatibility inventory and rollback reference; verify mixed or unapproved migration input is rejected clearly; record the v1 removal exit criterion (all adopters approved or opted out and suite passing with v1 reading disabled).

## 2. Generation And Safe Regeneration

- [ ] 2.1 Add an effective pipeline/output inventory and classify active `cicd/fabric` files as regenerated, retained-active, shared-incompatible or legacy-archive; verify the complete archive bundle and `archive/cicd/fabric/<migration-id>/` destination are rendered deterministically.
- [ ] 2.2 Recompute and enforce the approved inventory in apply, refusing stale approval or repository drift before replacing or moving files; verify an omitted effective UAT route, profile behavior or archive member blocks without changing active files.
- [ ] 2.3 Replace fixed generated `config.yml` workspace keys and rendering inputs with a profile registry while retaining a v1 reader for the migration window; verify generated configuration validates for legacy, TEST2 and UAT fixtures.
- [ ] 2.4 Replace named pipeline rendering loops with one generic profile renderer that uses each profile's pipeline path, branch, protected environment, fixed workspace, Key Vault source and promotion policy; verify TEST2 and realized UAT generation changes only setup-derived values.
- [ ] 2.5 Render SETUP.md with profile lifecycle, route, resolved target, promotion eligibility, evidence, secret source, migration/asset decisions and rollback instructions; verify unresolved or incompatible profiles block approval with actionable messages.
- [ ] 2.6 Preserve legacy pipeline filenames and profile CLI targets through translated profiles while versioning new generated files; verify the existing DEV/TEST/PROD/HOTFIX topology renders equivalently.

## 3. Binding And Managed-Item Compatibility

- [ ] 3.1 Change binding generation to derive replacement-value keys from the approved profile set; verify TEST2 receives every applicable workspace, item, SQL endpoint and connection binding without a template edit.
- [ ] 3.2 Add `id`, normalized `logical_id`, `name`, folder, type and dependency metadata to generated `managed-items.yml`; verify discovered Fabric Git logical IDs are preserved for Lakehouses, notebooks, pipelines and Copy Jobs.
- [ ] 3.3 Backfill legacy missing logical IDs through read-only DEV item and `.platform` discovery, retaining direct/logical/endpoint aliases; verify unresolved required mappings fail instead of being guessed.
- [ ] 3.4 Materialize ad hoc UAT and Lakehouse/item binding results into the approved profile before artifact generation; verify runtime target overrides are rejected and profile identity drift triggers regeneration and re-approval.
- [ ] 3.5 Add managed-item and binding compatibility tests for current direct IDs, Fabric Git logical IDs, reversed IDs, SQL endpoints, pipeline connections, Copy Jobs and a legacy manifest missing `logical_id`; verify the new generation repairs or blocks each supported case deterministically.
- [ ] 3.6 Add a removal gate for any future logical-ID replacement requiring equivalent dual-form emission, consumer-test evidence and explicit migration; verify tests reject a migration that drops `logical_id` without that evidence.

## 4. Artifact And Runtime Profile Resolution

- [ ] 4.1 Add a shared profile loader and replace fixed environment allow-lists in release, build, validation, deployment, comparison and release-recording helpers; verify every runtime command resolves declared profile keys from approved generated configuration.
- [ ] 4.2 Change `build_release.py` target validation from fixed `choices` to approved profile lookup and include profile key, lifecycle, fixed target digest, branch, revision, required evidence and source hashes in release metadata; verify DEV/TEST/PROD/HOTFIX, TEST2 and UAT artifacts build through the same path for equivalent content.
- [ ] 4.3 Make the generated `build_release.py` reject `--uat-contract` and any runtime target-contract input with a clear error, and have the importer preserve the existing UAT pipeline name and YAML path by default (listing any change as a manual reconciliation step in the migration record); verify a stale `--uat-contract` invocation fails before packaging and no adapter is generated.
- [ ] 4.4 Implement canonical UAT profile generation from realized/imported target data, including fixed workspace, capacity, Lakehouse, managed-item scope and binding values; verify stale source, unresolved target, incomplete fields and unapproved identity drift fail before deployment.
- [ ] 4.5 Make the deployment runner resolve every target from the approved fixed profile mapping and check target identity plus binding digest before any Fabric write; verify cross-profile, contract-file and workspace-override attempts fail.
- [ ] 4.6 Separate deployment evidence from UAT runtime/manual verification evidence in release recording and make generated records report deployment success plus verification pending until explicitly completed; verify deployment alone cannot mark UAT verification complete.

## 5. Routing, Artifact Selection And PROD Promotion

- [ ] 5.1 Replace hard-coded branch-to-environment logic with profile route matching and reject unknown or ambiguous routes; verify legacy branches, TEST2 and a UAT queue source each resolve exactly once.
- [ ] 5.2 Make PROD-like artifact selection consume only explicit `promotion.accepts_from` profile edges and resolve the source profile, source branch, exact revision and eligible pipeline from approved configuration; verify TEST2 is rejected unless PROD explicitly lists it.
- [ ] 5.3 Validate successful upstream evidence, required evidence types, source revision, artifact digest, member hashes and managed-content equivalence before production target selection; verify any evidence or digest mismatch fails before target write.
- [ ] 5.4 Preserve HOTFIX-as-an-explicit-source behavior through translated legacy policy and forward-port/runbook rendering from profile topology; verify a nonmatching cherry-pick route and undeclared HOTFIX source are rejected.
- [ ] 5.5 Add release-selection tests for TEST, TEST2, HOTFIX, UAT-ineligible-by-default and unknown branches; verify the selected artifact always matches the source profile's pipeline, revision and accepted-source policy.

## 6. Secret Safety And Protected Jobs

- [ ] 6.1 Generate protected jobs with the profile's approved WIF Key Vault service connection, vault and secret reference and keep validation/build jobs secretless; verify generated YAML and setup artifacts contain references only, never secret values.
- [ ] 6.2 Remove all runtime credential fallback paths from protected deployment, including variable-group client secrets, unapproved environment variables, developer credentials and interactive discovery; verify missing Key Vault access or secret retrieval fails before identity use or Fabric write.
- [ ] 6.3 Validate each pipeline's authorization only for its own protected environment, queue, Key Vault endpoint and approved variable group; verify cross-profile authorization reuse is rejected and a missing permission names the profile and resource.
- [ ] 6.4 Extend secret scanning to profile-bearing setup, generated YAML, manifests and artifacts; verify representative secret values fail scanning while Key Vault and secret-reference names remain permitted.

## 7. Effective Pipeline Migration And UAT Archive

- [ ] 7.1 Add an imported/generated UAT profile fixture from effective pipeline setup and generate its normal pipeline, immutable artifact and fixed target mappings; verify the generic `--target UAT` path uses approved workspace/Lakehouse bindings and UAT-specific evidence.
- [ ] 7.2 Add a compatibility harness that compares existing and regenerated registered/YAML pipeline behavior, protected resource references, target/binding rules, artifact checks, evidence and manual-verification boundary; verify a mismatch blocks generation and active-file movement.
- [ ] 7.3 Add an all-or-nothing archive manifest and move operation for `uat_bootstrap.py`, old target contracts/schemas, generator-specific tests, obsolete UAT pipeline/config overlays and superseded generated outputs; verify they move together to `archive/cicd/fabric/<migration-id>/` and no legacy file remains duplicated in an active path; the move is performed by the generator in a consumer repository only at that consumer's own approved apply, using fixture repositories here.
- [ ] 7.4 Configure every active source scan, unittest discovery, package builder, secret scan and generated-file reconciler to exclude `archive/cicd/fabric/`; verify archived `.py`, YAML, schema and generated files cannot affect active behavior.
- [ ] 7.5 Add archive rollback coverage that restores the complete bundle to the prior active paths if validation or apply fails; verify no partial bundle state or mixed active/archive implementation is accepted.
- [ ] 7.6 Add a repository fixture with logical-ID-dependent binding validation and a current four-profile manifest; verify regenerated output adds metadata, preserves effective pipeline behavior and passes compatibility checks without modifying the consumer repository.

## 8. Offline Regression And Validation Matrix

- [ ] 8.1 Add deterministic secretless fixtures for legacy DEV/TEST/PROD/HOTFIX, TEST2 and imported/generated UAT profiles; verify plan, ad hoc realization, generation, validation, artifact build and runner preflight use the same canonical path.
- [ ] 8.2 Add invalid-profile cases for missing route/workspace/pipeline/protected environment/credential source/evidence/promotion policy, invalid duplicate key, invalid PROD source, unresolved binding and unapproved target change; verify every case fails before write with an actionable field-level error.
- [ ] 8.3 Add routing cases for unsupported and ambiguous branches, cross-profile pipeline triggers and unsupported promotion sources; verify no candidate artifact is selected for invalid routes.
- [ ] 8.4 Add digest and evidence cases for modified archive members, source-content mismatch, revision mismatch, missing/failed upstream evidence, and ambiguous source build (including multiple successful builds for the same revision); verify every case blocks before any protected write.
- [ ] 8.5 Add Key Vault and fallback cases for missing service connection, vault, secret reference, pipeline authorization and variable-group-only secret availability; verify no fallback is attempted and no Fabric API write method is called.
- [ ] 8.6 Add canonical artifact/deployment validation tests for every profile, including fixed workspace mismatch, ad hoc realization drift, runtime target override, stale `--uat-contract` input, managed-scope mismatch and UAT manual-verification boundary; verify each failure occurs before a protected write.
- [ ] 8.7 Extend existing Fabric CI/CD tests so the full offline suite covers the validation matrix in design and the prior FIN-2101 regressions; verify `py -3 -B -m unittest discover plugins/fabric/skills/fabric-cicd/tests` passes.

## 9. Documentation, Rollout And Evidence

- [ ] 9.1 Rewrite `SKILL.md` as the profile-aware plan/realize -> review -> approve -> apply command flow and document persistent, ad hoc and legacy migration inputs; verify no fixed-environment setup wording remains outside the explicit backward-compatibility section.
- [ ] 9.2 Update generated SETUP.md guidance and repository docs for TEST2/UAT configuration-only additions, ad hoc target realization, UAT contract-to-profile import, explicit PROD source policy, logical-ID compatibility, regeneration blocking and rollback; verify all links and documented commands resolve.
- [ ] 9.3 Add migration validation that compares generated legacy assets before/after v1-to-v2 normalization and records expected profile-only schema changes; verify no routing, workspace, secret source or artifact-promotion behavior changes silently.
- [ ] 9.4 Run strict OpenSpec and offline compatibility validation, capture the generated test/asset-diff evidence and mark live Fabric/Azure DevOps/UAT execution as not performed by this change; verify planning artifacts do not claim deployment or runtime verification.
- [ ] 9.5 Verify rollback fixtures restore the prior active files, the complete archived legacy bundle and approval metadata without partial archive mixing or destructive Fabric/customer-data actions; verify the rollback record names any external authorization that requires manual reconciliation.
