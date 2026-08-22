# Data Source and Research Boundary

- Input is a user-provided dated return series.
- The implementation has no built-in market-data vendor, network call, API key, or `panda_data` dependency.
- PandaAI or another lawful source may supply raw prices; users must handle adjustment conventions, calendars, time zones, missing data, and return conversion.
- Demo data is synthetic and deterministic.
- Assumptions: unique ordered dates, consistent return frequency, and an appropriate sample period.
- Key parameters: Newey-West lag, significance level, bootstrap count/block size, and calendar bucket definitions.
- Known limitations: data mining, structural change, execution costs, and calendar-definition choices remain material risks.
- Research and education only; no investment advice or return promise.
