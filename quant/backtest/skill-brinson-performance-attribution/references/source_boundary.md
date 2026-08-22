# Data Source and Research Boundary

- Inputs are user-provided sector weights and returns for a portfolio and benchmark.
- The implementation has no built-in market-data vendor, network call, API key, or `panda_data` dependency.
- PandaAI or another lawful source may optionally supply benchmark constituents, classifications, and prices; portfolio holdings remain user-supplied and all data must be aggregated to the required sector schema.
- Demo data is synthetic and deterministic.
- Assumptions: consistent sector mapping, currency convention, period, and weights near one.
- Key parameters: Fachler versus BHB method and, for multiple periods, period ordering and Carino linking inputs.
- Known limitations: historical decomposition only; cash, fees, derivatives, classification changes, and intra-period trades may create residuals.
- Research and education only; no investment advice or return promise.
