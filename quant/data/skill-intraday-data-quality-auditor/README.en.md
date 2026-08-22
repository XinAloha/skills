# Intraday Data Quality Auditor

Community-maintained QuantSkills package for deterministic checks on normalized intraday OHLCV bars.

## Quick start

```bash
python scripts/audit_bars.py --demo
python scripts/audit_bars.py --input your_data.csv --out report.json
python scripts/audit_bars.py --input your_data.csv --expected-seconds 300 --out report.json
```

The CSV must contain `symbol`, `trading_date`, `session`, `timestamp`, `open`, `high`, `low`, `close`, and `volume`. Within each `symbol + trading_date + session` group, ISO-8601 timestamps must consistently be timezone-aware or timezone-naive; mixed awareness produces an `insufficient-evidence` report. The report flags timestamp order, duplicates, gaps, invalid OHLC relationships, non-positive prices, negative volume, and trading-date mismatches. Legitimate prior-calendar-date futures night sessions must use an explicit `night`, `night_session`, `overnight`, or `night_*` label.

## CLI parameters

- `--demo`: use the built-in anomalous sample instead of `--input`.
- `--input <csv>`: input path; required unless `--demo` is used.
- `--out <json>`: optional output path; omit it to print JSON to stdout.
- `--expected-seconds <int>`: expected bar interval, default `60`, must be positive. A gap above `1.5` times this value is flagged as `missing_bar_gap`.

Exactly one of `--demo` and `--input` is required. Supplying both or neither is a CLI usage error that prints argparse help and exits with code `2`. A non-positive `--expected-seconds` or insufficient input evidence produces an `insufficient-evidence` JSON report.

For PandaData acquisition, use the sibling [`skill-pandadata-api`](https://github.com/quantskills/skill-pandadata-api) and normalize its output before running this offline script. Minute bars are not tick trades or Level-2 order-book data.

## Validation and limits

See [validation/README.md](validation/README.md). A gap is evidence to investigate, not proof of a vendor error or exchange halt. This research tool does not modify source data, trade, or provide investment advice.

GPL-3.0-only.
