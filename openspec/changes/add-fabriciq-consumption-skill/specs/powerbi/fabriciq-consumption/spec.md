## Purpose

Provide a governed, source-bound way to answer natural-language business questions using existing Power BI reports and semantic models.

## ADDED Requirements

### Requirement: FabricIQ availability is verified before routing requests

The system SHALL expose FabricIQ consumption guidance only when the configured MCP integration exposes the operations needed to discover artifacts, inspect report metadata and semantic-model schema, search entity values, and execute DAX queries. When those operations are unavailable, the system SHALL state that FabricIQ consumption is unavailable and SHALL NOT route a user to a non-existent capability.

#### Scenario: Required FabricIQ operations are available

- **WHEN** the FabricIQ MCP integration exposes all required consumption operations
- **THEN** a natural-language business question over a Power BI report or semantic model is routed to FabricIQ consumption guidance

#### Scenario: Required FabricIQ operations are unavailable

- **WHEN** a user asks a business question over report data and the required FabricIQ operations are not available
- **THEN** the system explains that the FabricIQ consumption capability is unavailable without fabricating an answer or referencing an unavailable skill

### Requirement: Natural-language questions are answered from Power BI artifacts

The system SHALL use FabricIQ consumption only for questions about existing Power BI reports or semantic models. It SHALL discover or resolve the requested artifact, retrieve the relevant report metadata and semantic-model schema, and answer only from the resulting Power BI data.

#### Scenario: Question names a report

- **WHEN** a user asks a business question about a named Power BI report
- **THEN** the system identifies the report, obtains its semantic-model context, and returns an answer grounded in query results

#### Scenario: Unsupported artifact is supplied

- **WHEN** a user asks a business question about an unsupported Fabric artifact type
- **THEN** the system explains that the artifact is unsupported and asks for a Power BI report or semantic model instead

### Requirement: Queries honor model and report governance

The system SHALL read and follow semantic-model custom instructions and matching verified answers before generating an ad-hoc query. It SHALL preserve applicable report, page, and visual filters unless the user explicitly requests a conflicting scope. When a user supplies a concrete entity value for filtering, the system SHALL resolve that value against the semantic model before querying.

#### Scenario: A verified answer matches the question

- **WHEN** the semantic model contains a verified answer matching the user's analysis intent
- **THEN** the system uses that verified answer's bindings, filters, and granularity as the query contract

#### Scenario: User requests a different report-filtered period

- **WHEN** a report is filtered to one period and the user explicitly asks for a conflicting period
- **THEN** the system applies the requested period while retaining non-conflicting filters and discloses the override in the answer

### Requirement: Consumption is distinct from authoring and management

The system SHALL route report-definition CRUD to report management, PBIR layout and formatting changes to report authoring, and semantic-model definition changes or user-supplied DAX to semantic-model authoring. FabricIQ consumption SHALL NOT create, edit, deploy, or delete report or semantic-model definitions.

#### Scenario: User asks to add a measure

- **WHEN** a user asks to save a new measure or modify a semantic-model definition
- **THEN** the system routes the request to semantic-model authoring rather than FabricIQ consumption

#### Scenario: User asks a report-data question

- **WHEN** a user asks for a business insight or value from an existing report
- **THEN** the system routes the request to FabricIQ consumption rather than report-definition management
