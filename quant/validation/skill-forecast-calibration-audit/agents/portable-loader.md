# Portable Runtime Loader

This file is the portable entrypoint for Hermes-compatible and other Markdown-driven runtimes.

## Activation

Load `../SKILL.md` when a user asks to audit binary probability forecasts, reliability, proper scores, calibration coefficients, threshold metrics, or time drift.

## Execution

1. Load `../references/input_contract.md` and verify `date,probability,outcome` plus any requested regime column.
2. Run `../scripts/calibrate_forecasts.py` with chronological time bins and the requested threshold.
3. Inspect `scored_predictions.csv`, `reliability.csv`, `time_metrics.csv`, and `summary.json`.
4. Report sample counts, date coverage, class balance, and warnings; interpret small bins cautiously.

Never randomly shuffle the time series or convert calibration diagnostics into investment advice.
