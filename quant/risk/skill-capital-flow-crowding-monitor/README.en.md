# Capital Flow and Crowding Monitor

[Chinese README](README.md) | English

This skill combines margin financing, northbound holdings, and block-trade data for
A-share names or sectors. It normalizes the sources, reports consensus or divergence,
and estimates a historical crowding percentile.

## Quick start

```bash
pip install -r requirements.txt
python examples/run_demo.py
python scripts/capital_report.py --symbols 600519.SH,000858.SZ \
  --window 60 --crowding-lookback 250 --out report.json --md report.md
```

The demo uses bundled sample data. A production run may use the Pandadata SDK through
the data-source adapter. Missing or sparse sources are reported as degradation rather
than filled with invented values.

## Data and output

The monitor uses `get_margin`, `get_hsgt_hold`, `get_block_trade`, and `get_stock_daily`.
It can also expand industry or concept lists. The report contains per-source changes,
standardized scores, consensus/divergence signals, crowding percentiles, source dates,
and a `degraded` section.

## Research boundary

Disclosure timing and coverage vary by source, and the data is not real time. Outputs
are for research and education only; this project does not place orders and is not
investment advice. Validate every conclusion against the cited data and the relevant
market rules.

## License

GPL-3.0-only. See [LICENSE](LICENSE).
