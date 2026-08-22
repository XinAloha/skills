---
name: calendar-anomaly-scanner
description: >
  Scan weekday/month/month-edge/turn-of-month effects with Newey-West HAC t-stats,
  bootstrap p-values, Benjamini-Hochberg FDR, and half-sample robustness. Use to
  avoid over-claiming calendar anomalies from raw t-stats alone.
quantSkills:
  organization: https://github.com/quantskills
  repository: skill-calendar-anomaly-scanner
  repository_url: https://github.com/quantskills/skill-calendar-anomaly-scanner
  project_type: skill
  category: analyst
  tags: [calendar, anomaly, newey-west, fdr, seasonality]
  platforms: [claude-code, codex, cursor, hermes, openclaw]
  language: zh-en
  status: draft
  validation_level: runnable
  maintainer_type: community
  requires: []
  summary_zh: 日历异象扫描：HAC t、Bootstrap、BH-FDR、半样本稳健与TOM窗口。
  summary_en: Calendar anomaly scanner with HAC t, bootstrap, BH-FDR and half-sample checks.
  license: GPL-3.0-only
---

# Calendar Anomaly Scanner

不做“发现一个 |t|>2 就宣称异象”，而是走多重检验与稳健性梯子。

## Core Workflow

1. 对日期排序并拒绝重复日期
2. 构造星期、月份、月初月末和 turn-of-month 分组
3. 对每个 bucket 检验“bucket 均值 − 其他日期均值”
4. 同一差异同时报告 Newey-West HAC 与区块 Bootstrap
5. 仅用 HAC p 值做统一 BH-FDR，并检查时间半样本方向

## Quick Start

```bash
pip install -r requirements.txt
python examples/run_demo.py
```

## CLI Contract

```bash
python scripts/calendar_scan.py \
  --input returns.csv --date-col date --return-col return \
  --nw-lag 5 --alpha 0.05 --out report.json
```

## Output Contract

输出每个分组的均值差、HAC t/p、独立 Bootstrap p、BH q、半样本方向和稳健性结论。
详见 `references/methodology.md`。多重检验校正不代表扣除交易成本后可获利。

## Boundaries

- 仅供研究和教育，不构成投资建议。

数据来源、假设、参数和风险边界详见 `references/source_boundary.md`。
