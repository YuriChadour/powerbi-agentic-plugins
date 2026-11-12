## Why

Fabric CI/CD setup should reuse the connected Analytics Reporting workflow rather than reconstruct it as many independent operations. A parameterized starter can carry that workflow to other repositories while making project-specific inputs explicit.

## What Changes

- Generalize the reference UAT bootstrap, artifact packaging, deployment and developer verification as one lightweight, PowerShell-led Fabric data-engineering workflow with one setup entry point, reviewable planning and recovery.
- Preserve the reference YAML manifest and pipeline structure where practical; render only the configured Fabric source and CI folders, and replace reference-specific workspace, capacity, identity, managed-item and Azure DevOps settings with adopter inputs.
- Use `fab` and the Azure DevOps `az` extension only through the invoking developer's authenticated local sessions for setup: create or reuse the selected workspace, apply explicitly mapped user, group and service-principal roles, and register rendered Fabric YAML pipelines after their YAML is committed. Protected pipeline identities are reserved for TEST/PROD deployment.
- Keep useful existing source checks within the workflow and report Fabric deployment and authorized runtime verification separately.
- Extend promotion so a protected PROD deployment consumes the artifact verified in TEST, without rebuilding.
- Keep Power BI CI/CD out of this bootstrap. A future Power BI bootstrap may use its own approved folder mapping and pipelines; the Fabric bootstrap routes by its configured Fabric source folder and never treats the presence of a Power BI folder as approval.
- Run a focused offline test set for plan-without-writes, folder scope, workspace roles, pipeline registration, manifest validation and artifact promotion. Exercise installed skills in Codex and Copilot and report live Fabric and Azure DevOps behavior as unverified until exercised.
- Reuse only a small number of earlier documentation or rendering helpers when each has a mapped workflow consumer. Preserve the incomplete prior attempt for reference rather than treating its Python REST adapters or broad test suite as completed work.

## Capabilities

### New Capabilities

- `fabric/reference-cicd-bootstrap`: Parameterized setup and release based on the Analytics Reporting workflow.

### Modified Capabilities

None.

## Impact

- Fabric CI/CD skill and its small PowerShell/CLI template set, rendered YAML, setup guide and focused tests.
- Adopter repositories, Azure DevOps resources and Fabric workspaces only when explicitly configured and authorized.
- Reference baseline: Analytics Reporting commit `4a77113ec051907c3e10e6da9d4a89e62bfb58ea`. Prior incomplete work: local Git branch `archive/FIN-2060-lifecycle-attempt`, commit `dbcf31bbd02ed2ff47241706544134873609f9b6`.
