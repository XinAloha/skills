# Metric Definitions

## Local mRMR

The implementation computes univariate regression F-statistic relevance with scikit-learn and absolute Pearson redundancy with pandas.

For a candidate factor `j` and the already selected set `S`:

```text
score(j) = relevance(j) / aggregate(abs(correlation(j, S)))
```

- `rank`: local greedy selection order from 1 to K.
- `relevance`: univariate regression F-statistic.
- `mrmr_redundancy_matrix.csv`: Pearson redundancy values calculated as factors are selected.
- `denominator=mean`: aggregate redundancy by the mean.
- `denominator=max`: aggregate redundancy by the maximum.
- `0.001`: fixed redundancy floor used by the reference-compatible implementation.

The mRMR output is a statistical relevance and redundancy ranking.

## Local Marginal-SAGE

The implementation uses empirical marginal imputation, random factor permutations, per-sample MSE deltas, and Welford online statistics.

- `sage_value`: mean global MSE predictive-power contribution.
- `sage_std`: estimated standard error of the mean contribution.
- `rank`: descending order of `sage_value`.
- `convergence_ratio`: maximum `sage_std` divided by the range of `sage_value`.
- `sage_sample_count`: number of sampled evaluation/permutation observations accumulated.

`n_permutations` follows the reference estimator's sample-count semantics rather than counting one dataset-wide path. Each sampled evaluation row receives its own random factor permutation, and fixed budgets are rounded up to a complete batch.

SAGE values describe fixed-model contributions under the configured marginal imputation and permutation procedure.

See `algorithm_sources.md` for algorithm provenance and license notices.
