---
name: signal-stability-audit
description: >
  Audit cross-sectional signal persistence via lag autocorr, half-life, top/bottom
  Jaccard turnover, Kendall tau, quintile migration, and cost-drag proxy. Use to
  choose rebalance horizon and reject untradeably noisy rankings.
quantSkills:
  organization: https://github.com/quantskills
  repository: skill-signal-stability-audit
  repository_url: https://github.com/quantskills/skill-signal-stability-audit
  project_type: skill
  category: tooling
  tags: [stability, turnover, half-life, jaccard, quant-research]
  platforms: [claude-code, codex, cursor, hermes, openclaw]
  language: zh-en
  status: draft
  validation_level: runnable
  maintainer_type: community
  requires: []
  summary_zh: 信号稳定性审计：半衰期、换手代理、五分位迁移、成本拖累与再平衡建议。
  summary_en: Signal stability audit with half-life, turnover proxies, migration and cost drag.
  license: GPL-3.0-only
---

# Signal Stability Audit

回答：排名粘不粘、Top 篮换不换、按这换手交易成本吃不吃得消。

## Core Workflow

1. 计算 lag1..K 秩自相关并拟合半衰期
2. Top/Bottom Jaccard → 单向换手代理
3. Kendall + 符号翻转率
4. 五分位迁移矩阵
5. 年化成本拖累与再平衡建议 → STABLE/MIXED/UNSTABLE

## Quick Start

```bash
pip install -r requirements.txt
python examples/run_demo.py
```

## CLI Contract

`signal.csv` 首列为日期，其他列为资产信号。成本按实际再平衡间隔年化：

```bash
python scripts/stability_audit.py \
  --signal signal.csv --top-frac 0.1 \
  --cost-bps 15 --rebalance-days 5 \
  --out report.json
```

## Output Contract

- lag 秩自相关、Kendall tau-b 与半衰期
- Top/Bottom Jaccard、五分位迁移矩阵和换手代理
- 与 `rebalance_days` 一致的年化成本拖累
- STABLE / MIXED / UNSTABLE 门禁结论

详见 `references/methodology.md` 与 `references/source_boundary.md`。仅供研究教育。

## Boundaries

- 仅供研究和教育，不构成投资建议。
