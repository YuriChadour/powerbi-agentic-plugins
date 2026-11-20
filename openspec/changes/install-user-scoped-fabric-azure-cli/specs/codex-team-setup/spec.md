## MODIFIED Requirements

### Requirement: External setup dependencies are provisioned idempotently

When a selected plugin requires external tooling, setup SHALL detect the installed capability before attempting installation. A force-enabled plugin update SHALL not reinstall an already available Power BI Desktop Bridge CLI, ADOMD.NET client, VS Code Python extension, Fabric CLI, or Azure CLI. The ADOMD.NET check SHALL include a usable `Microsoft.AnalysisServices.AdomdClient.dll` in the existing user-profile NuGet/package cache locations before considering a download. Missing or outdated capabilities SHALL be installed through a supported user-scoped channel or reported with actionable remediation. npm CLI installations SHALL use global mode (`-g`) with an explicit prefix under the current user's profile; installer-managed path additions SHALL be persisted for future sessions and applied to the current process without removing unrelated entries.

#### Scenario: Existing Power BI dependencies are reused
- **WHEN** setup targets the `powerbi` plugin and the Desktop Bridge CLI and ADOMD.NET client are already resolvable
- **THEN** setup reports them as already available and does not invoke their installers

#### Scenario: ADOMD.NET in user cache is reused during force update
- **WHEN** setup targets the `powerbi` plugin with `-Force` and a valid ADOMD.NET client assembly already exists in the current user's NuGet/package cache
- **THEN** setup reports the discovered cache path and does not download, extract, replace, or reinstall ADOMD.NET

#### Scenario: ADOMD.NET user cache contains an unusable assembly
- **WHEN** an ADOMD.NET candidate exists in the user cache but is missing, empty, corrupt, or not loadable
- **THEN** setup treats that candidate as unavailable and uses the documented recovery or download path without treating the invalid file as ready

#### Scenario: Existing VS Code extension is reused
- **WHEN** VS Code is available and `ms-python.python` is present in the installed extension list
- **THEN** setup reports the extension as already installed and does not invoke the extension installer

#### Scenario: Existing Fabric CLIs are reused
- **WHEN** setup targets the `fabric` plugin, `fab` and `az` resolve on `PATH`, and both satisfy the latest-stable policy
- **THEN** setup reports both current versions and skips their installers, including during a `-Force` plugin refresh

#### Scenario: Missing or outdated Fabric CLI is provisioned
- **WHEN** setup targets the `fabric` plugin and either `fab` or `az` is missing or outdated
- **THEN** setup provisions only the affected CLI through a supported user-scoped channel, refreshes `PATH`, and verifies the command before reporting it ready

#### Scenario: Missing optional dependency is handled safely
- **WHEN** a selected external dependency is unavailable or its installer cannot run
- **THEN** setup reports the affected capability and remediation without claiming that capability is ready
