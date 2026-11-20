## 1. Shared Provisioning Helpers

- [ ] 1.1 Add a user-profile tool-root resolver and verify it produces no machine-writable or elevated destination on Windows.
- [ ] 1.2 Add normalized user `PATH` read/update helpers and verify unrelated entries, ordering, casing, and duplicates are preserved correctly.
- [ ] 1.3 Add bounded command and version parsing helpers and verify successful, timed-out, nonzero, and unparseable command results are distinguishable.
- [ ] 1.4 Add a structured external-dependency result shape for name, version, path, channel, ready state, and remediation; verify the setup summary can render both ready and failed results.

## 2. Fabric CLI Provisioning

- [ ] 2.1 Add official `fab` package/channel discovery with latest-stable selection and verify prerelease versions are excluded.
- [ ] 2.2 Prefer `npm install -g` with an explicit installer-owned user prefix when the verified official Fabric CLI channel supports it; verify the exact package identity, `-g`, prefix, generated shim, and executable directory are correct.
- [ ] 2.3 Add the official no-admin fallback for a Fabric CLI channel that is not supported through npm, and verify no unofficial package or elevated installer is attempted.
- [ ] 2.4 Reuse a resolvable current `fab` installation and verify missing, current, and outdated branches invoke the installer the expected number of times.
- [ ] 2.5 Verify `fab --version` after process `PATH` refresh and verify an unresolved or failed command is not reported as ready.

## 3. Azure CLI Provisioning

- [ ] 3.1 Add latest-stable Azure CLI version and official Windows ZIP source discovery; verify prerelease and MSI routes are not selected.
- [ ] 3.2 Download, validate, and extract the Azure CLI ZIP beneath the installer-owned user tool root; verify a failed download or extraction leaves the previous installation intact.
- [ ] 3.3 Add the extracted Azure CLI `bin` directory to process and user `PATH`; verify `az version` resolves in the same setup process and from a newly constructed user environment.
- [ ] 3.4 Reuse a current `az` installation, upgrade an outdated user-owned installation, and verify `-Force` does not replace a current version.

## 4. ADOMD.NET Reuse

- [ ] 4.1 Strengthen ADOMD.NET discovery to check user-profile NuGet/package cache candidates before download and verify a valid `Microsoft.AnalysisServices.AdomdClient.dll` is returned with its cache path.
- [ ] 4.2 Make `-Force` reuse a valid cached ADOMD.NET assembly and verify no download, extract, replace, or reinstall operation occurs.
- [ ] 4.3 Cover empty, corrupt, missing, and non-loadable ADOMD cache candidates and verify they are not reported as ready and fall through to existing remediation.

## 5. Setup Integration

- [ ] 5.1 Invoke `fab` and `az` provisioning only when the selected plugin set contains `fabric`; verify Power BI-only and DevOps-only setup do not touch either CLI.
- [ ] 5.2 Invoke ADOMD discovery/provisioning only when the selected plugin set contains `powerbi`; verify Fabric-only setup does not inspect or replace ADOMD.
- [ ] 5.3 Add CLI dependency status to the setup summary and verify ready, reused, upgraded, unavailable, and failed-verification states are explicit.
- [ ] 5.4 Preserve target independence and plugin backups when CLI provisioning fails; verify `Codex`, `Copilot`, and `All` still report their existing projection result accurately.

## 6. Tests and Documentation

- [ ] 6.1 Extend `scripts/test-setup-team-plugins.ps1` with isolated user-profile fixtures for npm acquisition, Azure ZIP fallback, user `PATH` persistence, command verification, and latest-stable comparison; verify the suite passes without real network installation.
- [ ] 6.2 Add isolated fixtures proving existing `fab`, `az`, and ADOMD cache installations are untouched by `-Force`; verify sentinel contents and timestamps remain unchanged.
- [ ] 6.3 Add failure fixtures for blocked download, missing npm, unresolved post-install command, and invalid ADOMD assembly; verify each emits actionable remediation without claiming readiness.
- [ ] 6.4 Update `DEVELOPER_SETUP.md`, `AGENTS.md`, and setup help text with latest-stable, npm-preferred, official fallback, no-admin, `PATH`, and verification behavior; verify documented commands match the implemented channels.
- [ ] 6.5 Run `scripts/test-setup-team-plugins.ps1 -RunIntegration`, the relevant static validators, and `openspec validate install-user-scoped-fabric-azure-cli --strict`; verify all commands pass.
