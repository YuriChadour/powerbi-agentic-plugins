# Reference asset inventory

Reference: Analytics Reporting, commit `db118e88dff09f5c422a4351eeb024d8ba539cf0`, tracked `cicd/` files. This is provenance only; the installed bundle must not depend on the reference checkout.

| Reference file | Planned disposition |
| --- | --- |
| `cicd/README.md` | Adapt as generic operator guidance; omit project-specific records. |
| `cicd/auth_check.py` | Port and generalize; validate against lifecycle security and target contracts. |
| `cicd/branch-policies.md` | Adapt as generic operator guidance; omit project-specific records. |
| `cicd/build_release.py` | Port and generalize; validate against lifecycle security and target contracts. |
| `cicd/config.yml` | Parameterize as adopter configuration; require explicit mappings. |
| `cicd/deploy_artifact.py` | Port and generalize; validate against lifecycle security and target contracts. |
| `cicd/deploy_runner.py` | Port and generalize; validate against lifecycle security and target contracts. |
| `cicd/dev_drift_gate.py` | Not applicable; do not generate a mandatory drift gate. |
| `cicd/fabric-dev.yml` | Adapt into the TEST wrapper; do not generate a DEV deployment wrapper. |
| `cicd/fabric-prod.yml` | Parameterize as compatible validation or protected release pipeline. |
| `cicd/fabric-release-stages.yml` | Parameterize as compatible validation or protected release pipeline. |
| `cicd/fabric-validation.yml` | Parameterize as compatible validation or protected release pipeline. |
| `cicd/keyvault-connectivity-test.yml` | Parameterize as an optional protected-resource connectivity example. |
| `cicd/managed-items.yml` | Parameterize as adopter configuration; require explicit mappings. |
| `cicd/parameter.yml` | Parameterize as adopter configuration; require explicit mappings. |
| `cicd/pbi-assets.yml` | Parameterize as adopter configuration; require explicit mappings. |
| `cicd/post_deploy_check.py` | Port and generalize; validate against lifecycle security and target contracts. |
| `cicd/powerbi-prod.yml` | Parameterize as independently scoped optional Power BI asset. |
| `cicd/powerbi-validation-steps.yml` | Parameterize as independently scoped optional Power BI asset. |
| `cicd/powerbi-validation.yml` | Parameterize as independently scoped optional Power BI asset. |
| `cicd/record_release.py` | Port and generalize; validate against lifecycle security and target contracts. |
| `cicd/requirements-fabric-cicd.lock` | Review and port as versioned dependency input. |
| `cicd/requirements-fabric-cicd.txt` | Review and port as versioned dependency input. |
| `cicd/secret_scan.py` | Port and generalize; validate against lifecycle security and target contracts. |
| `cicd/validate.py` | Port and generalize; validate against lifecycle security and target contracts. |
| `cicd/validate_config.py` | Port and generalize; validate against lifecycle security and target contracts. |
| `cicd/validate_powerbi.py` | Port and generalize; validate against lifecycle security and target contracts. |
| `cicd/validation-steps.yml` | Parameterize as compatible validation or protected release pipeline. |
| `cicd/verify_deployment.py` | Port and generalize; validate against lifecycle security and target contracts. |
