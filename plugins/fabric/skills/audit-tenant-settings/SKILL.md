---
name: audit-tenant-settings
description: Audit Microsoft Fabric and Power BI tenant settings against the bundled baseline, identify configuration drift and delegated overrides, and investigate referenced Entra security groups. Use when a user asks about Fabric administration, tenant settings, governance posture, or a tenant-settings audit.
---

# Audit Fabric Tenant Settings

Use this skill with [fabric-cli](../fabric-cli/SKILL.md). It provides a read-only tenant-settings audit workflow; it never changes tenant, capacity, domain, workspace, or security-group state.

## Prerequisites

- `fab` (`ms-fabric-cli`) is installed and authenticated as a Fabric or Power BI administrator. Confirm with `fab auth status`; ask the user to authenticate if necessary.
- The audit script requires uv. Its PEP 723 metadata lets `uv run` resolve PyYAML, and PDF output additionally resolves ReportLab, in an isolated environment without a global install.
- Entra security-group investigation additionally needs an authenticated `az` session with suitable Microsoft Graph read permissions. Do not authenticate automatically.

## Safety and scope

- Verify access with a small read-only request before a broad tenant query. A 401 or 403 is a stop condition, not an invitation to work around access controls.
- Read the bundled metadata first, then the live API, then Microsoft Learn when the metadata is silent or stale. Do not fabricate setting behavior, group membership, risk, or compliance conclusions.
- Tenant, delegated-override, and group changes require an explicit user decision after the audit. Present commands or portal steps only after explaining their effects.
- Do not reveal full security-group or workspace membership unless the user explicitly asks. Summarize counts, roles, and material findings by default.

## Run the audit

Run scripts from this skill directory so their paths resolve in Codex and Copilot installations:

```powershell
uv run scripts/audit-tenant-settings.py -o ./tenant-audit.md
uv run scripts/generate_audit_pdf.py -o ./tenant-audit.pdf
```

Useful options include `--drift-only`, `--snapshot <path>`, and `--no-snapshot`. Use a user-approved, tenant-specific snapshot location; do not assume a `.claude` directory or another harness-specific state file.

The audit compares live tenant settings with [tenant-settings-metadata.yaml](references/tenant-settings-metadata.yaml), identifies drift and preview features, and can enumerate delegated overrides. The PDF is a stakeholder summary; the Markdown report is the working record.

## Review workflow

1. Report headline counts, changes since the last approved snapshot, high-risk drift, security-group scoping findings, preview features, and delegated overrides.
2. For each material setting, use the metadata, the live API value, and its Microsoft Learn source. State what is observed versus what is a general recommendation.
3. Enumerate capacity, domain, and workspace overrides when applicable; distinguish effective posture from the tenant default.
4. Discuss remediation as options. Recommendations are scenario-dependent and never a blanket compliance assertion.
5. If the user wants a change, obtain explicit confirmation for the exact affected setting and scope before handing off to `fabric-cli`.

## Resources

- [Tenant-settings baseline](references/tenant-settings-metadata.yaml)
- [Delegated overrides](references/delegated-overrides.md)
- [Security-group investigation](references/security-groups.md)
- [Audit script](scripts/audit-tenant-settings.py)
- [PDF generator](scripts/generate_audit_pdf.py)
- [Microsoft Learn tenant settings index](https://learn.microsoft.com/en-us/fabric/admin/tenant-settings-index)
