# Deprecated Power BI mapping compatibility contract

`pbi-assets.yml` is retained only so existing adopters can validate their
previous explicit mapping while they migrate. It never enabled Fabric CI/CD to
deploy Power BI assets, and it remains frozen: do not add fields or new
deployment behavior here. New Power BI CI/CD adopters must use
`plugins/powerbi/skills/powerbi-cicd/assets/templates/bootstrap-config.json`
and `powerbi-assets.yml`, which add explicit item identities, dependencies,
RDL bindings, target protections, and immutable-release metadata.

Validate a completed mapping with:

```powershell
py -3 <skill-path>/scripts/validate_pbi_mapping.py <repo>/cicd/pbi-assets.yml
```

The compatibility validator checks the old contract only; it does not deploy,
establish a Fabric prerequisite, verify access, or authorize any external
operation. An absent or unapproved mapping must not enable Power BI assets.
Its removal requires a separately approved adopter migration decision.
