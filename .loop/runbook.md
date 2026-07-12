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

The scheduler is intentionally not configured by this project artifact. First complete and approve a manual dry run. Then configure a local or CI scheduler to invoke exactly the command in the contract once per UTC day, with concurrency one and no source-write credentials.

Before treating the scheduler as stable, collect evidence from three completed scheduled runs. If a run is missed, duplicated, or cannot write a report, mark it blocked and use the manual command; do not silently increase retries or frequency.

## Recovery

If interrupted, rerun the read-only command. It is idempotent except for replacing `.loop/reports/latest.json`. If report writing fails, do not retry source changes; preserve the error and escalate.
