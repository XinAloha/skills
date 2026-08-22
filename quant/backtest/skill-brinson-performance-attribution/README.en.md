# Brinson Performance Attribution

> Brinson-Fachler / BHB portfolio attribution decomposing allocation, selection, and interaction effects, with HHI, contributor ranking, and optional Carino linking.

## What it provides

This repository contains a runnable QuantSkills skill with a documented input contract, deterministic demo, and research-oriented diagnostics. Read [`SKILL.md`](SKILL.md) for the full workflow, output contract, and limitations.

## Quick start

```bash
pip install -r requirements.txt
python examples/run_demo.py
```

## CLI example

```bash
python scripts/brinson.py --input attribution.csv --method fachler --out report.json
```

## Runtime adapters

- Codex: [`agents/codex.md`](agents/codex.md)
- Claude Code: [`agents/claude-code.md`](agents/claude-code.md)
- Cursor: [`agents/cursor-rule.mdc`](agents/cursor-rule.mdc)
- Hermes: [`agents/portable-loader.md`](agents/portable-loader.md)
- OpenClaw: [`agents/openclaw.md`](agents/openclaw.md)

## Data sources and boundaries

- **Required inputs:** sector-level portfolio weights, benchmark weights, portfolio returns, and benchmark returns.
- **Data source:** the tool is vendor-neutral. Portfolio holdings and weights come from the user's own records. Benchmark constituents, classifications, or market data may optionally come from the [PandaAI data service](https://www.pandaaiquant.com/data-service/api-docs?id=149) or another lawful source, but users must aggregate and map them to the required sector-level fields.
- **Assumptions and parameters:** portfolio and benchmark use consistent sector classifications, currency conventions, and periods; weights sum approximately to one; `method` explicitly selects Fachler or BHB.
- **Limitations and risks:** attribution explains historical returns and is not predictive. Classification mapping, cash, fees, derivatives, and intra-period trading may create residuals. Results do not imply future returns.
- **Maintenance status:** community-maintained research tooling; it is not represented as officially certified, endorsed, or production-ready by QUANTSKILLS.

## Scope and license

Use attribution diagnostics to explain active return components. The outputs are for research and education only, are not investment advice, and do not promise returns. No private data, credentials, or network access are required by the demo.

Licensed under [GPL-3.0-only](LICENSE).

Chinese documentation: [`README.md`](README.md)
