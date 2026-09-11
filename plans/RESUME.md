# Resume Notes: PQL.Assert / GATE-001 Integration Plan

**Plan file:** [plan-pqlAssertIntegration.prompt.md](plan-pqlAssertIntegration.prompt.md)
**Ticket:** FIN-1787 ("Glasslake Testing Framework"), branch `feature/FIN-1787-glasslake-testing-framework`
**Source spec reviewed (not in repo, was a chat attachment):** `GATE-001-measure-certification.prompt.md` — BI COE's "Measure Certification & Testing" gate, originally from `c:\Users\IOURICHADOUR\Downloads\GATE-001-measure-certification.prompt (1).md`. Re-attach it if a future session needs to re-verify section numbers (§5, §7, §8, §14 are cited throughout the plan).

This file tracks the PQL.Assert planning work, the separate dependency-checking OpenSpec change, and decisions that future implementation work must preserve.

---

## 1. Completed planning work

- [OpenSpec change](../openspec/changes/integrate-pql-assert-dax-testing) is complete and passes `openspec validate --strict --changes "integrate-pql-assert-dax-testing"`. It contains `proposal.md`, `design.md`, `tasks.md`, and three new capability specs: `powerbi/dax-unit-testing`, `powerbi/pql-tester-agent`, and `powerbi/architect-test-planning`.
- Full GATE-001 CSV registry model is planned: `Certification/MeasureCertification.csv` schema reference, four automation scripts (`validate_registry.py`, `generate_measure_tests.py`, `certify_measures.py`, `coverage_report.py`), registry-driven `SKILL.md` workflow, model-wide coverage statistics, and the fixed error-type vocabulary.
- `pql-tester.agent.md` is planned with the full mode set (`scan`/`sync`/`generate`/`run`/`report`/`diagnose`), DEV/CLOUD execution, a restricted write scope, and no-silent-failure-suppression guardrails.
- `powerbi-architect.agent.md` is planned to include the progressive measure-testing chain: `sync` (automated Structural coverage) → developer certification of an explicit, reproducible baseline → `generate`+`run`; business certification is an optional additive step, never a blocking prerequisite.
- One-time prerequisite rule for deploying `functions.tmdl` before the first `sync` task.
- Verification includes registry-integrity fixtures, idempotent generation, content-hash tamper detection, sync behavior, coverage-report statistics, branch guard, and strict OpenSpec validation.
- GATE-001's CI/PR plumbing (JUnit publication, PR comments, blocking-merge rollout) remains explicitly **out of scope**. This work supplies reusable tooling that a target semantic model project's gate consumes.

## 2. Decisions recorded

### 2a. DECIDED AGAINST — do not mirror/reuse the DQ skills' files or structure for `dax-unit-testing`

An earlier recommendation (this session) proposed mirroring `dax-data-quality`/`sql-data-quality`'s file layout and approval-gate UX for `dax-unit-testing` — e.g. an `interaction-playbook.md` and `examples/*.csv` styled after theirs, cross-linked to their docs. **Rejected.** Decision: keep `dax-unit-testing` fully independent from `dax-data-quality`/`sql-data-quality` — no shared/mirrored reference files, no cross-linking between the skills' docs, no styling `dax-unit-testing`'s SKILL.md or registry docs after theirs. Rationale: per §2b below, the two are testing fundamentally different things (model/measure logic vs. row-level data values); making their file layout or wording look like variations of the same pattern risks users conflating a data-quality exception with a broken measure/relationship, or assuming the two registries (`MeasureCertification.csv` vs `dq_rules.csv`) are interchangeable or migrate the same way. `dax-unit-testing`'s own `SKILL.md`, `references/`, and any registry-workflow documentation should be authored on their own terms, informed only by GATE-001 and the PQL.Assert framework — not by the DQ skills' conventions.

The PowerShell-vs-Python scripting-language point still stands on its own merits (Python for `dax-unit-testing`'s scripts is justified by shared fixtures/CLOUD-XMLA connectivity with the existing Python DAX Test Framework and notebook runner) but should be explained from that rationale alone, not framed as a divergence from the DQ skills.

### 2b. Clarify scope: `dax-unit-testing` tests the model, DQ skills test the data

User correction, important and correct: `dax-data-quality`/`sql-data-quality` validate **data** (row-level field values — blanks, duplicates, domain/range violations, referential integrity via `RuleType`: `KeyNotBlank/KeyUnique/TypeNumber/TypeDate/Range/Domain/RI`). `dax-unit-testing` (PQL.Assert) validates the **model** — DAX logic, relationships, partitions, perspectives, OLS, and measure behavior under specific filter contexts (`TestCategory`: `Structural/Certification/Aggregation/Regression`, plus the broader assertion taxonomy: Relationship, Partition, Perspective, OLS, Best Practice). A model can be logically perfect and still fail every DQ check (dirty source data), or pass every DQ check and still have a broken measure/relationship. These are orthogonal axes, not overlapping ones — the CSV+approval-gate *mechanism* is reusable UX, but `MeasureCertification.csv` is not a same-shape rename of `dq_rules.csv`.

Implementation must preserve this boundary: `dax-unit-testing`'s assertion taxonomy is broader than the `MeasureCertification.csv` registry. Relationship/Partition/Perspective/OLS/Best-Practice assertions are structural, agent-verifiable checks that do not need developer or business certification and may later back a GATE-002-style semantic-model-governance gate. `Certification`/`Aggregation`/`Regression` measure-value tests use the progressive registry path: `Pending` → developer-approved executable baseline and, optionally, additive business certification.

Keep this distinction explicit in the skill documentation: `dax-data-quality`/`sql-data-quality` test data; `dax-unit-testing` tests model behavior. Their registries are neither interchangeable nor migration-compatible.

### 2c. DECIDED — progressive certification replaces a blocking business checkpoint

The original plan's mandatory business-approval checkpoint was replaced in the OpenSpec change. A developer can explicitly certify an observed, reproducible baseline and make it executable immediately; the row records `Status=Approved`, `ApprovalSource=Developer`, `ApprovedBy`, and `ApprovedOn`. `Structural` rows use `ApprovalSource=Structural` and remain fully automated. Later business-owned checks are additive rows or certifications recorded as `ApprovalSource=Business`; they do not block `sync`, generation, or execution of the developer baseline.

`ApprovalSource` is intentionally separate from `Status`: `Status=Approved` means eligible for generation/execution, not necessarily business-signed-off. Coverage reporting must independently show Structural, developer-certified, and business-certified coverage rather than collapsing them into one percentage.

## 3. Separate Power BI dependency-checking change

- [OpenSpec change](../openspec/changes/add-python-powerbi-dependency-checking) is complete and passes `openspec validate --strict --changes "add-python-powerbi-dependency-checking"`. It contains the proposal, design, tasks, and a new `powerbi/dependency-checking` capability spec.
- It adds a standalone `powerbi-dependency-checking` skill, not a subfeature of `dax-unit-testing`. The planned Python static scanner analyzes local PBIP/TMDL/PBIR source offline, builds a typed dependency graph, supports impact queries, identifies potentially unused objects, and returns stable human-readable/JSON/quiet outputs suitable for CI.
- The design is informed by ripbi's local-PBIP static-analysis approach but implements an independent Python tool, rather than vendoring or requiring ripbi's Rust binary.
- Route architecture, semantic-model authoring, report authoring, and DAX-unit-testing workflows to it before rename/removal, dependency-sensitive changes, or test-coverage impact review. Findings are advisory evidence only; the tool never changes PBIP source or deletes objects.
- Keep the existing `powerbi-report-authoring` report-term scanner unchanged. It serves targeted raw-text searches; dependency checking provides the complete cross-model graph.

## 4. Next steps when resuming

1. Start implementation with `/opsx-apply` for `integrate-pql-assert-dax-testing` or `add-python-powerbi-dependency-checking`, depending on the priority.
2. Follow the selected change's task order; preserve §§2a-2c for PQL.Assert implementation and §3's standalone ownership boundary for dependency checking.
3. Do not add an `interaction-playbook.md`/`examples/` pair modeled after the DQ skills; any future supporting files for `dax-unit-testing` must be independently authored.
4. `plan-skillMigrationReview.prompt.md` remains an unrelated migration plan and was not touched by this work.

## 5. Unrelated addition this session: `spec-lifecycle` plugin scaffolded

Not part of the PQL.Assert/GATE-001 plan above — scaffolded in a separate conversation (paired with
Glasslake-1's OpenSpec pilot on the same `feature/FIN-1787-glasslake-testing-framework` branch) and
noted here only because it's the repo's only `RESUME.md`.

- New plugin: [plugins/spec-lifecycle](../plugins/spec-lifecycle) — one skill
  (`openspec-bridge`), no agent. Bridges an existing `powerbi-architect` `specs/<Name>.spec.md`
  into OpenSpec's proposal/specs/design/tasks change-tracking and archive lifecycle, with an
  explicit rule for when that's worth doing (iteratively-revised specs) vs. not (one-shot/
  implemented specs).
- Fully additive: does not touch `plugins/powerbi/*`, so `check-updates`/`skill-merge-planner`
  diffs against the upstream `skills-for-fabric` marketplace stay unaffected.
- Registered in `.claude-plugin/marketplace.json` and the top-level `README.md` plugin table.
- Not yet installed/tested via `setup-team-plugins.ps1 -PluginName spec-lifecycle`; not yet used
  against a real spec end-to-end. Next step if resuming this thread: dogfood it against
  Glasslake-1's `specs/Python-MCP-DAX-Test-Framework.spec.md` (already has a hand-built OpenSpec
  change at `openspec/changes/add-dax-test-framework` in that repo — good candidate to verify the
  skill's mapping instructions produce equivalent output).

## 6. Unrelated addition this session: `skill-merge-planner` scored via `skill-creator`'s eval loop

Also unrelated to the PQL.Assert/GATE-001 work above — a separate `/skill-creator` invocation to
evaluate and score `plugins/powerbi/skills/skill-merge-planner`. Noted here only because it's the
repo's only `RESUME.md`.

- Ran `quick_validate.py` (from the sibling `skill-creator` skill) against `skill-merge-planner`'s
  `SKILL.md`: **fails** — frontmatter `description` is 1144 chars, over the 1024-char limit. This
  is an objective defect independent of behavior; not yet fixed.
- Ran the full with-skill vs. no-skill baseline eval loop (2 test cases from the skill's existing
  `evals/evals.json`, graded against their existing `expectations`). Results saved under
  `plugins/powerbi/skills/skill-merge-planner-workspace/iteration-1/` (`benchmark.json`/`.md`,
  per-eval `grading.json`, and a static `review.html` viewer already generated and opened).
  - **With-skill: 90% pass rate. No-skill baseline: 100% pass rate** (skill currently *underperforms*
    a plain agent on one of the two test cases).
  - Eval 1 (explicit reference path pointing at `skill-creator`, which has no Power BI counterpart):
    with-skill scored 4/5 — it correctly found zero functionally-matched skill pairs but then, per
    Step 4's literal wording ("score every compared pair"), left the entire 7-dimension rubric table
    `N/A` instead of scoring anything. The baseline agent, unconstrained by that wording, used
    judgment to benchmark the nearest adjacent pair anyway (`skill-merge-planner` 32/35 vs.
    `skill-creator` 23/35) and produced a materially more complete, more useful plan from the same
    input.
  - Eval 2 (missing default sibling reference path): both configurations handled it identically and
    correctly (detected the missing path, refused to fabricate results, asked for the right input,
    preserved the plan-only scope). Non-discriminating — keep as a regression guard, not as primary
    evidence of skill value.
  - Both configurations respected the read-only/plan-only scope boundary in every run — no repo
    files were touched (verified via `git status`).
- **Two fixes identified but not yet applied** (paused for user confirmation before proceeding):
  1. Trim the frontmatter `description` under 1024 chars.
  2. Add guidance to Step 2/4 for the zero-functional-match case: still offer an architecture-only
     benchmark of the nearest adjacent skill for informational value, rather than leaving the rubric
     table empty.
- Next step if resuming this thread: apply the two fixes above, bump `metadata.version`, re-run the
  same 2-eval loop into `iteration-2/` (with `--previous-workspace iteration-1`), and confirm the
  with-skill pass rate closes the gap with (or exceeds) the 100% baseline.
