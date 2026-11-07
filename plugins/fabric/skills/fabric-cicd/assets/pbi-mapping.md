# Power BI mapping contract

`pbi-assets.yml` is a separate opt-in contract. Its starter is JSON-formatted
YAML so the validator needs only the Python standard library. Folder discovery
alone never enables generation or deployment. To opt in, explicitly approve a
nonempty list of source-to-workspace mappings, each with a unique `name`, a
repository-relative `source`, a nonzero workspace UUID in `workspace_id`, and
an optional list of named `fabric_prerequisites`. No credentials belong here.

Validate a completed mapping with:

```powershell
py -3 <skill-path>/scripts/validate_pbi_mapping.py <repo>/cicd/pbi-assets.yml
```

The validator checks the contract only; it does not deploy, establish a Fabric
prerequisite, verify access or authorize any external operation. An absent or
unapproved mapping must not enable Power BI assets. Generic dependency graph
validation and pipeline generation remain pending lifecycle tasks.
