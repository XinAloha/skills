# Interpretation Rules

## Hurst / ADF / KPSS

- Hurst above 0.55 plus ADF p-value above 0.05 and KPSS p-value below 0.05 suggests persistent non-stationary trend behavior.
- Hurst below 0.5 plus ADF p-value below 0.05 and KPSS p-value above 0.05 suggests mean-reverting stationary behavior.
- Conflicting ADF/KPSS results require more evidence; do not force a single label.

## Distribution

- KDE and QQ diagnostics describe return-shape evidence, not profitability.
- High skew or QQ deviation indicates non-normality; it does not imply a tradable edge.
- Strategy and factor sections should be phrased as research directions, not order instructions.

## Mean Reversion

- Half-life is meaningful only when the AR(1) lambda is negative.
- Very short half-life with noisy data can be an overfit symptom.

## Cointegration

- Engle-Granger evidence depends on aligned observations and residual stationarity.
- A low residual ADF p-value is necessary evidence, not a complete trading rule.
