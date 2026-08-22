---
name: brinson-performance-attribution
description: >
  Brinson-Fachler / BHB sector attribution with interaction, concentration (HHI),
  top contributors, and optional Carino multi-period linking. Use to explain
  active return as allocation vs selection.
quantSkills:
  organization: https://github.com/quantskills
  repository: skill-brinson-performance-attribution
  repository_url: https://github.com/quantskills/skill-brinson-performance-attribution
  project_type: skill
  category: analyst
  tags: [brinson, fachler, carino, attribution, portfolio]
  platforms: [claude-code, codex, cursor, hermes, openclaw]
  language: zh-en
  status: draft
  validation_level: runnable
  maintainer_type: community
  requires: []
  summary_zh: Brinson归因（Fachler/BHB）+ HHI/贡献排序 + Carino多期链接。
  summary_en: Brinson Fachler/BHB attribution with HHI, contributors and Carino linking.
  license: GPL-3.0-only
---

# Brinson Performance Attribution

把超额收益拆成配置 / 选股 / 交互，并支持多期几何链接。

## Core Workflow

1. 校验行业唯一、字段有限值、组合和基准权重和接近 1
2. 按 Fachler 或 BHB 计算配置、选股、交互效应
3. 检查 active return 与效应和的残差
4. 输出 HHI 集中度及绝对贡献最大的行业
5. 多期 API 使用 Carino 方法链接到几何主动收益

## Quick Start

```bash
pip install -r requirements.txt
python examples/run_demo.py
```

## CLI Contract

输入 CSV 必须含 `sector,w_p,w_b,r_p,r_b`，每个行业仅一行：

```bash
python scripts/brinson.py \
  --input attribution.csv --method fachler --out report.json
```

## Output Contract

输出组合/基准/主动收益、三类效应、残差、HHI、行业贡献和质量门禁。多期链接通过
Python API `multiperiod_brinson()` 使用。详见 `references/methodology.md`。

## Boundaries

- 仅供研究和教育，不构成投资建议。

数据来源、假设、参数和风险边界详见 `references/source_boundary.md`。
