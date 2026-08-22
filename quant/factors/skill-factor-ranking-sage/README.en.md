# Factor Ranking SAGE

**English** | [简体中文](README.md)

> A Codex / QUANTSKILLS skill that applies regression mRMR or fixed-model Marginal-SAGE to local factor and label data and exports reproducible, auditable Top-K rankings.

## What It Does

The repository packages two independent factor-ranking methods behind one local JSON CLI:

- **mRMR** uses univariate regression F-statistic relevance, absolute Pearson redundancy, and greedy quotient selection.
- **Marginal-SAGE** fits one LGBM or MLP model and estimates global validation MSE contribution with empirical marginal imputation and random factor permutations.

Both methods use the same JSON configuration workflow and command-line entry point, with inspectable ranking artifacts and run records.

## Quick Start

~~~bash
python -m pip install -r requirements.txt

python scripts/run_factor_selection.py --input examples/factor_selection_mrmr_smoke.json
python scripts/run_factor_selection.py --input examples/factor_selection_lgbm_smoke.json
python scripts/run_factor_selection.py --input examples/factor_selection_mlp_smoke.json
~~~

Run a custom JSON configuration:

~~~bash
python scripts/run_factor_selection.py --input <input-json>
~~~

## Input

Provide local factor and label CSV files with unique (date, ticker) rows. Factor columns must be numeric. Configure one fixed train/validation split and an embargo that matches the overlapping label horizon.

The bundled toy CSV files are synthetic data constructed for smoke tests. They do not represent real securities, market data, or accounts.

- mRMR uses training rows only.
- SAGE fits on training rows and estimates contribution on sampled validation rows.
- available_date is optional. When it is absent, the runtime records a point-in-time notice in the results.

See references/input_schema.md for the full JSON contract.

## Outputs

Each run writes output_root/runs/<run_id>/ with selected_factors.json, selection_report.md, resolved_config.json, input_manifest.json, and run_manifest.json.

mRMR also writes mrmr_ranking.csv and mrmr_redundancy_matrix.csv. SAGE also writes sage_values.csv and sage_metadata.json.

Read references/output_contract.md and references/metric_definitions.md before consuming results.

## Validation and Interpretation

- mRMR relevance and redundancy characterize target association and pairwise factor overlap.
- SAGE values characterize each factor's average MSE contribution in a fixed model.
- Use sage_std, converged, and convergence_ratio to assess contribution and ranking stability.
- Compare Top-K on a locked holdout against the full factor set and multiple random Top-K baselines.

The current runnable validation scope covers smoke workflows, method behavior, convergence diagnostics, and output contracts.

## References

- references/source_boundary.md: data, algorithm, and research boundaries
- references/input_schema.md: configuration fields
- references/output_contract.md: artifact contract
- references/metric_definitions.md: mRMR and SAGE values
- references/validation_notes.md: validation limitations
- references/algorithm_sources.md: algorithm provenance and license notices

## Project Status

This is a QUANTSKILLS Community Project for quantitative research and education. It reproduces the documented mRMR and Marginal-SAGE workflows on user-provided data and does not constitute investment advice.

## License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE).
