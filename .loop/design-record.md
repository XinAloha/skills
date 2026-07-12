# Daily Skills Health — Design Record

## Decision

Use a hybrid design: a deterministic daily health scan plus a bounded evidence-triage loop. The scan checks Skill frontmatter, index freshness, local Markdown links and Python syntax. Findings are recorded as suggestions only; no source file, commit, merge, pull request, notification or external API action is permitted.

## Verified facts

- `_meta/build_index.py` exists and supports a no-write `--check` mode.
- The repository contains 74 `SKILL.md` files, 20 Python files and local Markdown links to inspect.
- The manual dry run completed, generated an evidence report and passed contract/state/audit checks.
- The repository now contains `.github/workflows/skills-health.yml`: a daily 02:17 UTC GitHub Actions trigger with read-only repository permission, concurrency one, a 10-minute timeout and a 30-day JSON artifact.

## Unknowns and boundaries

- The GitHub Actions workflow is present on the task branch but is not a live scheduler until a human approves and merges its draft PR into the default branch. No Issue, PR API, MCP or external notification connector is assumed.
- Existing imported Skills use mixed frontmatter conventions. Name/folder mismatch and noncanonical keys are triage findings, not automatic rename authorization.
- The loop has zero model-call budget. Any future AI-generated repair draft requires a separate approved contract and human gate.

## Acceptance

One scheduled invocation must exit 0, write a parseable report under `.loop/reports/`, archive it, update state and create triage rows. Repository health findings do not make the scan fail; a scanner failure does.

## Next decision

Create a draft PR for the workflow, obtain human approval, then collect evidence from three scheduled GitHub Actions runs before treating the scheduler as stable.
