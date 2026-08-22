# Validation Notes

## Recommended Validation Sequence

1. Run `examples/hpo_lgbm_smoke.json` to verify dependencies and output paths.
2. Run `examples/hpo_mlp_smoke.json` only after confirming `torch` is installed.
3. Run `examples/hpo_custom_extension_smoke.json` after adding or changing an extension.
4. Run a small real-data LGBM experiment with fixed train/validation/test dates.
5. Run the same budget with `search.method=grid` when deterministic grid-search coverage is needed.
6. For LLM decision tests, use `decision_provider.type=codex_external` so the runtime exchanges evidence and decision JSON files through the run directory.
7. For `legacy_v1`, confirm trial-index seeds and automatic test artifacts. For `research_v2`, confirm a common initial seed and multi-seed confirmation artifacts.
8. Under `research_v2`, run holdout only after freezing the selected search run.
9. For a public report, keep the split, trial budget, seed list, search space, and objective fixed across compared methods.

## Practical Assumptions

- LGBM can consume NaN values natively.
- MLP uses configured filling before tensor conversion.
- `rankic_ir` is a validation ranking metric, not a portfolio return metric.
- `robust_rankic` uses equal-weight time blocks and penalizes block standard error.
- `top_bottom_spread` is computed on prediction-ranked groups inside the validation evaluator.
- `positive_window_ratio` measures the fraction of validation windows with positive rankIC.

## Common Failure Modes

- Empty merge: feature and label files do not share `(date, ticker)` keys.
- Embargo violation: train/valid/test dates do not leave enough gap relative to `label_window + trade_lag_days`.
- All-null factor columns: set `data.all_null_feature_policy` to `allow`, `drop`, or `raise` explicitly.
- Missing LLM decision file: use `decision_provider.on_missing=stop` to pause for a decision, or `fallback` for non-blocking smoke tests.
- MLP runs slowly on CPU with large datasets; reduce dates, assets, layers, epochs, or trials for smoke tests.
- Unknown extension component: confirm the module is listed, `allow_external=true`, and its `register(registry)` function registers the configured name.
- External model with structured probes: use `sampler=adaptive` or `search.method=grid`; LGBM/MLP probes are model-specific.
- Strict PIT failure: provide `available_date`, `label_start_date`, `label_end_date`, and a point-in-time universe, or disable strict mode only for toy data.
- Holdout metrics missing under `research_v2`: this is expected; use the explicit holdout command after freezing parameters.

## Reporting Caution

Do not present one holdout result as proof of trading profitability. A stronger report should include multiple periods, multiple seeds, fixed-budget comparisons, and separation between validation-selected parameters and holdout reporting.
