# Corporate Action Adjustment Auditor

Checks cash-dividend and split consistency across raw and adjusted prices before equity research or backtesting.

## Quick start

```bash
python scripts/audit_adjustments.py --demo
python scripts/audit_adjustments.py --input your_data.csv --out report.json
```

## CLI parameters

| Argument | Requirement | Description |
| --- | --- | --- |
| `--demo` | Choose exactly one source | Use built-in rows; mutually exclusive with `--input` |
| `--input <csv>` | Choose exactly one source | Read a UTF-8 CSV whose `date` values use `YYYY-MM-DD` |
| `--return-tolerance <float>` | Optional | Absolute return-difference tolerance; defaults to `0.02` and must be finite and non-negative |
| `--jump-threshold <float>` | Optional | Unexplained raw-price jump threshold; defaults to `0.40` and must be finite and positive |
| `--out <json>` | Optional | Write JSON to a file; otherwise print it to standard output |

Supplying both data sources, or neither source, exits with argparse status 2.

The CSV must contain `symbol`, `date`, `close`, `adj_close`, `split_factor`, and `cash_dividend`. A symbol must be non-empty, contain no surrounding whitespace, and have at least two distinct dates. `split_factor` is new shares per old share on the current row (`1` when absent); `cash_dividend` is cash per old share on the current row (`0` when absent). Both prices must be positive and use the same currency and unit.

For PandaData acquisition, use [`skill-pandadata-api`](https://github.com/quantskills/skill-pandadata-api). Rights issues, spin-offs, mergers, symbol changes, and share-count adjustments need additional event evidence and are not covered by the executable checker.

## Validation and limits

See [validation/README.md](validation/README.md). Confirm the vendor's split-factor direction before interpreting results.

GPL-3.0-only.
