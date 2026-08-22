# API Reference

## Main APIs

- `generate_time_series_report(price, series_name="series", title=None, windows=None, lags=None, output_dir=None, include_plots=True, language="zh")`
- `generate_spread_report(spread, series_name="spread", title=None, windows=None, output_dir=None, include_plots=True, language="zh")`
- `generate_pair_cointegration_report(y, x, pair_name="pair", title=None, significance=0.05, output_dir=None, language="zh")`
- `interpret_time_series_analysis(analysis, language="zh")`
- `analyze_price_series(price, windows=None, lags=None, log_diff_lags=None, plot=False, output_dir=None)`
- `analyze_spread(spread, windows=None, plot=False, output_dir=None)`
- `analyze_pair_cointegration(y, x, significance=0.05)`

## Diagnostics APIs

- `distribution_diagnostics(price, lags=None, plot=False, output_dir=None)`
- `stationarity_diagnostics(series, windows=None)`
- `log_diff_diagnostics(price, lags=None, windows=None)`
- `mean_reversion_diagnostics(spread)`
- `cointegration_diagnostics(y, x, significance=0.05)`

## Low-Level Helpers

- `kde_analysis`, `qq_analysis`, `ts_groupby_period`
- `TimeSeriesAnalyzer`, `analysis_results_to_df`
- `half_life_of_mean_reversion`, `engle_granger_cointegration`
