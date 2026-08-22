# Signal Stability Audit

> Cross-sectional signal stability audit covering lag autocorrelation, half-life, Jaccard overlap, Kendall tau, quintile migration, and a cost-drag proxy.

## What it provides

This repository contains a runnable QuantSkills skill with a documented input contract, deterministic demo, and research-oriented diagnostics. Read [`SKILL.md`](SKILL.md) for the full workflow, output contract, and limitations.

## Quick start

```bash
pip install -r requirements.txt
python examples/run_demo.py
```

## CLI example

```bash
python scripts/stability_audit.py --signal signal.csv --top-frac 0.1 --cost-bps 15 --rebalance-days 5 --out report.json
```

## Runtime adapters

- Codex: [`agents/codex.md`](agents/codex.md)
- Claude Code: [`agents/claude-code.md`](agents/claude-code.md)
- Cursor: [`agents/cursor-rule.mdc`](agents/cursor-rule.mdc)
- Hermes: [`agents/portable-loader.md`](agents/portable-loader.md)
- OpenClaw: [`agents/openclaw.md`](agents/openclaw.md)

## Data sources and boundaries

- **Required input:** a date-by-asset cross-sectional signal matrix.
- **Data source:** the tool is vendor-neutral and consumes user-provided signals. Raw market or factor inputs may optionally come from the [PandaAI data service](https://www.pandaaiquant.com/data-service/api-docs?id=149) or another lawful source, but signals must be constructed point-in-time without look-ahead information.
- **Assumptions and parameters:** asset columns and date order are consistent; `top_frac`, `cost_bps`, and `rebalance_days` reflect the intended research setup.
- **Limitations and risks:** turnover and cost drag are proxies, not a holdings-level backtest. Stability does not imply efficacy, tradability, or future profit.
- **Maintenance status:** community-maintained research tooling; it is not represented as officially certified, endorsed, or production-ready by QUANTSKILLS.

## Scope and license

Use persistence and turnover diagnostics to assess ranking stability. The outputs are for research and education only, are not investment advice, and do not promise returns. No private data, credentials, or network access are required by the demo.

Licensed under [GPL-3.0-only](LICENSE).

Chinese documentation: [`README.md`](README.md)
