# Downstream Evaluation Boundary

The search workflow ends when `summary.json.selected_factors` is frozen. Label-level OOS evaluation and portfolio-level return evaluation are distinct stages. Portfolio construction, transaction costs, execution, and return calculation remain responsibilities of the registered `$factor-backtest` Skill.

## Research Sequence

```text
Development search
    -> freeze one factor set and model configuration
    -> explicit label-level OOS evaluation

Frozen factors and preprocessing
    -> point-in-time model predictions
    -> export signal and handoff manifest
    -> $factor-backtest
    -> portfolio construction and cost-aware backtest
```

`evaluate-oos` refits the frozen model on Train+Valid and evaluates predictions against the configured OOS label. It does not create holdings or calculate strategy returns.

## Evaluation Routing

- Requests for prediction IC, ICIR, error, or label-level accuracy use `evaluate-oos`.
- Requests for returns, NAV, drawdown, holdings, turnover, transaction costs, benchmark comparison, or hedged performance export a handoff after `evaluate-oos`, then use `$factor-backtest`.
- A request that combines both stages first freezes the development checkpoint, then evaluates OOS, then backtests only the generated OOS prediction interval.

## Integration Contract

- Read the factor list from `summary.json.selected_factors`.
- Use `oos_predictions.parquet` when the downstream system accepts precomputed signals.
- Export only `prediction` as the trading signal. The realized `target` remains an evaluation field and must not enter the backtest input.
- Preserve factor definitions, preprocessing, point-in-time availability, label timing, and universe construction.
- Define retraining windows, rebalance schedules, execution prices, costs, constraints, and benchmarks in the downstream system.
- Keep rolling retraining windows separate from the factor-selection CV folds.
- Version changes to factors, thresholds, model settings, portfolio rules, or evaluation periods as separate runs.

Read `backtest_integration.md` before exporting a handoff or running a return backtest.
