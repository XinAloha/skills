---
name: skill-transaction-cost-analysis
description: >
  A-share / cross-market transaction cost analysis (TCA). Use when a user has
  trade fills or backtest turnover and asks "how much did execution actually
  cost". Decomposes implementation shortfall into timing, market impact
  (square-root model), spread, commission and slippage, benchmarks fills
  against interval VWAP / TWAP from minute bars, and outputs a Chinese
  attribution report.
license: GPL-3.0-only
category: 工具
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-transaction-cost-analysis
  repository_url: https://github.com/quantskills/skill-transaction-cost-analysis
  project_type: skill
  collection: execution-analytics
  status: community-draft
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "上传成交记录 CSV（symbol, side, datetime, price, qty），或说明回测换手明细；给出决策价/基准",
    "required": true
  },
  "fields": [
    {
      "key": "benchmark",
      "label": "执行基准",
      "type": "select",
      "default": "vwap",
      "options": [
        { "value": "vwap", "label": "区间 VWAP" },
        { "value": "twap", "label": "区间 TWAP" },
        { "value": "arrival", "label": "到达价 (Arrival)" }
      ]
    },
    {
      "key": "commission_bps",
      "label": "佣金（bps）",
      "type": "number",
      "default": "2.5",
      "help": "单边佣金，含规费；A 股卖出另计印花税"
    },
    {
      "key": "impact_coef",
      "label": "冲击系数 k",
      "type": "number",
      "default": "0.1",
      "help": "square-root 冲击模型系数，缺省用默认经验值"
    }
  ],
  "prompt_template": "{{#task}}成交与要求：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}对上述成交做交易成本分析(TCA)。{{#benchmark}}执行基准采用 {{benchmark}}。{{/benchmark}}{{#commission_bps}}佣金按 {{commission_bps}} bps 计。{{/commission_bps}}{{#impact_coef}}冲击模型系数 k={{impact_coef}}。{{/impact_coef}}用分钟线重建区间 VWAP/TWAP，拆解 implementation shortfall = 择时 + 冲击(square-root) + 点差 + 佣金 + 滑点，逐笔与汇总归因，输出中文报告并标注数据降级项。仅研究参考，不构成投资建议。"
}
```

# skill-transaction-cost-analysis

role: skill · output: TCAReport (JSON + text) · paradigm: execution cost attribution

把"这笔/这批成交到底贵在哪"变成可计算、可归因、可对标的报告。这是买方研究里标准、组织里却缺失的**执行成本账本**。

## 🎯 这个 Skill 解决什么问题

回测里 3% 的年化 edge，实盘可能被交易成本吃掉一半。组织有回测、有组合优化、有清算流动性压力测试，却**没有一个把成交成本拆开算清**的工具。本 Skill 回答："相对决策价/VWAP，我多付了多少？其中多少是冲击、多少是择时、多少是费用？"

核心分解（Perold implementation shortfall 框架）：

- **择时成本 (timing)** — 决策价 → 所选执行基准的漂移；arrival 基准下为 0。
- **市场冲击 (impact)** — square-root 模型 `k · σ · sqrt(Q/ADV)`，用分钟线估波动与 ADV。
- **点差成本 (spread)** — 有 bid/ask（港美股日线自带）时直接算，A 股用分钟高低价代理。
- **佣金/税费 (fees)** — 佣金 bps + A 股卖出印花税。
- **滑点 (slippage)** — 实际成交价相对所选 VWAP/TWAP/arrival 基准的残差。

## ⚡ 工作流（Agent 按此执行）

1. **解析成交**：读 fills（symbol/side/datetime/price/qty），标准化。
2. **取分钟行情**：`scripts/data_source.py` 用 `get_stock_min`（1/5/15/60m）或港美股日线（含 `vwap`）重建成交区间的 VWAP/TWAP、波动率、ADV。
3. **分解成本**：`scripts/tca_decompose.py` 逐笔算 timing/impact/spread/fees/slippage（bps）。
4. **汇总归因**：`scripts/tca_report.py` → `TCAReport`（JSON + 中文文本），按 symbol/side/日期聚合，给总成本 bps 与占比瀑布。
5. **解释结论**：指出成本主要来源（冲击 or 择时）、异常大单，给执行改进方向。

```bash
python scripts/tca_report.py --fills fills.csv --benchmark vwap --commission-bps 2.5 --out report.json
python examples/run_demo.py   # 无凭证回退合成分钟线
```

## 🗃️ 输入契约

| 输入 | 形态 | 必需 | 说明 |
|------|------|------|------|
| `fills` | CSV | 是 | symbol, side(buy/sell), datetime, price, qty |
| `benchmark` | vwap/twap/arrival | 否 | 默认 vwap |
| `commission_bps` | float | 否 | 默认 2.5，单边 |
| `impact_coef` | float | 否 | 默认 0.1，square-root k |

输出 `TCAReport`：`total_cost_bps / breakdown{timing,impact,spread,fees,slippage} / by_symbol[] / by_side[] / degraded[]`

## 📦 输出契约

产物对象 `TCAReport`（JSON + 中文文本双形态）：

| 字段 | 说明 |
|------|------|
| `total_cost_bps` | 总交易成本（bps，正=对本方不利） |
| `breakdown{timing,impact,spread,fees,slippage}` | 五项瀑布分解 |
| `by_symbol[] / by_side[]` | 按标的/买卖方向汇总 |
| `degraded[]` | 降级项（数据缺失/近似）显式列出 |

文件产物：`--out report.json`（结构化）、`--md report.md`（中文报告）。每个 bps 数字须可溯源到成交记录与基准口径。

## 🔗 管线定位

```
策略/回测 → 实盘成交 → [本 Skill：成本归因] → 执行优化 / 回测成本校准
```

与 `skill-portfolio-liquidity-stress-test` 共用 square-root 冲击模型：那个测"能不能清得掉"，本 Skill 算"清掉花了多少"。

## 📦 仓库结构

```
skill-transaction-cost-analysis/
├── SKILL.md / README.md / requirements.txt
├── scripts/
│   ├── data_source.py       # 分钟线/日线 VWAP·ADV·σ（无凭证回退合成）
│   ├── tca_decompose.py      # IS 五项分解
│   ├── tca_report.py         # 汇总 → TCAReport（CLI）
│   └── benchmarks.py         # VWAP / TWAP / arrival 计算
├── references/
│   └── methodology.md        # IS 框架 + square-root 冲击 + 文献
└── examples/
    └── run_demo.py
```

## ✅ 质量门槛

产物交付前须满足（不达标则降级并在报告显式声明，不静默通过）：

- **可溯源**：每个关键数字可回溯到具体 Pandadata 接口 + 数据日期；缺失数据进 `degraded[]`，绝不编造或用近似冒充真实值。
- **降级透明**：任一数据源为空/受限时，报告如实标注并降低结论置信度。
- **口径一致**：单位、频率、基准口径在报告中显式声明。
- **仅研究**：产物为研究/教育参考，不构成投资建议，不承诺收益。
- 五项分解之和须等于 total_cost_bps（对账闭合）；冲击/点差为分钟级近似须声明。

## ⚠️ 使用规则

- Pandadata 无逐笔 tick/盘口，冲击与点差为**分钟级近似**，报告须声明该局限。
- A 股卖出印花税单独计入 fees；港美股用日线自带 `vwap`/`bid`/`ask` 提升精度。
- 决策价(arrival)需用户提供或用下单前一分钟收盘价代理。
- 只做研究/执行分析参考，不构成投资建议。
