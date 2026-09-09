## 1. Skill Folder & Reference Assets

- [ ] 1.1 Create `plugins/powerbi/skills/dax-unit-testing/` with `references/` and `assets/assets/scripts/` subdirectories and verify the directory tree exists
- [ ] 1.2 Combine PQL.Assert library files from `C:\Development\PQL.Assert\src\lib\*.tmdl` into a single `references/functions.tmdl` and verify it parses with valid indentation/tabs and contains `annotation DAXLIB_PackageId = PQL.Assert`
- [ ] 1.3 Stage `references/model-independence.md` (from PQL.Assert's `model-independence/SKILL.md`) and `references/reserved-dax-words.md`, and verify both render as valid markdown with working relative links
- [ ] 1.4 Create `references/certification-registry-schema.md` documenting the exact `MeasureCertification.csv` column schema (`MeasureName, TestName, TestCategory, FilterExpression, ExpectedValue, Tolerance, Owner, Status, ApprovalSource, ApprovedBy, ApprovedOn, Severity, RequirementId, LastReviewed`), the `TestCategory` definitions, the executable `Status` lifecycle, the `ApprovalSource` audit trail (`Structural`/`Developer`/`Business`), the `FilterExpression` rule, and the full integrity-rule checklist, and verify it satisfies the `powerbi/dax-unit-testing` spec's registry-schema and status-lifecycle requirements

## 2. Registry Automation Scripts

- [ ] 2.1 Implement `assets/scripts/validate_registry.py` enforcing every integrity rule (header match, `MeasureName`+`TestName` uniqueness, `MeasureName` exists in model, permitted `TestCategory`/`Status`/`ApprovalSource`/`Severity` values, non-empty `FilterExpression` unless `Structural`, `ExpectedValue` valid when `Approved`, `Tolerance >= 0`, ISO `ApprovedOn`/`LastReviewed` where required) and reporting failures as `REGISTRY_INVALID`; verify against valid, malformed, and quoted-comma-`FilterExpression` fixtures
- [ ] 2.2 Implement `assets/scripts/generate_measure_tests.py` converting `Status=Approved` rows into one `.dax` file per measure with a `DO NOT EDIT BY HAND` header, skipping `Pending` (reported as `CERTIFICATION_PENDING`) and `Retired` rows; verify two runs against identical fixture input produce byte-identical output
- [ ] 2.3 Add a content-hash guard to `generate_measure_tests.py` that fails as `GENERATED_FILE_MODIFIED` instead of overwriting a hand-edited file; verify by hand-editing a generated `.dax` file and re-running generation
- [ ] 2.4 Implement `assets/scripts/certify_measures.py` with `scan` (read-only metadata compliance report: description, format string, display folder, home table, registry coverage) and `sync` (auto-generate + auto-approve `Structural` rows with `ApprovalSource=Structural`, append `Status=Pending` `Certification` placeholders, support explicit developer certification of a reproducible baseline with `ApprovalSource=Developer`, flag but never auto-delete orphaned rows, record business certification only when explicitly supplied); verify both modes against a fixture model + registry
- [ ] 2.5 Implement `assets/scripts/coverage_report.py` computing % measures with any registry row (vs. untested), executable `Structural` coverage, developer-certified and business-certified non-Structural coverage, and a `TestCategory` × `Status` × `ApprovalSource` breakdown, emitting `reports/coverage.json` and `reports/coverage-summary.md`; verify against a fixture model + registry with a mix of untested/pending/developer-certified/business-certified rows, confirming no writes occur to the registry or model

## 3. Fabric Notebook Runner & Skill Instructions

- [ ] 3.1 Copy `RunPQLAssertTests.ipynb` to `plugins/powerbi/skills/dax-unit-testing/assets/RunPQLAssertTests.ipynb` with execution output and session metadata stripped, and verify it is valid JSON with all cell outputs blank
- [ ] 3.2 Author `plugins/powerbi/skills/dax-unit-testing/SKILL.md` covering getting-started deployment, the DAX Query View test-creation workflow, environment governance (DEV/TEST/PROD/ANY), the assertion taxonomy, the Fabric notebook execution pattern, the progressive registry workflow (Structural, developer-certified baseline, optional business certification), the coverage-statistics workflow, and the full error-type vocabulary; verify YAML frontmatter syntax and that relative links resolve

## 4. `pql-tester` Agent

- [ ] 4.1 Create `plugins/powerbi/agents/pql-tester.agent.md` configured for Claude Haiku 4.5 with tools `vscode`, `read`, `edit`, `agent`, `powerbi-modeling-mcp/*`, defining the explicit `scan`/`sync`/`generate`/`run`/`report`/`diagnose` modes with no silent side effects between them; verify YAML frontmatter and mode definitions against the `powerbi/pql-tester-agent` spec's operating-modes requirement
- [ ] 4.2 Add progressive-certification guardrails (never invent `ExpectedValue`/`Owner`/`FilterExpression`/`RequirementId`; self-approve `Structural` rows with `ApprovalSource=Structural`; record a developer-approved reproducible baseline as `ApprovalSource=Developer`; record business values as `ApprovalSource=Business` only on explicit business approval) and verify them against the spec's progressive-certification requirement
- [ ] 4.3 Add DEV/CLOUD dual execution guidance (local Desktop vs. XMLA, identical artifacts, credentials from `PBI_WORKSPACE`/`PBI_MODEL`/`PBI_CLIENT_ID`/`PBI_TENANT_ID`/`PBI_CLIENT_SECRET` environment variables only, never logged) and verify against the spec's dual-execution-environment requirement
- [ ] 4.4 Add write-scope restriction (`Certification/`, `DAXQueries/`, `reports/`, `TESTING.md` only; never modify model objects), no-silent-failure-suppression guardrails (no tolerance widening, no retiring to silence, no deleting/disabling failing tests), and naming/structure conventions (`[Area].[Environment].Test(s)`, `UNION`-combined assertions, `daxQueries.json` maintenance); verify each against the corresponding `powerbi/pql-tester-agent` spec requirement

## 5. `powerbi-architect` Test-Task Planning

- [ ] 5.1 Update `plugins/powerbi/agents/powerbi-architect.agent.md` to add `dax-unit-testing` to the Skills to use list, described as the source of the registry schema and assertion taxonomy for planning (not writing DAX)
- [ ] 5.2 Add the progressive test-task-planning guideline (sync task → developer-certification → generate+run task, with optional additive business certification; calculated columns/layout-only tasks exempt) and verify against a spot-check spec containing a measure with no business value (baseline path remains executable) and one with a known business value (business certification is included but does not replace or block the baseline path)
- [ ] 5.3 Add the one-time PQL.Assert library-setup prerequisite rule and verify a spot-check spec whose first measure task targets an unequipped model includes exactly one setup task before the first `sync` task
- [ ] 5.4 Update the Spec Template's Tasks section guidance/example to show the progressive task sequence and add a test-coverage/registry-status/approval-source callout line to the Measures/Calculations guidance under Components and Interfaces; verify the rendered template matches the `powerbi/architect-test-planning` spec's task-chain requirement

## 6. Ecosystem Wiring & Documentation

- [ ] 6.1 Update `plugins/powerbi/README.md` to document the `pql-tester` agent and `dax-unit-testing` skill, and verify the new entries render correctly
- [ ] 6.2 Update `plugins/powerbi/agents/powerbi-developer.agent.md` to include `dax-unit-testing` and delegate DQV test generation to `pql-tester`; verify the routing reference resolves
- [ ] 6.3 Update `plugins/powerbi/skills/semantic-model-authoring/SKILL.md` to add a Workflow Selector row routing test requests to `dax-unit-testing`; verify the table entry is present and correctly formatted
- [ ] 6.4 Update `AGENTS.md` and `CLAUDE.md` to register `dax-unit-testing` and `pql-tester` in the skill/agent registries; verify both files list the new entries

## 7. Final Verification

- [ ] 7.1 Run `check_git_branch_guard.txt` to confirm branch compliance on `feature/FIN-1787-glasslake-testing-framework`
- [ ] 7.2 Inspect `git status` and `git diff` to confirm all additions are clean and match repo conventions
- [ ] 7.3 Run `openspec validate --strict` for this change and confirm no errors are reported
