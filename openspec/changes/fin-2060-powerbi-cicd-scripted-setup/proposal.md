## Why

`powerbi-cicd` still asks adopters and agents to assemble a hand-authored bootstrap JSON and manifest, then operate through a PowerShell mode switch. The completed `fabric-cicd` scripted setup proved a simpler fail-closed path: scripts discover non-secret values, render one review contract, bind approval to its content, and apply a fixed idempotent sequence. Power BI CI/CD now needs the same operator experience without losing its stricter Power BI item, dependency, binding, and protected-deployment safeguards.

## What Changes

- Add fixed `plan`, `approve`, and `apply` scripts for Power BI CI/CD setup. Plan performs read-only repository, Fabric, Power BI, `fab`, and Azure DevOps discovery and writes `cicd/powerbi/setup.yml` plus `cicd/powerbi/SETUP.md`.
- Generate the Power BI configuration, explicit managed-item manifest, per-environment semantic-model bindings, paginated-report bindings, substitutions, pipeline YAML, and validation/deployment assets from the approved setup instead of requiring adopters to maintain those files independently.
- Make approval content-bound by recording the SHA-256 of `setup.yml`; refuse approval while required values or blocking gaps remain, and refuse apply after an approved file changes.
- Make apply a fixed, resumable ordered sequence that generates files, reconciles supported Power BI environments and roles, checks protected identities and connection access, registers Azure DevOps resources, and reports the first failing step with a direct corrective action. Re-running completed steps is idempotent and never runs a workload.
- Preserve the existing Power BI release boundary: offline source validation, PBIP/PBIR/TMDL/RDL-only packaging, dependency-aware deployment, immutable TEST-verified promotion, isolated HOTFIX promotion, Windows protected jobs, runtime Key Vault retrieval, artifact hash verification, model-ownership transfer, live binding verification, drift blocking, and rollback through a known-good artifact.
- **BREAKING**: replace the `Initialize-PowerBiCicd.ps1` mode-based setup operator contract, `bootstrap-config.json`, and hand-authored `CICD-SETUP.json` approval flow with `plan.py`, `approve.py`, `apply.py`, `setup.yml`, and `SETUP.md`.
- Rewrite `SKILL.md` as a short numbered command workflow and add deterministic offline tests for planning, generated mappings, approval changes, idempotent apply steps, protected-resource readiness, missing Power BI bindings, and migration from the legacy inputs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `powerbi/cicd-lifecycle`: Power BI setup becomes a generated `plan -> review -> approve -> apply` workflow driven by one `setup.yml`; the Power BI-specific source manifest and release safeguards remain explicit and fail closed.

## Impact

- `plugins/powerbi/skills/powerbi-cicd/`: `SKILL.md`, setup scripts, lifecycle scripts, templates, migration handling, and tests.
- The legacy PowerShell bootstrap, bootstrap JSON template, separate rendered approval JSON, and setup/resume state path are retired or migrated by explicit compatibility handling.
- Existing `powerbi_cicd.py` and `deploy_adapter.py` release behavior remains the protected release engine; generated setup feeds its validated configuration and manifest rather than replacing it.
- Dependencies remain Python 3, `PyYAML`, `fab`, and authenticated developer `az` access for setup. Protected deployment keeps the existing pinned Power BI/Fabric deployment dependencies and secret boundary.
- Existing Power BI adopters must re-plan and review their mappings once; committed artifacts remain valid until they opt into the new setup flow.
