# Rolling Beta Exposure

> Rolling CAPM exposure diagnostics covering alpha/beta, robust confidence intervals, up/down beta asymmetry, residual volatility, and Vasicek shrinkage.

## What it provides

This repository contains a runnable QuantSkills skill with a documented input contract, deterministic demo, and research-oriented diagnostics. Read [`SKILL.md`](SKILL.md) for the full workflow, output contract, and limitations.

## Quick start

```bash
pip install -r requirements.txt
python examples/run_demo.py
```

## CLI example

```bash
python scripts/rolling_beta.py --asset asset_returns.csv --market market_returns.csv --window 60 --out report.json
```

## Runtime adapters

- Codex: [`agents/codex.md`](agents/codex.md)
- Claude Code: [`agents/claude-code.md`](agents/claude-code.md)
- Cursor: [`agents/cursor-rule.mdc`](agents/cursor-rule.mdc)
- Hermes: [`agents/portable-loader.md`](agents/portable-loader.md)
- OpenClaw: [`agents/openclaw.md`](agents/openclaw.md)

## Data sources and boundaries

- **Required inputs:** asset and market return series with the same frequency and ordering.
- **Data source:** the tool is vendor-neutral. Users may obtain asset and benchmark prices from the [PandaAI data service](https://www.pandaaiquant.com/data-service/api-docs?id=149) or another lawful source, then handle adjustments, calendars, and frequency before converting prices to returns.
- **Assumptions and parameters:** asset and market returns are strictly aligned; each rolling window has enough observations; the market proxy, `window`, and prior settings fit the research purpose.
- **Limitations and risks:** single-factor CAPM beta is sensitive to proxy choice, window length, and regime change. Beta is not a return forecast and is not a complete risk model.
- **Maintenance status:** community-maintained research tooling; it is not represented as officially certified, endorsed, or production-ready by QUANTSKILLS.

## Scope and license

Use rolling CAPM diagnostics to monitor an asset's market exposure and stability. The outputs are for research and education only, are not investment advice, and do not promise returns. No private data, credentials, or network access are required by the demo.

Licensed under [GPL-3.0-only](LICENSE).

Chinese documentation: [`README.md`](README.md)
