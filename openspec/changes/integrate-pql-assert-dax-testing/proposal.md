## Why

There is no reusable, repeatable way in this repo to unit-test Power BI semantic model measures or certify their business-approved values — measure quality checks are ad hoc, and the BI COE's GATE-001 "Measure Certification & Testing" gate has no skill/agent to depend on. Integrating the PQL.Assert DAX unit testing library gives the `powerbi` plugin a dedicated testing skill, agent, and CSV-based certification registry contract that GATE-001-style gates (and everyday measure development) can consume, while allowing developers to establish initial executable coverage before business certification is available.

## What Changes

- Add a `dax-unit-testing` skill to `plugins/powerbi/skills/` staging the PQL.Assert assertion library (`functions.tmdl`), model-independence and reserved-word references, the `Certification/MeasureCertification.csv` registry schema (columns, `TestCategory`/`Status`/`ApprovalSource` lifecycle, `FilterExpression` rules, integrity checklist), four automation scripts (`validate_registry.py`, `generate_measure_tests.py`, `certify_measures.py`, `coverage_report.py`), and a cleaned Fabric notebook test runner (`RunPQLAssertTests.ipynb`).
- Add model-wide **test coverage statistics** reporting (`coverage_report.py`): read-only % of measures with any registry row (vs. untested), % with executable `Structural`/developer-certified/business-certified rows, and a `TestCategory` × `Status` × `ApprovalSource` breakdown, emitted as `reports/coverage.json` and `reports/coverage-summary.md`.
- Add a dedicated `pql-tester` agent (`plugins/powerbi/agents/pql-tester.agent.md`) with explicit, separately-invoked operating modes: `scan`, `sync`, `generate`, `run`, `report` (including coverage stats), `diagnose` — plus guardrails preventing fabrication of business-approved values, tolerance-widening, silencing failures, or modifying production model objects.
- Update `powerbi-architect.agent.md` to plan a progressive test-task pattern (`sync` → developer baseline certification → `generate`+`run`, followed by optional additive business certification) for every new/modified measure in specs authored after this change lands.
- Update `powerbi-developer.agent.md` and `semantic-model-authoring/SKILL.md` to route test-generation requests to `pql-tester`/`dax-unit-testing`.
- Update `plugins/powerbi/README.md`, `AGENTS.md`, and `CLAUDE.md` to register the new skill and agent.

## Capabilities

### New Capabilities
- `powerbi/dax-unit-testing`: DAX Query View unit-testing skill — assertion library staging, the measure certification registry contract (schema, lifecycle, integrity rules), the validate/generate/certify/coverage automation scripts, and the progressive certification workflow (Structural, developer-certified, then optional business-certified checks).
- `powerbi/pql-tester-agent`: dedicated testing agent — its operating modes (scan/sync/generate/run/report/diagnose), the developer-certification and business-value guardrails, and its write-scope/secret-handling constraints.
- `powerbi/architect-test-planning`: `powerbi-architect` agent's requirement to emit the sync → developer-certification → generate/run chain, with optional additive business-certification tasks, for every new or modified measure in specs authored after this change.

### Modified Capabilities
<!-- none: openspec/specs has no existing capabilities yet, so every behavior introduced here is new -->

## Impact

- New: `plugins/powerbi/skills/dax-unit-testing/**` (SKILL.md, references/, assets/, assets/scripts/).
- New: `plugins/powerbi/agents/pql-tester.agent.md`.
- Modified: `plugins/powerbi/agents/powerbi-architect.agent.md`, `plugins/powerbi/agents/powerbi-developer.agent.md`, `plugins/powerbi/skills/semantic-model-authoring/SKILL.md`, `plugins/powerbi/README.md`, `AGENTS.md`, `CLAUDE.md`.
- Depends on PQL.Assert 0.6.0 assertion functions/UDF library sourced from `C:\Development\PQL.Assert`.
- No changes to existing `dax-data-quality` skill (Power Query row-level checks remain separate from DAX Query View unit assertions).
- Does not implement GATE-001's own CI/PR enforcement plumbing — this change is a dependency GATE-001 consumes, not GATE-001 itself.
- Tracked against Jira **FIN-1787** on branch `feature/FIN-1787-glasslake-testing-framework`.
