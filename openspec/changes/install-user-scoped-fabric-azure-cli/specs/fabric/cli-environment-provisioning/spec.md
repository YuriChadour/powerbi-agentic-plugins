## Purpose

Ensure Fabric workflows have current, verifiable `fab` and `az` commands installed for the current user without administrator rights, while preserving existing user configuration and package installations.

## ADDED Requirements

### Requirement: Fabric CLIs are provisioned per user
When the `fabric` plugin is selected, setup SHALL discover and provision the latest stable Microsoft Fabric CLI (`fab`) and Azure CLI (`az`) entirely under the current user's profile. The workflow SHALL NOT invoke an elevated or system-wide installer, overwrite unrelated user-managed installations, or claim the CLIs are ready before command verification succeeds.

#### Scenario: Both CLIs are missing
- **WHEN** the `fabric` plugin is selected and neither `fab` nor `az` is resolvable
- **THEN** setup installs current stable versions into user-writable locations without elevation and verifies both commands

#### Scenario: Latest stable versions are available
- **WHEN** setup resolves release metadata from an official Microsoft-supported source
- **THEN** the selected version is the latest stable release and prerelease versions are excluded unless the CLI's official stable channel explicitly identifies one

#### Scenario: Installation requires elevation
- **WHEN** a proposed install route would require administrator privileges
- **THEN** setup SHALL not invoke that route and SHALL report a no-admin installation remedy

### Requirement: npm is preferred when officially supported
For any CLI with an official npm distribution that provides the required command on Windows, setup SHALL use `npm install -g` with an explicit npm prefix under the current user's profile. If a CLI is not distributed as an official supported npm package, setup SHALL use that CLI's official no-admin portable or package-manager distribution and SHALL NOT substitute an unofficial npm wrapper.

#### Scenario: Official npm package exists
- **WHEN** a required CLI has an official stable npm package
- **THEN** setup runs global npm installation with an installer-owned user prefix, adds that prefix's executable directory to user `PATH`, and verifies the installed command

#### Scenario: Azure CLI has no supported npm distribution
- **WHEN** Azure CLI is required and no supported current `az` npm distribution is available
- **THEN** setup uses the official no-admin Windows ZIP/portable distribution and reports that fallback

#### Scenario: npm is unavailable
- **WHEN** npm is unavailable for a CLI that has an official supported npm package
- **THEN** setup reports the missing Node.js/npm prerequisite and any officially supported no-admin alternative without attempting an unsupported package

### Requirement: Existing CLI installations are reused
Setup SHALL test for a resolvable command and determine whether its installed stable version satisfies the latest-stable policy before installing. A plugin `-Force` operation SHALL force plugin file replacement only and SHALL NOT by itself reinstall or replace a usable current CLI.

#### Scenario: Current CLI is already installed
- **WHEN** a selected CLI resolves on `PATH` and reports the latest stable version
- **THEN** setup reports it as already installed and skips all download and package installation for that CLI

#### Scenario: Older CLI is installed
- **WHEN** a selected CLI resolves but reports an older stable version
- **THEN** setup upgrades it through the supported user-scoped channel and verifies the upgraded version

#### Scenario: Force refresh excludes current CLI
- **WHEN** setup runs with `-Force` for `fabric` and the CLI is current
- **THEN** setup preserves the existing CLI files and installation metadata

### Requirement: User PATH is updated safely
Setup SHALL add only installer-managed executable directories to the current process `PATH` and persistent user `PATH`. It SHALL normalize path comparisons, avoid duplicate entries, preserve all unrelated entries and ordering, and make `fab` and `az` resolvable during the same setup process after installation.

#### Scenario: User PATH lacks install directory
- **WHEN** a CLI installs successfully into a user-profile directory not yet present in user `PATH`
- **THEN** setup adds that exact directory once to user `PATH` and to the current process `PATH`

#### Scenario: Path is already configured
- **WHEN** the installer-managed directory already appears in user or process `PATH` with different casing or trailing separators
- **THEN** setup reuses the normalized equivalent and does not append a duplicate

#### Scenario: Other PATH entries exist
- **WHEN** setup persists a user `PATH` update
- **THEN** existing user entries and machine `PATH` composition remain unchanged except for the added installer-owned directory

### Requirement: CLI provisioning reports bounded failures
After acquisition and `PATH` refresh, setup SHALL run a bounded version command for each selected CLI. A command, download, extraction, package, or verification failure SHALL be reported with the affected CLI and actionable remediation; plugin-file installation SHALL continue when the CLI is an optional external dependency, and setup SHALL NOT report that CLI as ready.

#### Scenario: Verification succeeds
- **WHEN** `fab --version` or `az version` exits successfully within the configured bound
- **THEN** setup reports the command, selected version, installation location, and ready status

#### Scenario: Download is blocked
- **WHEN** network or corporate policy blocks the official release endpoint
- **THEN** setup reports the failed official endpoint and manual no-admin remediation while continuing the remaining plugin setup

#### Scenario: Command remains unresolved
- **WHEN** installation completes but the command is still not resolvable after current-process `PATH` refresh
- **THEN** setup reports the expected install bin directory and does not mark the CLI ready
