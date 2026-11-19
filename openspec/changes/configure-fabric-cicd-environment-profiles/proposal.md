## Why

The `fabric-cicd` generator currently hard-codes DEV, TEST, PROD and HOTFIX across setup, generated YAML, release scripts, bindings, deployment guards and evidence. Regenerating a consumer with an existing ad hoc environment such as UAT can overwrite that environment's setup or shared release tooling, while adding TEST2 or another stage requires generator source changes. The skill needs one configuration-driven environment profile model plus an agent-assisted setup path that can realize an ad hoc target, normalize it into that model and then use the normal build and deployment workflow.

## What Changes

- **BREAKING**: replace fixed environment constants, command options, loops and generated-schema assumptions with declared environment profiles in setup input and configuration.
- Add one canonical profile shape for persistent and ad hoc environments. A profile records the environment key/name, source branch or pattern, resolved workspace and capacity, pipeline/environment references, approved Key Vault credential source, bindings, verification requirements, promotion role and accepted artifact sources.
- Support ad hoc environment generation as a setup-time lifecycle: an agent or planner may inspect an existing custom setup or create/discover an isolated target, validate it, resolve workspace/Lakehouse/item IDs, and emit a complete canonical profile for review and approval.
- After approval, every profile uses the same immutable artifact, validation, deployment runner, target guard and release-evidence path. Runtime target selection remains fixed to the approved profile; artifacts do not carry arbitrary target-redirection contracts.
- Support adding profiles such as TEST2 or UAT through setup/configuration and generation only, including their own workspace, protected Azure DevOps environment, pipeline YAML, bindings, evidence and optional lifecycle/verification assets.
- Keep PROD fail-closed: artifacts are accepted only from explicitly configured promotion-source profiles and after source-branch, content digest, upstream evidence, revision and target-workspace checks pass. No environment becomes a PROD source by name or by default.
- Migrate existing ad hoc UAT behavior from the effective pipeline setup: review the registered/YAML pipeline contract, protected resources, fixed target and bindings, immutable artifact behavior, and verification requirements; convert those effective results into a canonical UAT profile; and block replacement when equivalence is not proven.
- After migration validation, move the old UAT generator, intermediate contracts/schemas, generator-specific tests, and superseded generated outputs together into an isolated archive directory. Active `cicd/fabric` generation, packaging and validation SHALL not discover or mix those archived files.
- Preserve secret safety: deployment credentials come only from approved Azure Key Vault-backed sources at runtime; validation and profile review remain secretless; generated files, artifacts and logs contain no secret values or fallback secret source.
- Preserve or generate managed-item `logical_id` metadata for existing Git logical-ID binding generation and repository compatibility, with an explicit migration and removal gate for any future replacement mechanism.
- Add regeneration compatibility checks and fail before overwrite when effective pipeline behavior or any active asset cannot be reconciled with the approved profiles and migration record.
- Extend offline coverage for legacy profiles, generated TEST2 and UAT profiles, invalid profiles and routing, PROD eligibility, digest/evidence failures, Key Vault enforcement, generated artifacts, ad hoc target realization, and binding metadata.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fabric/reference-cicd-bootstrap`: replace the fixed four-environment bootstrap with validated profiles, agent-assisted ad hoc environment realization, explicit promotion policy, safe regeneration and managed-item metadata compatibility.

## Impact

- Affects `plugins/fabric/skills/fabric-cicd/`, especially plan/import, approval, apply, ad hoc setup guidance, pipeline rendering, bindings, release-contract helpers, artifact validation/build selection, deployment routing and offline tests.
- Changes the reviewed `setup.yml`, generated `config.yml`, `managed-items.yml`, parameter and pipeline schemas. Existing four-environment repositories require a one-time profile migration; existing custom UAT consumers require a reviewed import into a fixed canonical UAT profile.
- Requires compatibility planning for the effective consumer pipeline setup and an isolated legacy archive. This change delivers only the generator, importer and archive tooling; the archive move happens in a consumer repository only when that consumer runs and approves its own migration apply. This change does not modify the Analytics Reporting consumer repository.
- Does not deploy workloads, change customer Fabric definitions or data, create schedule/trigger changes, or read, write, reveal or migrate secret values.
