# Workflow

1. Clean the input series: numeric, sorted, no missing values in the diagnostic window.
2. Pick the highest-level API:
   - user-facing price report: `generate_time_series_report`
   - user-facing spread report: `generate_spread_report` using `analyze_spread`
   - user-facing pair cointegration report: `generate_pair_cointegration_report` using `analyze_pair_cointegration`
   - one price series diagnostics: `analyze_price_series`
   - spread or residual: `analyze_spread`
   - two related series: `analyze_pair_cointegration`
3. For user-facing price reports, include original-series evidence and Log diff 1/5/10 diagnostics.
4. For user-facing spread reports, include half-life plus Hurst/ADF/KPSS evidence.
5. For user-facing pair reports, include Engle-Granger alpha/beta and residual stationarity evidence.
6. For user-facing output, write `report.to_markdown()` or return the saved Markdown file.
7. Explain stationarity, memory, trend, and distribution shape in plain language.
8. Phrase strategy and factor output as research directions.
9. Add caveats for short samples, conflicting tests, non-positive prices, or unstable residuals.
