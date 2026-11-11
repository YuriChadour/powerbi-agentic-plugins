## Why

Fabric CI/CD setup should reuse the connected Analytics Reporting workflow rather than reconstruct it as many independent operations. A parameterized starter can carry that workflow to other repositories while making project-specific inputs explicit.

## What Changes

- Generalize the reference UAT bootstrap, artifact packaging, deployment and developer verification as one compatible workflow with one setup entry point, reviewable planning and recovery.
- Preserve the reference YAML manifest and pipeline structure where practical; replace reference-specific workspace, capacity, identity, managed-item and Azure DevOps settings with adopter inputs.
- Keep useful existing source checks within the workflow and report Fabric deployment and authorized runtime verification separately.
- Extend promotion so a protected PROD deployment consumes the artifact verified in TEST, without rebuilding.
- Test the generalized reference behavior offline and exercise installed skills in Codex and Copilot. Report live Fabric and Azure DevOps behavior as unverified until exercised.
- Reuse an earlier helper only when it demonstrably fits the connected workflow. Preserve the incomplete prior attempt for reference rather than treating it as completed.

## Capabilities

### New Capabilities

- `fabric/reference-cicd-bootstrap`: Parameterized setup and release based on the Analytics Reporting workflow.

### Modified Capabilities

None.

## Impact

- Fabric CI/CD skill and its scripts, templates, setup guide and tests.
- Adopter repositories, Azure DevOps resources and Fabric workspaces only when explicitly configured and authorized.
- Reference baseline: Analytics Reporting commit `4a77113ec051907c3e10e6da9d4a89e62bfb58ea`. Prior incomplete work: local Git branch `archive/FIN-2060-lifecycle-attempt`, commit `dbcf31bbd02ed2ff47241706544134873609f9b6`.
