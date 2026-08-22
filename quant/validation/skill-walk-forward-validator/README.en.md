# Walk-Forward Validator

> Purged and embargoed out-of-sample signal validation with dual IC, ICIR, quantile spread, bootstrap confidence intervals, and multi-gate conclusions.

## What it provides

This repository contains a runnable QuantSkills skill with a documented input contract, deterministic demo, and research-oriented diagnostics. Read [`SKILL.md`](SKILL.md) for the full workflow, output contract, and limitations.

## Quick start

```bash
pip install -r requirements.txt
python examples/run_demo.py
```

## CLI example

```bash
python scripts/walk_forward.py --signal signal.csv --forward forward.csv --train-size 120 --test-size 40 --step 40 --label-horizon 5 --embargo 5 --top-frac 0.2 --out report.json
```

## Runtime adapters

- Codex: [`agents/codex.md`](agents/codex.md)
- Claude Code: [`agents/claude-code.md`](agents/claude-code.md)
- Cursor: [`agents/cursor-rule.mdc`](agents/cursor-rule.mdc)
- Hermes: [`agents/portable-loader.md`](agents/portable-loader.md)
- OpenClaw: [`agents/openclaw.md`](agents/openclaw.md)

## Data sources and boundaries

- **Required inputs:** date-by-asset signal and forward-return matrices with identical indexes and columns.
- **Data source:** the tool is vendor-neutral and consumes user-provided files. Market data may come from the [PandaAI data service](https://www.pandaaiquant.com/data-service/api-docs?id=149) or another lawful source, but prices must first be converted to forward returns matching `label_horizon`; signal values still come from the user's research process.
- **Assumptions and parameters:** signals must have been available at the observation time; `label_horizon`, `embargo`, training windows, and test windows must match the research design.
- **Limitations and risks:** this is a statistical out-of-sample validator, not a trading simulator. It does not model costs, liquidity, trading limits, borrow constraints, or market impact. Passing gates does not imply future efficacy or tradability.
- **Maintenance status:** community-maintained research tooling; it is not represented as officially certified, endorsed, or production-ready by QUANTSKILLS.

## Scope and license

Use time-aware validation before relying on a full-sample factor IC. The outputs are for research and education only, are not investment advice, and do not promise returns. No private data, credentials, or network access are required by the demo.

Licensed under [GPL-3.0-only](LICENSE).

Chinese documentation: [`README.md`](README.md)
