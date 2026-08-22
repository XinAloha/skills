# Input Schema

The preferred portable entrypoint is JSON:

```bash
python scripts/run_hpo_search.py --input examples/hpo_lgbm_smoke.json
```

The JSON file may contain wrapper fields plus a native config object:

```json
{
  "output_root": "../outputs/my_run",
  "config": {
    "compatibility": {"profile": "legacy_v1"},
    "task": {},
    "input": {},
    "data": {},
    "features": {},
    "model": {},
    "extensions": {},
    "search": {},
    "validation": {},
    "evaluation": {},
    "space_controller": {},
    "llm": {},
    "final_selector": {}
  }
}
```

Relative paths in `input` and `data` are resolved relative to the JSON file location. Paths in `extensions.plugin_roots` are resolved the same way.

## Compatibility Profiles

`compatibility.profile` controls methodology defaults while leaving the extensible code framework unchanged:

| Default | `legacy_v1` | `research_v2` |
| --- | --- | --- |
| Objective | `rankic_ir` | `robust_rankic` |
| Metric policy | pooled overfit and continuous turnover | cross-sectional overfit and window-reset turnover |
| Trial seed | `seed + trial_index * 997` | common seed for every initial trial |
| Date sample weight | `none` | `equal_date` |
| Multi-seed confirmation | disabled | enabled |
| Point-in-time strictness | disabled | enabled |
| Fixed test/holdout | evaluated automatically | sealed during search |

The profile defaults to `legacy_v1` so existing experiments reproduce the prior settings. Explicit fields such as `evaluation.objective`, `training.sample_weight`, `reproducibility`, `data.strict_point_in_time`, and `holdout.mode` override profile defaults. Do not mix overrides when exact historical reproduction is required.

## Required Data Files

`input.feature_path` points to a CSV or parquet file with:

- `date`: date as `YYYYMMDD` integer/string or parseable date string
- ticker column: configured by `data.ticker_col`, for example `symbol`
- numeric factor columns, for example `alpha_001`, `alpha_002`

`input.label_path` points to a CSV or parquet file with:

- same date column
- same ticker column
- label column configured by `data.label_col`, usually `y`

The runtime merges features and labels on `(date, ticker)`. It raises on duplicated keys.

Optional point-in-time metadata:

- `available_date` in factor data: checked to be no later than signal date
- `label_start_date`, `label_end_date` in label data: checked against `time.trade_lag_days`

## Core Config Sections

`data`:

- `date_col`: source date column name
- `ticker_col`: source ticker/asset column name
- `label_col`: label column name in label file
- `start_date`, `end_date`: optional date filter
- `feature_include`: optional explicit factor list
- `feature_exclude`: optional factor exclusions
- `all_null_feature_policy`: `allow`, `drop`, or `raise`
- `compute_hash`: whether to hash input files in metadata
- `provider`: optional `{name, params}` factor-provider selection; defaults to `file_panel`
- `strict_point_in_time`: defaults to `false` in `legacy_v1` and `true` in `research_v2`; strict mode requires `available_date`, `label_start_date`, `label_end_date`, and `universe_path`

`features`:

- `pipeline`: optional `{name, params}` feature-pipeline selection; defaults to `cross_sectional`

`model`:

- `type`: built-in or registered model name
- `plugin`: optional explicit registered model name; when set, it is authoritative

`extensions`:

- `allow_external`: must be `true` before local user modules can be imported
- `plugin_roots`: explicit allowed local module directories
- `modules`: explicit module names exposing `register(registry)`

See `extension_api.md` and `examples/hpo_custom_extension_smoke.json`. Existing configurations that omit these sections keep the original file/LGBM/MLP behavior.

`search`:

- `model_type`: `lgbm`, `mlp`, or the canonical name of an explicitly registered model plugin
- `method`: `evidence_driven` or `grid`; legacy aliases remain accepted
- `sampler`: for `evidence_driven`, use `evidence_probe`, `adaptive`, `structured_probe`, or `local_probe`; for `grid`, this is forced to `grid`
- `max_trials`: total trial budget
- `max_rounds`: maximum search rounds
- `trials_per_round`: trials per round
- `random_start_trials`: random warm-up trials before adaptive sampling; ignored by `grid`
- `top_fraction`: fraction of successful trials used as top evidence; ignored by `grid`
- `space`: search-space mapping used by evidence-driven sampling and generated grid search
- `grid`: generated-grid settings when `method=grid`
- `grid_trials`: optional explicit parameter list when `method=grid`; takes precedence over generated `grid`

Custom model plugins support `sampler=adaptive` or `method=grid`. Structured probe samplers remain specific to built-in LGBM/MLP parameter semantics.

Search methods:

- `evidence_driven`: uses the built-in `adaptive_top_fraction` heuristic, records trial evidence, and optionally lets the decision provider adapt the search space between rounds. It is not a probabilistic TPE implementation.
- `grid`: evaluates a deterministic sequence of parameter points. It does not call the decision provider and automatically disables `space_controller`.

Generated grid config:

```json
{
  "method": "grid",
  "max_trials": 12,
  "grid": {
    "strategy": "budgeted_cartesian",
    "numeric_levels": 3,
    "log_levels": 3,
    "choice_policy": "first_middle_last",
    "selection": "evenly_spaced",
    "shuffle": false,
    "seed": 42
  },
  "space": {}
}
```

- `strategy`: currently `budgeted_cartesian`
- `numeric_levels`: number of values generated for `uniform` and `quniform` specs
- `log_levels`: number of values generated for `loguniform` and `qloguniform` specs
- `choice_policy`: `all`, `first_last`, or `first_middle_last`
- `selection`: `evenly_spaced` or `random` when the full Cartesian grid exceeds `max_trials`
- `shuffle`: whether to shuffle selected grid points after deterministic selection
- `seed`: deterministic seed for random selection or shuffle

Search-space spec types:

```json
{"type": "choice", "values": [1, 2, 3]}
{"type": "uniform", "low": 0.1, "high": 1.0}
{"type": "loguniform", "low": 0.0001, "high": 0.01}
{"type": "quniform", "low": 1, "high": 10, "q": 1}
{"type": "qloguniform", "low": 1, "high": 100, "q": 1}
```

`validation` supports:

- `fixed_train_valid_test`: explicit train, validation, and holdout test dates
- `walk_forward`: rolling train/validation windows using trading-day counts
- `expanding_walk_forward`: anchored growing training windows, either count-based or explicit `folds`

Explicit expanding folds:

```yaml
validation:
  method: expanding_walk_forward
  embargo_days: 5
  folds:
    - {train_start: 20150101, train_end: 20181231, valid_start: 20190101, valid_end: 20191231}
    - {train_start: 20150101, train_end: 20191231, valid_start: 20200101, valid_end: 20201231}
    - {train_start: 20150101, train_end: 20201231, valid_start: 20210101, valid_end: 20211231}
    - {train_start: 20150101, train_end: 20211231, valid_start: 20220101, valid_end: 20221231}
time:
  locked_test_start: 20230101
```

Training rows are additionally purged when their actual `label_end_date >= valid_start`.

For `fixed_train_valid_test`, define:

- `train_start`, `train_end`
- `valid_start`, `valid_end`
- `test_start`, `test_end`
- `embargo_days`
- `min_assets_per_date`

`evaluation.objective` can be:

- `rankic_ir`: `legacy_v1` default; mean daily RankIC divided by its standard deviation
- `robust_rankic`: `research_v2` default; block mean RankIC minus a standard-error penalty
- `rmse`: optimize prediction loss directly
- `fast_score`: weighted composite score

Recommended robust objective:

```yaml
evaluation:
  objective: robust_rankic
  robust_rankic:
    block: month
    min_valid_dates: 60
    min_blocks: 6
    se_multiplier: 1.0
```

`training`:

- `label_transform.method`: `none`, `rank_by_date`, or `zscore_by_date`
- `sample_weight.method`: `none` in `legacy_v1`, `equal_date` in `research_v2`

`reproducibility`:

```yaml
reproducibility:
  trial_seed_policy: common
  confirmation:
    enabled: true
    top_k: 3
    seeds: [42, 137, 2027]
    selection: mean_minus_std
    std_penalty: 0.5
    min_successful_seeds: 3
```

`legacy_v1` uses `trial_seed_policy=legacy_trial_index` and disables confirmation. `research_v2` uses a common initial seed, then reruns Top K candidates across the listed confirmation seeds.

## Holdout Access

`legacy_v1` automatically evaluates a configured fixed test period and returns `status=evaluated`. `research_v2` truncates search data at `validation.valid_end` or `time.locked_test_start`, returns `status=selected_not_tested`, and evaluates a frozen result separately:

```bash
python scripts/run_holdout_evaluation.py \
  --source-run-dir <run-dir> \
  --confirm-holdout-access
```


## Decision Provider

`decision_provider` controls who makes search-space and final-selection decisions:

```json
{
  "type": "rule | codex_external",
  "decision_dir": "codex_decisions",
  "wait_for_decision": false,
  "on_missing": "fallback",
  "on_invalid": "fallback"
}
```

- `rule`: deterministic guarded rule decisions.
- `codex_external`: Python writes evidence/template files and reads externally written LLM decision JSON files. This is the file-based LLM decision mode used by the skill.

For `codex_external`, set `on_missing=stop` when the run should pause after evidence generation, or `on_missing=fallback` for non-blocking smoke tests. `decision_provider` is used by evidence-driven search and final selection; `search.method=grid` does not request search-space decisions. This Skill supports `rule` and `codex_external` decision providers only.

`space_controller` controls whether and how the search space is adapted:

- `enabled`: true/false
- `mode`: `rule` or `llm_guarded`
- `exploration_preferred_actions`: usually `expand`, `shift`
- `relocation_preferred_actions`: usually `shift`, `expand`, `narrow`
- `exploitation_preferred_actions`: usually `narrow`, `shift`, `keep`, `stop`

LLM decision settings:

- Set `decision_provider.type` to `codex_external`.
- Keep `llm.enabled=false`; the LLM decision is supplied through the `codex_decisions/` JSON handoff files.
- Use `decision_provider.on_missing=stop` when a run should pause for the external LLM decision step.
- Use `decision_provider.on_missing=fallback` for non-blocking smoke tests.

`final_selector` lets the LLM inspect all completed trials plus small neighborhood probes and select one existing center trial:

- `enabled`: true/false
- `mode`: `llm_guarded`
- `top_k`: number of top candidates shown
- `neighbors_per_candidate`: local probes per candidate
- `max_extra_trials`: cap on neighborhood probes
- `max_score_drop`: guardrail versus score-best candidate
- `fallback`: usually `score_best`
