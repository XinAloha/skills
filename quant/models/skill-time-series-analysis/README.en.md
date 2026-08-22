# skill-time-series-analysis

[简体中文](README.md) | English

This is a time-series analysis tool for AI agents and quantitative researchers.
It provides Python APIs for price-series diagnostics, spread analysis,
Engle-Granger cointegration, and mean-reversion half-life, and it can generate
Markdown reports that explain the conclusion first and then show the evidence.

## Workflow

```mermaid
flowchart TD
    A["User asks for time-series analysis"] --> B["Agent identifies the input type"]
    B --> C{"Input type"}
    C --> D["Single price series"]
    C --> E["Spread or price difference"]
    C --> F["Two related series"]
    D --> G["generate_time_series_report"]
    G --> H["Analyze original series and Log diff 1/5/10"]
    E --> I["generate_spread_report"]
    I --> J["analyze_spread: half-life Hurst ADF KPSS"]
    F --> K["generate_pair_cointegration_report"]
    K --> L["analyze_pair_cointegration: Engle-Granger and residual stationarity"]
    H --> M["Explain stationarity memory trend distribution"]
    J --> M
    L --> M
    M --> N["Suggest strategy and factor research directions"]
    N --> O["Output Markdown and PNG charts"]
    O --> P["User reads conclusions then evidence"]
```

## Example Visualization And Summary

The example below is generated from
`reports/panda_data_futures/multi_symbol_futures_timeseries.md`. It uses real
PandaData futures daily bars for `IF_DOMINANT.CFE`, `CU_DOMINANT.SHF`, and
`I_DOMINANT.DCE`. Each report analyzes both the original price series and
`Log diff 1/5/10`.

| symbol | n_obs | trend_type | tail | skew |
| --- | ---: | --- | --- | --- |
| `IF_DOMINANT.CFE` | 242 | strong trend, non-stationary (trend strategies) | fat_tail | right_skew |
| `CU_DOMINANT.SHF` | 242 | weak trend or counter-trend | fat_tail | symmetric |
| `I_DOMINANT.DCE` | 242 | weak trend or counter-trend | fat_tail | right_skew |

Example conclusion for `IF_DOMINANT.CFE`:

- Stationarity: ADF does not reject a unit root and KPSS rejects stationarity, so the latest window looks trend non-stationary.
- Memory: Hurst is elevated, indicating persistence and directional continuation.
- Trend: the latest window is classified as strong trend and trend non-stationary from the Hurst, ADF, and KPSS combination.
- Log diff: the report checks 1-, 5-, and 10-period log-diff series for stationarity, memory, KDE, and QQ distribution shape.
- Research directions: trend following, time-series momentum, breakout confirmation, trend-state filters, and tail-risk filters.

![IF_DOMINANT.CFE KDE](reports/panda_data_futures/IF_DOMINANT_CFE/distribution_kde_dist.png)

![IF_DOMINANT.CFE QQ](reports/panda_data_futures/IF_DOMINANT_CFE/distribution_qq_plot.png)

Spread and pair-cointegration reports are also included as inspectable Markdown
examples:

- Spread half-life report: `reports/time_series_examples/demo_spread/demo_spread_spread_report.md`
- Pair cointegration report: `reports/time_series_examples/demo_pair/demo_pair_cointegration_report.md`

## Quick Start

```bash
uv run python -m pytest tests/ -q
uv run ruff check .
```

```python
from skill_time_series_analysis import generate_time_series_report

report = generate_time_series_report(
    price,
    series_name="demo",
    windows=[60, 120, 180],
    lags=[1, 5, 20],
    output_dir="reports/demo",
)
print(report.to_markdown())
```

```python
from skill_time_series_analysis import generate_pair_cointegration_report, generate_spread_report

spread_report = generate_spread_report(spread, series_name="demo_spread", output_dir="reports/demo_spread")
pair_report = generate_pair_cointegration_report(y, x, pair_name="demo_pair", output_dir="reports/demo_pair")
```

## Real-Data Example Report

The repository keeps one PandaData multi-symbol futures analysis report:

- Report entry: `reports/panda_data_futures/multi_symbol_futures_timeseries.md`
- Generating test: `tests/test_panda_data_futures_report.py`
- Data source: PandaData `get_market_data(type="future")`
- Symbols: `IF_DOMINANT.CFE`, `CU_DOMINANT.SHF`, `I_DOMINANT.DCE`

Regenerate the report with PandaData credentials:

```bash
PANDA_DATA_ENV_FILE=/path/to/.env \
  uv run python -m pytest tests/test_panda_data_futures_report.py -q
```

The `.env` file should define `PANDA_DATA_USERNAME` and `PANDA_DATA_PASSWORD`.
The integration test skips when credentials or the SDK are unavailable; the
runtime Python package itself does not depend on PandaData.

## Public API Pyramid

Use top-level APIs first:

- `generate_time_series_report`
- `generate_spread_report`
- `generate_pair_cointegration_report`
- `interpret_time_series_analysis`
- `analyze_price_series`
- `analyze_spread`
- `analyze_pair_cointegration`

Use diagnostics APIs when composing custom workflows:

- `distribution_diagnostics`
- `stationarity_diagnostics`
- `log_diff_diagnostics`
- `mean_reversion_diagnostics`
- `cointegration_diagnostics`

Low-level helpers remain available for advanced use:

- `kde_analysis`, `qq_analysis`, `ts_groupby_period`
- `TimeSeriesAnalyzer`, `analysis_results_to_df`
- `half_life_of_mean_reversion`, `engle_granger_cointegration`

## Boundary

The runtime package does not include strategy generation, ML, triple-barrier
labels, backtesting, a PandaData client, or market-data management.
`tests/test_panda_data_futures_report.py` is an optional real-data integration
example that demonstrates the API on external futures bars. Outputs are research
diagnostics, not investment advice or trading signals.
