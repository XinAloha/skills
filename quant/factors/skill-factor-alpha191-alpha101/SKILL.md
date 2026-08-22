---
name: factor-alpha191-alpha101
description: "Compute Alpha101 and Alpha191 factor-library values based on JoinQuant formulas from long-form OHLCV CSV market data. Use when an agent needs to calculate selected or full Alpha101/Alpha191 factor columns, export wide factor CSVs, and list skipped factors without running LLMs or factor evaluation."
quantSkills:
  organization: https://github.com/quantskills
  repository: quantskills/skill-factor-alpha191-alpha101
  repository_url: https://github.com/quantskills/skill-factor-alpha191-alpha101
  project_type: skill
  collection: factor-library
  license: GPL-3.0-only
  category: factor
  tags: [factor-library, alpha101, alpha191, alpha-factor]
  platforms: [codex]
  language: zh-en
  status: stable
  validation_level: verified
  maintainer_type: community
  requires: []
  summary_zh: 参考 JoinQuant 公式计算 Alpha101 和 Alpha191 因子值，支持全量和指定因子运行。
  summary_en: Compute Alpha101 and Alpha191 factor values based on JoinQuant formulas with full or selected factor runs.
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "说明 OHLCV 数据文件、计算范围及输出要求；请上传或指明输入数据",
    "required": true
  },
  "fields": [
    {
      "key": "alpha_sets",
      "label": "因子库",
      "type": "select",
      "default": "both",
      "options": [
        { "value": "both", "label": "Alpha101 + Alpha191" },
        { "value": "alpha101", "label": "仅 Alpha101" },
        { "value": "alpha191", "label": "仅 Alpha191" }
      ]
    },
    {
      "key": "alpha_names",
      "label": "指定因子",
      "type": "textarea",
      "placeholder": "留空计算全部；可填 alpha101:alpha_001、alpha191:alpha_018 等"
    },
    {
      "key": "exclude_alpha_names",
      "label": "排除因子",
      "type": "textarea",
      "placeholder": "可选，填写不需要计算的因子名"
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}依据输入契约从长表 OHLCV 数据确定性计算因子值。因子库范围：{{alpha_sets}}（both 表示 Alpha101+Alpha191 全部）。{{#alpha_names}}仅计算指定因子：{{alpha_names}}；{{/alpha_names}}{{#exclude_alpha_names}}排除：{{exclude_alpha_names}}；{{/exclude_alpha_names}}导出宽表因子 CSV、运行配置、计算摘要和跳过因子清单，不执行 IC、回测或投资判断，输出中文报告。"
}
```

# Factor Alpha191 Alpha101

Use this skill to compute deterministic Alpha101 and Alpha191 factor-library values from long-form OHLCV market data.

## Core Workflow

1. Read `references/input_schema.md` before preparing the input JSON.
2. Choose `alpha_sets`: `alpha101`, `alpha191`, or both.
3. Use `alpha_names` and `exclude_alpha_names` to select factors. Qualified names such as `alpha101:alpha_001` and `alpha191:alpha_018` are supported.
4. Run the unified CLI:

```bash
python scripts/compute_alpha_factors.py --input examples/compute_input.json
```

5. Read `references/output_contract.md` before consuming generated artifacts.

## Output Contract

The skill writes wide CSV factor values and JSON metadata under the configured output directory:

- `alpha101_values.csv` when Alpha101 factors are computed
- `alpha191_values.csv` when Alpha191 factors are computed
- `alpha_compute_summary.json`
- `skipped_factors.json`
- `run_config.json`

## Boundaries

This is a factor-library computation skill. It does not compute IC, ICIR, portfolio returns, backtests, or trading recommendations.

## References

- Use `references/input_schema.md` for input fields.
- Use `references/output_contract.md` for artifact names and result fields.
- Use `references/source_boundary.md` for source and data boundaries.
- Use `references/validation_notes.md` for implementation assumptions and limitations.
