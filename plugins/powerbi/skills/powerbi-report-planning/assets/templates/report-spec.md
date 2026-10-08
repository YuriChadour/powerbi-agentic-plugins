# Report Spec

## Report identity
- Report name:
- Semantic model:
- Audience:
- Primary purpose:
- Delivery target:

## User decisions and constraints
- Scope:
- Page count:
- Interactivity:
- Design direction:
- Publishing:
- Tooling:
- Model edit permissions:
- Accessibility:
- Data caveats:

## Narrative
- Core story:
- Audience promise:
- Key questions answered:

## Design identity (from `powerbi-report-design` Step 1)
- Tone: <named entry from tone-catalog, e.g. "Editorial Newsroom">
- Signature: <one defining move, e.g. "tabular numerals + display serif headlines">
- Brownfield delta (if applicable): <current_tone -> target_tone>

## Page plan (archetypes from `powerbi-report-design` Step 3)
1. Page name
   - Archetype:                      <Executive Summary | Analytical Canvas | ...>
   - Layout variant (A/B/C):         <plus one-sentence variant_rationale>
   - Purpose:
   - Visuals:
   - Fields/measures:
   - Slicers/interactions:

## Design system summary
- Theme name + base palette (1-2 lines):
- Color semantics (which measure -> which color, 1-2 lines):
- Typography pairing (display + body):
- Layout pattern (grid + gutter + density):
- Accessibility commitments:

## Model requirements
- Existing measures:
- New measures:
- New calculated columns:
- Relationship/sort requirements:

## Canonical design contract

Paste the exact fenced `yaml` block produced by `powerbi-report-design` here.
Do not rewrite it from planner memory and do not replace its mechanical
`layout_contract` with a freeform ASCII wireframe.

The YAML block is authoritative for implementation. `powerbi-report-authoring`
must implement this block; surrounding prose is context and conflict detection.

## Implementation notes

- Model changes:
- PBIR/report authoring:
- Validation:
- Desktop screenshot verification:
- Publishing boundary:
- Risks:
