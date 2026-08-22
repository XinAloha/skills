---
name: skill-capital-flow-crowding-monitor
description: >
  A-share capital-flow & crowding monitor across margin financing, northbound
  (HSGT) holdings, and block trades. Use when a user wants to gauge who is
  buying/selling a name or sector, and whether a trade is getting crowded.
  Pulls margin balances, northbound holdings, and block-trade discounts,
  builds a multi-source capital consensus/divergence and crowding score.
license: GPL-3.0-only
category: 工具
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-capital-flow-crowding-monitor
  repository_url: https://github.com/quantskills/skill-capital-flow-crowding-monitor
  project_type: skill
  collection: capital-flow-analytics
  status: community-draft
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "粘贴股票代码或行业/概念（如 600519.SH，或“白酒”“半导体”），说明关注的资金维度与时间窗",
    "required": true
  },
  "fields": [
    {
      "key": "window_days",
      "label": "观察窗口（天）",
      "type": "number",
      "default": "60"
    },
    {
      "key": "dimensions",
      "label": "资金维度",
      "type": "select",
      "default": "all",
      "options": [
        { "value": "all", "label": "全部（两融+北向+大宗）" },
        { "value": "margin", "label": "仅融资融券" },
        { "value": "northbound", "label": "仅北向持股" },
        { "value": "block", "label": "仅大宗交易" }
      ]
    },
    {
      "key": "crowding_lookback",
      "label": "拥挤度分位回溯（天）",
      "type": "number",
      "default": "250",
      "help": "用于把当前资金强度换算成历史分位"
    }
  ],
  "prompt_template": "{{#task}}标的/板块与要求：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}对上述标的做多源资金流与拥挤度监测。{{#window_days}}观察窗口 {{window_days}} 天。{{/window_days}}{{#dimensions}}资金维度：{{dimensions}}。{{/dimensions}}{{#crowding_lookback}}拥挤度按 {{crowding_lookback}} 天历史分位标准化。{{/crowding_lookback}}聚合融资融券余额变化、北向持股变化、大宗交易折溢价与规模，构建资金一致性/背离信号与拥挤度分位，输出中文资金画像与拥挤预警，标注数据降级项。仅研究参考，不构成投资建议。"
}
```

# skill-capital-flow-crowding-monitor

role: skill · output: CapitalFlowReport (JSON + text) · paradigm: multi-source capital flow & crowding scoring

把"谁在买、谁在卖、这笔交易是不是太挤了"变成可量化的资金画像 + 拥挤度分位。组织里两融/北向/大宗资金面 **无专门工具**,现有 crowding-risk / smart-money 只从单一角度沾边。

## 🎯 这个 Skill 解决什么问题

判断一只股票/一个板块的资金面,散落在三类互不相通的数据里:**融资融券**(杠杆资金情绪)、**北向持股**(外资/聪明钱)、**大宗交易**(机构/大股东折价出货或接盘)。组织现有 `crowding-risk-monitor` 偏宏观情绪、`smart-money-profiler` 偏龙虎榜席位,都没把这三源资金**统一成一致性/背离信号 + 拥挤度分位**。

本 Skill 输出三层:

- **资金流强度**:两融余额变化、北向持股变化、大宗成交额,按窗口标准化。
- **一致性 / 背离**:三源同向(共识)还是打架(背离)——共识信号更强,背离提示分歧。
- **拥挤度分位**:当前资金强度在历史 N 天的分位,>90% 分位预警"交易过挤、反转风险"。

## ⚡ 工作流（Agent 按此执行）

1. **解析标的**:个股代码,或行业/概念(经 `get_industry_constituents`/`get_concept_constituents` 展开成成分)。
2. **拉三源**:`scripts/data_source.py` 取 `get_margin`(融资融券余额)、`get_hsgt_hold`(北向持股)、`get_block_trade`(大宗折溢价+规模)。
3. **标准化**:`scripts/flows.py` 各源按窗口 z-score / 变化率标准化到可比尺度。
4. **一致性 + 拥挤**:`scripts/crowding.py` 算三源同向度(共识分)与当前强度的历史分位(拥挤分)。
5. **出报告**:`scripts/capital_report.py` → `CapitalFlowReport`,资金画像 + 共识/背离标签 + 拥挤预警。
6. **解释**:指出资金主力是谁、方向、是否过挤、背离在哪。

```bash
python scripts/capital_report.py --symbols 600519.SH --window 60 --out report.json
python examples/run_demo.py   # 无凭证回退样本
```

## 🗃️ 输入契约

| 输入 | 形态 | 必需 | 说明 |
|------|------|------|------|
| `symbols` | 代码 / 行业名 / 概念名 | 是 | 个股或板块 |
| `window_days` | int | 否 | 默认 60 |
| `dimensions` | all/margin/northbound/block | 否 | 默认 all |
| `crowding_lookback` | int | 否 | 默认 250,拥挤分位回溯 |

输出 `CapitalFlowReport`:`items[] (symbol, margin_flow, northbound_flow, block_flow, consensus, divergence, crowding_pct, signal) / degraded[]`

## 📦 输出契约

产物对象 `CapitalFlowReport`（JSON + 中文文本）：

| 字段 | 说明 |
|------|------|
| `items[]` | 每标的：`symbol, margin_flow, northbound_flow, block_flow, consensus, divergence, crowding_pct, signal` |
| `degraded[]` | 降级源（北向停披露/大宗稀疏等）显式列出 |

文件产物：`--out report.json`、`--md report.md`。三源资金流须各自标注来源接口与数据日期；有效源不足时在 `degraded[]` 声明并降低结论置信度，不用单源冒充共识。

## 🔗 管线定位

```
选股/板块 → [本 Skill：三源资金流+拥挤度] → 择时/加减仓判断
```
与 `crowding-risk-monitor`(宏观情绪)、`smart-money-profiler`(龙虎榜席位)互补:本 Skill 专注**两融+北向+大宗**的标的级资金画像。

## 📦 仓库结构

```
skill-capital-flow-crowding-monitor/
├── SKILL.md / README.md / requirements.txt / .gitignore
├── scripts/ data_source.py · flows.py · crowding.py · capital_report.py · formatters.py
├── references/ methodology.md(三源口径+拥挤分位算法) · data-fields.md
└── examples/ run_demo.py · sample_data/ · sample_report.md
```

## ✅ 质量门槛

产物交付前须满足（不达标则降级并在报告显式声明，不静默通过）：

- **可溯源**：每个关键数字可回溯到具体 Pandadata 接口 + 数据日期；缺失数据进 `degraded[]`，绝不编造或用近似冒充真实值。
- **降级透明**：任一数据源为空/受限时，报告如实标注并降低结论置信度。
- **口径一致**：单位、频率、基准口径在报告中显式声明。
- **仅研究**：产物为研究/教育参考，不构成投资建议，不承诺收益。
- 有效资金源不足时不用单源冒充三源共识；拥挤度分位须≥250天窗口才给统计结论。

## ⚠️ 使用规则

- **接口字段已实测确认(2026-07-27,MCP get_method_doc)**:
  - `get_margin` ✅ 实测字段:`margin_balance`(融资余额)、`short_balance`(融券余额)、`total_balance`(总余额)、`buy_on_margin_value`(融资买入额)、`short_sell_quantity`(融券卖出量)、`margin_type`(cash=融资/stock=融券)。资金强度直接用余额变化。
  - `get_hsgt_hold` ✅ 实测字段:`shares_num`(北向持股数)、`holding_ratio`(持股比例)、`adjusted_holding_ratio`。北向资金流用持股比例/持股数的变化。
  - `get_block_trade` ✅ 实测字段:`price`(成交价)、`volume`、`amount`、`buyer`/`seller`(买卖营业部)。**注意:无现成"折溢价"字段——大宗折溢价须自算(成交价 vs 当日收盘价,需额外取 `get_stock_daily`)**;买卖营业部可判断机构/游资属性。
- 北向持股披露有滞后/口径调整(沪股通/深股通合并),须按披露日对齐。
- 拥挤度分位需足够历史窗口(建议 ≥250 天)才有统计意义。
- 只做研究/资金面参考,不构成投资建议。
