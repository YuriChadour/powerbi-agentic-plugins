## 1. Patch the decision rule

- [ ] 1.1 Replace `openspec-bridge/SKILL.md`'s two-outcome decision table (ongoing-tracking
      yes/no) with the new two-outcome table (Backfill now / Skip) and verify the "implemented
      and stable" row now routes to "Backfill now" instead of "No action", with no remaining
      "ongoing tracking" outcome anywhere in the table
- [ ] 1.2 Update the skill's introductory Purpose section so it describes a single
      backfill-on-completion workflow (not ongoing tracking), and verify by re-reading the file
      end-to-end for internal consistency

## 2. Replace the workflow with backfill-on-completion

- [ ] 2.1 Replace the existing "adopt tracking" workflow section with "Workflow: backfill archive
      history for an already-completed spec", reusing its read/derive-name/`openspec new change`/
      map-sections steps, and verify it explicitly states `tasks.md` is scaffolded with every
      checkbox pre-checked `[x]`
- [ ] 2.2 Add the immediate-archive handoff step: after `tasks.md` is scaffolded, run
      `openspec validate --strict`, then invoke the repo's `openspec-archive-change` skill (not a
      bare `openspec archive` CLI call) so sync-before-move gating and date-prefixed archive
      naming are honored, and verify the workflow text names `openspec-archive-change` explicitly
- [ ] 2.3 Keep the final step (one-line tracking pointer added to the original `spec.md`) in the
      replacement workflow, verified by reading the section and confirming it still ends with that
      step, and verify no leftover references to an "ongoing tracking" workflow remain anywhere in
      the file

## 3. Cross-check against the real archive/sync contract

- [ ] 3.1 Re-read `.agents/skills/openspec-archive-change/SKILL.md` and
      `.agents/skills/openspec-sync-specs/SKILL.md` and verify the new backfill workflow text
      matches: sync happens before the folder move, archive stops on sync failure, and the archive
      folder name is date-prefixed only if not already present
- [ ] 3.2 Verify the delta-spec mapping instructions tell the bridge to treat a first-time backfill
      as `## ADDED Requirements` only (no existing main spec to diff against), matching
      `openspec-sync-specs`'s new-capability case

## 4. Dogfood the backfill workflow

- [ ] 4.1 In `C:\Development\Glasslake-1`, run `openspec init` to scaffold `openspec/config.yaml`
      and the `changes/`/`specs/` folders, and verify the `openspec/` folder now exists there
- [ ] 4.2 Install the `spec-lifecycle` plugin via `setup-team-plugins.ps1 -PluginName spec-lifecycle`
      and verify `openspec-bridge` is loadable as a skill
- [ ] 4.3 Run the patched backfill workflow against
      `Glasslake-1/specs/Python-MCP-DAX-Test-Framework.spec.md` only (the remaining 6 specs in that
      repo are explicitly out of scope for this change) and verify the resulting change lands at
      `openspec/changes/archive/YYYY-MM-DD-add-dax-test-framework/` (not left open under
      `openspec/changes/`), with a synced delta present under `openspec/specs/`
- [ ] 4.4 Run `openspec validate --strict` in Glasslake-1 against the archived change and verify it
      passes
- [ ] 4.5 Diff the scaffolded `proposal.md`/`design.md`/`tasks.md`/delta spec against the source
      `.spec.md` and verify no content was lost (Mermaid diagram carried over verbatim, every task
      scaffolded as `[x]`, every EARS acceptance criterion became a `#### Scenario` block)
- [ ] 4.6 Verify the original `specs/Python-MCP-DAX-Test-Framework.spec.md` still exists unchanged
      except for the added one-line tracking pointer

## 5. Close out

- [ ] 5.1 Update `plans/RESUME.md` §5's stale claim that Glasslake-1 already has a hand-built
      OpenSpec change, replacing it with the real state established in task 4.3, and verify the
      note no longer references a nonexistent pre-existing change
- [ ] 5.2 If task 4.5's diff surfaces any further section-mapping gaps (EARS edge cases, verbatim
      reference-implementation placement), patch `openspec-bridge/SKILL.md` again and re-verify
      task 4.5's diff is clean
