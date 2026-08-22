# Input Schema

Provide factor and label CSV files with unique `(date, ticker)` rows. Dates may be `YYYYMMDD` values or parseable date strings. Factor columns must be numeric.

Both modes require one fixed time split. mRMR uses only the training rows. SAGE fits on the training rows and explains validation loss on the validation rows.

## mRMR

```json
{
  "run_name": "mrmr_run",
  "output_root": "outputs/mrmr_run",
  "mode": "mrmr",
  "selection_count": 50,
  "input": {
    "feature_path": "factors.csv",
    "label_path": "labels.csv"
  },
  "data": {
    "date_col": "date",
    "ticker_col": "symbol",
    "label_col": "y"
  },
  "validation": {
    "method": "fixed",
    "train_start": 20150101,
    "train_end": 20201231,
    "valid_start": 20210101,
    "valid_end": 20221231,
    "embargo_days": 0
  },
  "mrmr": {
    "relevance": "f",
    "redundancy": "c",
    "denominator": "mean"
  }
}
```

The local mRMR implementation accepts regression relevance `f`, Pearson-correlation redundancy `c`, and denominator `mean` or `max`.

## SAGE

```json
{
  "run_name": "sage_run",
  "output_root": "outputs/sage_run",
  "random_seed": 42,
  "mode": "sage",
  "selection_count": 50,
  "input": {
    "feature_path": "factors.csv",
    "label_path": "labels.csv"
  },
  "data": {
    "date_col": "date",
    "ticker_col": "symbol",
    "label_col": "y"
  },
  "validation": {
    "method": "fixed",
    "train_start": 20150101,
    "train_end": 20201231,
    "valid_start": 20210101,
    "valid_end": 20221231,
    "embargo_days": 0
  },
  "model": {
    "type": "lgbm",
    "params": {}
  },
  "sage": {
    "loss": "mse",
    "background_size": 128,
    "evaluation_size": 10000,
    "batch_size": 512,
    "n_permutations": null,
    "detect_convergence": true,
    "convergence_threshold": 0.025
  }
}
```

Use `model.type=lgbm` or `model.type=mlp`. `background_size` and `evaluation_size` cap deterministic random samples used by the local SAGE implementation. Set `n_permutations` to a positive requested sample budget or `null` with convergence detection enabled. For reference compatibility, the estimator processes complete batches, so the actual `sage_sample_count` is `ceil(n_permutations / batch_size) * batch_size`.
