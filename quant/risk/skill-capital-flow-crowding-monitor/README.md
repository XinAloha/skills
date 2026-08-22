# skill-capital-flow-crowding-monitor

[English](README.en.md)

A股跨市场资金面 / 拥挤度监测 —— 输入个股代码或行业/概念，聚合 **融资融券（杠杆情绪）+ 北向持股（外资/聪明钱）+ 大宗交易（机构/大股东）** 三源资金流，构建 **一致性/背离信号** 与 **拥挤度历史分位**，回答"谁在买、谁在卖、这笔交易是不是太挤了"。

> QuantSkills 组织技能 · 数据源 Pandadata · 组织首个两融+北向+大宗标的级资金画像技能 · 仅供研究参考，不构成投资建议。

## 快速开始

```bash
pip install -r requirements.txt   # 纯标准库，无强制依赖（标准化/分位用 statistics 与手写实现）

# 离线演示（无需凭证，内置样本；含"三源共识买入"与"高拥挤预警"对比案例）
python examples/run_demo.py

# 真实扫描（需 panda_data SDK，见 skill-pandadata-api）
python scripts/capital_report.py --symbols 600519.SH,000858.SZ \
    --window 60 --crowding-lookback 250 \
    --out report.json --md report.md
```

## 三源资金流口径

`scripts/flows.py` 把三类互不相通的数据标准化到可比尺度（近段窗口内的 z-score / 变化率）：

1. **融资融券**（`get_margin`）：用 `margin_balance`（融资余额）窗口变化衡量杠杆资金净流入/流出方向与强度。强度分基于**整段变化率序列的 z-score**；报告同时呈现**区间累计变化**（首→末）与**末日环比**两个维度，避免只看单日环比误读整体趋势（如某标的区间累计 -4.9% 但末日环比 +0.3%）。
2. **北向持股**（`get_hsgt_hold`）：用 `holding_ratio`（持股比例）与 `shares_num`（持股数）窗口变化衡量外资加/减仓。
3. **大宗交易**（`get_block_trade`）：用成交额规模 + 自算折溢价（成交价 vs 当日收盘价）+ 买卖营业部（是否"机构专用"）判断机构接盘/出货方向与强度。

> ⚠️ 大宗交易接口**无现成折溢价字段**——本技能用 `get_stock_daily` 的 `close` 与大宗 `price` 自算折溢价：`折溢价% = (price - close) / close × 100`（正=溢价买入=承接意愿强，负=折价出货）。

## 三层输出

- **资金流强度**：三源各自标准化后的强度分（正=净流入/加仓，负=净流出/减仓）。
- **一致性 / 背离**：三源方向同向度。三源全同向 → **共识**（信号更强）；方向打架 → **背离**（分歧，信号弱化）。
- **拥挤度分位**：把当前综合资金强度放进历史 N 天分布求分位。`>90%` 分位 → **高拥挤预警**（交易过挤、反转风险）；`<10%` 分位 → 冷门/被抛弃。

## 拥挤/共识判定逻辑（核心）

- **共识买入信号**：三源方向一致向上 + 拥挤分位处中位 → 资金合力做多且未过热，最优形态。
- **高拥挤预警**：拥挤分位 > 90% → 无论共识与否都提示"过挤"，共识+过挤=拥挤交易反转风险最高。
- **背离信号**：三源方向不一致 → 标注哪一源与其余打架（如北向减仓但两融加杠杆，多为散户接盘外资出货）。

## 接口字段（2026-07-27 实测确认）

| 接口 | 关键字段 |
|---|---|
| `get_margin` | margin_balance（融资余额）, short_balance（融券余额）, total_balance, buy_on_margin_value（融资买入额）, margin_type（cash/stock） |
| `get_hsgt_hold` | shares_num（持股数）, holding_ratio（持股比例%）, adjusted_holding_ratio |
| `get_block_trade` | price（成交价）, volume, amount, buyer/seller（营业部，判机构/游资）；**无折溢价字段，须自算** |
| `get_stock_daily` | close（当日收盘价，用于大宗折溢价分母） |
| `get_industry_constituents` / `get_concept_constituents` | 行业/概念展开成分股 |

## 目录

```
scripts/     data_source.py · flows.py · crowding.py · capital_report.py · formatters.py
references/  methodology.md · data-fields.md
examples/    run_demo.py · sample_data/ · sample_report.md
```

## 免责

三源资金披露有滞后（尤其北向口径调整、大宗 T+N 披露）；折溢价为自算估值。拥挤度分位需足够历史窗口（建议 ≥250 天）才有统计意义。数据非实时。仅供研究参考，不构成投资建议。

## ⚠️ 真实数据可得性边界（2026-07-27 端到端实测）

真实场景下三源可得性差异很大，本技能对缺失源自动降级并如实标注：

- **融资融券 `get_margin`**：✅ 稳定可得（逐日 margin_balance/short_balance/total_balance）。
- **北向持股 `get_hsgt_hold`**：❌ 实测返回空——**2024 年 8 月起北向个股持股明细已停止披露**，该源在近期数据下基本不可用。
- **大宗交易 `get_block_trade`**：⚠️ 实测多只大蓝筹（600519/000858）一整月返回空，覆盖稀疏。

→ 因此真实场景中"三源合成"常退化为**主要依赖融资融券单源**，北向/大宗降级。报告会显示"有效源 N"与降级说明，不会用缺失源硬凑信号。这是数据现实，非技能缺陷。

## 许可证

GPL-3.0-only，详见 [LICENSE](LICENSE)。
