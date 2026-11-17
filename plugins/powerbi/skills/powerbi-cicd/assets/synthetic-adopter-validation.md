# Synthetic adopter validation record

The focused `test_powerbi_cicd.py` suite exercises a temporary, synthetic
PBIP/TMDL/RDL repository and does not authenticate to Fabric or Azure DevOps.

| Lifecycle check | Evidence |
| --- | --- |
| Offline validation, plan, and immutable packaging | `test_valid_source_orders_model_before_dependents`, `test_package_and_promotion_digest_gate` |
| DEV/TEST/PROD artifact gates and target protections | `test_adapter_preflight_blocks_before_write_and_verifies_read_only_inventory`, `test_artifact_tampering_stops_before_a_write` |
| Optional target contracts and substitutions | `test_required_and_optional_target_profiles_are_unambiguous`, `test_substitutions_are_target_complete_and_only_apply_to_staged_payload` |
| HOTFIX source selection and failed-validation block | `test_hotfix_resolution_requires_successful_hotfix_validation` |
| External RDL binding and semantic-model connection simulation | `test_adapter_preflight_blocks_before_write_and_verifies_read_only_inventory` |
| Drift, unmanaged-item preservation, and protected recovery path | `test_adapter_preflight_blocks_before_write_and_verifies_read_only_inventory` |
| Exclusion of unrelated files, Fabric content, and credentials | `test_package_and_promotion_digest_gate`, `test_source_blocks_escaped_path_and_committed_secret` |

Live workspace deployment, Azure DevOps branch-policy execution, and tenant
identity checks remain unverified until an adopter supplies approved targets.
