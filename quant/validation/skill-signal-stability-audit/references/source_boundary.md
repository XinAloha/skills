# Data Source and Research Boundary

- Input is a user-provided date-by-asset signal matrix.
- The implementation has no built-in market-data vendor, network call, API key, or `panda_data` dependency.
- PandaAI or another lawful source may optionally provide raw market/factor inputs; point-in-time signal construction remains the user's responsibility.
- Demo data is synthetic and deterministic.
- Assumptions: no look-ahead data, consistent assets and dates, and meaningful cross-sectional coverage.
- Key parameters: lag range, top fraction, cost basis points, and rebalance interval.
- Known limitations: turnover and annual cost drag are proxies, not execution-aware portfolio simulation.
- Research and education only; no investment advice or return promise.
