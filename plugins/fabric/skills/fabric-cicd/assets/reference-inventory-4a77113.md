# Analytics Reporting UAT reference inventory

Reference snapshot: `4a77113ec051907c3e10e6da9d4a89e62bfb58ea` from the connected Analytics Reporting checkout. This inventory is provenance, not a runtime dependency. It deliberately excludes the reference's tenant IDs, workspace IDs, display names, principal IDs, variable-group names and secrets.

| Reference file | Connected consumers | Bootstrap disposition |
| --- | --- | --- |
| `cicd/create_uat.ps1` | `uat_bootstrap.py` | Preserve the PowerShell operator shape as `Initialize-FabricCicd.ps1`; explicit configuration replaces every default. |
| `cicd/managed-items.yml` | `validate.py`, packaging and deployment | Preserve its `source_root`, `managed_items`, `dependencies` and `excluded` interface; validate it with the focused bootstrap helper. |
| `cicd/parameter.yml` and `config.yml` | `build_release.py`, deployment | Replace with one non-secret JSON target configuration plus the managed-item mapping. |
| `cicd/fabric-uat.yml` | `validation-steps.yml`, release scripts | Render a manual UAT template with an explicit target profile; it never changes TEST or PROD mappings. |
| `cicd/fabric-test.yml` | `validation-steps.yml`, release scripts | Render a DEV-branch-triggered TEST pipeline that builds and publishes one immutable artifact. |
| `cicd/fabric-prod.yml` | `validation-steps.yml`, release scripts | Render a PROD-branch-triggered pipeline that consumes the TEST pipeline artifact and verifies its source digest before deployment. |
| `cicd/validation-steps.yml`, `validate.py`, `secret_scan.py` | all Fabric YAML | Replace with one focused validation template and source/package checks. File checks are not runtime evidence. |
| `cicd/build_release.py`, `release_contract.py`, `compare_release.py` | TEST, PROD and UAT YAML | Replace with the focused `bootstrap.py` package and release-gate commands; it packages only selected Fabric definitions and CI tooling. |
| `cicd/deploy_artifact.py`, `deploy_runner.py`, `auth_check.py`, `record_release.py` | protected deployment jobs | Replace with the PowerShell entry point's explicit `fab` deployment mode and redacted release evidence; no generic REST adapter is carried forward. |
| `cicd/post_deploy_check.py`, `run_uat_runtime.py` | optional verification | Generate a manual checklist and leave workload execution opt-in. |
| `cicd/test_uat_bootstrap.py` | reference UAT bootstrap | Adapt only focused offline cases for config, manifest, plan-without-writes, path scope, package digest and promotion gate. |

The reference contains YAML but does not provision Azure Pipelines definitions through `az`. The generalized setup registers only the explicitly configured TEST and PROD YAML definitions after their files are committed to the configured Azure Repos branches. A configured UAT profile renders a manual template and is not a PROD promotion source.

## Retained helper assessment

The archived `FIN-2060-lifecycle-attempt` is not imported wholesale. The only candidate concepts are its reference inventory and generated-asset/documentation approach. `bootstrap.py` is the workflow consumer for the compact validator, package manifest and documentation renderer; `Initialize-FabricCicd.ps1` is the workflow consumer for `fab` and `az` operations. No Python Fabric or Azure DevOps REST client is reused.
