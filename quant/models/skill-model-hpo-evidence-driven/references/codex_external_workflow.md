# LLM Decision Handoff Workflow

Use this workflow when the skill runs inside an agent environment and LLM decisions should be exchanged through files.

## Core Idea

Python remains the deterministic executor:

- load local factor and label data
- train LGBM/MLP trials
- compute validation metrics
- build evidence JSON
- validate decision JSON
- write final artifacts

The external LLM decision step acts as the decision maker:

- read generated evidence JSON
- reason over trial metrics and search-space constraints
- write a strict decision JSON file
- rerun the command with the same `task.run_id` after writing the decision file

The Python runtime never trusts the external decision blindly. Every externally written decision is passed through schema validation and guarded search-space constraints before it is accepted.

## Config

Set:

```json
"decision_provider": {
  "type": "codex_external",
  "decision_dir": "codex_decisions",
  "wait_for_decision": false,
  "on_missing": "fallback",
  "on_invalid": "fallback"
}
```

`decision_dir` is resolved under the timestamped run directory unless it is absolute.

Modes:

- `on_missing=fallback`: write evidence/template files and continue with guarded rule fallback. Use for smoke tests.
- `on_missing=stop`: write evidence/template files and return `status=external_decision_required`. Use when the external LLM decision step should decide before continuing.
- `on_invalid=fallback`: invalid external decisions are logged and replaced by guarded rule fallback.
- `on_invalid=stop`: invalid external decisions stop the run so the decision JSON can be corrected.

## Space Decision Files

After a search round, the runtime writes:

```text
<run_dir>/codex_decisions/round_0000_space_evidence.json
<run_dir>/codex_decisions/round_0000_space_decision.template.json
<run_dir>/codex_decisions/round_0000_space_codex_instructions.json
```

The LLM decision step writes:

```text
<run_dir>/codex_decisions/round_0000_space_decision.json
```

Decision schema:

```json
{
  "action": "keep",
  "reason": "Evidence-grounded explanation.",
  "next_search_space": null,
  "next_round_trials": 2,
  "hypothesis": "Optional hypothesis for the next round.",
  "risk_flags": ["sparse_evidence"]
}
```

For `narrow`, `expand`, or `shift`, `next_search_space` must be a full search-space mapping with the same hyperparameter names and valid spec types. The runtime validates bounds, choices, action semantics, and model-specific constraints.

## Final Selection Files

When `final_selector.enabled=true`, the runtime writes:

```text
<run_dir>/codex_decisions/final_selection_evidence.json
<run_dir>/codex_decisions/final_selection_decision.template.json
<run_dir>/codex_decisions/final_selection_codex_instructions.json
```

The LLM decision step writes:

```text
<run_dir>/codex_decisions/final_selection_decision.json
```

Decision schema:

```json
{
  "selected_trial_id": "lgbm_trial_0000",
  "reason": "Why this existing center trial is selected.",
  "risk_flags": ["validation_spike_risk"],
  "confidence": "medium"
}
```

The LLM decision must select one existing center trial listed in `selection_policy.allowed_selected_trial_ids`; it must not select a neighbor trial or invent new parameters.

## Example Commands

Smoke run that writes evidence and falls back automatically when no decision file exists:

```bash
python scripts/run_hpo_search.py --input examples/hpo_lgbm_codex_external.json
```

Interactive LLM decision mode:

1. Set `decision_provider.on_missing` to `stop`.
2. Run the same command.
3. Open `external_decision_required.json` in the run directory.
4. Read the referenced evidence file.
5. Write the referenced decision file.
6. Rerun the same command with the same `task.run_id` so the runtime can consume the decision file.

Current implementation is optimized for simple LLM decision handoff through files. It does not implement checkpoint resume: rerunning with the same `task.run_id` re-executes the search while reading existing decision files from the run directory. A future version can add a true step runner to avoid rerunning earlier rounds.
