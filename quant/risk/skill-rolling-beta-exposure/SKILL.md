---
name: rolling-beta-exposure
description: >
  Rolling CAPM exposure diagnostics with alpha/beta/SE/CI, R2, residual vol,
  up/down beta asymmetry, and Vasicek shrinkage. Use when an agent needs risk
  monitoring or exposure regime labels for an asset versus the market.
quantSkills:
  organization: https://github.com/quantskills
  repository: skill-rolling-beta-exposure
  repository_url: https://github.com/quantskills/skill-rolling-beta-exposure
  project_type: skill
  category: monitor
  tags: [beta, capm, up-down-beta, shrinkage, risk]
  platforms: [claude-code, codex, cursor, hermes, openclaw]
  language: zh-en
  status: draft
  validation_level: runnable
  maintainer_type: community
  requires: []
  summary_zh: 滚动CAPM暴露：α/β/标准误/置信区间、涨跌beta、Vasicek收缩与残差波动。
  summary_en: Rolling CAPM beta with SE/CI, up/down beta, Vasicek shrink and residual vol.
  license: GPL-3.0-only
---

# Rolling Beta Exposure

轻量风险暴露诊断（单因子市场模型），不是完整 Barra。

## Core Workflow

1. 在每个滚动窗口估计带截距 CAPM
2. 用 HC1 异方差稳健标准误计算 beta 置信区间
3. 在同一个最新窗口估计上涨/下跌 beta
4. 用 Vasicek 方法向 beta=1 的先验收缩
5. 输出暴露状态、路径稳定性和质量门禁

## Quick Start

```bash
pip install -r requirements.txt
python examples/run_demo.py
```

## CLI Contract

资产和市场 CSV 的最后一列应为同频、同顺序的收益率：

```bash
python scripts/rolling_beta.py \
  --asset asset_returns.csv --market market_returns.csv \
  --window 60 --out report.json
```

## Output Contract

输出 alpha、beta、HC1 SE/CI、R²、残差波动、同窗 up/down beta、Vasicek beta 和门禁。
详见 `references/methodology.md`。仅供研究教育，不构成投资建议。

数据来源、假设、参数和风险边界详见 `references/source_boundary.md`。
