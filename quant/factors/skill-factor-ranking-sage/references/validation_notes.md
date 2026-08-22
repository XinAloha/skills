# Validation Notes And Boundaries

- Verify factor and label timing before running; `available_date` can record the factor availability date when it is present.
- Use an embargo at least as long as the overlapping label horizon.
- mRMR uses only training rows and ignores validation rows.
- SAGE trains the fixed model on training rows and evaluates global contribution on sampled validation rows.
- SAGE uses the local empirical marginal imputer; correlated factors may receive unstable or shared attribution.
- The Top-K size is supplied by `selection_count`.
- Use a locked holdout to compare the selected subset with full-factor and random-subset baselines.
