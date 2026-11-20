# Power BI CI/CD ownership inventory

## Source checkout

The deployment-template source is the local `Glasslake CICD` checkout at
`C:\Development\Glasslake CICD`, revision `22f3fd6e`
(`feature/FIN-1882-setup-ci-cd-for-glasslake`).  Its scripts are generalized
only through this skill's non-secret configuration and manifest contracts;
workspace names, model names, artifact names, runtime variable names, and
source roots are not reusable defaults.

| Retained dependency | Owner | Reused boundary |
| --- | --- | --- |
| Glasslake environment-bootstrap pattern | `powerbi-cicd` | Five ordered non-secret readiness gates and immutable promotion concepts only; no resource names, identities, or client code are copied. |
| Power BI project validation | `powerbi-report-authoring` | PBIP/PBIR structure; this skill owns only CI source-boundary orchestration. |
| Semantic-model changes | `semantic-model-authoring` | Model authoring and model-specific verification. |
| Paginated report validation | `paginated-report-authoring` | RDL structure and explicit data-source binding. |
| DAX tests | `dax-unit-testing` and `dax-test-framework` | Optional source-only DAX checks; no DAX runner is duplicated. |
| Branch/Jira routing | `jira-workflow` and `git-branch-guard` | Normal Jira-keyed feature/bugfix route for every Power BI CI/CD request. |
| Fabric lifecycle operator shape | `fabric-cicd` | Parameter vocabulary and plan/recovery terminology only. |

The retained set is deliberately small. `powerbi-cicd` owns Power BI source
mapping, dependency locks, artifacts, target guards, and release evidence.
`fabric-cicd` owns no Power BI deployment path; its legacy `pbi-assets.yml`
contract is a migration-only compatibility input.
