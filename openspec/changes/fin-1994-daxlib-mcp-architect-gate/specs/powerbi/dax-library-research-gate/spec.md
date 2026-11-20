## Purpose

Ensures Power BI specifications consider reusable community DAX user-defined function packages before architect handoff, without treating catalog matches as proof of performance or authorizing model changes.

## ADDED Requirements

### Requirement: Review DAX library reuse before specification finalization
When the `powerbi-architect` has completed a technical draft of a new or revised specification, the architect SHALL assess whether its required DAX behavior could be served by a reusable DAX user-defined function package before presenting the specification as finalized. For applicable specifications, the architect SHALL search the DAX Lib catalog and inspect relevant package descriptions and documentation. The architect SHALL base searches on generic functional needs and SHALL NOT submit confidential business data, model contents, or credentials to the public catalog.

#### Scenario: Relevant packages are found
- **WHEN** a completed specification contains behavior that may be supplied by a DAX user-defined function package and catalog candidates are returned
- **THEN** the specification SHALL record candidate package identity and version, links, functional fit, relevant compatibility evidence, license, known limitations, and a reasoned recommendation before finalization

#### Scenario: No suitable package is found
- **WHEN** the catalog search completes but no candidate satisfies the specification's functional or compatibility needs
- **THEN** the specification SHALL record the search outcome and why no candidate is suitable, and the review gate SHALL be considered complete

#### Scenario: DAX library review is not applicable
- **WHEN** the completed specification contains no DAX behavior that could reasonably be supplied by a DAX user-defined function package
- **THEN** the specification SHALL record that the review is not applicable and the reason before finalization

### Requirement: Unavailable catalog review remains visible
When the DAX Lib search or package-inspection capability is unavailable or fails, the `powerbi-architect` SHALL identify the review as unresolved and SHALL NOT present the specification as having passed the gate. The architect MAY proceed only after the user explicitly accepts the unresolved review as an exception, which SHALL be recorded with the review outcome.

#### Scenario: DAX Lib MCP is unavailable
- **WHEN** the architect reaches the review checkpoint and cannot access the required DAX Lib search or inspection capability
- **THEN** the architect SHALL report the unavailable capability, identify the review as unresolved, and request configuration or explicit user acceptance of an exception

#### Scenario: User accepts an unavailable-review exception
- **WHEN** the user explicitly accepts proceeding without the DAX Lib review
- **THEN** the specification SHALL record that the gate was bypassed by user acceptance and SHALL NOT represent the result as a completed catalog review

### Requirement: Architect review cannot mutate a model
The DAX library review SHALL be read-only. The `powerbi-architect` SHALL NOT install a package, change a semantic model, or claim that a candidate improves runtime performance solely because it appears in the catalog. Package installation or performance validation SHALL require a separate user-authorized implementation or validation action.

#### Scenario: Candidate package is recommended
- **WHEN** the architect recommends a DAX Lib package for a specification
- **THEN** the architect SHALL describe it as a candidate for developer evaluation and SHALL NOT install it or modify a model

#### Scenario: Performance benefit is not measured
- **WHEN** catalog metadata describes a package but no target-model performance validation has been performed
- **THEN** the specification SHALL NOT claim that using the package improves performance