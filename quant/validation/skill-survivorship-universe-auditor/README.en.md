# Survivorship Universe Auditor

Audits lifecycle records and reconstructs point-in-time universes from supplied symbol-date snapshots.

## Quick start

```bash
python scripts/audit_universe.py --demo
python scripts/audit_universe.py --input your_data.csv --out report.json
```

## CLI parameters

| Argument | Requirement | Description |
| --- | --- | --- |
| `--demo` | Choose exactly one source | Use built-in rows; mutually exclusive with `--input` |
| `--input <csv>` | Choose exactly one source | Read a UTF-8 CSV |
| `--out <json>` | Optional | Write JSON to a file; otherwise print to standard output |

Supplying both data sources, or neither source, exits with argparse status 2.

The CSV must contain `symbol`, `date`, `eligible`, `listed_at`, `delisted_at`, `return`, and `delisting_return`. Dates use `YYYY-MM-DD`; `eligible` is strictly `0` or `1`. `return` is the ordinary simple return without delisting treatment, while `delisting_return` is the authoritative same-period total return including the delisting effect. Add `stable_id` when ticker changes must be linked.

Use [`skill-pandadata-api`](https://github.com/quantskills/skill-pandadata-api) for calendars, security lists, status changes, and prices. Standardized delisting returns may require a separate authoritative source.

## Validation and limits

See [validation/README.md](validation/README.md). The script reconstructs only dates and securities present in the input; it cannot prove completeness without a full historical security master.

GPL-3.0-only.
