# Input Contract

`forecasts.csv` must contain `date,probability,outcome`. Probabilities must be numeric in `[0, 1]`; outcomes must be realized binary values `0` or `1`. An optional `regime` (or other column passed with `--regime-column`) enables subgroup metrics.

The script sorts chronologically, never shuffles rows, clips probabilities only for the logarithm in log loss, and keeps the original probability in the scored output. Time bins are contiguous row blocks, not random cross-validation folds.
