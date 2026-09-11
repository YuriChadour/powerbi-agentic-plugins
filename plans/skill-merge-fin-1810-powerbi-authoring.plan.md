# Migration Plan: Keep Local `powerbi` Skills as Base, Selectively Graft from `skills-for-fabric\powerbi-authoring`

> **Strategy:** Local (`plugins/powerbi/skills`) becomes the base for every matched skill — it now scores higher or ties on the 7-dimension rubric across all 5 pairs — and the reference collection (`C:\Development\skills-for-fabric\plugins\powerbi-authoring\skills`) becomes a donor for a small number of specific, cost-effective additions only.

**Ticket:** FIN-1810 ("Merge updates from skills-for-fabric repo into Bayview"), branch `feature/FIN-1810-merge-skills-for-fabric-powerbi-authoring`
**Scope boundary:** This is a plan document only. No files were copied, deleted, or edited as part of producing it. Execution is a separate, explicit step to be approved per-phase.

---

## TL;DR

The reference collection (`skills-for-fabric\plugins\powerbi-authoring`) has aged relative to this repo's fork: it contains exactly the same 5 skill names as local (no reference-only skills, no capability gaps to import wholesale), and on 3 of 5 pairs its `SKILL.md` now references `scripts/`/`assets/` folders or companion skills (`fabriciq`) that don't actually exist in the current snapshot. Local wins the rubric on `powerbi-report-authoring` (31 vs 23), `powerbi-report-management` (28 vs 24), and `semantic-model-authoring` (31 vs 24), and is judged already-aligned/tied on `powerbi-report-design` (31 vs 30) and `powerbi-report-planning` (29 vs 29). Net outcome: **0 skills adopt reference as base, 3 skills get local-as-base merges with 1–2 small grafted files each, 2 skills are confirmed already-aligned with no file changes required, 0 wholesale imports, and 9 local-only skills are untouched.** The one genuinely valuable reference-only asset is `semantic-model-authoring/references/metadata-discovery.md`. Two phantom companion-skill redirects (`fabriciq`, `power-bi-custom-visuals`) must be stripped as part of the corresponding merges regardless of source.

**Note on prior art:** `plans/skill-merge.plan.md` (pre-existing) analyzed `powerbi-report-authoring` against an older reference path, `skills-for-fabric-1`, which **no longer exists on disk** — it was apparently replaced by the current `skills-for-fabric`. That plan recommended reference-as-base for `powerbi-report-authoring` on the strength of a `scripts/`/`assets/` bundle (BPA script, PBIR template) that **no longer ships** in the current reference snapshot. This plan supersedes that recommendation for `powerbi-report-authoring`: local is now the stronger and only-complete side.

---

## Skill-by-Skill Inventory & Disposition

| Reference | Local | Local /35 | Ref /35 | Disposition |
|---|---|---|---|---|
| `powerbi-report-authoring` | `powerbi-report-authoring` | 31 | 23 | **Merge, local as base** |
| `powerbi-report-design` | `powerbi-report-design` | 31 | 30 | **Already aligned** |
| `powerbi-report-management` | `powerbi-report-management` | 28 | 24 | **Merge, local as base** |
| `powerbi-report-planning` | `powerbi-report-planning` | 29 | 29 | **Already aligned** |
| `semantic-model-authoring` | `semantic-model-authoring` | 31 | 24 | **Merge, local as base** |
| *(none)* | `check-updates` | — | — | Keep as-is (local-only) |
| *(none)* | `dax-data-quality` | — | — | Keep as-is (local-only) |
| *(none)* | `dax-test-framework` | — | — | Keep as-is (local-only) |
| *(none)* | `dax-unit-testing` | — | — | Keep as-is (local-only) |
| *(none)* | `prep-powerbi-for-report-copilot` | — | — | Keep as-is (local-only) |
| *(none)* | `skill-merge-planner` | — | — | Keep as-is (local-only) |
| *(none)* | `skill-merge-planner-workspace` | — | — | Keep as-is (local-only, working artifacts) |
| *(none)* | `sql-data-quality` | — | — | Keep as-is (local-only) |
| *(none)* | `tmdl` | — | — | Keep as-is (local-only) |

**Confirmed infrastructure compatibility:** No reference-only skills exist, so there is no wholesale-import phase and no new cross-repo dependency to wire in. All 5 matched pairs already share the same routing-table/reference-file architecture pattern, so grafted files slot into existing `references/` folders without structural changes.

---

## Detailed Merge Plans

### 1. `powerbi-report-authoring` (local is base)

**Local architecture to adopt as base (unchanged):** existing routing table, CLI integrations (`powerbi-report-author`, `powerbi-desktop`), 30+ anti-pattern catalog, Must/Prefer/Avoid governance block, Edit→Validate→Reload→Screenshot loop, and the full `scripts/`+`assets/templateReport/` bundle (BPA script, BPA rules, PBIR starter report, dummy companion model).

**Cost-effective additions to graft from reference:**

| File | Why keep it | Action |
|---|---|---|
| *(none identified)* | Reference ships no `scripts/`/`assets/`, and all 22 same-named `references/*.md` files are near-identical in size/content to local's versions | No graft needed |

**Do NOT bring over:** Reference's `SKILL.md` body text describing BPA/template/dependency-scan tasks — it points to `scripts/bpa.ps1`, `scripts/bpa-rules-report.json`, `scripts/report_reference_scan.*`, and `assets/templateReport/**`, none of which exist in the current reference snapshot. Do not let any future sync re-introduce these as phantom references.

**Structural fixes required regardless of source:**
- None beyond periodic diffing of the 22 same-named reference files listed in the analysis (`card.md`, `conditional-formatting.md`, `formatting.md`, `table.md` showed the most byte-size drift and are the first to line-diff if a sync is desired).

### 2. `powerbi-report-management` (local is base)

**Local architecture to adopt as base (unchanged):** existing routing table and Must/Prefer/Avoid governance; no `references/`/`scripts/`/`assets/` on either side — this is a SKILL.md-only skill.

**Cost-effective additions to graft from reference:**

| File | Why keep it | Action |
|---|---|---|
| *(no separate file — body text only)* | Reference has stronger telemetry-header guidance and richer publish-path/LRO (long-running operation) and duplicate-report-recovery troubleshooting language | Manually port the relevant paragraphs into local `SKILL.md`'s existing troubleshooting/telemetry sections; do not restructure the file |

**Do NOT bring over:** Reference frontmatter's `fabriciq` redirect for data-question routing — no such skill exists in either repo (see Decision 1).

**Structural fixes required regardless of source:**
- Confirm local `SKILL.md` has no equivalent phantom redirect before/after the text port.

### 3. `semantic-model-authoring` (local is base)

**Local architecture to adopt as base (unchanged):** existing routing table, delegation to `dax-unit-testing`/`pql-tester`/report-authoring, DAX query/UDF guideline refs, and the `scripts/bpa-rules-semanticmodel.json` + `scripts/bpa.ps1` bundle.

**Cost-effective additions to graft from reference:**

| File | Why keep it | Action |
|---|---|---|
| `references/metadata-discovery.md` (~7 KB) | Genuine reference-only addition: a dedicated metadata-discovery workflow not present locally | Copy into local `references/`, add a routing-table row in local `SKILL.md` pointing to it, and lightly edit for local terminology/CLI consistency |

**Do NOT bring over:** Reference frontmatter's `fabriciq` redirect (same phantom issue as `powerbi-report-management`, see Decision 1).

**Structural fixes required regardless of source:**
- After grafting `metadata-discovery.md`, verify no other local reference file already partially covers metadata discovery (avoid duplication) — the analysis found none, but confirm at merge time.

### 4. `powerbi-report-design` (already aligned — no merge required)

Architecture ties (31 vs 30). Local carries 6 extra local-only topic refs (`cards-and-kpis.md`, `custom-visuals.md`, `filter-pane.md`, `mobile.md`, `tables-and-matrices.md`, `tooltips-and-annotations.md`) with no reference counterpart — keep all six as-is. 19 same-named files are near-identical; only `accessibility.md`, `layout.md`, `operational-monitor.md`, and `visual-cookbook.md` showed minor byte-size drift and are optional low-priority diff targets, not required for this plan.

**Structural fix required regardless of source:** local `custom-visuals.md` redirects to a `power-bi-custom-visuals` companion skill that doesn't exist in either repo (see Decision 1) — strip or rewrite that redirect independent of any reference-side merge.

### 5. `powerbi-report-planning` (already aligned — no merge required)

Tied rubric (29 vs 29), SKILL.md-only skill (no companion files on either side), functionally the same round-based planning workflow. No action required beyond periodic re-diff if either side changes.

### 6. Exclude: `fabriciq` companion-skill mechanism

Referenced only in the *reference* copies of `powerbi-report-management` and `semantic-model-authoring` frontmatter/body as a redirect target for data-question routing. Not imported: no `fabriciq` skill or file exists in either repo, and this repo has no equivalent capability to route to. If left in place after merging body text, it would become a phantom reference. Strip it during Phase 3 (Section 3.2/3.3 below) rather than porting it verbatim.

### 7. Exclude: Reference `powerbi-report-authoring`'s "periodic GitHub release check" language

The current reference `SKILL.md` body still describes a PBI Inspector download/update flow, but ships no backing `scripts/`/`assets/`. Not imported — this repo already has its own `check-updates` skill for explicit, repo-appropriate update checking, and importing reference's now-unbacked language would recreate a phantom reference.

---

## Steps (Implementation Order)

### Phase 1 — Wholesale Imports
*None required.* No reference-only skills exist to import.

### Phase 2 — Verify Already-Aligned Skills (independent, parallel-safe)
2.1 Diff `powerbi-report-design`'s 19 same-named reference files against the current reference copies; confirm the 4 flagged files (`accessibility.md`, `layout.md`, `operational-monitor.md`, `visual-cookbook.md`) have no reference-side improvement worth porting.
2.2 Diff `powerbi-report-planning`'s `SKILL.md` bodies line-by-line to confirm no drift beyond wording.
2.3 Strip/rewrite the phantom `power-bi-custom-visuals` redirect in local `powerbi-report-design/references/custom-visuals.md`.

### Phase 3 — Merge `powerbi-report-management` and `semantic-model-authoring` (parallel-safe, independent of each other)
3.1 For `powerbi-report-management`: port the telemetry-header and publish-path/LRO troubleshooting paragraphs from reference `SKILL.md` into local `SKILL.md`'s existing sections (no new files).
3.2 Strip the `fabriciq` redirect from the ported text; confirm no residual mention remains.
3.3 For `semantic-model-authoring`: copy `references/metadata-discovery.md` from reference into local `references/`.
3.4 Add a routing-table row in local `semantic-model-authoring/SKILL.md` pointing to the newly-grafted `metadata-discovery.md`.
3.5 Strip the `fabriciq` redirect from any ported reference text for this skill.
3.6 Bump `metadata.version` (semver patch/minor bump per repo convention) on both merged `SKILL.md` files.

### Phase 4 — Verify `powerbi-report-authoring` Requires No Merge Action
4.1 Confirm (already done in this plan's analysis) that reference ships no `scripts/`/`assets/` and no same-named reference file differs materially from local.
4.2 No file changes required for this skill under this plan; local stays exactly as-is.

### Phase 5 — Repo-Level Wiring & Cleanup
5.1 Update `plugins/powerbi/README.md` if the `metadata-discovery.md` addition changes the skill's documented capability list.
5.2 Confirm no repo-wide text (README, agent files) references `fabriciq` or `power-bi-custom-visuals` outside the two files fixed above.
5.3 Confirm all 5 merged/aligned skills have valid semver `metadata.version` after Phase 3's bumps.

---

## Verification

1. `plugins/powerbi/skills/` still contains exactly the same 14 skill folders — no new or removed folders (no wholesale imports in this plan).
2. `grep -r "fabriciq"` across `plugins/powerbi/skills/powerbi-report-management` and `plugins/powerbi/skills/semantic-model-authoring` → 0 matches after Phase 3.
3. `grep -r "power-bi-custom-visuals"` across `plugins/powerbi/skills/powerbi-report-design` → 0 matches after Phase 2.3.
4. `plugins/powerbi/skills/semantic-model-authoring/references/metadata-discovery.md` exists and is cross-linked from that skill's `SKILL.md` routing table.
5. All 5 matched skills' `SKILL.md` have `metadata.version` in valid semver format.
6. Existing BPA scripts (`powerbi-report-authoring/scripts/bpa.ps1`, `semantic-model-authoring/scripts/bpa.ps1`) still run unmodified — this plan does not touch either.

---

## Decisions

### Decision 1: Strip all phantom companion-skill redirects rather than importing/creating stub skills
**Choice:** Remove/rewrite `fabriciq` (2 occurrences, reference-side) and `power-bi-custom-visuals` (1 occurrence, local-side) redirects rather than treating them as capability gaps to fill.
**Rationale:** Neither companion skill exists in either repo; leaving them in place after a merge would create broken routing that agents following the SKILL.md would hit as a dead end. No user request indicated these companions should be built.
**Alternative considered:** Scaffold stub skills for `fabriciq`/`power-bi-custom-visuals` — rejected as out of scope for a merge-planning task; would require its own design/proposal.

### Decision 2: Treat the older `skills-for-fabric-1`-based `plans/skill-merge.plan.md` as superseded, not merged with this plan
**Choice:** This plan stands alone and does not attempt to reconcile line-by-line with the prior plan's recommendation (reference-as-base for `powerbi-report-authoring`).
**Rationale:** The prior plan's reference path (`skills-for-fabric-1`) no longer exists on disk; its `scripts/`/`assets/` inventory for reference-side `powerbi-report-authoring` is stale and does not reflect the current `skills-for-fabric` snapshot, which ships neither folder.
**Alternative considered:** Archive/delete `plans/skill-merge.plan.md` — deferred to the user; not done as part of this plan-only step.

### Decision 3: Do not run `quick_validate.py` results as ground truth — inferred from source + frontmatter instead
**Choice:** The background analysis inferred pass/fail from `quick_validate.py`'s validation logic plus manual frontmatter inspection, because live script execution was blocked by the sandboxed environment (`Permission denied`) during analysis.
**Rationale:** All 10 `SKILL.md` files (5 pairs) have valid YAML frontmatter, kebab-case names, and description lengths within limits by manual inspection; the only rubric impact identified was reference `semantic-model-authoring`'s missing `metadata.version`, which independently caps its Version-hygiene dimension at 2 per the rubric's own rule.
**Alternative considered:** Re-run `quick_validate.py` in an unrestricted shell before finalizing this plan — recommended as a Phase 0 sanity check before Phase 3 execution begins, since it is cheap and removes the one inference in this plan.

---

## Further Considerations

1. **Re-run `quick_validate.py` for real before execution.** Live execution was blocked during analysis (process-launch permission denial); scores here rely on manual inference. Low risk given manual frontmatter review, but should be confirmed with a working shell before Phase 3 starts.
2. **`powerbi-report-management`'s Phase 3 merge is text-only** (no companion files), so it requires careful manual editing rather than a mechanical file copy — re-read the full merged section afterward for tone/structure consistency with the rest of local's `SKILL.md`.
3. **The 4 flagged `powerbi-report-design` files** (`accessibility.md`, `layout.md`, `operational-monitor.md`, `visual-cookbook.md`) showed byte-size drift but were not deep-diffed line-by-line in this pass — Phase 2.1 should do that diff before considering `powerbi-report-design` fully verified.
4. **This plan does not address** the local-only `skill-merge-planner-workspace/iteration-1` eval artifacts or the two previously-identified `skill-merge-planner` self-fixes (frontmatter description length, zero-functional-match guidance) noted in `plans/RESUME.md` §6 — those are a separate, already-scoped follow-up, not part of this ticket.
5. **No reference-only skill or mechanism required exclusion beyond the two phantom redirects and the stale PBI-Inspector update-check language** already covered in Decision 1 and the "Exclude" sections above.

---

## Skill Quality Rating — Skill-Authoring Quality Rubric v1 (1–5 scale, /35 total)

> Not an official Anthropic-published framework — see `plugins/powerbi/skills/skill-merge-planner/references/skill-quality-rubric.md` for the caveat and dimension definitions. `quick_validate.py` results below are inferred from source + manual frontmatter review (see Decision 3), not a live run.

### `powerbi-report-authoring`

| Dimension | Local | Reference |
|---|---|---|
| Conciseness / context cost | 3 | 4 |
| Progressive disclosure | 4 | 3 |
| No duplication / boundary | 5 | 2 |
| Degrees-of-freedom matching | 5 | 4 |
| Description/trigger quality | 5 | 4 |
| No extraneous files | 4 | 3 |
| Version hygiene | 5 | 3 |
| **Total (/35)** | **31** | **23** |

### `powerbi-report-design`

| Dimension | Local | Reference |
|---|---|---|
| Conciseness / context cost | 4 | 4 |
| Progressive disclosure | 5 | 5 |
| No duplication / boundary | 4 | 5 |
| Degrees-of-freedom matching | 5 | 5 |
| Description/trigger quality | 4 | 4 |
| No extraneous files | 4 | 4 |
| Version hygiene | 5 | 3 |
| **Total (/35)** | **31** | **30** |

### `powerbi-report-management`

| Dimension | Local | Reference |
|---|---|---|
| Conciseness / context cost | 3 | 3 |
| Progressive disclosure | 4 | 4 |
| No duplication / boundary | 5 | 3 |
| Degrees-of-freedom matching | 4 | 5 |
| Description/trigger quality | 5 | 2 |
| No extraneous files | 4 | 4 |
| Version hygiene | 3 | 3 |
| **Total (/35)** | **28** | **24** |

### `powerbi-report-planning`

| Dimension | Local | Reference |
|---|---|---|
| Conciseness / context cost | 3 | 3 |
| Progressive disclosure | 5 | 5 |
| No duplication / boundary | 5 | 5 |
| Degrees-of-freedom matching | 5 | 5 |
| Description/trigger quality | 4 | 4 |
| No extraneous files | 4 | 4 |
| Version hygiene | 3 | 3 |
| **Total (/35)** | **29** | **29** |

### `semantic-model-authoring`

| Dimension | Local | Reference |
|---|---|---|
| Conciseness / context cost | 3 | 3 |
| Progressive disclosure | 4 | 5 |
| No duplication / boundary | 5 | 3 |
| Degrees-of-freedom matching | 5 | 5 |
| Description/trigger quality | 5 | 2 |
| No extraneous files | 4 | 4 |
| Version hygiene | 5 | 2 |
| **Total (/35)** | **31** | **24** |

**Reading the scores:** `powerbi-report-authoring`, `powerbi-report-management`, and `semantic-model-authoring` all show a clear, rubric-supported case for local-as-base — the gaps are driven mainly by reference-side phantom references (missing `scripts/`/`assets/`, `fabriciq` redirects) and missing `metadata.version`, not by local being architecturally weaker. `powerbi-report-design` and `powerbi-report-planning` are close enough (1-point and 0-point gaps) that "already aligned" is the correct call — the scores do not capture the small but real content differences (local's 6 extra design-topic refs, reference's `metadata-discovery.md`), which are handled separately in the file-inventory sections above.
