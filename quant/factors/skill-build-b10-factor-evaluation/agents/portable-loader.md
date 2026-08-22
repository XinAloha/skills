# Portable Loader: B10 Factor Evaluation

This adapter lets Hermes, OpenClaw, and other agents load the QuantSkills B10 factor evaluation skill.

## Load Order

1. Read `SKILL.md` at the repository root.
2. Read `开发产物/SKILL.md` for the complete development/runtime contract.
3. Read `生产产物/SKILL.md` only when the task is to inspect existing production Parquet results.

## When To Use

Use this skill for Alpha factor evaluation tasks:

- IC and RankIC analysis;
- ICIR and HAC t-statistics;
- quintile/decile stratified backtests;
- turnover and RankIC decay diagnostics;
- stock-pool-filtered evaluation;
- HTML report generation;
- production Parquet writing or reading.

## Standard Commands

Run from `开发产物/`:

```bash
python scripts/demo.py
python scripts/test.py
python scripts/daily_runner.py --input factor_panel.csv --output reports/ --production ../生产产物/
```

## Safety And Scope

- B10 consumes prepared factor panels. It does not pull raw market data.
- Do not treat research diagnostics as investment advice.
- Do not include credentials, tokens, local absolute paths, private data, or cache files in commits.
- Preserve GPL-3.0-only licensing and QuantSkills attribution.
