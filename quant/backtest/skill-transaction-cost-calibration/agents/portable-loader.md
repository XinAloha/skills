# Portable Runtime Loader

This file is the portable entrypoint for Hermes-compatible and other Markdown-driven runtimes.

## Activation

Load `../SKILL.md` when a user asks to calibrate execution friction, slippage, spread, commissions, or participation-based market impact.

## Execution

1. Load `../references/input_contract.md` and validate fills, quotes, bars, and UTC timestamps.
2. Run `../scripts/calibrate_costs.py` with executions and any available quotes or bars.
3. Inspect `execution_costs.csv`, `cost_curve.csv`, and `summary.json`.
4. Report reference coverage, outliers, commission convention, and the observed participation range.

Never use post-fill information, silently invent a missing reference, or turn cost diagnostics into trading advice.
