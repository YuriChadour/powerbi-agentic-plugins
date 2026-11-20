---
name: powerbi-cicd
description: Run the reviewed Power BI CI/CD setup and release lifecycle for PBIP, PBIR, TMDL semantic models, and paginated RDL reports. Use for scripted plan/review/approve/apply setup, offline validation, immutable release promotion, deployment evidence, drift, HOTFIX, or rollback; never use for Fabric data-engineering CI/CD.
---

# Power BI CI/CD Workflow

Run this skill only for Power BI scope after Jira intake and the normal
Jira-keyed feature or bugfix branch guard. Keep every command in this order.
If any command exits nonzero or prints a blocking question, gap, drift, or
validation error, stop. Correct the named cause and rerun the same command;
do not continue to the next step.

1. Run read-only planning from the adopter repository. Supply the reviewed
   DEV, TEST, PROD, and HOTFIX workspace names plus the service-principal
   application ID. Add UAT/REHEARSAL selectors only when configured.

```powershell
py -3 -B "<skill-path>/scripts/plan.py" --repo . --no-prompt `
  --app-id <APP_ID> --dev-workspace <DEV_NAME> --test-workspace <TEST_NAME> `
  --prod-workspace <PROD_NAME> --hotfix-workspace <HOTFIX_NAME>
```

For a one-time legacy migration, append `--legacy-config <PATH>` and/or
`--legacy-manifest <PATH>`. Planning never edits those files. Resolve every
printed `--answer key=value` question and rerun; never guess a value.

2. Review `cicd/powerbi/setup.yml` and `cicd/powerbi/SETUP.md`. Require every
   managed item, dependency, target, identity reference, connection binding,
   substitution, protected resource, generated file, and rollback path to be
   explicit. Do not approve while a question or blocking gap remains.

3. After explicit human review, bind approval to the exact setup bytes.

```powershell
py -3 -B "<skill-path>/scripts/approve.py" --setup cicd/powerbi/setup.yml
```

Changing `setup.yml` invalidates `setup.approved`; repeat review and approval.
For the one-time legacy-input migration and rollback procedure, read
`assets/migration-guide.md`.

4. Apply the approved fixed idempotent sequence. This step generates files,
   reconciles reviewed workspaces and direct access, and checks protected
   resources. It never deploys an item or runs a workload.

```powershell
py -3 -B "<skill-path>/scripts/apply.py" --repo . --setup cicd/powerbi/setup.yml
```

Stop on failure and use `cicd/powerbi/apply-readiness.json` plus the command's
actionable diagnostic. A corrected rerun resumes from current external state.

5. Run the synthetic lifecycle checks and strict OpenSpec validation before
   committing. These tests do not prove live tenant support or authorization.

```powershell
py -3 -B -m unittest discover "<skill-path>/tests" -v
openspec validate fin-2060-powerbi-cicd-scripted-setup --strict
```

6. Commit only the reviewed FIN-2060 files with a Jira-prefixed message.
   Preserve unrelated worktree changes. Then open the normal Power BI pull
   request through the repository's DevOps workflow.

```powershell
git add cicd/powerbi plugins/powerbi/skills/powerbi-cicd openspec/changes/fin-2060-powerbi-cicd-scripted-setup
git commit -m "FIN-2060: <summary>"
```

Do not commit the approval marker if the repository policy excludes local
approval evidence. Never bypass a rejected branch policy or CI check.

## HOTFIX Route

Create `hotfix/<Jira-key>` from the configured PROD branch. The validated
source is packaged once and deployed only to the isolated HOTFIX workspace
through PROD semantic-model bindings and substitutions. A merged PROD build
must resolve the uniquely successful HOTFIX validation before promotion;
otherwise stop before workspace write. Forward-port the merged fix to TEST and
DEV afterward. Rollback means redeploying a retained known-good artifact
through the same protected adapter path.
