---
name: paper-replication
description: Use when systematically reproducing quantitative finance papers with
  framework-neutral scripts, third-party market data, standalone research backtests,
  charts, metrics, and packaged outputs.
version: 2.0.2
author: PandaAI
license: GPL-3.0-only
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-paper-replication
  repository_url: https://github.com/quantskills/skill-paper-replication
  project_type: skill
  collection: paper-replication
  creator: abgyjaguo
  maintainer: abgyjaguo
  tags:
  - quant
  - research
  - paper
  - replication
  - backtest
  compatible_agents:
  - codex
  - hermes
  - claude-code
  - aider
  - cursor
  - generic-cli-agent
quantSkills:
  project_type: skill
  category: replication
  tags:
  - paper-replication
  - quant-finance
  - backtest
  - research
  - workflow
  platforms:
  - claude-code
  - codex
  - hermes
  - openclaw
  - cursor
  status: stable
  validation_level: runnable
  maintainer_type: official
  summary_zh: 把一篇量化金融论文（arXiv 或本地 PDF），变成一套可运行、可审计的复现实验：检索 → 提取 → 回测 → 图表 → 指标对照，全程框架无关。
  summary_en: Framework-neutral quantitative paper replication skill for research
    scripts, backtests, charts, and auditable outputs.
  license: GPL-3.0
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "请提供论文标题、arXiv ID、本地 PDF 或复现目标，并说明期望对照的结果",
    "required": true
  },
  "fields": [
    {
      "key": "strategy",
      "label": "复现策略",
      "type": "select",
      "default": "custom",
      "options": [
        { "value": "tsmom", "label": "时间序列动量" },
        { "value": "csmom", "label": "截面动量" },
        { "value": "risk_parity", "label": "风险平价" },
        { "value": "trend_vol", "label": "趋势与波动率" },
        { "value": "custom", "label": "按论文自定义" }
      ]
    },
    {
      "key": "universe",
      "label": "资产范围",
      "type": "text",
      "placeholder": "例如：rb,if,au；也可在任务或材料中说明"
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}系统复现量化金融论文。{{#strategy}}若论文与内置模板匹配，可采用 {{strategy}} 复现路径；{{/strategy}}复现路径以论文本身为准。{{#universe}}资产范围为 {{universe}}。{{/universe}}提取公式、样本、信号时点、组合构建、成本与基准口径，先给出实现计划，再完成无前视偏差的独立回测、图表、指标对照和可审计产物，并如实解释与论文结果的差异，输出中文报告。"
}
```

# Paper Replication

Use this skill to reproduce quantitative finance papers in any agent framework that can read
this directory and run local Python scripts.

The primary pipeline is standalone: paper search/download, PDF extraction, formula reconstruction,
Pandas-based research backtest, charts, metrics, and deliverable packaging.

## Framework-Neutral Usage

Agents should resolve paths relative to this `SKILL.md` file:

```text
paper-replication/
  SKILL.md
  README.md
  requirements.txt
  scripts/
  templates/
  references/
```

Do not assume any agent-specific install folder. When invoking scripts, use the actual
local path to this skill directory.

## Dependencies

Install dependencies in the active Python environment:

```bash
python -m pip install -r /path/to/paper-replication/requirements.txt
```

## Output Location

Generated paper artifacts must go under:

```text
/home/coder/project/replication/paper-replication/{paper_id}/
```

Never write generated paper artifacts back into the skill directory.

## Chart Image Text Rules

- Text rendered inside generated chart image files must be English ASCII only. This includes PNG/SVG titles, subtitles, axis labels, legends, colorbar labels, annotation text, heatmap labels, in-image table headers, and watermarks.
- Keep any Chinese explanations outside the image in Markdown/HTML notes. The chart pixels themselves must stay font-compatible across environments.
- When using Matplotlib, Seaborn, Plotly static export, or another image renderer, use broadly available Latin fonts such as `DejaVu Sans` or `Arial`. Do not set CJK chart fonts such as `SimHei`, `SimSun`, `Microsoft YaHei`, `Noto Sans CJK`, or `Source Han Sans`.
- If the source paper or factor name is Chinese, draw an ASCII-safe display label in the chart and keep the original Chinese name in the surrounding text.

## Quick Start

```bash
cd /home/coder/project/replication/paper-replication

python /path/to/paper-replication/scripts/run_research.py \
  --pipeline \
  --paper-id 2201.06635 \
  --symbols rb,if,au \
  --strategy tsmom
```

## Workflow

1. Search or select a paper.
   Use `scripts/search_arxiv.py`, or accept a user-provided arXiv ID/PDF.

2. Extract the paper.
   Use `scripts/extract_paper.py` with PyMuPDF. Focus on formulas, asset universe,
   data period, benchmark metrics, transaction cost assumptions, and signal timing.

3. Define the implementation plan.
   State the data source, signal logic, portfolio construction, normalization,
   costs, and validation metrics before coding.

4. Run standalone reproduction.
   Use `scripts/reproduce_paper.py`. The default Chinese futures data path uses akshare;
   CSV data is acceptable when the paper requires a custom dataset.

5. Validate results.
   Compare the reproduction metrics against the paper and explain gaps using data
   coverage, signal delay, universe differences, costs, or normalization choices.

6. Package deliverables.
   Save extracted notes, metrics JSON, equity/weights CSVs, and charts in the paper
   output directory.

## Data Source Rules

- Keep third-party data sources for market data access.
- Default Chinese futures data source: akshare `futures_zh_daily_sina`.
- International data may use yfinance when appropriate.
- User-provided CSV is allowed when the paper or user supplies a dataset.
- Always record the data source, date range, and latest available date.
- Always guard against look-ahead bias with shifted weights/signals.

## Standalone Strategies

Supported by `scripts/reproduce_paper.py`:

| Strategy | Signal | Portfolio |
| --- | --- | --- |
| `tsmom` | sign of lookback return | inverse volatility |
| `csmom` | cross-sectional return rank | signal weighted |
| `risk_parity` | long-only risk allocation | covariance based |
| `trend_vol` | short lookback trend | inverse volatility |

## Quality Checks

- Verify `df["date"].max()` or equivalent latest timestamp is plausible.
- Confirm no future bars enter signal calculation.
- Check output files exist and are non-empty.
- Report replication gaps honestly instead of forcing a match.
