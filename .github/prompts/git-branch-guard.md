# Sample prompts — git-branch-guard

For implementation work, `jira-workflow` first obtains the user-provided Jira
key, records it in `RESUME.md`, and asks for work area then work type. A
plain-text prompt is equivalent when structured choices are unavailable.

- `I want to work on FIN-1740`: select the work area and bug, feature, or
  story. Explicit exclusive Fabric data engineering in an adopter project
  uses the configured DEV branch and mandatory scope-aware guard.
- `Create a branch for FIN-1740`: resolve scope and type first. Other work
  searches for existing ticket branches and asks before switching or creating;
  run the guard after branch selection.
- `Check my current branch`: the guard can validate the current branch with no
  arguments. Starting implementation still requires scope-first intake and a
  user-provided Jira key. Broad Fabric, mixed or unknown scope never qualifies
  for the DEV exception.

The guard validates branches; it does not create them or modify remote policies.
