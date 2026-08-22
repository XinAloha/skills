# Data Source and Research Boundary

- Inputs are user-provided, aligned asset and market return series.
- The implementation has no built-in market-data vendor, network call, API key, or `panda_data` dependency.
- PandaAI or another lawful source may supply raw prices; users must handle adjustments, calendars, frequency, missing data, and return conversion.
- Demo data is synthetic and deterministic.
- Assumptions: synchronized returns, an appropriate market proxy, and enough observations per rolling window.
- Key parameters: rolling window, confidence level, and Vasicek prior mean/variance.
- Known limitations: a single-factor CAPM is proxy- and regime-sensitive and is not a complete risk model or return forecast.
- Research and education only; no investment advice or return promise.
