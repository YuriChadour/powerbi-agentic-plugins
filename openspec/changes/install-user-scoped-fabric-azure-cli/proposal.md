## Why

The team setup flow can install the Fabric plugin but does not currently guarantee that the external `fab` and Azure CLI commands used by Fabric workflows are available. On managed Windows machines, system-wide installers may require permissions the developer does not have, while existing setup dependencies already demonstrate a working pattern: reuse first, install per-user, refresh the process path, verify the command, and warn with remediation on failure.

## What Changes

- Provision the latest stable Microsoft Fabric CLI (`fab`) and Azure CLI (`az`) when the `fabric` plugin is targeted.
- Prefer npm for CLI acquisition where Microsoft provides an official npm package, using global mode (`-g`) with an explicit npm prefix under the current user's profile; use the official no-admin portable distribution when a CLI is not published as a supported npm package.
- Install both CLIs under the current user's profile without administrator rights or elevation; never run a system-wide installer.
- Reuse an already resolvable compatible CLI instead of reinstalling it on every run, including `-Force` plugin refreshes.
- Detect a usable ADOMD.NET client in the current user's NuGet/package cache before downloading it, and never replace or reinstall it during `-Force` plugin updates.
- Add installer-managed directories to the current process and persistent user-scoped `PATH`, without deleting or rewriting unrelated user or machine entries.
- Verify `fab --version` and `az version` after provisioning and report each result without claiming readiness on failure.
- Extend setup tests and documentation for missing, existing, outdated, npm-unavailable, path-update, blocked-install, and per-user ADOMD cache scenarios.

## Capabilities

### New Capabilities
- `fabric/cli-environment-provisioning`: Latest-stable, user-scoped discovery and installation, npm-preferred acquisition, persistent `PATH` management, reuse, and verification for the Fabric CLI and Azure CLI.

### Modified Capabilities
- `codex-team-setup`: The setup orchestrator invokes Fabric CLI dependency provisioning only for the selected `fabric` plugin and reports CLI dependency status as part of setup.

## Impact

- `setup-team-plugins.ps1`: per-user npm/package discovery, portable CLI installation, `PATH`, and verification helpers plus Fabric-selected invocation; explicit ADOMD user-cache reuse before download.
- `scripts/test-setup-team-plugins.ps1`: isolated tests for reuse, latest-stable selection, missing tools, npm availability, portable fallback, path updates, install failure, plugin isolation, and ADOMD cache reuse.
- `DEVELOPER_SETUP.md`, `AGENTS.md`, and related setup guidance: prerequisites, npm preference, supported Azure CLI portable fallback, verification, and remediation for `fab` and `az`.
- Network access to npm and the applicable official Microsoft release source is required only when a CLI is missing or outdated; no credentials or administrator privileges are required for installation.
