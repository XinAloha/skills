# Statistical Validation for Quant Research

Use this reference before interpreting backtest performance or model metrics as evidence.

## Contents

- [Hypothesis and baselines](#hypothesis-and-baselines)
- [Splits and leakage](#splits-and-leakage)
- [Dependence and uncertainty](#dependence-and-uncertainty)
- [Multiple testing](#multiple-testing)
- [Robustness](#robustness)
- [Decision language](#decision-language)

## Hypothesis and baselines

State the economic mechanism, expected sign, holding period, eligible universe, and conditions under which the effect should fail. Define the primary metric before comparing variants. Use an uncomplicated baseline and an implementability baseline that includes costs and constraints.

Separate:

- **discovery**: generate ideas and diagnostics;
- **selection**: choose a specification using training or validation data;
- **confirmation**: evaluate once on untouched data;
- **monitoring**: assess live or paper behavior against the predeclared expectation.

Do not use the confirmation set to pick features, thresholds, windows, universes, or report-friendly subperiods.

## Splits and leakage

Use chronological splits for forecasting. For cross-sectional data, preserve date boundaries and ensure that every feature is available before the target period. When labels overlap, remove observations whose information or label windows overlap the validation interval and add an embargo after the split.

Use walk-forward evaluation when the strategy would be periodically refit:

```text
fit [t0, t1] -> validate [t1, t2] -> advance -> fit [t0, t2] -> validate [t2, t3]
```

Fit scalers, imputers, encoders, feature selectors, and model hyperparameters inside each training window. Test the pipeline with a future sentinel row and a shuffled-label control. A suspiciously strong result should trigger an audit of every join and shift before more modeling.

## Dependence and uncertainty

Financial returns are usually autocorrelated, heteroskedastic, heavy-tailed, and cross-sectionally dependent. Do not treat every bar, asset, or overlapping label as an independent observation.

Choose uncertainty methods that match the data-generating structure:

- use block or stationary bootstrap for serial dependence;
- resample dates or clusters when cross-sectional dependence dominates;
- report confidence intervals for returns, Sharpe, drawdown, hit rate, or IC when decision-relevant;
- show the number of independent bets or effective sample size;
- use robust or heteroskedasticity-and-autocorrelation-consistent errors for regression claims when appropriate;
- distinguish statistical significance from economic significance after costs and constraints.

For Sharpe ratios, state the return frequency, annualization factor, arithmetic or geometric convention, risk-free treatment, and whether serial-correlation adjustment was used. Prefer a distribution or interval over a single point estimate.

## Multiple testing

Record the search surface: number of factors, parameter combinations, universes, horizons, models, feature-selection attempts, and discarded trials. A best-of-many backtest is not equivalent to a single pre-specified test.

Consider false-discovery control, family-wise or false-discovery adjustments, White's reality check, Hansen's SPA, probability of backtest overfitting, and deflated Sharpe ratio when the search process and sample size justify them. Explain assumptions and do not present a correction as a guarantee.

## Robustness

Evaluate changes that should not destroy a genuine effect:

- reasonable parameter perturbations and nearby holding periods;
- alternative but defensible data cleaning and corporate-action choices;
- delayed execution, wider spreads, higher impact, borrow limits, and lower capacity;
- different rebalance dates, sectors, countries, liquidity buckets, and universe definitions;
- subperiods, crises, volatility regimes, and rising or falling markets;
- signal ablations, neutralized variants, placebo features, and shuffled labels;
- turnover, concentration, leverage, and exposure controls.

Use a compact sensitivity grid or distribution, not only the best configuration. Investigate discontinuities and parameter cliffs. A strategy that survives only one exact parameter value is not robust evidence.

## Decision language

Use calibrated labels:

- **reject**: no useful signal or implementation fails basic controls;
- **exploratory**: result is descriptive, in-sample, data-limited, or otherwise not confirmed;
- **promising but unvalidated**: economic rationale and some out-of-sample evidence, with material unresolved risks;
- **research-ready**: reproducible, cost-aware, out-of-sample, and robust enough for paper trading review;
- **production-candidate**: additionally passes operational, capacity, monitoring, governance, and approval requirements.

Never state that a backtest proves future returns. State what was tested, what was not tested, and what evidence would change the decision.

