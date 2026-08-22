# Calendar Anomaly Scanner

> Calendar-effect scanner for weekday, month, month-edge, and turn-of-month patterns using HAC statistics, bootstrap p-values, BH-FDR, and half-sample checks.

## What it provides

This repository contains a runnable QuantSkills skill with a documented input contract, deterministic demo, and research-oriented diagnostics. Read [`SKILL.md`](SKILL.md) for the full workflow, output contract, and limitations.

## Quick start

```bash
pip install -r requirements.txt
python examples/run_demo.py
```

## CLI example

```bash
python scripts/calendar_scan.py --input returns.csv --date-col date --return-col return --nw-lag 5 --alpha 0.05 --out report.json
```

## Runtime adapters

- Codex: [`agents/codex.md`](agents/codex.md)
- Claude Code: [`agents/claude-code.md`](agents/claude-code.md)
- Cursor: [`agents/cursor-rule.mdc`](agents/cursor-rule.mdc)
- Hermes: [`agents/portable-loader.md`](agents/portable-loader.md)
- OpenClaw: [`agents/openclaw.md`](agents/openclaw.md)

## Data sources and boundaries

- **Required input:** a time series containing a date column and a same-frequency return column.
- **Data source:** the tool is vendor-neutral. Users may obtain prices from the [PandaAI data service](https://www.pandaaiquant.com/data-service/api-docs?id=149) or another lawful source, then handle adjustments, trading calendars, and time zones before converting prices to returns.
- **Assumptions and parameters:** dates are unique and correctly ordered, returns have a consistent frequency, and `nw_lag`, significance level, and bootstrap settings fit the sample.
- **Limitations and risks:** multiple-testing and half-sample checks do not eliminate data mining, regime change, or transaction costs. Statistical significance does not imply tradability or future profit.
- **Maintenance status:** community-maintained research tooling; it is not represented as officially certified, endorsed, or production-ready by QUANTSKILLS.

## Scope and license

Use multiple-testing-aware diagnostics to avoid over-claiming calendar effects. The outputs are for research and education only, are not investment advice, and do not promise returns. No private data, credentials, or network access are required by the demo.

Licensed under [GPL-3.0-only](LICENSE).

Chinese documentation: [`README.md`](README.md)
