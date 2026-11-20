## Why

The `fabric-cicd` generator hard-codes DEV, TEST, PROD and HOTFIX in setup, generated YAML, release scripts, bindings and deployment guards. Adding UAT, GO-LIVE or TEST2 needs generator source changes, and regenerating a repository that already has a custom environment (such as the Analytics Reporting UAT) can overwrite it.

## What Changes

- **BREAKING**: replace the fixed environment constants and loops with a list of environment profiles in `setup.yml`. A v1 four-environment setup is translated automatically to explicit DEV/TEST/PROD/HOTFIX profiles with unchanged behavior.
- Adding an environment (UAT, GO-LIVE, TEST2) is a configuration entry plus regeneration. No generator or template edit.
- Each profile declares key, source branch, workspace, pipeline name and YAML path, protected environment, variable group, Key Vault credential reference, deploy enablement, optional manual-verification boundary, and for PROD-like profiles an explicit `accepts_from` list.
- Every profile uses the same immutable artifact, validation, deploy runner, target guard and evidence path. PROD accepts artifacts only from profiles it lists; no environment becomes a PROD source by name.
- Custom existing environments are imported by the agent: it reads the existing pipeline, YAML and target details and writes an equivalent profile entry into `setup.yml` so the environment fits the standard template. The agent creates a new target workspace, when needed, with existing Fabric skills (`fabric-cli`), not new generator code.
- Plan lists every existing `cicd/fabric` file that regeneration would overwrite and blocks on files it did not generate until the user acknowledges them.
- Generated `managed-items.yml` keeps the item `logical_id` so existing logical-ID binding checks continue to work.
- The generated release builder rejects the old `--uat-contract` and any runtime target override.
- Key Vault-only credentials and secretless validation are preserved; no fallback secret source.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `fabric/reference-cicd-bootstrap`: environments become configured profiles; PROD promotion sources are explicit; `logical_id` is preserved.

## Impact

- Affects `plugins/fabric/skills/fabric-cicd/` (plan/apply, pipeline rendering, bindings, release helpers, deploy runner, tests, `SKILL.md`).
- Existing four-environment repositories need a one-time reviewed v1 to v2 setup translation.
- Does not modify the Analytics Reporting repository, deploy workloads, change schedules or triggers, or read or write secret values.
- Out of scope: ad hoc target creation tooling, a UAT importer program, a legacy archive/move mechanism and a `--uat-contract` compatibility adapter.
