## Why

The repository currently has Fabric workload skills and a DevOps PR helper, but no reusable capability that establishes CI/CD for a Fabric-enabled project, spanning DEV authoring, validation, release packaging, protected deployment, governance, and rollback evidence.

## What Changes

- Introduce a Jira-linked `fabric-cicd-lifecycle` capability for net-new Fabric CI/CD setup and ongoing operation.
- Port and generalize the complete reference `cicd/` asset set into a versioned, self-contained skill bundle, including runnable scripts, sample pipeline YAML, configuration templates, dependency locks, and operational guidance, with a documented disposition for every reference file.
- Provide a quick, template-driven bootstrap that renders a mutually consistent, validated starter from explicit adopter inputs and works without access to the reference repository.
- Generate an adopter-facing `SETUP.md` and explicit setup parameter contract covering one-click orchestration, protected deployment, separate verification, and recovery.
- Discover a repository's Fabric and Power BI scope and generate or validate the repository CI/CD contract, including managed-item manifest, source roots, optional Fabric Git connection and initial-sync evidence when used, exclusions, pinned dependencies, and validation entry points.
- Scaffold secretless source validation, immutable release packaging, protected TEST and PROD deployment, post-deployment verification, and rollback evidence assets.
- Configure and validate path-scoped Azure DevOps build-validation policies, environments, service connections, protected variable groups/Key Vault references, and agent-pool permissions through explicit user-confirmed operations. Keep Jira as the work-tracking system unless the adopter explicitly chooses another integration.
- Keep shared DEV available for human and agent authoring and execution, including the Data Engineering extension. The release pipeline never deploys to DEV; after a reviewed DEV commit is selected for release it deploys to protected TEST, then promotes to PROD after TEST verification and approval. A PR must never write to Fabric.
- For Fabric data engineering only, author and test in DEV using the Data Engineering extension, review and commit the selected managed definitions to the DEV branch, and deliberately select a validated DEV commit for release. Feature and bugfix branches are not required for this scope.
- Adapt the reference project's shared release-stage topology to thin `fabric-test.yml`/`fabric-prod.yml` wrappers with target-specific guards and deployment verification, without copying project-specific paths, IDs, or secrets.
- Protect trusted pipeline execution and bind TEST deployment and verification, approval, and PROD promotion to one trusted immutable artifact digest.
- Install the implemented skills in selected harnesses after offline checks and test discovery, routing and lifecycle behavior from the installed copies; record results and unverified scenarios.
- Route work using user-selected work area first, then bug/feature/story, with a narrowly scoped DEV-branch exception for Fabric data engineering; preserve feature/bugfix and Jira rules for other and mixed work. The related `fin-2060-fabric-de-branch-guard` change owns guard and intake behavior.
- Provide plan, bootstrap, configure, validate, release, status, and rollback-oriented operating modes.

### Target-neutral bootstrap and recovery

- Generate reusable scripts, YAML and configuration templates from versioned plugin assets; package adopter-owned notebook and pipeline definitions from the selected source revision instead of reconstructing business logic.
- Accept an explicit target workspace name or ID and capacity when needed. A separately selected rehearsal target is isolated from configured DEV, TEST and PROD mappings; it is not a fourth permanent environment and cannot supply production-promotion evidence unless explicitly authorized by the applicable release contract.
- Verify schema-enabled Lakehouse readiness, identities, managed shells, notebook bindings and pipeline destinations; lock deployment through verification. Run data ingestion and integration checks only when explicitly selected, and keep schedules disabled.
- Prefer Spark notebooks for initial Lakehouse schemas, Delta transformations, validation and materialized data; keep pipelines focused on ingestion and orchestration.
- Redeploy retained known-good artifacts through protected verification; treat Delta data recovery as a distinct reviewed action with an explicit scope and recovery point. Preserve unrelated items and report residual managed items.
- Record redacted, provenance-bound evidence in an explicitly configured approved location with a retention period; revalidate mutable state when resuming.
- Keep isolated-target definition deployment separate from manual developer verification; optional runtime automation requires explicit selection and separate evidence.

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
- Post-installation testing requires a selected harness and test context; any separately selected live exercise requires explicit targets, identities, protected resources and permissions.
- Protected Azure DevOps resources: path-scoped build policies, `fabric-test`/`fabric-prod` environments, service connections, variable groups/Key Vault references, and agent-pool permissions.
- No PR validation or release-pipeline write to DEV, no data-row export, and no change to existing Power BI release behavior unless a repository explicitly opts into a separate Power BI scope.
