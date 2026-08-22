# Methodology — Barra-style structural risk model

## 1. The structural model

Each stock's return is a linear combination of factor exposures times factor
returns, plus an idiosyncratic residual:

```
r_{i,t+1} = sum_k X_{i,k,t} f_{k,t} + u_{i,t}
```

- `X` — exposures (known at t): style factors + industry dummies.
- `f` — factor returns (estimated): the regression coefficients.
- `u` — specific (idiosyncratic) returns: the residuals.

## 2. Exposures (`exposures.py`)

Style factors computed from returns + market cap, then **winsorised (MAD) and
z-scored cross-sectionally each date** so they are comparable through time:

| Factor | Definition |
|--------|-----------|
| SIZE | `ln(market cap)` |
| MOMENTUM | cumulative return over [t-252, t-21] (12-1 month) |
| SHORT_REV | trailing 21-day return (short-term reversal) |
| VOLATILITY | annualised 60-day return stdev |
| BETA | 120-day rolling beta to the cap-weighted market |

VALUE (book-to-price) and LIQUIDITY (turnover / Amihud) require fundamentals and
turnover and can be passed in via `extra_exposures`. Industry membership becomes
one-hot dummy columns.

## 3. Factor returns via cross-sectional WLS (`cross_section_reg.py`)

Each date we regress next-period returns on exposures with weights
`∝ sqrt(market cap)` (larger names anchor the fit, as in commercial models):

```
f_t = argmin_f  sum_i w_i ( r_{i,t+1} - X_{i,t} f )^2
```

This is the cross-sectional (Fama-MacBeth style) regression. The fitted `f_t`
are factor returns; residuals `u_{i,t}` are specific returns. A tiny ridge keeps
the normal equations stable when exposures are near-collinear.

> The cross-section must have **many more stocks than factors**, otherwise the
> system is under-identified. With 5 styles + N industries you want 30+ names.

## 4. Covariance (`factor_cov.py`)

- **Factor covariance F**: EWMA of demeaned factor-return cross-products
  (half-life ~90d) so recent regimes dominate, then eigenvalue-clipped to PSD
  and annualised. A Ledoit-Wolf option is available for short samples.
- **Specific variance Δ**: EWMA of squared specific returns per stock
  (half-life ~60d), annualised. Assumed diagonal (idiosyncratic risks
  uncorrelated).

The full asset covariance is then

```
Sigma = X F X' + diag(Delta)
```

structural, well-conditioned and positive definite — ready for
`skill-portfolio-optimize`.

## 5. Risk attribution (`risk_attribution.py`)

For weights `w`, portfolio factor exposure `b = X'w`. Total variance splits
exactly into factor and specific parts:

```
sigma_p^2 = b' F b           (factor)
          + w' diag(Delta) w (specific)
```

Each factor's **component contribution to risk (CCTR)** via Euler's theorem:

```
CCTR_k = b_k (F b)_k ,    sum_k CCTR_k = b' F b
```

so the per-factor `%var` figures sum to the factor-risk share. This tells you
*which* style or industry your portfolio's risk actually comes from.

## References

- Rosenberg, B. (1974); MSCI Barra *US Equity Model (USE4)* methodology.
- Fama, E. F., & MacBeth, J. D. (1973). *Risk, Return, and Equilibrium.* JPE 81(3).
- J.P. Morgan/Reuters (1996). *RiskMetrics Technical Document* (EWMA covariance).
- Ledoit, O., & Wolf, M. (2004). *A well-conditioned estimator for large-dimensional covariance matrices.* J. Multivariate Analysis 88(2).
- Menchero, J., & Davis, B. (2011). *Risk Contribution is Exposure times Volatility times Correlation.* J. Portfolio Management 37(2).
