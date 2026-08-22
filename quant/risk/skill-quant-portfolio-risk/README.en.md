# Quant Portfolio Risk

This skill provides an auditable workflow for translating forecasts or signals into portfolio decisions under explicit mandates, risk budgets, constraints, liquidity limits, transaction costs, stress scenarios, and governance controls.

## When to Use

Use it for portfolio construction, risk budgeting, risk parity, volatility targeting, benchmark-relative optimization, factor and sector exposure control, turnover-aware rebalancing, capacity analysis, pre-trade checks, limit monitoring, and post-trade reconciliation.

Use `quant-research` for signal discovery, feature engineering, backtest design, and statistical validation. Use `quant-execution-microstructure` for order scheduling, fill modeling, routing, and execution-layer transaction-cost analysis.

## Contents

- `SKILL.md`: authoritative workflow, controls, result contract, and reference routing.
- `README.md`: Chinese-first project documentation.
- `references/`: portfolio construction, risk-model, governance, and monitoring guidance.
- `scripts/`: validation utilities for portfolio weights and constraints.
- `agents/`: Codex, Cursor, Hermes, and OpenClaw runtime adapters.
- `CLAUDE.md`: Claude Code runtime adapter.

## Operating Defaults

- Start with the mandate and risk budget, not with an optimizer default.
- Keep target weights, executable orders, filled positions, and accounting positions separate.
- Treat hard limits as testable invariants and fail closed on missing or stale risk inputs.
- Include turnover, spread, impact, financing, borrow, liquidity, and stress costs when relevant.
- Default to analysis, simulation, and paper trading; do not alter broker or account state without explicit authorization.
- This project is not investment advice, does not promise returns, and is not an official QUANTSKILLS endorsement.

## License and Provenance

Licensed under GPL-3.0-only. Upstream organization: QuantSkills. Repository: `skill-quant-portfolio-risk`. Final listing, recommendation, and official recognition remain subject to maintainer review.
