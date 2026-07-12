# Daily Skills Health Runbook

## Scope and authority

This Loop reads repository files and writes only `.loop/` evidence, state, triage and reports. It does not edit Skills, regenerate `INDEX.md`, create commits, open pull requests, merge, notify external systems, or use model calls.

## Run one cycle

1. Confirm the repository root contains `_meta/build_index.py` and read `.loop/contract.json`.
2. Run `python .loop/scripts/skills_health_check.py --root . --report .loop/reports/latest.json`.
3. Verify the command exited `0`, then inspect the report schema and summary.
4. Append a journal entry with scan ID, timestamp, summary and report path; update `state.json` atomically.
5. For every `error`, `warning` or `review`, add one triage row containing rule ID, evidence path, suggested command and owner. Do not apply the suggestion.
6. Mark the run complete. If the scanner itself fails, preserve its output, mark the run blocked and escalate to `repository-maintainer`.

## Handling findings

- `error`: report a concrete breakage. Draft a repair plan only after a human chooses the item.
- `warning`: report a probable inconsistency or link issue. Verify before proposing edits.
- `review`: report cross-agent compatibility or policy ambiguity. Do not normalize imported content automatically.

## Scheduling

GitHub Actions is configured in `.github/workflows/skills-health.yml` to invoke the contract command once per UTC day at 02:17, with repository-wide concurrency one, a 10-minute timeout and read-only `contents` permission. It uploads the JSON report as a 30-day workflow artifact and publishes only the scanner's counts and suggestions in the run summary.

The workflow does not receive source-write permission and must not edit Skills, regenerate `INDEX.md`, commit, open or update a pull request, or merge. It becomes scheduled only after the draft pull request containing it is human-approved and merged into the default branch.

Before treating the scheduler as stable, collect evidence from three completed scheduled runs. If a run is missed, duplicated, or cannot write a report, mark it blocked and use the manual command; do not silently increase retries or frequency.

## Recovery

If interrupted, rerun the read-only command. It is idempotent except for replacing `.loop/reports/latest.json`. If report writing fails, do not retry source changes; preserve the error and escalate.
