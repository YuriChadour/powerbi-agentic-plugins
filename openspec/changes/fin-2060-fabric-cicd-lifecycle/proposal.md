## Why

The repository currently has Fabric workload skills and a DevOps PR helper, but no reusable capability that establishes CI/CD for a Fabric-enabled project, spanning DEV authoring, validation, release packaging, protected deployment, governance, and rollback evidence.

## What Changes

- Introduce a Jira-linked `fabric-cicd-lifecycle` capability for net-new Fabric CI/CD setup and ongoing operation.
- Port and generalize the complete reference `cicd/` asset set into a versioned, self-contained skill bundle, including runnable scripts, sample pipeline YAML, configuration templates, dependency locks, and operational guidance, with a documented disposition for every reference file.
- Provide a quick, template-driven bootstrap that renders a mutually consistent, validated starter from explicit adopter inputs and works without access to the reference repository.
- Discover a repository's Fabric and Power BI scope and generate or validate the repository CI/CD contract, including managed-item manifest, source roots, optional Fabric Git connection and initial-sync evidence when used, exclusions, pinned dependencies, and validation entry points.
- Scaffold secretless source validation, immutable release packaging, protected TEST and PROD deployment, post-deployment verification, and rollback evidence assets.
- Configure and validate path-scoped Azure DevOps build-validation policies, environments, service connections, protected variable groups/Key Vault references, and agent-pool permissions through explicit user-confirmed operations. Keep Jira as the work-tracking system unless the adopter explicitly chooses another integration.
- Keep shared DEV available for human and agent authoring and execution, including the Data Engineering extension. The release pipeline never deploys to DEV; after a reviewed DEV commit is selected for release it deploys to protected TEST, then promotes to PROD after TEST verification and approval. A PR must never write to Fabric.
- For Fabric data engineering only, author and test in DEV using the Data Engineering extension, review and commit the selected managed definitions to the DEV branch, and deliberately select a validated DEV commit for release. Feature and bugfix branches are not required for this scope.
- Adapt the reference project's shared release-stage topology to thin `fabric-test.yml`/`fabric-prod.yml` wrappers with target-specific guards and deployment verification, without copying project-specific paths, IDs, or secrets.
- Protect trusted pipeline execution and bind TEST deployment and verification, approval, and PROD promotion to one trusted immutable artifact digest.
- Exercise the implemented lifecycle end to end using `C:\Development\PREQIN-1`: create dedicated DEV authoring, TEST, and PROD Fabric workspaces with the Fabric CLI, grant the specified Power BI EOT service principal Contributor in each, validate in TEST, then promote the same artifact to PROD.
- Route work using user-selected work area first, then bug/feature/story, with a narrowly scoped DEV-branch exception for Fabric data engineering; preserve feature/bugfix and Jira rules for other and mixed work. The related `fin-2060-fabric-de-branch-guard` change owns guard and intake behavior.
- Provide plan, bootstrap, configure, validate, release, status, and rollback-oriented operating modes.

## Capabilities

### New Capabilities

- `fabric/cicd-lifecycle`: Establish and operate a complete Fabric CI/CD lifecycle, including repository bootstrap, governance, validation, immutable release packaging, protected deployment, and operational evidence.

### Modified Capabilities

- None.

## Impact

- New reusable Fabric CI/CD skill, templates, adapters, tests, and documentation under `plugins/fabric`.
- Integration with `FabricDataEngineer` routing from the existing Fabric orchestration capability.
- Integrate the `fin-2060-fabric-de-branch-guard` capability and its mandatory scope-aware guard; retain feature/bugfix rules for Power BI, other, mixed and ambiguous work and keep Jira tracking separate from branch naming.
- Fabric CLI export/authentication and Azure DevOps CLI/API dependencies.
- A live PREQIN-1 integration exercise requires a selected Fabric capacity, dedicated workspaces, deployment identities, protected resources, and permissions. Unsupported items and unresolved dependencies must be reported before deployment.
- Protected Azure DevOps resources: path-scoped build policies, `fabric-test`/`fabric-prod` environments, service connections, variable groups/Key Vault references, and agent-pool permissions.
- No PR validation or release-pipeline write to DEV, no data-row export, and no change to existing Power BI release behavior unless a repository explicitly opts into a separate Power BI scope.
