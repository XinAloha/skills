---
name: walk-forward-validator
description: >
  Purged/embargoed walk-forward validation for cross-sectional signals with dual IC,
  ICIR, Q5-Q1 spread, bootstrap CI, degradation diagnostics, and a multi-gate
  PASS/WEAK_PASS/FAIL scorecard. Use before trusting a factor's full-sample IC.
quantSkills:
  organization: https://github.com/quantskills
  repository: skill-walk-forward-validator
  repository_url: https://github.com/quantskills/skill-walk-forward-validator
  project_type: skill
  category: tooling
  tags: [walk-forward, purged-cv, icir, validation, quant-research]
  platforms: [claude-code, codex, cursor, hermes, openclaw]
  language: zh-en
  status: draft
  validation_level: runnable
  maintainer_type: community
  summary_zh: 按标签周期清洗并带 embargo 的样本外验证：双 IC、分层收益、区块 Bootstrap 与多门禁结论。
  summary_en: Horizon-aware purged walk-forward validation with dual IC, spreads, block bootstrap CI and gates.
  license: GPL-3.0-only
---

# Walk-Forward Validator

把“全样本 IC 好看”升级为可审计的 **时间外推稳定性协议**。

## Core Workflow

1. 校验 `signal[T×N]` 与 `forward[T×N]` 对齐
2. 根据 `label_horizon` 清除标签覆盖测试期的训练行，并插入 embargo
3. 每折计算 Rank/Pearson IC、ICIR、多空 Sharpe、Q5−Q1
4. 汇总 bootstrap CI + 退化率 + scorecard
5. 输出 PASS / WEAK_PASS / FAIL 与折表

## Output Contract

- 文本诊断报告（含 gates）
- JSON（`--out`）
- 详见 `references/methodology.md`

## Quick Start

```bash
pip install -r requirements.txt
python examples/run_demo.py
```

## CLI Contract

输入是两个同形状 CSV：首列为日期索引，其余列为资产；索引和资产列必须完全一致。

```bash
python scripts/walk_forward.py \
  --signal signal.csv --forward forward.csv \
  --train-size 120 --test-size 40 --step 40 \
  --label-horizon 5 --embargo 5 --top-frac 0.2 \
  --out report.json
```

`label_horizon` 必须与 forward return 覆盖的期数一致。输出 JSON 包含折级指标、日级 OOS IC
区块 Bootstrap 置信区间、purged 行数、门禁和结论。

## Boundaries

- 调用方仍须保证 signal 在当时可获得，不能把未来字段预先放进 signal。
- 本工具不是交易回测，不模拟费用、涨跌停、融券与市场冲击。
- 仅供研究和教育，不构成投资建议。

数据来源、假设、参数和风险边界详见 `references/source_boundary.md`。
