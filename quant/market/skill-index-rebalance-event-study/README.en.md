# Index Rebalance Event Study

Runs descriptive index-addition, deletion, and weight-change event studies around declared event anchors.

## Quick start

```bash
python scripts/study_index_rebalance.py --demo
python scripts/study_index_rebalance.py --input your_data.csv --start 0 --end 1 --out report.json
```

## CLI parameters

| Argument | Requirement | Description |
| --- | --- | --- |
| `--demo` | Choose exactly one source | Use built-in rows; mutually exclusive with `--input` |
| `--input <csv>` | Choose exactly one source | Read a UTF-8 CSV |
| `--start <int>` | Optional | First relative day, default `0` |
| `--end <int>` | Optional | Last relative day, default `1`; must not precede start |
| `--out <json>` | Optional | Write JSON to a file; otherwise print to standard output |

Supplying both data sources, or neither source, exits with argparse status 2.

Required fields are `event_id`, `symbol`, `action`, `announcement_date`, `effective_date`, `relative_day`, `return`, `benchmark_return`, and `volume_ratio`. Dates use `YYYY-MM-DD`; relative days are integers. Add `relative_to=announcement` or `relative_to=effective` to calculate each event-anchor panel separately; optional finite `weight_before` and `weight_after` fields support weight-change summaries.

Event metadata and non-empty weight fields must remain consistent across anchors. Action summaries are nested by anchor so announcement and effective-date CARs are never averaged together.

Use [`skill-pandadata-api`](https://github.com/quantskills/skill-pandadata-api) for market and weight data. Official index notices remain the authoritative source for announcement timestamps.

## Validation and limits

See [validation/README.md](validation/README.md). The script reports descriptive arithmetic CAR and does not implement statistical inference or overlapping-event controls.

GPL-3.0-only.
