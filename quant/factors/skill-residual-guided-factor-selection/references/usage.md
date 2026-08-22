# Usage and Configuration

## Contents

- [1. Input Data](#1-input-data)
- [2. Required YAML Sections](#2-required-yaml-sections)
- [3. Data Section](#3-data-section)
- [4. Split and Universe](#4-split-and-universe)
- [5. Preprocessing](#5-preprocessing)
- [6. Model Section](#6-model-section)
- [7. Selection Section](#7-selection-section)
- [8. Beam Section](#8-beam-section)
- [9. Pool Section](#9-pool-section)
- [10. Output Section](#10-output-section)
- [11. Commands](#11-commands)
- [12. Outputs](#12-outputs)
- [13. Factor Backtest Skill Handoff](#13-factor-backtest-skill-handoff)

## 1. Input Data

Provide one wide label Parquet and either:

- one wide Parquet per factor under `data.factor_dir`; or
- a prepared-feature Parquet under `data.prepared_feature_cache`.

Wide files use a date index and symbol columns. A prepared cache uses a `(datetime, symbol)` MultiIndex and one column per already-preprocessed factor. Factor file stems or cache column names become the factor identifiers.

A prepared cache requires a sibling `<cache>.meta.json` manifest. The runtime verifies exact panel keys, index hash, ordered factor names, universe, split, preprocessing configuration, row count, and date range. `validate-cache --write-manifest` is intended only for a cache whose provenance has already been independently verified.

All relative paths are resolved from the YAML file location.

## 2. Required YAML Sections

Search, cache-validation, and OOS commands require:

- `data`
- `split`
- `universe`
- `preprocess`
- `model`
- `selection`
- `beam`
- `output`

`run-pool` additionally requires `pool`. `materialize` reads only the relevant source and destination fields from `data`.

Use these templates as starting points:

- `examples/residual_search/ridge_beam_template.yaml`
- `examples/residual_search/lgbm_oof_beam_template.yaml`
- `examples/residual_search/toy_config.yaml`

## 3. Data Section

Common fields:

| Field | Meaning |
|---|---|
| `label_path` | Wide target Parquet |
| `factor_dir` | Directory containing one wide Parquet per factor |
| `prepared_feature_cache` | Optional preprocessed feature matrix |
| `factor_manifest` | Materialization manifest path |
| `bar_dir` | Per-symbol market-bar directory for materialization |

Materialization can also use:

| Field | Meaning |
|---|---|
| `alpha158_source_dir` | Python modules containing Alpha158 factor specifications |
| `alpha_formula_source_repo` | Compatible formula runtime for Alpha101/Alpha191 |

Search requires either a valid `factor_dir` or a valid prepared cache. Cache-only mode derives the frozen factor bank from cache columns and its manifest.

## 4. Split and Universe

```yaml
split:
  train_start: "2015-01-01"
  train_end: "2019-12-31"
  valid_start: "2020-01-01"
  valid_end: "2021-12-31"
  oos_start: "2022-01-01"
  oos_end: "2023-12-31"
  embargo_bars: 1

universe:
  symbols: null
  train_label_min_coverage: 0.95
```

The required order is `Train < Valid < OOS`, with no overlap. When `universe.symbols` is null, symbols are fixed from Train label coverage. Otherwise, every requested symbol must exist in the label file.

`embargo_bars` purges the end of Train, Valid, and every temporal-CV fit interval by that number of distinct trading dates. Set it from the forward-label overlap rather than inferring it from file names.

Each `beam.cv_folds` entry requires `fit_start`, `fit_end`, `score_start`, and `score_end`. The fit interval must strictly precede the score interval, and the entire fold must remain inside the Train+Valid development period.

## 5. Preprocessing

Cross-sectional example:

```yaml
preprocess:
  factor_transform: cross_sectional
  label_transform: raw
  winsor_lower: 0.01
  winsor_upper: 0.99
  cross_sectional_zscore: true
  demean_label: true
  min_cross_section: 50
```

Rolling example:

```yaml
preprocess:
  factor_transform: rolling_median_zscore
  label_transform: cross_sectional_rank
  rolling_window: 252
  rolling_min_periods: 63
  rolling_clip: 3.0
  demean_label: true
  min_cross_section: 50
```

`cross_sectional` applies daily winsorization and optional z-score. `rolling_median_zscore` applies per-symbol rolling normalization. Non-finite and post-transform missing factor values become zero. Labels remain missing when invalid and are excluded from training and metrics.

## 6. Model Section

Ridge example:

```yaml
model:
  type: ridge
  ridge_alpha: 10.0
  equal_date_weight: true
```

`ridge_alpha` controls coefficient shrinkage. The intercept remains unpenalized. `equal_date_weight: true` gives every date the same total sample weight.

LightGBM example:

```yaml
model:
  type: lgbm
  model_threads: 4
  lgbm:
    learning_rate: 0.03
    n_estimators: 1500
    search_estimators: 200
    num_leaves: 7
    max_depth: 4
    min_child_samples: 300
    colsample_bytree: 0.8
    reg_alpha: 0.5
    reg_lambda: 20.0
    random_state: 20260716
    validation_days: 126
    early_stopping_rounds: 100
    fallback_estimators: 200
```

LightGBM is supported by `run-beam`, `run-many-beam`, cache validation, and OOS evaluation. Candidate ranking uses temporal OOF residuals. `model_threads` sets the LightGBM worker count for each fitted model; keep `beam.cv_jobs * model.model_threads` within the allocated CPU budget.

| Field | Meaning |
|---|---|
| `search_estimators` | Fixed tree count used during Beam search and temporal CV |
| `n_estimators` | Maximum tree count used by final-model early stopping |
| `validation_days` | Development-tail length used to select the final tree count |
| `early_stopping_rounds` | Final-model early-stopping patience |
| `fallback_estimators` | Final tree count when the development period is too short for tail validation |
| `learning_rate`, `num_leaves`, `max_depth`, `min_child_samples` | Tree-growth controls |
| `colsample_bytree`, `reg_alpha`, `reg_lambda` | Feature-sampling and regularization controls |
| `random_state` | Deterministic LightGBM seed |

## 7. Selection Section

```yaml
selection:
  random_seed: 20260721
  initial_factor: null
  max_factors: 20
  top_n_log: 10
  patience: 3
  min_factors_before_stopping: 2
  min_delta: 0.00001
  min_residual_score: 0.0
  score_method: pearson
```

- `random_seed`: deterministic seed for single-path initialization and repeated-path generation.
- `initial_factor`: fixed root for single-path or non-deterministic Beam search.
- `max_factors`: maximum length for single-path selection and default pool steps.
- `top_n_log`: residual-ranked candidates retained in diagnostics.
- `patience`: single-path stale-checkpoint tolerance.
- `min_factors_before_stopping`: minimum selected-factor count before stale-checkpoint stopping can apply.
- `min_delta`: minimum Valid mean-IC improvement for single-path selection.
- `min_residual_score`: minimum absolute mean residual IC required to continue.
- `score_method`: candidate and prediction correlation method.

## 8. Beam Section

Core fields:

| Field | Meaning |
|---|---|
| `progress` | Print depth-level or step-level progress |
| `deterministic_roots` | Build the first Beam deterministically instead of using one configured or random root |
| `root_width` | Number of high-priority root candidates considered |
| `width` | Maximum retained paths per depth |
| `branch_width` | Residual-ranked expansions per parent |
| `final_depth` | Maximum factor-set size |
| `diversity_max_jaccard` | Maximum preferred overlap among retained sets |
| `ridge_alphas` | Ridge penalties evaluated by joint temporal CV |
| `cv_folds` | Ordered causal fit/score folds |
| `cv_jobs` | Parallel candidate-CV jobs |
| `stability_penalty` | Penalty on fold-IC standard deviation |
| `min_year_weight` | Weight on the weakest fold |
| `complexity_penalty` | Per-factor score penalty |

Optional search controls:

| Field | Meaning |
|---|---|
| `search_objective` | `cv`, or Ridge-only `residual` |
| `root_residual_shortlist` | LightGBM singleton roots retained by absolute daily target correlation before root CV |
| `residual_ridge_alpha` | Fixed Ridge penalty for residual-objective search |
| `residual_selection_depth` | Frozen depth for residual-objective search |
| `trend_window` | Number of recent CV increments used by path priority |
| `trend_weight` | Weight on recent CV increments |
| `continuation_probe_width` | Number of expanded states probed one step ahead |
| `continuation_weight` | Weight on the best next residual score |
| `early_stopping_patience` | Allowed stale Beam depths; zero disables |
| `early_stopping_min_delta` | Minimum best-depth improvement |
| `one_standard_error` | Prefer a shallower checkpoint within one peak SE |
| `deep_selection_tolerance` | Prefer a deeper checkpoint within this peak-score gap |
| `checkpoint_path` | Incremental Beam-history destination |
| `resume_history` | Existing Beam history used to restore the frontier |
| `screen_fold_count` | LightGBM folds used in first-stage screening |
| `full_cv_candidates_per_parent` | LightGBM candidates per parent promoted to full CV |

Ridge deterministic Beam evaluates all singleton roots. LightGBM deterministic Beam first keeps `root_residual_shortlist` singleton candidates and then evaluates their root CV. When `deep_selection_tolerance` is configured, it takes precedence over `one_standard_error`.

## 9. Pool Section

```yaml
pool:
  progress: true
  max_steps: 20
  pool_capacity: null
  pruning_alpha: 10.0
  min_delta: 0.0
  patience: 0
  top_n_log: 10
```

`run-pool` is Ridge-only and evaluates every remaining candidate through joint temporal CV at each step. A null `pool_capacity` permits monotonic growth. A positive capacity removes the smallest absolute full-sample Ridge coefficient after an oversized augmentation. Each candidate is formally proposed at most once; a previously proposed factor removed by capacity pruning does not re-enter the candidate queue.

## 10. Output Section

```yaml
output:
  root: outputs
  experiment_name: residual_selection
```

- `root`: base directory for timestamped search and batch run directories.
- `experiment_name`: prefix used when constructing each run-directory name.

Both fields are required by every non-materialize command. Relative `root` paths are resolved from the YAML file location.

## 11. Commands

```bash
python scripts/run_factor_selection.py --config <config.yaml> materialize --jobs 4
python scripts/run_factor_selection.py --config <config.yaml> validate-cache
python scripts/run_factor_selection.py --config <config.yaml> validate-cache --write-manifest

python scripts/run_factor_selection.py --config <config.yaml> run
python scripts/run_factor_selection.py --config <config.yaml> run-many --runs 20 --master-seed 20260721
python scripts/run_factor_selection.py --config <config.yaml> run-beam
python scripts/run_factor_selection.py --config <config.yaml> run-many-beam --runs 5 --jobs 4
python scripts/run_factor_selection.py --config <config.yaml> run-pool

python scripts/run_factor_selection.py \
  --config <config.yaml> evaluate-oos \
  --run-dir <frozen-run-directory>
```

For `materialize`, `--library` is repeatable and accepts `alpha101`, `alpha158`, and `alpha191`. `--factor` and `--symbol` restrict the requested factors and symbols. `evaluate-oos` refuses to overwrite existing OOS artifacts by default; use `--force` only for an explicitly requested replacement.

## 12. Outputs

Search-run directories contain:

- `summary.json`: frozen factors, development metrics, seed, root, and model metadata;
- `iteration_history.csv`: checkpoint-level training and validation/CV evidence;
- `beam_history.csv`: retained Beam paths and fold scores when applicable;
- `residual_top10.csv`: residual candidate rankings;
- `config.json`: resolved configuration.

Batch directories additionally contain:

- `batch_summary.csv`;
- `batch_metrics.json`;
- `factor_frequency.csv`;
- `path_similarity.csv`.

After freezing a run, `evaluate-oos` refits the selected factor set on Train+Valid and writes:

- `oos_predictions.parquet`;
- `oos_evaluation.json`.

Ridge metadata includes alpha, intercept, and coefficients. LightGBM metadata includes the selected iteration count and feature importance. JSON output uses `null` for unavailable values.

## 13. Factor Backtest Skill Handoff

Run this stage only after `evaluate-oos` has completed for a frozen run:

```bash
python scripts/run_selection_backtest.py \
  --run-dir <frozen-run-directory> \
  --export-only
```

The adapter exports only the frozen `prediction` to `date`, `ticker`, and `prediction`, then prints a structured handoff for `$factor-backtest`. It rejects incomplete OOS runs, invalid predictions, duplicate keys, and unsafe security-code conversion. Supply `--ticker-map` when source symbols are not directly integer-compatible.

Pass the emitted `input_file`, `factor_column`, `timespan`, `signal_manifest`, and `signal_direction` to `$factor-backtest`, together with the real market-data root and portfolio assumptions. The export-only path neither discovers an external installation nor starts a subprocess.

The default timespan is the complete frozen OOS interval; an explicit `--timespan` must remain inside that interval. Direct external CLI execution remains an explicit compatibility mode and requires `--data-root`; use `--dry-run` only to preview that fallback command.

See `references/backtest_integration.md` for the complete data, mapping, routing, and output contract.
