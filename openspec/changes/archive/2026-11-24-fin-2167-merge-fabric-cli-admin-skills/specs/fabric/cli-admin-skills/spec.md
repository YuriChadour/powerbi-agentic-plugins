## Purpose

Provide discoverable Fabric CLI and administration guidance with the resources needed to use it across supported plugin installations.

## ADDED Requirements

### Requirement: Fabric CLI guidance is integrated
The Fabric plugin SHALL provide merged CLI guidance and supporting resources while retaining applicable existing functionality and routing to specialist skills.

#### Scenario: User requests a Fabric CLI operation
- **WHEN** a user requests a supported Fabric resource operation
- **THEN** the skill identifies relevant guidance and packaged resources and routes specialist workloads to their existing owners.

### Requirement: Administration skills are discoverable
The Fabric plugin SHALL provide discoverable capacity and tenant-settings audit skills and their required references and scripts.

#### Scenario: User requests a tenant settings audit
- **WHEN** a user requests an audit of Fabric tenant settings
- **THEN** the audit skill identifies its prerequisites, supporting resources and dependency on Fabric CLI guidance.

#### Scenario: User requests capacity diagnostics
- **WHEN** a user asks about capacity utilization or throttling
- **THEN** capacity guidance identifies the metrics source and routes related operations to applicable CLI guidance.

### Requirement: Compatible and reviewable integration
The integrated skills SHALL preserve authorization boundaries, document external dependencies, and resolve references within supported installations without relying on source-repository paths.

#### Scenario: Skills are installed
- **WHEN** the Fabric plugin is packaged or installed for a supported harness
- **THEN** skill resources and cross-references resolve and harness-specific instructions do not require unavailable tools.

#### Scenario: An operation changes tenant or capacity state
- **WHEN** guidance describes a state-changing operation
- **THEN** it preserves the user's authorization and existing repository constraints rather than silently performing the operation.

### Requirement: Newly integrated Python scripts use uv
Newly integrated Python scripts under the Fabric CLI and tenant-audit skills SHALL declare their Python runtime dependencies using uv-compatible inline metadata and document invocation through `uv run`.

#### Scenario: A user runs an integrated script
- **WHEN** a user follows the packaged script guidance on a machine with uv available
- **THEN** `uv run` resolves only the script's declared Python dependencies without requiring global package installation.

#### Scenario: A script needs an external command or live authorization
- **WHEN** an integrated script requires `fab`, `az`, DuckDB, SQLCMD, or a live Fabric connection
- **THEN** its guidance distinguishes that external prerequisite from uv-managed Python dependencies and preserves the existing authentication and consent boundaries.
