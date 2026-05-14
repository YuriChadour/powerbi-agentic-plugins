---
name: prep-powerbi-for-report-copilot
description: |
   This skill should be used to optimize a Power BI report and semantic model so the Report Copilot pane can reliably answer common questions using existing visuals (preferred) and generate accurate visuals when querying the semantic model. Use when asked to "prep a report for Copilot", "improve Copilot answers", "build an Answer Pack", "create AI instructions for Power BI", "design an AI data schema", or "test Copilot behavior". Provides a step-by-step workflow, templates, and governance for Copilot readiness.
---

# Skill: Prep Power BI for Report Copilot Pane (Schema + Instructions + Answer Pack)
**Skill ID:** prep-powerbi-for-report-copilot  
**Version:** 1.0.0  
**Primary Objective:** Optimize an existing Power BI report + semantic model so the **Report Copilot pane** reliably:
1) answers common questions using **existing visuals** (preferred), and  
2) generates accurate visuals when it must query the semantic model.

**Why this matters:** In the report Copilot pane, Copilot checks whether an answer can be found in report visuals; if not, it queries the model and builds a visual.

---

## Agent Mode

This skill supports two operating modes. **Select one based on whether the model has native reasoning/chain-of-thought capability.**

| Mode | Models | Behavior |
|------|--------|----------|
| **Reasoning** | o1, o3, o3-mini, o4-mini, Claude (all versions), GPT-5 and above | Full workflow. Model self-plans, handles ambiguity, and makes multi-step decisions autonomously. Use Variant A template. |
| **Non-reasoning** | GPT-4.1, GPT-4.1 mini, GPT-4o, GPT-4o mini, and any model below GPT-4.1 | Simplified workflow. Uses explicit step-by-step instructions with no open choices. Every decision is pre-made for the model. Use Variant B template. |

> **Reasoning models** (o-series, Claude, GPT-5+) plan and reflect internally — give them latitude.  
> **Non-reasoning models** (GPT-4.1, GPT-4o, and their minis) are instruction-following only — they need every step spelled out explicitly with examples.

**If the model is unknown, use Non-reasoning (Variant B)** — it is always safe.

---

## What this skill produces (Outputs)
Create the following repo artifacts (Markdown, repo-controlled):

1) `docs/copilot-prep/01-report-usage-inventory.md`
   - Pages → visuals → fields/measures used (axes, legend, values, tooltips)
   - Filters used (visual/page/report), slicers, drillthrough
   - Calculated measure usage frequency

2) `docs/copilot-prep/02-ai-schema-recommendations.md`
   - **Include list** (fields/measures Copilot should reason over)
   - **Exclude list** (hide from Copilot by removing from AI data schema)
   - **Model-hide suggestions** (optional): fields that should be hidden from users too
   - Rationale for each group (technical ID, unused, ambiguous, sensitive)

3) `docs/copilot-prep/03-ai-instructions.md`
   - Concise Copilot Instructions in a structured format (similar to BLAST example)
   - Terminology defaults, metric defaults, date clarifications, response format rules
   - “How to interpret questions” rules
   - Optional “Verified Answers” and “Answer Pack” references

4) `docs/copilot-prep/04-answer-pack-design.md`
   - Answer Pack page plan (pages, visuals, titles, anchor text)
   - Question → target visual mapping
   - Naming standards for visuals and pages
   - Testing prompts for each visual

5) `docs/copilot-prep/05-test-script-and-results.md`
   - Prompt → expected behavior → actual behavior
   - Fix applied (title changes, schema refinement, instruction tweak)

Optional (if permitted and tooling available):
- Configure **AI data schema**, **AI instructions**, and **Verified Answers** in Power BI Desktop / Service via Prep data for AI.
- Create Answer Pack pages inside the report.

---

## Required Inputs (Agent MUST ask if missing)
1) Repo path and report format:
   - PBIP (preferred) or PBIX
2) Report name and primary semantic model name
3) Business domain (2–5 sentences)
4) Primary user personas (exec/analyst/risk/etc.)
5) Top questions (min 10; ideal 25–50)
6) Sensitive fields policy (PII, restricted dims, internal-only measures)
7) Environment (Dev/Test/Prod) + any naming conventions

---

## Guardrails & Governance
- Do not surface restricted or sensitive fields in AI data schema or Answer Pack visuals.
- Prefer excluding sensitive fields from AI schema rather than relying on Copilot behavior.
- Avoid breaking changes: add new curated measures instead of altering widely used ones unless instructed.
- Keep Copilot instructions concise and deterministic; avoid speculative narrative.

---

# Workflow (Agent Playbook)

## Step 0 — Discover & baseline

> **Skills to load:** Load the **`pbip`** skill first to understand the project's folder layout (`definition/`, `pages/`, `visuals/`, `Copilot/`, `StaticResources/`, `DAXQueries/`). If Power BI Desktop is open and live model enumeration is needed, also load the **`connect-pbid`** skill.

1) Identify report artifact(s):
   - PBIP: locate the `.Report/definition/` folder (PBIR format) and the `.SemanticModel/definition/` folder (TMDL format). The `pbip` skill describes the full tree.
   - PBIX: note that you may need to export to PBIP (File > Save As in PBI Desktop) to enable file-level inspection. The `pbip` skill describes the conversion steps.
   - Also locate `<Name>.SemanticModel/Copilot/` — this is where AI instructions and AI data schema artifacts are stored (see `pbip` skill).
2) Capture baseline Copilot behavior:
   - Run 10 representative prompts in Report Copilot pane
   - Record what Copilot used: existing visual vs generated visual

Deliverable: Baseline section in `05-test-script-and-results.md`

---

## Step 1 — Build a Report Usage Inventory (what the report actually uses)
**Goal:** Determine which model objects are used by report visuals and filters.

### Preferred (PBIP)
Parse report definitions to extract:
- Visual fields:
  - axis / legend / values / tooltips
- Filters:
  - visual/page/report filters
- Slicers:
  - slicer fields
- Drillthrough and tooltips pages:
  - drillthrough fields and tooltip fields
- Measures:
  - measure names referenced in visuals (and how often)

### Fallback (PBIX without extraction)
Use authoring tools (manual) to gather:
- Fields listed in each visual’s field well
- Fields used in slicers and filter panes
- Measures used on each page

**Output:** `01-report-usage-inventory.md`

---

## Step 2 — Recommend “Hide from Copilot” list (AI Data Schema design)
**Goal:** Create a focused AI data schema:
- INCLUDE: objects Copilot should reason over
- EXCLUDE: objects to hide from Copilot (remove from AI data schema)
> **Skills to load (preferred — MCP path):**
> 1. Load the **`powerbi-consumption-cli`** skill and ask the user for the semantic model artifact ID
>    (found in the Fabric URL: `.../dataset/{artifactId}`).
> 2. Run these DAX INFO queries in order:
>    - `EVALUATE INFO.VIEW.RELATIONSHIPS()` — **run first**; maps every FK column on the fact table
>      (`[FromColumn]`) to its dimension. These FK columns must be EXCLUDED.
>    - `EVALUATE INFO.VIEW.COLUMNS()` — full column inventory with `[Table]`, `[Name]`,
>      `[DataType]`, `[IsHidden]`, `[DisplayFolder]`
>    - `EVALUATE INFO.VIEW.MEASURES()` — all measures with `[DisplayFolder]` and `[IsHidden]`
>      for classification
> 3. Every `[FromColumn]` value in the relationships result is a FK on the fact table → EXCLUDE in the schema.
>
> **Fallback (no service connection — TMDL path):**
> Load the **`tmdl`** skill and read all `.tmdl` files in `<Name>.SemanticModel/definition/tables/`.
> **Caution:** TMDL parsing is fragile — scan `dim_*` tables separately from the fact table,
> cross-reference `relationships.tmdl` manually for FK columns, and verify every column name
> exists in the live model before adding it to the CSV.
>
> If naming conventions are inconsistent or abbreviated, load the **`standardize-naming-conventions`** skill first.
### Key Principle
AI data schema should be a **focused subset** of the model: pick clean, relevant fields and remove confusing/unneeded fields.

### Algorithm (Report-driven)

> **⚠️ CRITICAL — Three-layer star schema:** A star-schema model has **(a) a fact table** with FK columns joining to dimensions, **(b) dimension tables** with the actual business attributes, and **(c) measures** calculated over the fact. These three layers need different treatment. The most common mistake is including FK columns from the fact table instead of the descriptive attributes from the dimension tables.

**Before classifying any column, read `relationships.tmdl`:**
- List every `fromColumn` on the fact table → these are **FK columns (EXCLUDE)**
- List every `toColumn` on each dimension → these are **PK columns (EXCLUDE)**
- Copilot traverses relationships automatically; FK/PK columns serve no analytical purpose and will cause confusion

1) Start with all objects referenced in the report inventory:
   - All measures used in visuals
   - All columns used in axes/legend/slicers/filters/drillthrough

2) Expand with **dimension table business attributes** (the real user-facing dimensions):
   - **Bucket/range columns** (e.g., `FICO Bucket`, `LTV Bucket`, `WAC Bucket`, `Delinquency Bucket`, `Loan Size Bucket`) — always INCLUDE; these are the grouping labels users talk about
   - **Description columns** (e.g., `State Desc`, `Purpose Desc`, `Occupancy Desc`, `Property Class Description`) — always INCLUDE; human-readable labels
   - `SortOrder` columns in every dimension table — always EXCLUDE (technical sort key)

3) Classify **fact table columns** carefully (cross-reference against `relationships.tmdl`):
   - Columns listed as `fromColumn` in relationships → **EXCLUDE** (FK joins, technical)
   - Raw numeric columns (e.g., `Current Balance`, `Original Balance`) → **EXCLUDE**; Copilot should use calculated measures, not raw row-level values
   - Descriptive attributes not used as FK (e.g., `Account`, `Seller Name`, `Original FICO Score`) → INCLUDE if business-meaningful

   > **⚠️ Measure-column name conflict:** After classifying columns, cross-check every INCLUDE column against the full measure list. If a column name **exactly or closely matches a measure name** (e.g., column `LTV` and measure `LTV`), **EXCLUDE the column** — Copilot will use the measure for aggregation and the column creates ambiguity. Raw per-loan numeric values (LTV, DTI, WAC, DSCR) almost always have a corresponding portfolio-level measure; the column adds noise without analytical value.

4) Classify **measures** by `displayFolder`:
   - Business folders (e.g., `Standard`, `PM`, `MoM`, `Delinquency`) → INCLUDE
   - Styling/visual helpers (`Visual`, `Visual\SVG`, `Signal`, `Narrative`, `Tolerance`, `Reference`, `Utility`) → EXCLUDE
   - Unknown/ambiguous folders → review individually; default EXCLUDE if purpose unclear

5) Exclude unconditionally:
   - Technical IDs, surrogate keys, ETL audit columns (`Source File Name`, `Pay String Date`, `BPO Date`, etc.)
   - Duplicate / ambiguous variants of the same concept unless curated
   - Sensitive / PII columns unless explicitly allowed

6) Add "Model-hide suggestions" (optional):
   - If excluded from AI schema AND never useful to end users, recommend hiding in the model too.

### Column Classification Quick Reference

| Column type | Example | Action |
|---|---|---|
| FK on fact table (in `relationships.tmdl` `fromColumn`) | `Delinquency_Bucket`, `LTV_Bucket` | **EXCLUDE** |
| Bucket/range label on dim table | `dim_fico_bucket[FICO Bucket]` | **INCLUDE** |
| Description column on dim table | `dim_states[State Desc]`, `dim_occupancy[Occupancy Desc]` | **INCLUDE** |
| `SortOrder` column | `dim_wac_bucket[SortOrder]` | **EXCLUDE** |
| Raw numeric fact column | `factweeklyposition[Current Balance]` | **EXCLUDE** — use measures |
| Column name matches a measure name | `factweeklyposition[LTV]` (measure `LTV` exists) | **EXCLUDE** — column creates ambiguity; Copilot uses the measure |
| Descriptive fact attribute | `factweeklyposition[Account]`, `[Seller Name]` | **INCLUDE** if business-facing |
| Business measure | `[Total Current Balance $M]`, `[30 Day Delinquency %]` | **INCLUDE** |
| Styling / visual measure | `[Balance BG Color]`, `[CPR Signal]` | **EXCLUDE** |

### Output structure (must be explicit)
Produce `02-ai-schema-recommendations.md` with:
- INCLUDE: `Table[Column]` + `Measure` list
- EXCLUDE: `Table[Column]` + `Measure` list
- Rationale categories:
  - Unused
  - Technical / FK
  - Raw fact (use measures instead)
  - Ambiguous
  - Sensitive
  - Non-business-facing (SortOrder, styling, signal)
  - Legacy / deprecated

### Notes (important limitations)
- Excluding from AI schema hides it from Copilot reasoning (desired).
- Hidden fields can affect Copilot tooling behaviors; prefer schema exclusion for "hide from Copilot" and model hiding for "hide from users."
- **Never modify `en-US.tmdl` directly** — it resets the live "Prep data for AI" configuration in Fabric. The CSV is the reference artifact; apply changes via Power BI UI only.”

---

## Step 3 — Generate Copilot AI Instructions (structured, concise)
**Goal:** Create concise AI instructions for the semantic model so Copilot interprets business terms consistently.

> **Skills to load:** Use the **`tmdl`** skill to audit measure `///` descriptions, `displayFolder` groupings, and `formatString` values — these directly inform the terminology defaults and KPI list in the AI instructions. If the model has no descriptions, recommend adding them via the `tmdl` skill before finalizing AI instructions. The **`standardize-naming-conventions`** skill can also surface naming inconsistencies that should be reflected in the "Terminology Defaults" section (e.g., mapping user-friendly terms to the actual measure names in the model).

### Instruction Design Rules
- Use a domain “specialization” line (who the agent is).
- Define default metrics, default dimensions, and term mappings.
- Clarify date logic (which date means what).
- Provide a standard workflow: how to respond, what to generate.
- Include response formatting rules (currency, % formatting, totals).

### Output
Create `03-ai-instructions.md` using the template below.

---

## Step 4 — Build Answer Pack pages inside the same report (Report pane optimized)
**Goal:** Ensure Copilot can find answers in existing visuals.

> **Skills to load:** Load the **`pbir-format`** skill before creating or modifying any PBIR JSON files for Answer Pack pages. It covers the correct structure for `page.json`, `visual.json` (including `singleVisual.projections`, `queryRef` syntax, visual container sizing, and title formatting), and theme-based formatting. Use the `pbip` skill to confirm the folder naming rules for new pages (`[PageName]/` — letters, digits, underscores, hyphens only) and to handle the `pages.json` page-order file. **Validate each `visual.json` immediately after editing** using `jq empty <file.json>` as described in the `pbir-format` skill.

### Page Strategy
Create 1–3 pages:
- `Answer Pack — Executive`
- `Answer Pack — Drivers`
- `Answer Pack — Exceptions` (optional)

### Visual Strategy
For each top question intent:
- Create exactly one canonical visual
- Title it like the question (with unit/timeframe/grain)
- Add a nearby textbox “anchor”:
  - definition, synonyms, “try asking” sample prompts

**Output:** `04-answer-pack-design.md` and, if editing is enabled, implement pages in report.

---

## Step 5 — Optional: Verified Answers for must-be-correct questions
> **Skills to load:** The **`pbip`** skill describes the `<Name>.SemanticModel/Copilot/` folder where Power BI stores AI-related metadata (AI instructions, AI data schema, verified answers). Check this folder for existing files before writing new ones.
If permitted:
- Define verified answers for top 10–20 high-stakes questions using the Answer Pack visuals.
- Add 5–7 trigger phrases each and optional “available to users” filters (up to 3).

Document decisions in `04-answer-pack-design.md`.

---

## Step 6 — Test & Iterate (Report Copilot pane)
**Test loops**
A) AI data schema test:
- Ask a question using a field EXCLUDED from schema → Copilot should not answer using that field.
- Ask a question using fields INCLUDED → Copilot should answer.

B) Instructions test:
- Ask prompts that use defined terminology and date clarifications
- Verify Copilot follows your mappings and defaults

C) Answer Pack test:
- Ask top questions:
  - If Copilot references an existing Answer Pack visual → PASS
  - If Copilot generates a new visual → improve visual title/anchor text OR refine AI schema OR add verified answer

Record results in `05-test-script-and-results.md`.

---

# Templates

> **Which template to use:** See the [Agent Mode](#agent-mode) table above.
> - Reasoning models (o-series, Claude, GPT-5+) → use **Variant A**
> - Non-reasoning models (GPT-4.1, GPT-4o, and their minis) → use **Variant B**

---

## Variant A — Reasoning Models (o1, o1-mini, o3, o3-mini, o4-mini / Claude all versions / GPT-5 and above)

### Template: AI Instructions (`03-ai-instructions.md`)
Use this exact structure (concise but complete):

# <MODEL/REPORT> — Report Copilot Pane Instructions (Concise)

**Specialization:** <domain specialization>  
**Semantic Model:** <model name + id if available>  
**Report:** <report name>  

---

## Core Purpose
<1–3 sentences describing what users come to this report to do>

---

## Default KPIs (authoritative)
List the KPIs Copilot should prefer (name → measure reference):
- **<KPI Name>** — `[Measure Name]`
- ...

---

## Standard Outputs (choose one pattern)
### Pattern A: “Answer Pack Visuals First”
When possible, use the existing Answer Pack visuals for:
- <question category 1>
- <question category 2>
If the answer is not already visualized, generate a new visual using the semantic model.

### Pattern B: “Strat Table Default” (like BLAST)
Define a standard table output (ordered metrics, default sorting, row limits).

---

## Common Dimensions
**Primary:** <dims>  
**Secondary:** <dims>  
**Time:** <primary date table/columns>  

---

## Terminology Defaults
- **<Term>** = <model field or measure meaning>
- **<Term>** = <mapping>

### Date Field Clarifications
- If user says “as-of”, “reported”, “close” → use **<date>**
- If user says “funded”, “originated” → use **<date>**

---

## Question Interpretation Rules
- If user asks “show me” + a dimension → return breakdown by that dimension using default KPI(s)
- If user asks “top N” → apply Top N with default KPI unless specified
- If request is ambiguous → state assumption + offer options

---

## Visual Recommendations
- Trend → line chart (Date on axis, KPI as values)
- 2D comparison → ribbon/stacked/100% stacked (based on question intent)
- Exceptions → table/matrix with filters applied

---

## Response Format Rules
- Currency formatting: <$#,##0.0,, "M"> etc.
- Percent: 42% (not 0.42)
- Always include:
  1) direct answer
  2) the source visual reference (if using existing)
  3) 2–4 key insights
  4) next-step suggestions

---

## Error Handling
- Too many categories (>50): propose bucketing or Top N
- Missing measure: offer to create with DAX and ask for approval
- Security: never reveal restricted columns; use aggregated safe metrics only

---

### Template: Answer Pack Visual Title & Anchor
**Visual title format:** `<Intent/KPI> — <Unit> — <Timeframe> — <Grain>`

**Textbox anchor template:**
**Definition:** …  
**Synonyms:** …  
**Grain/Filters:** …  
**Try asking:** "…"; "…"; "…"

---

## Variant B — Non-Reasoning Models (GPT-4.1 / GPT-4.1 mini / GPT-4o / GPT-4o mini)

> Instructions for this variant must be **shorter, explicit, and have no open choices**. Every field has an inline example. No prose paragraphs.

### Template: AI Instructions (`03-ai-instructions.md`)

```markdown
# <REPORT NAME> — Copilot Instructions

You are a Copilot assistant for the "<report name>" Power BI report.
This report is used by <personas, e.g. portfolio managers and risk analysts> to monitor <domain, e.g. loan-level portfolio exposure>.

## Primary KPIs — always use these unless the user specifies otherwise
- <KPI 1 label>: [<Measure Name>]  (e.g. Current Balance: [Total Current Balance $M])
- <KPI 2 label>: [<Measure Name>]
- <KPI 3 label>: [<Measure Name>]

## Default Answer Behavior
First check whether an existing Answer Pack visual answers the question.
- If yes: reference that visual by name and summarize it.
- If no: generate a new visual using the semantic model.

## Dimensions — use these for grouping and filtering
- Primary: <dim1>, <dim2>  (e.g. Loan Status, Property Type)
- Date: <date table>.<date column>  (e.g. Calendar[Report Date])

## Term Mappings — translate user words to model fields
- "<user word>" means [<Model Field>]  (e.g. "balance" means [Total Current Balance $M])
- "<user word>" means [<Model Field>]

## Date Rules
- "as-of", "current", "reported" → use <date field>  (e.g. Calendar[Report Date])
- "originated", "funded" → use <date field>  (e.g. factweeklyposition[Origination Date])

## Output Format
- Currency: $#,##0.0,, "M"
- Percent: show as 42%, not 0.42
- Always return: (1) direct answer, (2) 2-3 key insights, (3) one follow-up suggestion

## Restricted Fields — never use these in any response
- <field 1>  (e.g. factweeklyposition[SSN])
- <field 2>

## If the question is unclear
State your assumption in one sentence, then answer based on that assumption.
```

### Template: Answer Pack Visual Anchor (textbox)

```
Definition: <one sentence>
Synonyms: <comma-separated synonyms>
Try asking: "<exact sample prompt>"; "<exact sample prompt>"
```

### Non-Reasoning Model Workflow Checklist

When operating with a non-reasoning model, follow only these steps in order. Do not skip or reorder.

- [ ] **Step 0:** Read the `pbip` skill. Find `.Report/definition/` and `.SemanticModel/definition/` paths.
- [ ] **Step 1:** For each page, open each `visual.json`. Copy all `queryRef` strings into `01-report-usage-inventory.md`. Do not interpret yet.
- [ ] **Step 2:** Open all `.tmdl` files in `definition/tables/`. Read the `tmdl` skill. List every measure and column with `isHidden` status. Then produce `02-ai-schema-recommendations.md` using this rule: INCLUDE if it appears in Step 1 results; EXCLUDE everything else.
- [ ] **Step 3:** Fill in every field of the Mini Agent AI Instructions template above. Do not leave any field blank — if unknown, write `[ASK USER]`.
- [ ] **Step 4:** For each top-3 user questions, define one Answer Pack visual title and one anchor textbox.
- [ ] **Step 5:** Record 5 test prompts in `05-test-script-and-results.md`. Mark each PASS or FAIL.

---

# Acceptance Criteria (Definition of Done)
- [ ] AI schema include/exclude lists produced (report-driven)
- [ ] AI instructions produced in `03-ai-instructions.md`
- [ ] Answer Pack page plan produced; pages built if permitted
- [ ] Test evidence shows:
  - ≥70% of top questions answered using existing visuals in report
  - Schema exclusion behaves as expected
  - Instructions are followed for terminology/date defaults

---

# References (for implementers)
- Prep data for AI (overview)
- AI data schemas
- AI instructions
- Verified answers
- Optimize semantic model for Copilot

---

# Related Skills (load when needed)

| Skill | When to load |
|-------|-------------|
| **`pbip`** | Step 0: understand folder layout, locate `Copilot/`, `pages/`, `visuals/`, `definition/`; Step 4 answer pack page folder naming; Step 5 Copilot folder |
| **`pbir-format`** | Step 1: parse `visual.json` field bindings, `page.json` filters, `report.json`; Step 4: author Answer Pack pages in PBIR JSON |
| **`powerbi-consumption-cli`** | **Step 2 (preferred):** Live model schema discovery via DAX INFO functions; exact FK/column/measure inventory; run `INFO.VIEW.RELATIONSHIPS()` + `INFO.VIEW.COLUMNS()` + `INFO.VIEW.MEASURES()` |
| **`tmdl`** | Step 2 (fallback): enumerate model measures/columns/tables from TMDL files when no service connection is available; Step 3: read `///` descriptions, `formatString`, `displayFolder` for AI instruction authoring |
| **`connect-pbid`** | Step 0 / Step 2: live model enumeration and DAX queries via TOM when Power BI Desktop is open (faster and validated alternative to reading raw TMDL) |
| **`standardize-naming-conventions`** | Step 2 (pre-req): fix abbreviated or inconsistent names before building the AI schema; Step 3: map user-friendly terminology to actual model names |

---

# AI Schema Configuration Workflow

> **⚠️ IMPORTANT:** This section describes the correct workflow for Fabric datasets using "Prep data for AI".
> 
> **Key Principle:** The CSV and en-US.tmdl changes are **reference artifacts** documenting what SHOULD be hidden/visible. They are NOT directly applied to the online Prep data for AI configuration.
> 
> **Why?** Modifying en-US.tmdl is useful for version control and documentation, but it does NOT automatically sync with the Fabric service's "Prep data for AI" configuration. Instead:
> 
> 1. **CSV + TMDL:** Generated and committed as **reference documentation** of schema decisions
> 2. **Power BI UI:** Manually apply schema decisions via "Prep data for AI" in Desktop or Fabric Service
> 3. **Result:** Reference CSV stays in repo; UI-configured schema stays in Power BI Service

## Generate Reference CSV (Documentation)

Use `Generate-AISchema.ps1` to create a reference document of measures and their proposed visibility:

```powershell
.\Generate-AISchema.ps1 -SemanticModelPath "IAM_FIELD_MAPPING.SemanticModel" `
  -OutputPath "documentation/copilot/ai-schema.csv"
```

**Output:** `ai-schema.csv` with default inclusion rules:
- **Visible (INCLUDE):** displayFolders `Standard`, `PM`, `MoM`, `Delinquency`, Reference measures
- **Hidden (EXCLUDE):** displayFolders `Visual`, `Visual\SVG`, Internal helpers, `Tolerance`, `Signal`, `Narrative`, `Utility`

## Review & Edit CSV as Reference

Open `documentation/copilot/ai-schema.csv` and review visibility decisions:

```csv
EntityKey,DisplayName,DisplayFolder,Visibility,Reason
"entity__measure.balance","Balance","Standard","Visible","Core KPI for all analyses"
"entity__measure.balance_BG_color","Balance BG Color","Visual","Hidden","Background color; Copilot cannot reason over styling"
"entity__measure.nz_dscr","NZ DSCR","Standard","Visible","Debt service coverage ratio; key risk metric"
```

This CSV serves as the **source of truth** for what should be visible/hidden to Copilot.

## Apply Schema via Power BI UI

**Apply schema decisions in Power BI Desktop or Fabric Service:**

### In Power BI Desktop:
1. Open semantic model in Power BI Desktop
2. Home ribbon → **Prep data for AI**
3. In the "AI data schema" tab:
   - **Add to schema:** All measures/columns from CSV with `Visibility = Visible`
   - **Remove from schema:** All measures/columns from CSV with `Visibility = Hidden`
4. Save and publish to Fabric

### In Fabric Service:
1. Navigate to semantic model
2. Click **Copilot** button (or three-dot menu → Copilot)
3. Go to "AI data schema" tab
4. Add/remove fields based on CSV reference
5. Save

This ensures your UI-based schema configuration is preserved and not overwritten by TMDL changes.

## CSV in Version Control (Reference Only)

The committed `documentation/copilot/ai-schema.csv` serves as:
- **Documentation:** What fields are intended to be visible/hidden
- **Audit trail:** Decision rationale in the `Reason` column
- **Reproducibility:** New team members can see historical schema decisions
- **Communication:** Share with stakeholders to explain Copilot field exposure

The en-US.tmdl changes are also committed as a reference checkpoint, but they do NOT override the Fabric service's live configuration.

### 4. Validate in Power BI / Fabric

1. Open the report in Power BI Desktop or Fabric
2. Verify that excluded measures do not appear in Copilot suggestions
3. Check that included measures are available
4. Test a sample Copilot query

### 5. Commit

```bash
git add documentation/copilot/ai-schema.csv \
        IAM_FIELD_MAPPING.SemanticModel/definition/cultures/en-US.tmdl
git commit -m "Generate AI schema CSV and reference TMDL configuration for Copilot readiness

- Generated ai-schema.csv listing 206 measure entities with Visibility defaults
- Generated by Generate-AISchema.ps1 to extract measures and propose schema
- CSV serves as SOURCE OF TRUTH for what fields should be hidden/visible
- TMDL changes committed as reference checkpoint (not applied to online config)
- 64 measures marked as Visible (Standard, PM, MoM, Delinquency, Reference)
- 142 measures marked as Hidden (Visual, SVG, helper, tolerance, signal, utility)

Implementation notes:
- CSV + TMDL are version-controlled reference documents
- Actual schema applied via Power BI UI (Prep data for AI) not Apply-AISchema-v2.ps1
- UI application prevents conflicts with Fabric service's live Prep data for AI config"
```

## CSV as Reference Document

The committed `documentation/copilot/ai-schema.csv` and TMDL changes serve as:
- **Source of truth:** What fields are intended to be visible/hidden to Copilot
- **Audit trail:** `Reason` column documents decision rationale
- **Reproducibility:** New team members see historical schema decisions
- **Team communication:** Share CSV with stakeholders to explain field exposure

## Application via Power BI UI (Manual Process)

Manually apply schema decisions in Power BI Desktop or Fabric Service using the CSV as reference:

### Workflow:
1. Review `documentation/copilot/ai-schema.csv`
2. In Power BI Desktop or Fabric Service, open "Prep data for AI" → "AI data schema" tab
3. For each row in CSV where `Visibility = Visible`:
   - Add to AI data schema (if not already present)
4. For each row in CSV where `Visibility = Hidden`:
   - Remove from AI data schema (if present)
5. Save and publish

This ensures the live Fabric configuration is preserved as the source of truth.

## Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `Generate-AISchema.ps1` | Extract measures/columns from TMDL; propose Visibility defaults | **Use for:** Generating reference CSV only |
| `Apply-AISchema-v2.ps1` | Patch en-US.tmdl with Visibility entries | **Deprecated:** Use manual UI application instead |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CSV not found | Run Generate-AISchema.ps1 first to create `documentation/copilot/ai-schema.csv` |
| CSV header incorrect | Verify header: `EntityKey,DisplayName,DisplayFolder,Visibility,Reason` |
| Copilot still sees excluded measures | Check Power BI Service "Prep data for AI" → verify fields are removed from schema |
| Schema seems out of sync | Do not use Apply-AISchema-v2.ps1; instead manually apply via Power BI UI |
| FK columns appearing in Copilot | Check `relationships.tmdl`; every `fromColumn` on the fact table must be EXCLUDE in the CSV |
| Dimension bucket columns missing from schema | Dimension tables (`dim_*`) must be scanned separately from the fact table; add `FICO Bucket`, `LTV Bucket`, `Delinquency Bucket`, etc. as INCLUDE |
| Raw balance/numeric columns confusing Copilot | Exclude raw fact columns (`Current Balance`, `Original Balance`); Copilot should use calculated measures only |
| Copilot cannot filter by State/Occupancy/Property Type | These are in dimension tables not the fact table; ensure `dim_states[State Desc]`, `dim_occupancy[Occupancy Desc]`, `dim_property_class[Property Class Description]` are INCLUDE |

---