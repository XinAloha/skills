---
name: quant-factor-directional-alpha
description: Use when an agent needs a verified library of directional OHLCV alpha
  factor Skills for trend, breakout, reversal, channel-position, or price-direction
  research across A-share and US equity samples.
license: GPL-3.0-only
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-quant-factor-directional-alpha
  repository_url: https://github.com/quantskills/skill-quant-factor-directional-alpha
  project_type: skill
  collection: quant-factor-directional-alpha
  creator: abgyjaguo
  maintainer: abgyjaguo
quantSkills:
  project_type: skill
  category: factor
  tags:
  - alpha-factor
  - directional
  - ohlcv
  - trend
  - breakout
  platforms:
  - claude-code
  - codex
  - hermes
  - openclaw
  - cursor
  status: stable
  validation_level: verified
  maintainer_type: official
  summary_zh: 方向类因子库：296 个独立 OHLCV 因子 Skill，真实行情验证 296/296 全部通过。
  summary_en: Directional OHLCV alpha factor library with 296 trend, breakout, reversal,
    and channel-position factor Skills validated on real market data.
  license: GPL-3.0
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "补充希望研究的趋势、突破、反转或通道位置逻辑，以及样本期和验证要求"
  },
  "fields": [
    {
      "key": "factor",
      "label": "因子名/主题线索 (可选)",
      "type": "text",
      "placeholder": "例如：趋势突破类、20日通道位置",
      "help": "运行时经本库 factor_index.json 定位具体因子"
    },
    {
      "key": "expr",
      "label": "自定义因子表达式",
      "type": "textarea",
      "placeholder": "如：-1 * correlation(rank(open), rank(volume), 10)"
    },
    {
      "key": "universe",
      "label": "股票池",
      "type": "select",
      "default": "000300.SH",
      "options": [
        { "value": "000300.SH", "label": "沪深300" },
        { "value": "000905.SH", "label": "中证500" },
        { "value": "399006.SZ", "label": "创业板指" },
        { "value": "000852.SH", "label": "中证1000" }
      ]
    },
    {
      "key": "horizon",
      "label": "预测周期",
      "type": "select",
      "default": "5",
      "options": [
        { "value": "1", "label": "未来1日" },
        { "value": "5", "label": "未来5日" },
        { "value": "10", "label": "未来10日" }
      ]
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}请从方向性 OHLCV Alpha 因子库中选择、检查或应用因子。{{#factor}}因子名/主题线索：{{factor}}。{{/factor}}{{#expr}}自定义表达式优先：{{expr}}。{{/expr}}在股票池 {{universe}} 和预测周期 {{horizon}} 日下复核其趋势、突破、反转或通道位置逻辑，并在当前样本与执行假设下重新验证，输出中文报告。"
}
```

# Quant Factor Directional Alpha

Use this skill when an agent needs to select, inspect, or apply directional OHLCV alpha factor Skills from this repository.

## Workflow

1. Read [README.md](README.md) for the repository-level inventory, validation scope, and market sample.
2. Use `factor_index.json` to locate the relevant factor family or individual factor directory.
3. Open the selected factor folder under the factors directory and follow its local instructions before writing or running code.
4. Treat validation metrics as historical research evidence, not investment advice. Re-run validation when the universe, time range, data vendor, or execution assumptions change.

## Scope

This repository focuses on price direction, trend continuation, breakout, reversal, and channel-position signals built from OHLCV data.
## Agent Compatibility

- Claude Code, Codex, Hermes, and OpenClaw can load this root folder as a collection skill, then drill into actors/*/SKILL.md.
- Cursor should use gents/cursor-rule.mdc and keep the full repository under .cursor/skills/quant-factor-directional-alpha.
- Agents without native skill discovery can paste gents/portable-loader.md.
