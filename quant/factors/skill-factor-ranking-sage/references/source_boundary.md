# Source Boundary

This skill ranks factors from user-provided local factor and label CSV files.

## Data Boundary

- The bundled toy CSV files are synthetic data constructed for smoke tests and do not represent real securities, market data, or accounts.
- Inputs are local CSV files with unique (date, ticker) keys.
- Factor and label rows are inner-joined on the configured date and ticker columns.
- Labels and factor availability timing must be constructed and verified by the user.
- When `available_date` is absent, the runtime records a point-in-time notice because publication and availability lags are supplied by the user.
- The fixed validation split is used for factor ranking and contribution estimation.

## Algorithm Boundary

- The mRMR mode reproduces regression F-statistic relevance, absolute Pearson redundancy, and greedy quotient selection.
- The SAGE mode reproduces empirical marginal imputation and permutation-based global MSE contribution for a fixed LGBM or MLP model.
- The runtime scope consists of these two documented ranking modes and their output contracts.

## Research Boundary

- mRMR ranks factors by target relevance and pairwise redundancy.
- SAGE attributes average fixed-model loss contribution under the configured marginal imputation procedure.
- Correlated factors may share Marginal-SAGE attribution.
- Use `sage_metadata.json` and `sage_std` to assess convergence and estimation stability.
- A locked holdout can be used to compare the selected subset with full-factor and random-subset baselines.
- Outputs are quantitative research artifacts, not investment advice, trading signals, return guarantees, or production validation.
