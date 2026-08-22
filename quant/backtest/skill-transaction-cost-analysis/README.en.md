# Transaction Cost Analysis

[Chinese README](README.md) | English

This skill analyzes trade fills or backtest turnover. It reconstructs interval VWAP or
TWAP from minute bars and decomposes implementation shortfall into timing, market
impact, spread, fees, and slippage.

## Quick start

```bash
pip install -r requirements.txt
python examples/run_demo.py
python scripts/tca_report.py --fills fills.csv --benchmark vwap \
  --commission-bps 2.5 --impact-coef 0.1 --out report.json --md report.md
```

`fills.csv` uses `symbol,side,datetime,price,qty`. The offline demo uses bundled sample
bars. The adapter can use `get_stock_min`, `get_stock_daily`, `get_hk_daily`, or
`get_us_daily`; missing benchmark data is recorded as degradation.

## Output

`TCAReport` contains total cost in basis points, a timing/impact/spread/fees/slippage
breakdown, per-side and per-symbol summaries, fill-level attribution, insights, and
degradation notes. Direction conventions and formulas are documented in
`references/methodology.md`.

## Research boundary

Minute bars are proxies for tick and order-book data, so impact and spread estimates are
model-based. Outputs are for research and execution-analysis education only; this
project does not place orders and is not investment advice.

## License

GPL-3.0-only. See [LICENSE](LICENSE).
