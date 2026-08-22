# Data Source and Research Boundary

- Inputs are user-provided, aligned signal and forward-return matrices.
- The implementation has no built-in market-data vendor, network call, API key, or `panda_data` dependency.
- PandaAI or another lawful source may supply raw market data; users must derive horizon-consistent forward returns and independently construct point-in-time signals.
- Demo data is synthetic and deterministic.
- Assumptions: point-in-time signal availability, correct return horizon, and identical date/asset alignment.
- Key parameters: training/test size, step, label horizon, embargo, and quantile fraction.
- Known limitations: no transaction costs, liquidity, borrow, execution, trading limits, or market impact.
- Research and education only; no investment advice or return promise.
