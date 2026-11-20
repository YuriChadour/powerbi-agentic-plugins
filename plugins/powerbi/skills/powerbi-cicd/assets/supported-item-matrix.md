# Supported Power BI deployment matrix

`powerbi-cicd` uses the Microsoft `fabric-cicd` Python package as its only
deployment adapter. It does not fall back to a generic REST client, `fab
import`, or developer credentials.

| Source item family | Approved operation | Read-only reference evidence | Status when unavailable |
| --- | --- | --- | --- |
| TMDL/PBIP semantic model | `fabric_cicd.deploy_with_config` with `SemanticModel` in `item_types_in_scope` | Glasslake `config.yml` and `scripts/deploy_fabric.py`; `fabric-cicd` 1.3.0 TEST `--dry-run` accepted the source and parameter contract | Block before target write |
| PBIR report | `fabric_cicd.deploy_with_config` with `Report` in `item_types_in_scope` | Same versioned Glasslake dry run and approved source boundary | Block before target write |
| Paginated RDL report | `fabric_cicd.deploy_with_config` with `PaginatedReport` in `item_types_in_scope` | Same versioned Glasslake dry run; an explicit binding remains required by this lifecycle | Block before target write |

The reference dry run resolves the repository, source directory, parameter
file, environment mapping, and item-type contract. It does not authenticate,
call a workspace, or prove a particular target identity. Therefore a target
without successful authenticated read-only preflight remains `unverified` and
the protected deployment path refuses to write. Other Power BI item types are
unsupported classifications until this matrix is deliberately extended and
tested.

The reference establishes the reusable adapter interface without importing
Glasslake identifiers, service-principal values, Key Vault names, or target
workspace IDs into this skill.
