# Sample prompts — jira-workflow

`I want to work on FIN-1740`: use the user's key, record it in `RESUME.md`,
then ask for the work area and the independent work type (bug, feature, or
story) before branch lookup or validation. Explicit exclusive Fabric data
engineering in an adopter project uses its configured DEV branch. Power BI,
other and mixed work use Jira-keyed feature/bugfix branches. Broad Fabric is
not sufficient to establish exclusive scope. If either choice is unresolved,
stop. Use plain-text choices when a structured selector is unavailable.

If Jira tools are available, fetch, assign and transition as supported. If
unavailable, report that limitation, keep the user's key, ask for a description
if needed, and continue the same intake and branch routing. Do not fabricate a
ticket or infer one from a branch.

For Power BI report work, preserve the report subtype and planning gates. For
Fabric development, create or resume the appropriate OpenSpec change and wait
for an explicit implementation request. Bugs and investigative work follow
troubleshooting.

For `finished with FIN-1740`, resolve the user-provided key from the request or
the current ticket block in `RESUME.md`, then follow the Jira finish flow.
After each agent commit, ask separately whether to add a Jira summary comment;
if Jira is unavailable, the user can post it manually.
