# Residual-Guided Factor Selection

This Codex-callable skill searches quantitative factor banks for compact sets with complementary predictive structure. It combines residual-guided candidate generation, causal temporal validation, multi-path retention, auditable checkpoints, and explicit sealed OOS evaluation.

## Project Information

- **Project status**: QuantSkills Community Project, not officially reviewed, certified, or endorsed by QuantSkills.
- **Maintainer**: `X-Tech-group`.
- **Repository metadata**: Organization, repository, project type, collection, license, and maintenance information are declared in [`skill.yml`](skill.yml).

## Method Overview

```text
Wide labels + factor bank
        |
        v
Universe -> preprocessing -> isolated Train / Valid / OOS periods
        |
        v
Joint model on the current factor set
        |
        +-- Ridge single path: Train in-sample residuals
        |
        +-- Ridge Beam: Train+Valid development-period in-sample residuals
        |
        +-- LightGBM Beam: expanding-fold OOF residuals
        |
        v
Daily cross-sectional candidate-to-residual correlations
        |
        v
Rank by |mean daily residual IC| and expand search paths
        |
        v
        +-- search_objective=cv: joint temporal CV and Beam pruning
        |
        +-- search_objective=residual: development weighted Ridge R^2 and Beam pruning
        |
        v
Select and freeze one development checkpoint
        |
        v
Explicit evaluate-oos -> frozen OOS prediction and label-level metrics
        |
        +-- handoff manifest -> Codex invokes $factor-backtest
```

For a current factor set `S`, target `y`, and fitted prediction `y_hat_S`, define `r_S = y - y_hat_S`. For each remaining factor `x_j`, the selector computes its cross-sectional correlation with `r_S` on each valid trading day and then calculates:

```text
signed_mean_ic_j = mean_t corr_cs(x_j,t, r_S,t)
candidate_score_j = abs(signed_mean_ic_j)
```

Absolute scoring admits complementary factors with either positive or negative residual correlation, while preserving the signed statistic in the output. After each addition, the model jointly refits the complete updated factor set.

## Residual Models

Ridge `run` and `run-many` use Train in-sample residuals from the current joint model. Ridge Beam uses in-sample residuals from the Train+Valid development period. The intercept is unpenalized, and `equal_date_weight` can assign equal total weight to each trading date. Ridge supports single paths, repeated random roots, deterministic super-root Beam search, and randomized Beam search.

LightGBM is available for Beam search. Each temporal fold trains on an earlier interval and predicts a later score interval; concatenating these predictions produces the OOF residuals used for candidate ranking. Final fitting can use a development-tail validation interval for early stopping and then refit the selected iteration count on the full development period.

## Multi-Path Search

Beam Search retains more than the current best path. At each depth, every retained path contributes its top `branch_width` residual-ranked candidates, and at most `width` paths survive. With `search_objective: cv`, expanded sets receive joint temporal-CV scores. With Ridge `search_objective: residual`, paths are retained by development-period weighted Ridge `R^2`, frozen at `residual_selection_depth`, and supplemented with temporal-CV checkpoint evidence. A Jaccard constraint limits overlap among retained sets.

The default CV score is:

```text
cv_score =
    mean(fold_ic)
    - stability_penalty * std(fold_ic)
    + min_year_weight * min(fold_ic)
    - complexity_penalty * factor_count
```

`trend_weight` can add recent CV improvement to search priority, and `continuation_weight` can add a one-step residual-complementarity probe. Under the CV objective, final checkpoint selection supports peak CV, a shallower one-standard-error checkpoint, or a deeper checkpoint within `deep_selection_tolerance` of the peak. When configured, `deep_selection_tolerance` takes precedence over `one_standard_error`.

`run-pool` provides exhaustive joint-CV pool search. It evaluates every remaining factor after joint augmentation at each step. When `pool_capacity` is set, an oversized pool removes the factor with the smallest absolute full-sample Ridge coefficient.

## Data and Temporal Isolation

Labels and raw factors use wide Parquet files:

- rows are trading dates;
- columns are symbols;
- each factor is stored in one file;
- labels are normally forward returns aligned to the observation date.

`Train < Valid < OOS` periods must be ordered and non-overlapping. The runtime may preprocess and cache the full panel, but search objectives, candidate rankings, and checkpoint selection access only the Train+Valid development period. Frozen `evaluate-oos` is the only operation that uses OOS values for predictions and metrics. `embargo_bars` purges the end of each fitting interval by a configured number of trading dates to isolate overlapping forward labels.

The runtime supports:

- `cross_sectional`: daily winsorization and optional cross-sectional z-score;
- `rolling_median_zscore`: causal per-symbol rolling median and standard-deviation normalization with clipping.

Non-finite or post-transform missing factor values become zero. Labels can remain raw or become daily cross-sectional ranks, with optional daily demeaning. The universe can be explicit or fixed from Train label coverage.

## Quick Start

```bash
python -m pip install -r requirements.txt
python examples/generate_residual_search_toy_data.py

python scripts/run_factor_selection.py \
  --config examples/residual_search/toy_config.yaml run

python scripts/run_factor_selection.py \
  --config examples/residual_search/toy_config.yaml run-beam

python scripts/run_factor_selection.py \
  --config examples/residual_search/toy_config.yaml run-pool
```

Freeze a development result before OOS evaluation:

```bash
python scripts/run_factor_selection.py \
  --config examples/residual_search/toy_config.yaml evaluate-oos \
  --run-dir <frozen-run-directory>
```

When return-level evaluation is requested, export the frozen OOS signal and handoff contract for the registered `$factor-backtest` Skill:

```bash
python scripts/run_selection_backtest.py \
  --run-dir <frozen-run-directory> \
  --export-only
```

The command emits structured JSON containing `input_file`, `factor_column=prediction`, `timespan`, `signal_manifest`, and `signal_direction`. Codex passes these fields, the real market-data root, and portfolio assumptions to `$factor-backtest`, which validates inputs, executes the backtest, and verifies its outputs. Export-only mode neither discovers an external script nor starts a subprocess; direct CLI execution remains an explicit compatibility path.

When both Skills are installed and registered, Codex routes natural-language requests mentioning returns, NAV, drawdown, holdings, turnover, or hedged performance through both Skills in sequence; users do not need to name either Skill explicitly.

| Command | Purpose |
|---|---|
| `materialize` | Materialize wide factor files from bars and factor formulas |
| `validate-cache` | Validate a prepared-feature cache and manifest |
| `run` | Run one Ridge residual-forward path |
| `run-many` | Run repeated Ridge paths with shared prepared features |
| `run-beam` | Run deterministic or randomized multi-path search |
| `run-many-beam` | Run repeated randomized Beam paths |
| `run-pool` | Run exhaustive joint-CV pool search |
| `evaluate-oos` | Refit a frozen result and write OOS predictions |

See [Usage and Configuration](references/usage.md) for the full contract, [Algorithm](references/algorithm.md) for implementation-level semantics, and [Backtest Integration](references/backtest_integration.md) for the Codex Skill handoff contract.

## Outputs

Each search directory contains:

- `summary.json`: frozen factors, development metrics, and model metadata;
- `iteration_history.csv`: checkpoint metrics and selection records;
- `beam_history.csv`: written only by Beam search, with paths, parents, fold scores, and retention state;
- `residual_top10.csv`: residual-ranked candidates by path and iteration;
- `config.json`: the fully resolved configuration.

Batch runs also write `batch_summary.csv`, `batch_metrics.json`, `factor_frequency.csv`, and `path_similarity.csv`. Explicit OOS evaluation writes `oos_predictions.parquet` and `oos_evaluation.json`. Backtest handoff writes `backtest_input/prediction.parquet`, its signal manifest, and handoff JSON on standard output; `$factor-backtest` writes portfolio results to its configured output directory.

## Code Layout

```text
scripts/
├── run_factor_selection.py
├── run_selection_backtest.py
└── residual_factor_selection/
    ├── cli.py
    ├── config.py
    ├── data.py
    ├── preprocess.py
    ├── ridge.py
    ├── metrics.py
    ├── selector.py
    ├── beam.py
    ├── lgbm_beam.py
    ├── pool.py
    ├── cache.py
    ├── materialize.py
    ├── serialization.py
    ├── experiment.py
    └── backtest_adapter.py
```

The skill owns frozen factor sets, model predictions, label-level metrics, and deterministic signal handoff to `$factor-backtest`. Portfolio construction, turnover, execution prices, transaction costs, and return calculation are owned by `$factor-backtest`, as described in [Downstream Evaluation](references/downstream_evaluation.md).

## Research Boundaries

- **Data source**: The repository does not distribute real market, factor, or label data; example scripts generate deterministic synthetic data only. Users provide real data and remain responsible for licensing, access authorization, and compliant use.
- **Core assumptions**: Factors are genuinely available at their observation timestamps, forward-return labels are aligned to the correct observation dates, Train, Valid, OOS, and `embargo_bars` isolate forward information, and universe and trading-calendar definitions remain auditable throughout the study.
- **Result dependencies**: Selection and backtest results depend on data quality, factor coverage, label definition, universe, preprocessing, model and search settings, and downstream transaction-cost, execution-price, and portfolio assumptions.
- **Method boundary**: This skill produces factor sets, label-level metrics, and frozen OOS signals. `$factor-backtest` independently calculates and validates portfolio returns, risk, holdings, and turnover.
- **Use**: Outputs are for quantitative research, education, and methodological evaluation only. They are not investment advice, rebalance recommendations, production-deployment approval, or profit assurance.
