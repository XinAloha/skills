# skill-transaction-cost-analysis

[English](README.en.md)

A股/跨市场 **交易成本分析 (TCA)** —— 输入成交记录 fills，用分钟线重建区间 VWAP/TWAP，按 **Perold implementation shortfall** 框架把执行成本拆成五项（bps）：**择时、市场冲击(square-root 模型)、点差、佣金税费、滑点**，逐笔计算 + 按 symbol/side 聚合，输出总成本 bps 与瀑布分解。

> QuantSkills 组织技能 · 数据源 Pandadata · 仅供研究参考，不构成投资建议。

## 快速开始

```bash
pip install -r requirements.txt

# 离线演示（无需任何凭证，用内置样本分钟线 + 样本成交）
python examples/run_demo.py

# 真实分析（需配置 panda_data）
python scripts/tca_report.py --fills fills.csv --benchmark vwap \
    --commission-bps 2.5 --impact-coef 0.1 \
    --out report.json --md report.md
```

`fills.csv` 列：`symbol, side(buy/sell), datetime, price, qty`

## 数据后端（三层回退）

`scripts/data_source.py` 按以下顺序自动选择：

1. **`panda_data` SDK**（组织生产标准）：`import panda_data` 成功即用。安装与鉴权见 `skill-pandadata-api`。
2. **内置样本**（`examples/sample_data/*.json`）：无 SDK 时回退，保证 demo 离线可跑。
3. 显式 `--prefer sample` 可强制用样本。

SDK 返回可能是 DataFrame 或 `list[dict]`，`_call_sdk` 两者都处理。

## 输入 → 接口映射

| 用途 | Pandadata 接口 | 关键字段 |
|---|---|---|
| A股分钟线（VWAP/TWAP/σ/ADV） | `get_stock_min(...,frequency='1m'/'5m'/'15m'/'60m')` | datetime, open, close, high, low, volume, amount |
| A股日线（ADV/决策价代理） | `get_stock_daily(...,st=True)` | close, volume, amount, pre_close, trade_status |
| 港股日线（自带 vwap/bid/ask） | `get_hk_daily` | vwap, bid, ask |
| 美股日线（自带 vwap/bid/ask） | `get_us_daily` | vwap, bid, ask |

日期格式 `YYYYMMDD`；symbol 传 `""` 表示全市场。

## 成本分解（implementation shortfall）

| 分项 | 公式（bps） |
|---|---|
| 择时 timing | `dir·(benchmark−arrival)/arrival·1e4`；arrival 基准下为 0 |
| 冲击 impact | `k·σ_day·sqrt(Q/ADV)·1e4`（square-root） |
| 点差 spread | `0.5·mean((H−L)/mid)·1e4`（分钟近似） |
| 佣金税费 fees | `佣金bps + 过户费 + (卖出A股)印花税5bps` |
| 滑点 slippage | `dir·(price−benchmark)/benchmark·1e4` |

方向约定：`buy→+1, sell→−1`，统一"对本方不利为正"。公式依据与文献见 `references/methodology.md`。

## 输出 `TCAReport`

`total_cost_bps` / `breakdown{timing,impact,spread,fees,slippage}` / `by_side[]` / `by_symbol[]` / `fills[]` / `insights[]` / `degraded[]`，可渲染为 JSON / 中文文本 / Markdown。

## 目录

```
scripts/       data_source.py · benchmarks.py · tca_decompose.py · tca_report.py · formatters.py
references/    methodology.md
examples/      run_demo.py · sample_report.md · sample_data/(get_stock_min.json · fills.csv)
```

## ⚠️ 局限

- Pandadata 无逐笔 tick/盘口，**冲击与点差为分钟级近似**（点差用分钟高低幅代理，通常偏高估）。
- 决策价(arrival) 建议用户提供真实下单时间戳；缺失时用成交前一分钟收盘价代理。
- 港美股用日线自带 `vwap/bid/ask` 精度更高。

## 免责

数据非实时。本工具仅用于研究与执行成本诊断方法论演示，不构成任何投资建议。

## 许可证

GPL-3.0-only，详见 [LICENSE](LICENSE)。
