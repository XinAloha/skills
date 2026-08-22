# Methodology

## Notation

`w` weights (n×1), `μ` expected returns, `Σ` covariance, `σ = sqrt(diag(Σ))`.
Portfolio variance `σ_p² = wᵀΣw`.

## Objectives

### Minimum Variance
```
min  wᵀ Σ w     s.t.  constraints
```
Ignores expected returns entirely — robust when `μ` is hard to estimate.

### Mean-Variance (Markowitz 1952)
```
max  wᵀμ − (λ/2) wᵀΣw
```
`λ` is risk aversion. Sweeping `λ` traces the efficient frontier
(`scripts/frontier.py`).

### Maximum Sharpe
```
max  wᵀμ / sqrt(wᵀΣw)
```
The tangency portfolio. Non-convex in raw form; solved by SLSQP from the
equal-weight start.

### Risk Parity / Equal Risk Contribution (Maillard et al. 2010)
Each asset's risk contribution `RC_i = w_i (Σw)_i` should be equal. We minimise
```
Σ_i ( RC_i − σ_p²/n )²
```
subject to long-only, fully invested. Diversifies *risk*, not dollars.

### Maximum Diversification (Choueifaty & Coignard 2008)
Maximise the diversification ratio
```
DR(w) = (wᵀσ) / sqrt(wᵀΣw)
```
the ratio of weighted-average vol to portfolio vol; high when holdings are
weakly correlated.

## Constraints

| Constraint | Form |
|-----------|------|
| Full investment | `Σ w = 1` |
| Long-only | `w ≥ 0` |
| Weight cap | `|w_i| ≤ cap` |
| Sector neutral | for each sector `s`: `Σ_{i∈s} w_i = target_s` (default 0) |
| Factor-exposure neutral | `Xᵀ w = 0` for exposure matrix `X` |
| Turnover limit | `Σ|w_i − w_prev,i| ≤ τ` |

Equality constraints (sector / exposure neutrality) can conflict with tight
weight caps and render the problem infeasible — relax one side if SLSQP fails.

## Covariance estimation (Ledoit & Wolf 2004)

The sample covariance is noisy and often ill-conditioned when `n` assets ≈ `T`
observations. Ledoit-Wolf shrinks it toward a structured target:
```
Σ_shrunk = (1 − δ) Σ_sample + δ F
```
with an analytically optimal intensity `δ`. We additionally clip negative
eigenvalues to guarantee a positive semi-definite matrix before optimisation.

For a richer, structural covariance (factor + specific risk) use
`skill-risk-model`, which plugs straight into this optimiser.

## Solver

All objectives use `scipy.optimize.minimize(method="SLSQP")` with analytic
bounds and constraint callbacks. Convex objectives (min-variance, mean-variance)
reach the global optimum; for risk-parity / max-diversification use multiple
starts if you suspect a local solution.

## References

- Markowitz, H. (1952). *Portfolio Selection.* Journal of Finance 7(1).
- Ledoit, O., & Wolf, M. (2004). *A well-conditioned estimator for large-dimensional covariance matrices.* J. Multivariate Analysis 88(2).
- Maillard, S., Roncalli, T., & Teïletche, J. (2010). *The properties of equally weighted risk contribution portfolios.* J. Portfolio Management 36(4).
- Choueifaty, Y., & Coignard, Y. (2008). *Toward Maximum Diversification.* J. Portfolio Management 35(1).
