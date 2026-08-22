# Methodology

## Model

Rolling CAPM-style OLS:

`r_i = α + β r_m + ε`

Reports α, β, HC1 heteroskedasticity-robust SE(β), 95% CI, R², residual vol (annualized).

## Extensions

- **Up/Down beta**: condition on `r_m > 0` / `< 0` within the latest rolling window
- **Vasicek shrink**: Bayesian shrink of latest β toward prior mean 1.0
- **Path diagnostics**: max |\Deltaβ| across rolling windows

## Verdict labels

- `HIGH_BETA` / `MODERATE_BETA` / `LOW_BETA`
- suffix `_ASYMMETRIC` when |up−down| ≥ 0.35

## Limits

- Single-factor market model only (not Barra multi-factor).
- Window choice matters; default 60 trading days.
