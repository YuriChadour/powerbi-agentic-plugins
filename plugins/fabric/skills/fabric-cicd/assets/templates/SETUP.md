# Fabric CI/CD bootstrap

This starter manages the configured Fabric source folder only. It does not configure Power BI CI/CD, copy data rows, schedules, credentials, or workspace items outside `managed-items.yml`.

## Developer setup identity

The person running `Initialize-FabricCicd.ps1` performs every setup action using their own existing sessions:

```powershell
fab auth status
az account show
az extension show --name azure-devops
```

The developer must have permission to create or reuse the selected Fabric workspace, read and assign only the configured direct workspace roles, and create/read the named Azure Pipeline definitions. The setup script accepts no access token, client secret, or service-principal credential. TEST and PROD deployment credentials belong only to their protected pipeline environments and variable groups.

## Render, review, commit, then register

1. Copy `bootstrap-config.json` and `managed-items.yml` to the configured CI folder and replace every `REPLACE_*` value with approved non-secret values.
2. Declare the existing DEV workspace name and ID, the Fabric source folder, target workspaces, explicit object-ID role mappings, Azure Repos binding, pipeline names and protected-resource references. Apply verifies the DEV Fabric Git connection and committed Fabric-folder baseline before any target write.
3. Render the YAML and helper files with the installed skill's `Initialize-FabricCicd.ps1 -Mode Render`; inspect the local diff.
4. Commit the CI YAML and configuration to the configured DEV and PROD branches. The setup script refuses to register a pipeline whose YAML is not present on its configured branch.
5. Run `-Mode Plan` to validate inputs without local or remote writes, then run `-Mode Apply` to reconcile the selected workspace roles and create missing named pipelines.

`fabric-test.yml` triggers on configured Fabric/CI folder changes in the DEV branch, creates one immutable artifact and deploys it to TEST. `fabric-prod.yml` triggers only from the PROD branch, downloads the TEST pipeline artifact and rejects it if the current PROD Fabric-folder digest differs. UAT remains an explicit manual pipeline and cannot supply PROD promotion evidence.

## Verification and recovery

Definition deployment and workload execution are separate. A successful deployment leaves runtime verification pending until the developer records the generated checklist. Do not enable runtime jobs or schedules as part of setup. `-Mode Status` displays the last redacted setup state and `-Mode Resume` revalidates the same approved configuration before continuing.

For protected recovery, select a previously retained immutable TEST artifact and
run the same protected target deployment with that artifact path. The deployment
imports only folders selected in `managed-items.yml`; it does not delete or
replace unrelated workspace items. Review the deployment result's
`managed_items` and complete a new verification checklist after recovery.
