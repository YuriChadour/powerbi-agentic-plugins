# Power BI CI/CD harness-routing evidence

| Harness | Power BI CI/CD | Fabric data engineering | Mixed / unresolved | Status |
| --- | --- | --- | --- | --- |
| Codex | `powerbi-cicd` is discoverable from the installed skill catalog; normal Jira-keyed branch validation applies. | `fabric-cicd` remains the separate data-engineering route. | Normal Jira-keyed branch validation applies; no DEV exception. | Verified locally. |
| Copilot | Plugin skill metadata is packaged under `plugins/powerbi/skills/powerbi-cicd/`. | The Fabric plugin retains `fabric-cicd`. | Normal Jira/branch instructions are supplied by the DevOps plugin. | Static packaging verified; interactive discovery unverified. |
| Claude | Source `SKILL.md` is plugin-packaged with the same trigger description. | The Fabric plugin retains its distinct skill. | Normal Jira/branch instructions are supplied by the DevOps plugin. | Static packaging verified; interactive discovery unverified. |

Live tenant operations are deliberately unverified: this repository validation
does not have an approved adopter configuration, protected deployment identity,
or target workspace. The lifecycle fails closed until those inputs exist.
