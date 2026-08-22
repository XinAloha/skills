# Portfolio Risk Models

Use this reference when estimating ex-ante risk, decomposing exposures, or validating a covariance and factor model.

## Contents

- [Model structure](#model-structure)
- [Covariance quality](#covariance-quality)
- [Risk decomposition](#risk-decomposition)
- [Stress overlays](#stress-overlays)
- [Validation and drift](#validation-and-drift)

## Model structure

A standard factor model is:

```text
r = B f + e
Sigma = B F B' + D
```

where `B` is the asset-by-factor exposure matrix, `F` is factor covariance, and `D` is specific variance. Record the factor definitions, estimation window, weighting scheme, exposure timestamp, factor-return source, treatment of missing exposures, and whether exposures are raw, neutralized, or benchmark-relative.

Match the model to the portfolio. A daily equity model is not sufficient for intraday derivatives, options Greeks, futures rolls, credit spread risk, rates curves, commodities, or multi-currency portfolios without explicit extensions.

## Covariance quality

Before using `Sigma`, check:

- symmetry within tolerance;
- finite values and valid diagonal variances;
- positive semidefiniteness, including the smallest eigenvalue;
- condition number and effective rank;
- factor and asset coverage for every held or traded instrument;
- sensitivity to estimation window, return frequency, volatility forecast, and correlation shrinkage;
- freshness relative to the portfolio decision timestamp.

Use shrinkage, factor structure, robust estimators, or eigenvalue regularization deliberately. If eigenvalue clipping is used, record the threshold and quantify how much risk changed. Never replace an invalid matrix with an identity matrix without labeling the resulting risk as a fallback estimate.

For volatility targeting, specify whether scaling uses realized, forecast, stressed, or blended volatility. Apply leverage caps, margin limits, liquidity limits, and gap-loss controls after scaling; a target volatility does not protect against jumps or model error.

## Risk decomposition

For weights `w`, report total variance `w' Sigma w`, total volatility, and contribution by factor and asset. A common marginal contribution is:

```text
MRC_i = (Sigma w)_i / sqrt(w' Sigma w)
RC_i  = w_i * MRC_i
```

Check that risk contributions reconcile to total volatility or variance under the chosen convention. Report signed and absolute contributions where short positions or hedges make signs ambiguous. Separate common-factor, specific, currency, financing, and scenario risk.

For benchmark-relative portfolios, compute active risk with `w - b`, but also report total portfolio risk and benchmark exposures. A low tracking error can coexist with large absolute leverage or concentrated tail risk.

## Stress overlays

Use at least three layers:

1. **Historical:** replay comparable shocks with consistent holdings, prices, FX, and liquidity assumptions.
2. **Hypothetical:** shocks to market, sector, factor, volatility, rates, spreads, FX, and correlations.
3. **Implementation:** wider spreads, higher impact, delayed fills, reduced ADV, borrow withdrawal, margin increase, and forced de-risking.

For derivatives, include nonlinear Greeks and revaluation where linear sensitivities are inadequate. For portfolios with options or path-dependent instruments, stress implied volatility, skew, term structure, and gap moves rather than only spot returns.

## Validation and drift

Compare ex-ante forecasts with realized volatility, tracking error, factor exposures, and stress outcomes. Track forecast bias, error by regime, underestimation frequency, and breaches of model confidence bands. Use rolling windows and out-of-sample monitoring; do not recalibrate solely to make a historical chart look better.

Monitor:

- covariance eigenvalues, condition number, factor coverage, and missingness;
- realized versus forecast risk and the decomposition error;
- exposure drift between model, broker, custodian, and accounting systems;
- sudden changes in correlations, betas, volatility, liquidity, or borrow;
- model version, input freshness, and any fallback path used.

Define action thresholds before production. An amber condition should trigger investigation or tighter limits; a red condition should block new risk or invoke a documented kill switch.

