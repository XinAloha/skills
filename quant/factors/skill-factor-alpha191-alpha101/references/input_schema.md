# Input Schema

The CLI accepts a JSON file:

```bash
python scripts/compute_alpha_factors.py --input examples/compute_input.json
```

Optional output override:

```bash
python scripts/compute_alpha_factors.py --input examples/compute_input.json --output outputs/my_run
```

## Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `market_data_csv_path` | string | yes | Long-form CSV path. Relative paths are resolved from the input JSON directory, then the skill root, then the skill `examples/` directory. |
| `benchmark_csv_path` | string | no | Optional benchmark CSV with `date`, `close` and optionally `open`; used by Alpha191 factors that require benchmark data. |
| `output_dir` | string | no | Output directory. Relative paths are resolved from the skill root. |
| `alpha_sets` | list/string | no | `alpha101`, `alpha191`, or both. Empty means both. |
| `alpha_names` | list/string | no | Empty means all selected factors. Supports `alpha_001`, `1`, and qualified names like `alpha101:alpha_001`. |
| `exclude_alpha_names` | list/string | no | Factors to exclude after selection. Supports qualified names. |
| `start_date` | string | no | Inclusive date filter, accepts `YYYYMMDD` or `YYYY-MM-DD`. Empty means no lower bound. |
| `end_date` | string | no | Inclusive date filter, accepts `YYYYMMDD` or `YYYY-MM-DD`. Empty means no upper bound. |
| `symbols` | list[string] | no | Optional stock universe filter. Empty means all symbols. |
| `n_jobs` | integer | no | Worker count. Default is the machine logical CPU count. |
| `show_progress` | bool | no | Print progress bars during factor computation. |

## Market Data Columns

Required columns:

```text
date, symbol, open, high, low, close, volume
```

Optional columns:

```text
amount, vwap, adjfactor, pre_close, limit_up, limit_down
```

If `vwap` is missing and `amount` plus `volume` are present, vwap is derived as `amount / volume`. If `amount` is missing, it is approximated as `close * volume`.
