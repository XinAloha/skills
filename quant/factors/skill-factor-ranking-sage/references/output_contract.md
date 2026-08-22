# Output Contract

Each run writes `output_root/runs/<run_id>/`.

## Common Artifacts

- `selected_factors.json`: mode, ordered selected factors, non-selected factors, Top-K count, and local selection basis.
- `selection_report.md`: concise method, input, selected-factor, warning, and boundary summary.
- `resolved_config.json`: resolved input configuration.
- `input_manifest.json`: source hashes, panel dimensions, fixed split, and warnings.
- `run_manifest.json`: completion status, mode, local algorithm versions, counts, and artifact inventory.

## mRMR Artifacts

- `mrmr_ranking.csv`: local selection order and F-statistic relevance for each selected factor.
- `mrmr_redundancy_matrix.csv`: reference-compatible Pearson redundancy values calculated during selection.

## SAGE Artifacts

- `sage_values.csv`: all factors sorted by local `sage_value`, with local standard errors in `sage_std`.
- `sage_metadata.json`: implementation version, explanation type, loss, sample sizes, convergence status, and convergence ratio.
