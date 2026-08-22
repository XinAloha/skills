---
name: skill-transaction-cost-calibration
description: Calibrate commissions, bid-ask spread, slippage, and simple market-impact assumptions from executions, quotes, or OHLCV data. Use when an agent needs an auditable transaction-cost model for backtest assumptions, execution review, or capacity analysis.
quantSkills:
  organization: https://github.com/quantskills
  repository: quantskills/skill-transaction-cost-calibration
  repository_url: https://github.com/quantskills/skill-transaction-cost-calibration
  project_type: skill
  collection: execution-analysis
  license: GPL-3.0-only
  category: trader-research
  tags: [transaction-cost, slippage, market-impact, execution]
  platforms: [claude-code, codex, cursor, hermes, openclaw]
  language: zh-en
  status: stable
  validation_level: runnable
  maintainer_type: community
  requires: []
  summary_zh: 从成交、盘口或 OHLCV 数据校准滑点、点差、手续费与参与率冲击成本。
  summary_en: Calibrate execution friction from fills, quotes, and bars with coverage and participation diagnostics.
---

<!-- qsh-form is optional; this declaration enables a structured run form in quantskillhub. -->
```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "例如：校准这批成交的滑点和参与率冲击成本",
    "required": true
  },
  "fields": [
    {"key": "executions_csv", "type": "text", "label": "成交 CSV"},
    {"key": "quotes_csv", "type": "text", "label": "盘口 CSV（可选）"},
    {"key": "bars_csv", "type": "text", "label": "K 线 CSV（可选）"},
    {"key": "commission_bps", "type": "number", "label": "手续费 bps"}
  ],
  "prompt_template": "请处理任务：{{task}}；成交：{{executions_csv}}；盘口：{{quotes_csv}}；K线：{{bars_csv}}；手续费 bps：{{commission_bps}}。附件：{{#attachments}}"
}
```

# Transaction Cost Calibration

Use this skill to estimate realized trading friction without treating one fixed bps value as universal. It uses only information available at or before execution, reports cost distributions, and fits a transparent participation-based impact curve.

## Core Workflow

1. Read [references/input_contract.md](references/input_contract.md) and identify whether quotes, bars, or only executions are available.
2. Parse timestamps with an explicit UTC assumption. Sort each symbol before as-of joining a quote or bar; never use a future reference.
3. Run `scripts/calibrate_costs.py`. Prefer quote mid and spread; use the latest prior bar close only as a documented fallback.
4. Review `execution_costs.csv` for signed slippage, spread, participation, and total cost. Review `summary.json` for coverage and outliers.
5. Use the fitted curve only inside the observed participation range. Report range, sample size, and commission convention with any backtest assumption.

## Command

```bash
python scripts/calibrate_costs.py --executions fills.csv --quotes quotes.csv \
  --bars bars.csv --commission-bps 2.5 --output-dir cost_out
```

Use `--demo --output-dir cost_out` for a deterministic smoke test without network access.

## Output Contract

- `execution_costs.csv`: one row per fill with as-of reference, signed slippage bps, spread bps, participation, commission, and total cost.
- `cost_curve.csv`: binned participation with median and p95 observed cost.
- `summary.json`: sample coverage, cost quantiles, impact coefficients, and warnings.

Keep signed slippage (price improvement is negative) separate from absolute cost. Do not extrapolate beyond observed participation without an explicit sensitivity assumption.

## Boundaries

- Use this skill for execution friction calibration and backtest cost assumptions.
- Do not use it as a replacement for portfolio liquidation stress testing or generic backtest skills.
- Do not infer alpha, trade recommendations, or broker quality from costs alone.
- Follow [references/source_boundary.md](references/source_boundary.md) for permitted sources.
