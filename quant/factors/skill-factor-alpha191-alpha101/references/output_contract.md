# Output Contract

The skill writes outputs under `output_dir`.

## Files

| File | Description |
| --- | --- |
| `alpha101_values.csv` | Wide Alpha101 factor values. Present only when at least one Alpha101 factor is computed. |
| `alpha191_values.csv` | Wide Alpha191 factor values. Present only when at least one Alpha191 factor is computed. |
| `alpha_compute_summary.json` | Run summary with counts, date range, output paths, and selected alpha sets. |
| `skipped_factors.json` | Factors that returned `None` or failed formula computation. The run does not stop for these factors. |
| `run_config.json` | Copy of the input JSON used for the run. |

## Wide CSV Layout

```text
date,symbol,alpha_001,alpha_002,...
```

Each row is one `(date, symbol)` observation. Each alpha column contains the computed factor value rounded by the runtime output builder.

## Skipped Factor Record

```json
{
  "alpha_set": "alpha191",
  "alpha_name": "alpha_075",
  "reason": "returned_none"
}
```

Skipped factors are omitted from the wide value CSV.
