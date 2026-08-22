# Quant Research

This skill turns quantitative research questions into falsifiable hypotheses, reproducible experiments, and bounded research reports. It covers data quality, factor and signal design, backtesting, statistical validation, robustness, risk analysis, and attribution.

## When to Use

Use it for OHLCV, fundamental, or alternative-data checks; feature and factor design; backtest construction; leakage audits; out-of-sample validation; robustness analysis; and research conclusions.

Use `quant-portfolio-risk` for portfolio construction, risk budgets, and portfolio constraints. Use `quant-execution-microstructure` for order logic, fill simulation, routing, and execution-quality analysis.

## Contents

- `SKILL.md`: authoritative workflow, controls, result contract, and reference routing.
- `README.md`: Chinese-first project documentation.
- `references/`: data contracts, statistical validation, risk, and reporting guidance.
- `scripts/`: validation utilities for quantitative time-series data.
- `agents/`: Codex, Cursor, Hermes, and OpenClaw runtime adapters.
- `CLAUDE.md`: Claude Code runtime adapter.

## Operating Defaults

- Enforce point-in-time information flow and explicit signal-to-trade timing.
- Compare proposed signals with simple baselines and preserve an untouched validation or test period.
- Include spread, slippage, impact, financing, borrow, FX, latency, and turnover costs when relevant.
- Default to research, simulation, and paper-trading analysis; do not place live orders without explicit authorization.
- This project is not investment advice, does not promise returns, and is not an official QUANTSKILLS endorsement.

## License and Provenance

Licensed under GPL-3.0-only. Upstream organization: QuantSkills. Repository: `skill-quant-research`. Final listing, recommendation, and official recognition remain subject to maintainer review.
