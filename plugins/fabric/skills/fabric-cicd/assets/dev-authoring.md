# DEV authoring and release selection

This guidance applies to an adopter project after its scope, workspace, branch,
Git connection and permissions have been explicitly resolved. The generic
lifecycle does not infer those values from a reference project.

1. Confirm the DEV workspace, Fabric Git-connected repository, branch and source
   path. Record the initial synchronization direction and result, source
   revision and managed-item scope. If evidence is missing, stop and establish
   the baseline with the workspace owner; an empty workspace is never authority
   to erase repository source.
2. Author Fabric data engineering in the DEV workspace using the Data
   Engineering extension. Preserve workspace definitions and other in-progress
   work. Confirm supported Git and deployment item types and dependencies.
3. Review the pending Fabric Git changes and select only the intended managed
   definitions. Resolve any unrelated or unfinished changes before committing;
   record the user-provided Jira key independently of the shared branch name.
   Apply the scope-aware branch guard and report remote policy conflicts rather
   than bypassing them.
4. Commit the reviewed definitions through the configured DEV Git integration.
   Verify the commit and its contents, account for remaining uncommitted
   workspace changes and deliberately select its exact commit SHA for release.
5. Run secretless source, manifest, dependency and excluded-content validation
   on that SHA. A failure or unknown result blocks release. The later trusted
   build must package that exact revision once; TEST and PROD consume the same
   verified digest, subject to their separate protections. Release pipelines
   must never write to DEV.

This guidance does not provide a working bootstrap or deployment command. Those
capabilities must pass the lifecycle change's implementation and verification
tasks before they are offered as operational.
