## 1. Profile Model

- [x] 1.1 Add a versioned profile model with strict validation (key pattern, branch, workspace/capacity, pipeline name and YAML path, protected environment, variable group, private agent pool, Key Vault reference, `deploy.enabled`, `verification.manual_boundary`, `promotion.accepts_from`); verify valid fixtures normalize deterministically and each invalid field or metacharacter fails with a profile-specific message.
- [x] 1.2 Replace `ENVIRONMENTS` and fixed plan/apply loops with profile iteration; grant pipeline invocation connection owners Contributor in every configured workspace unless they already have Contributor or higher; verify a complete TEST2, UAT or GO-LIVE profile is accepted without a Python or template edit and receives the grant when needed.
- [x] 1.3 Add the deterministic v1 four-environment translator (PROD `accepts_from: [TEST, HOTFIX]`); verify branches, workspaces, pipeline names and paths, environments, private agent pools and credential references are preserved.
- [x] 1.4 Reject duplicate or conflicting profile keys, branch routes, pipeline paths, protected environments and workspace ownership before any write; verify with conflicting fixtures.

## 2. Generation

- [x] 2.1 Replace named pipeline loops and fixed `config.yml` and binding keys with one generic renderer driven by the profile list, keeping legacy filenames for translated profiles; verify every generated deployment pipeline uses its profile's private agent pool, DEV/TEST/PROD/HOTFIX render equivalently and TEST2 receives its workspace, item, SQL endpoint and connection bindings.
- [x] 2.2 Render SETUP.md with each profile's route, target, credential reference, promotion sources and verification boundary, and list every existing `cicd/fabric` file regeneration would overwrite; verify files the generator did not create block apply until acknowledged and that a changed setup after approval blocks apply.

## 3. Managed-Item Metadata

- [x] 3.1 Emit normalized `logical_id` in `managed-items.yml`, backfilling from read-only DEV item and `.platform` discovery; verify direct, logical, reversed and SQL endpoint IDs, pipeline connections and Copy Jobs bind correctly and an unresolved required value fails instead of being guessed.

## 4. Runtime

- [x] 4.1 Add a shared profile loader and replace environment allow-lists in release, build, validation, deploy and selection helpers; make `build_release.py --target` accept any configured profile and reject `--uat-contract` or any runtime target override before packaging.
- [x] 4.2 Make the deploy runner resolve the target from the approved fixed profile and verify workspace identity before any Fabric write; verify cross-profile and override attempts fail.
- [x] 4.3 Report deployment success plus verification pending for profiles with `manual_boundary`; verify deployment alone never marks verification complete.

## 5. Routing And Promotion

- [x] 5.1 Route source branches to exactly one profile and reject unknown or ambiguous routes; verify legacy branches, TEST2 and UAT each resolve once.
- [x] 5.2 Make PROD-like selection use only `promotion.accepts_from`, and validate source branch, exact revision, upstream evidence, artifact and member digests and target workspace before any write; verify TEST2 or UAT is rejected unless explicitly listed, and missing, failed or ambiguous evidence blocks.

## 6. Secrets

- [x] 6.1 Generate protected jobs from each profile's Key Vault reference with no variable-group or environment-variable fallback, keeping validation and build secretless; verify missing Key Vault access fails before any Fabric write and secret scanning covers setup, YAML and manifests.

## 7. Agent Flow And Docs

- [x] 7.1 Rewrite `SKILL.md` as a profile-aware plan -> review -> approve -> apply flow, including the agent steps to import an existing custom environment as a profile and to create a new target with `fabric-cli`; verify no fixed-environment wording remains outside the v1 compatibility note.
- [x] 7.2 Document adding UAT or GO-LIVE as a config entry, explicit PROD sources and the v1 removal exit criterion; verify documented commands resolve.

## 8. Tests

- [x] 8.1 Add offline, secretless fixtures for legacy four profiles, a TEST2 profile, a UAT profile and a GO-LIVE profile through plan, generation, artifact build and runner preflight, plus negative cases for invalid profiles, routing, promotion source, digest or evidence mismatch and Key Vault failure; verify each failure occurs before a Fabric write.
- [x] 8.2 Run `py -3 -B -m unittest discover plugins/fabric/skills/fabric-cicd/tests` and strict OpenSpec validation; record that no live Fabric or Azure DevOps execution was performed.
