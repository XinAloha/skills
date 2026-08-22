---
name: build-b10-factor-evaluation
description: Use this skill to evaluate Alpha factors with IC/RankIC, ICIR, stratified backtests, turnover, decay curves, stock-pool filters, statistical diagnostics, and standalone HTML reports.
tags: [quant, skill, build, factor-evaluation]
license: GPL-3.0-only
maintainer: quantskills
runtime_adapters: [codex, claude-code, cursor, hermes, openclaw]
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-build-b10-factor-evaluation
  repository_url: https://github.com/quantskills/skill-build-b10-factor-evaluation
  project_type: skill
  collection: build
---

# B10 Factor Evaluation Skill

## Purpose

This repository packages the QuantSkills B10 factor evaluation BUILD as a reusable skill. It evaluates caller-provided Alpha factor panels and writes research and production artifacts without depending on a specific Alpha repository.

Use it when a user needs to:

- evaluate a factor's cross-sectional predictive power;
- compute IC, RankIC, ICIR, HAC t-statistics, decay curves, turnover, and stratified returns;
- compare quintile and decile grouping results;
- generate a standalone HTML factor-evaluation report;
- write production Parquet summaries for downstream agents.

## Repository Layout

- `开发产物/SKILL.md`: full development skill manual and Python API reference.
- `开发产物/skill.json`: machine-readable metadata.
- `开发产物/scripts/`: implementation, CLI runner, demo, visual report renderer, and tests.
- `开发产物/references/`: API guide, changelog, and sample panels.
- `生产产物/SKILL.md`: production artifact reader contract.
- `生产产物/数据库.parquet`: production-format example/output database.
- `README.md` and `README.en.md`: Chinese and English project introductions.

## Inputs

The main input is a factor panel with these required fields:

| Field | Meaning |
|---|---|
| `trade_date` | signal date |
| `ts_code` | asset code |
| `factor_value` | factor value |
| `forward_return` | forward return aligned by the caller |

The implementation also accepts documented aliases such as `date`, `asset`, `factor`, and `return`. Multi-horizon forward-return columns may be supplied for decay analysis.

## Usage

Run commands from `开发产物/` unless the caller has installed the scripts as a package.

```bash
python scripts/demo.py
python scripts/test.py
python scripts/daily_runner.py --input factor_panel.csv --output reports/ --production ../生产产物/
```

Python entrypoints:

```python
from scripts.build import run, write_report, write_production

result = run(input_data, config={"group_mode": "quintile"})
write_report(input_data, "reports/factor_report.html", config={"target_id": "my_factor"})
write_production(input_data, "../生产产物/数据库.parquet", config={"target_id": "my_factor"})
```

## Runtime Adapter Notes

- Codex and Claude Code can use this root `SKILL.md` directly, then open `开发产物/SKILL.md` for the complete implementation contract.
- Cursor should load `agents/cursor-rule.mdc`.
- Hermes and other portable agents should load `agents/portable-loader.md`.
- OpenClaw should load `agents/openai.yaml` or `agents/portable-loader.md`.

## Limitations

- This skill does not fetch market data or call PandaData directly. All raw market, industry, style, and forward-return data must be prepared before entering B10.
- It is an evaluation tool, not investment advice. Reports are research diagnostics and may not be presented as return promises or trading recommendations.
- Neutralization requires caller-supplied industry/style exposure panels.
- Production readers should read existing Parquet outputs and must not trigger recomputation during ordinary queries.

## Compliance Metadata

- Repository type: QuantSkills skill repository.
- Upstream organization: QuantSkills, https://github.com/quantskills.
- Repository: https://github.com/quantskills/skill-build-b10-factor-evaluation.
- License: GPL-3.0-only.
- Maintainer: QuantSkills.
- Sensitive data: do not commit credentials, tokens, proprietary data, user directories, or local absolute paths.
