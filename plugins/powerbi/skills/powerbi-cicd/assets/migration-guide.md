# One-Time Power BI CI/CD Re-Plan

Existing adopters must run the scripted setup once before the new operator surface can replace hand-maintained release inputs. This is a review migration, not an in-place rewrite of the running release contract.

## Migrate

1. Preserve the current skill and committed `bootstrap-config.json` and `powerbi-assets.yml` files.
2. Run `plan.py` with `--legacy-config` and/or `--legacy-manifest` as described in `SKILL.md`.
3. Resolve every open question, conflict, or blocking gap in `cicd/powerbi/setup.yml` and review `SETUP.md`.
4. Run `approve.py`, then `apply.py`. Apply writes generated compatibility and pipeline files only after the approved hash matches.

Planning does not change legacy files or existing generated release files. Imported substitution rules retain their original order, paths or globs, exact find text, and string replacement values. Secret-bearing or conflicting values block migration instead of being silently translated.

## Generated Locations

The default reviewed source of truth is `cicd/powerbi/setup.yml`, with `cicd/powerbi/SETUP.md` and `cicd/powerbi/setup.approved` beside it. Apply generates:

- `cicd/powerbi/bootstrap-config.json`
- `cicd/powerbi/powerbi-assets.yml`
- `cicd/powerbi/bindings.yml`
- `cicd/powerbi/azure-pipelines.yml`
- `cicd/powerbi/powerbi-validation.yml`
- `cicd/powerbi/scripts/`
- `cicd/powerbi/deployment/`
- `cicd/powerbi/apply-readiness.json`

The CI folder can be changed in the reviewed setup; the paths above are defaults.

## Rollback

Before migration, retain the previously installed skill version and do not delete the last reviewed legacy release files until generated files are committed and validated. To roll back, restore the previous skill installation and continue from the last reviewed legacy files. Existing immutable release ZIPs remain valid and can be redeployed through the previous protected release path.

A failed apply is safe to rerun: completed idempotent steps become no-ops and no deployment workload is started during setup. A failed protected deployment is recovered by selecting and redeploying a retained known-good immutable artifact through the same guarded adapter, not by editing an artifact or bypassing validation.
