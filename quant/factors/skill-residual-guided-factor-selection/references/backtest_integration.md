# Factor Backtest Skill Handoff

## Purpose

Use this integration only after a development checkpoint has been frozen and `evaluate-oos` has completed. The adapter converts the frozen OOS prediction into the public input contract of the registered `$factor-backtest` Skill and emits a structured handoff. It does not import, copy, or modify the downstream backtest engine.

## Natural-Language Routing

Treat the following concepts as portfolio-level backtest intent:

- strategy return, annualized return, or NAV;
- maximum drawdown or monthly win rate;
- holdings, turnover, execution, or transaction costs;
- benchmark-relative or hedged performance;
- a request to connect the selected signal to the existing backtest system.

Prediction IC, ICIR, residual score, and label error remain label-level evaluation requests and do not require a return backtest.

## Required Artifacts

`--run-dir` must contain:

- `summary.json`;
- `config.json`;
- `oos_evaluation.json`;
- `oos_predictions.parquet`.

The source prediction file has a `(datetime, symbol)` index and contains `target` and `prediction`. The adapter exports exactly:

| Column | Type | Meaning |
|---|---|---|
| `date` | integer `YYYYMMDD` | Signal observation date |
| `ticker` | non-negative integer | Security code used by the market-data matrices |
| `prediction` | finite float | Frozen model prediction used for cross-sectional ranking |

The realized `target` is never exported. Duplicate `(date, ticker)` rows, invalid dates, and non-finite predictions are rejected.

## Security-Code Mapping

Integer-like symbols such as `000001` and `600000` are converted directly to integers. Symbols containing exchange suffixes or other text require `--ticker-map` with `symbol` and `ticker` columns. Mapping keys and resulting integer tickers must both be unique, and every OOS symbol must be covered.

The explicit mapping requirement prevents silent collisions between identifiers that share a numeric prefix.

## Codex Skill Handoff

Use `--export-only` as the primary portfolio-evaluation path. It exports the frozen signal, prints a JSON object, and returns without locating a backtest installation or starting a subprocess.

The handoff JSON contains:

| Field | Meaning |
|---|---|
| `handoff_skill` | Registered downstream Skill name: `factor-backtest` |
| `input_file` | Absolute path to the exported Parquet signal |
| `factor_column` | Signal column, always `prediction` |
| `timespan` | Inclusive interval inside the frozen OOS period |
| `signal_manifest` | Provenance and integrity manifest |
| `signal_direction` | `higher_is_better` or `lower_is_better` |
| `target_exported` | Always `false` |

Pass these fields to `$factor-backtest` together with the actual market-data root and the requested portfolio assumptions. If `$factor-backtest` is unavailable, request installation instead of silently substituting test data or another runtime.

## Handoff Command

```bash
python scripts/run_selection_backtest.py \
  --run-dir <frozen-run-directory> \
  --export-only
```

Common export options:

| Option | Meaning |
|---|---|
| `--ticker-map` | CSV or Parquet symbol-to-ticker mapping |
| `--signal-output` | Optional exported Parquet path |
| `--timespan START END` | Optional subperiod contained inside frozen OOS |
| `--reverse` | Mark lower predictions as better signals |
| `--force-export` | Replace an existing derived signal and manifest |
| `--export-only` | Emit the `$factor-backtest` handoff and exit |

By default, the handoff interval is the complete OOS prediction period and higher predictions are treated as better signals. Set `--reverse` only when the configured target direction requires it.

## Direct CLI Compatibility

Direct execution remains available only as an explicit compatibility path:

```bash
python scripts/run_selection_backtest.py \
  --run-dir <frozen-run-directory> \
  --data-root <market-data-root> \
  --backtest-root <factor-backtest-skill-root> \
  --override longx=200
```

In this mode the adapter discovers `scripts/run_factor_backtest.py` through `--backtest-root`, `FACTOR_BACKTEST_SKILL_ROOT`, a sibling `skill-factor-backtest`, or `~/.codex/skills/skill-factor-backtest`. Use `--dry-run` to print the command without executing it. Align downstream `buy_sell_shift` with the forward-label horizon and intended execution convention.

## Outputs

The handoff path writes:

```text
<run-dir>/
└── backtest_input/
    ├── prediction.parquet
    └── prediction.manifest.json
```

The signal manifest records source and output hashes, schema, row count, symbol count, date interval, ticker-mapping provenance, and confirmation that the target was not exported. The JSON handoff is printed to standard output for Codex to pass to `$factor-backtest`.

Repeated exports reuse an existing derived signal only when its table contents, source hash, output hash, and ticker-mapping provenance match the current frozen source. Otherwise, replacement requires `--force-export`. Direct compatibility execution additionally writes external outputs and `selection_backtest_invocation.json` under `backtest_results/`.

## Agent Procedure

1. Confirm that factor selection is frozen and `evaluate-oos` has completed.
2. Determine whether symbols are directly integer-compatible or require a ticker map.
3. Run the adapter with `--export-only` and parse the emitted JSON.
4. Verify that `target_exported` is `false` and that the signal and manifest paths exist.
5. Obtain the real market-data root; never substitute a test fixture for research evaluation.
6. Invoke `$factor-backtest` with the handoff fields and the requested benchmark, holdings count, costs, signal direction, and execution delay.
7. Let `$factor-backtest` validate inputs, execute the backtest, and verify its expected outputs.
8. Report the OOS interval, signal direction, portfolio assumptions, output directory, return metrics, drawdown, turnover, and benchmark-relative results.
