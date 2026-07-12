# Daily Skills Health — Design Record

## Decision

Use a hybrid design: a deterministic daily health scan plus a bounded evidence-triage loop. The scan checks Skill frontmatter, index freshness, local Markdown links and Python syntax. Findings are recorded as suggestions only; no source file, commit, merge, pull request, notification or external API action is permitted.

## Verified facts

- `_meta/build_index.py` exists and supports a no-write `--check` mode.
- The repository contains 67 `SKILL.md` files, 20 Python files and local Markdown links to inspect.
- The manual dry run completed, generated an evidence report and passed contract/state/audit checks.

## Unknowns and boundaries

- No scheduler, CI schedule, worktree adapter or external notification integration was found or configured. A human must choose and configure the daily trigger.
- Existing imported Skills use mixed frontmatter conventions. Name/folder mismatch and noncanonical keys are triage findings, not automatic rename authorization.
- The loop has zero model-call budget. Any future AI-generated repair draft requires a separate approved contract and human gate.

## Acceptance

One scheduled invocation must exit 0, write a parseable report under `.loop/reports/`, archive it, update state and create triage rows. Repository health findings do not make the scan fail; a scanner failure does.

## Next decision

After reviewing the first triage queue, choose a scheduler (local task scheduler, CI schedule, or Codex automation) and explicitly authorize its credentials and cadence.
