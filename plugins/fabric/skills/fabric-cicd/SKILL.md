---
name: fabric-cicd
description: Set up Fabric data-engineering CI/CD for a repository with fixed scripts - plan, approve, apply - producing DEV/TEST/PROD/HOTFIX workspaces, protected release pipelines, generated fabric-cicd parameter rules, connection bindings and a TEST-verified promotion to PROD. Use for creating or re-running Fabric CI/CD setup, hotfix flow, or the FIN-2101-style rollout. Power BI CI/CD belongs to powerbi-cicd.
---

# Fabric data-engineering CI/CD setup

Run the commands below in order. Do not edit generated files, write YAML or invent
values; if a script prints a question, ask the user and pass the answer back.
`<skill>` is this skill's folder. Run everything from the adopter repository root,
signed in to `fab` and `az` (with the `azure-devops` extension) as the developer.

1. Run the branch guard (`git-branch-guard`); stop if it blocks.
2. Ask the user for: the DEV, TEST, PROD and HOTFIX workspace names or IDs; the
   service principal application ID; the Azure DevOps variable group (one shared
   group is the default).
3. Run
   `py <skill>/scripts/plan.py --no-prompt --dev-workspace "<DEV>" --test-workspace "<TEST>" --prod-workspace "<PROD>" --hotfix-workspace "<HOTFIX>" --app-id <appId> --variable-group "<group>"`.
   Exit code 2 means questions were printed: ask the user each one and re-run step 3
   adding `--answer <key>=<value>` for every answer. A GUID that matches nothing is
   reported as a gap; ask whether to exclude it (`--exclude-guid <guid>`), map it to a
   target reference such as the workspace (`--map-guid "<guid>=$workspace.$id"`) when it
   comes from another discovery workspace, or fix the source.
4. Show `cicd/fabric/SETUP.md` to the user. If they want a change, they edit
   `cicd/fabric/setup.yml` and you re-run step 3.
5. On the user's explicit confirmation run `py <skill>/scripts/approve.py`. It refuses
   while a question or gap remains.
6. Run `py <skill>/scripts/apply.py`. It creates or reuses the workspaces and
   schema-enabled Lakehouses, generates the files under `cicd/`, grants the service
   principal and connection roles, and wires variable groups, environments and pipelines.
   It never runs a workload.
7. Commit the generated files with the Jira-key prefix, push the feature branch and open
   the DEV pull request. If apply stopped at "pipeline is not registered", run the
   printed `az pipelines create` command after the files are on the remote, then re-run step 6.
8. If any script fails, show its message to the user and stop. Re-run it after the
   user fixes the cause; finished steps are no-ops.

Run the offline checks with `py -3 -B -m unittest discover <skill>/tests`.

## What the setup produces

- DEV branch deploys DEV; TEST branch builds and deploys TEST; PROD branch deploys the
  TEST-built artifact after a digest comparison; `hotfix/*` deploys to HOTFIX and, after
  its pull request merges to PROD, PROD deploys that HOTFIX artifact. Any other source
  into PROD is blocked.
- Deploy jobs run on a hosted Linux agent with no checkout, after every artifact hash is
  verified, using the pinned toolchain and a per-environment write guard.
- The user creates the service principal and its secret and enables service-principal
  access in the Fabric tenant; setup never reads or writes secrets.

`assets/dev-authoring.md` covers authoring in DEV before the first release;
`assets/pbi-mapping.md` covers the Power BI boundary.
