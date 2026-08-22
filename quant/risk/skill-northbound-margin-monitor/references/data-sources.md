# 数据源参考手册 v2.0

## 概览

| 数据类别 | API | 库 | 频率 | 覆盖范围 | 可靠性 |
|----------|-----|-----|------|----------|--------|
| 融资融券个股 | `pdd.get_margin()` | panda_data | 日 | ~5186只A股 | ✅ 高 |
| 融资融券宏观SH | `ak.macro_china_market_margin_sh()` | akshare | 日 | 沪市汇总 | ✅ 高 |
| 融资融券宏观SZ | `ak.macro_china_market_margin_sz()` | akshare | 日 | 深市汇总 | ✅ 高 |
| 融资融券个股(备) | `ak.stock_margin_detail_sse/szse()` | akshare | 日 | ~4000只 | ⚠️ 备源 |
| 股票交易列表 | `pdd.get_trade_list()` | panda_data | 日 | 全A股 | ✅ 高 |
| 股票详情 | `pdd.get_stock_detail()` | panda_data | 日 | 全A股 | ✅ 高 |
| 北向资金汇总 | `ak.stock_hsgt_hist_em()` | akshare | 日 | 沪深港通 | ⚠️ 部分字段缺失 |
| 北向资金流向 | `ak.stock_hsgt_fund_flow_summary_em()` | akshare | 日 | 沪/深股通 | ✅ 高 |
| 北向流向历史 | FlowAccumulator 累积 | 内部 | 日 | 北向方向累积 | ✅ 高 |
| 股指期货 | `ak.futures_main_sina()` | akshare | 日 | IF/IC/IH | ✅ 高 |
| 现货指数 | `ak.stock_zh_index_daily()` | akshare | 日 | CSI300/SSE50/CSI500 | ✅ 高 |
| 申万行业分类 | `ak.stock_board_industry_name_em()` | akshare | 日 | 全行业 | ⚠️ 30天缓存+离线备份 |
| 主力资金流向 | `ak.stock_market_fund_flow()` | akshare | 日 | 全市场 | ⚠️ best-effort |
| HKEX 补充 | 港交所 CSV | urllib | 日 | 北向成交额 | ⚠️ best-effort |
| 涨跌停统计 | `ak.stock_zt_pool_em()` | akshare | 日 | 全A股 | ⚠️ best-effort |
| 龙虎榜 | `ak.stock_lhb_detail_em()` | akshare | 日 | 全A股 | ⚠️ best-effort |
| 新高新低 | `ak.stock_a_high_low_statistics()` | akshare | 日 | 全A股 | ⚠️ best-effort |
| LLM 研判 | DeepSeek / Claude API | anthropic | — | — | ⚠️ 含规则引擎备选 |

---

## 1. Pandadata — 融资融券

### get_margin

```python
import panda_data as pdd

pdd.init_token(username="86...", password="...", base_url="...")
df = pdd.get_margin(
    symbol=["000001.SZ", "600519.SH"],
    start_date="20260601",
    end_date="20260630",
)
```

**返回字段:**

| 字段 | 类型 | 说明 |
|------|------|------|
| `symbol` | str | 股票代码 (000001.SZ) |
| `date` | str | 日期 (20260630) |
| `margin_balance` | float | 融资余额（元） |
| `buy_on_margin_value` | float | 融资买入额（元） |
| `margin_repayment` | float | 融资偿还额（元） |
| `short_balance` | float | 融券余额（元） |
| `short_sell_quantity` | float | 融券卖出量（股） |
| `short_repayment_quantity` | float | 融券偿还量（股） |
| `short_balance_quantity` | float | 融券余量（股） |
| `total_balance` | float | 总余额（元） |
| `margin_type` | str | 融资类型（现金/股票） |

**批量查询限制:**
- 单次最多 200 只股票
- 建议 4 线程并发
- 5186 只全量数据约 5 分钟
- 返回约 550K 行

### get_trade_list

```python
df = pdd.get_trade_list(date="20260630")
```

返回当日可交易股票列表，包含 `symbol`, `name` 等字段。

### get_stock_detail

```python
df = pdd.get_stock_detail(symbol=["000001.SZ", ...])
```

**关键字段:**
- `symbol` — 股票代码
- `sector_code_name` — 行业分类（映射为 `industry`）
- `status` — 上市状态（映射为 `list_status`）

---

## 2. 东方财富 (via AKShare) — 北向资金

### stock_hsgt_hist_em

```python
import akshare as ak
df = ak.stock_hsgt_hist_em()
```

**原始字段（中文）** → 映射后（英文）:

| 原始字段 | 映射字段 | 数据质量 |
|----------|----------|----------|
| 日期 | `date` | ✅ |
| 当日成交净买额 | `net_buy_amount` | ❌ 2024-08起 NaN |
| 买入成交额 | `buy_turnover` | ✅ |
| 卖出成交额 | `sell_turnover` | ✅ |
| 历史累计净买额 | `cumulative_net_buy` | ✅ |
| 当日资金流入 | `daily_inflow` | ✅ |
| 当日余额 | `daily_balance` | ✅ |
| 持股市值 | `market_value` | ❌ 2026-04后全为0 |
| 沪深300 | `csi300` | ✅ 用作替代指标 |
| 沪深300-涨跌幅 | `csi300_change` | ✅ |
| 领涨股 | `top_gainer_name` | ✅ |
| 领涨股-涨跌幅 | `top_gainer_pct` | ✅ |
| 领涨股-代码 | `top_gainer_code` | ✅ |

**数据量**: 约 2699 行（2014年至今每个交易日）

### stock_hsgt_fund_flow_summary_em

```python
df = ak.stock_hsgt_fund_flow_summary_em()
```

**返回 4 行**（当前交易日）:

| 板块 | 资金方向 | 关键字段 |
|------|----------|----------|
| 沪股通 | 北向/南向 | 成交净买额, 资金净流入 |
| 港股通(沪) | 北向/南向 | 上涨数, 下跌数 |
| 深股通 | 北向/南向 | 相关指数, 指数涨跌幅 |
| 港股通(深) | 北向/南向 | 当日资金余额 |

**处理逻辑:**
1. 过滤掉 `港股通` 行（保留 沪股通 + 深股通）
2. 判断 `资金方向`: 北向/入 = 流入, 南向/出 = 流出
3. 如果方向不明确，使用 `指数涨跌幅` 作为替代

---

## 3. 东方财富 (via AKShare) — 融资融券

### macro_china_market_margin_sh / sz

```python
df_sh = ak.macro_china_market_margin_sh()
df_sz = ak.macro_china_market_margin_sz()
```

**原始字段（中文）**:

| 字段 | 映射字段 | 说明 |
|------|----------|------|
| 日期 | `date` | 日期 |
| 融资余额 | `margin_balance` | 当日融资余额（元） |
| 融资买入额 | `buy_on_margin_value` | 当日融资买入（元） |
| 融券余额 | `short_balance` | 当日融券余额（元） |
| 融券卖出量 | `short_sell_quantity` | 当日融券卖出量 |

**数据量**: SH ~3941 行, SZ ~3743 行（2013年至今每个交易日）

### stock_margin_detail_sse / szse（备源）

```python
df_sse = ak.stock_margin_detail_sse(date="20260630")
df_szse = ak.stock_margin_detail_szse(date="20260630")
```

**原始字段（中文）** → 映射后:

| 原始字段 | 映射字段 |
|----------|----------|
| 股票代码 | `symbol` |
| 股票名称 | `name` |
| 融资余额 | `margin_balance` |
| 融资买入额 | `buy_on_margin_value` |
| 融资偿还额 | `margin_repayment` |
| 融券余量 | `short_balance_quantity` |
| 融券卖出量 | `short_sell_quantity` |
| 融券偿还量 | `short_repayment_quantity` |
| 融券余额 | `short_balance` |

**限制**: 仅返回单日数据，无历史。不带 `margin_type` 字段。

---

## 4. 新浪 (via AKShare) — 股指期货

### futures_main_sina

```python
df_if = ak.futures_main_sina(symbol="IF")
df_ic = ak.futures_main_sina(symbol="IC")
df_ih = ak.futures_main_sina(symbol="IH")
```

**返回字段**:

| 字段 | 说明 |
|------|------|
| `date` | 日期 |
| `close` | 期货收盘价 |
| `volume` | 成交量 |
| `open_interest` | 持仓量 |
| `open` / `high` / `low` | OHLC数据 |

### stock_zh_index_daily

```python
df = ak.stock_zh_index_daily(symbol="sh000300")  # CSI300 现货
```

获取对应现货指数日线，用于基差计算（期货 - 现货）。

---

## 5. 东方财富 (via AKShare) — 申万行业分类

### stock_board_industry_name_em

```python
df = ak.stock_board_industry_name_em()
```

**返回字段**: 股票代码、名称、申万行业分类。

**缓存策略**:
- 主缓存: `cache/sw_industry_mapping.parquet`（30天有效期）
- 离线备份: `cache/shenwan_backup.parquet`（永不过期）
- 降级链: 30天缓存 → AKShare API → 离线备份

---

## 6. 东方财富 (via AKShare) — 涨跌停统计

### stock_zt_pool_em

```python
df = ak.stock_zt_pool_em(date="20260702")
```

返回当日涨停/跌停股票列表，用于极端情绪检测。**best-effort**，API 偶尔返回空。

> **2026-07-06 规则变更：** 主板 ST/\*ST 股涨跌幅限制由 ±5%→±10%，与普通股统一。涨跌停统计中 ST 股也算入 ±10% 涨跌停计数。涨跌停比的极端情绪阈值（当前 > 3:1 偏多 / < 1:3 偏空）可能需要重新校准。建议积累 ≥60 天新数据后运行回测确认。运行 `scripts/calibrate_zt_thresholds.py --since 2026-07-06` 进行自动阈值校准。

---

## 7. 东方财富 (via AKShare) — 主力资金流向

### stock_market_fund_flow

```python
df = ak.stock_market_fund_flow()
```

返回全市场每日资金流向，按订单大小分为五类：

| 字段 | 说明 |
|------|------|
| 日期 | 交易日期 |
| 主力净流入-净额 | 超大单+大单净流入（亿元） |
| 超大单净流入-净额 | 超大单净流入（亿元） |
| 大单净流入-净额 | 大单净流入（亿元） |
| 中单净流入-净额 | 中单净流入（亿元） |
| 小单净流入-净额 | 小单净流入（亿元） |
| 上证-收盘价 / 涨跌幅 | 上证指数参考 |
| 深证-收盘价 / 涨跌幅 | 深证指数参考 |

**检测逻辑**:
- 主力净流入 > 50亿 且 散户(中单+小单)净流出 → 聪明钱逆势进场 (bullish, +0.7)
- 主力净流入 > 50亿 → 主力资金偏多 (bullish, +0.5)
- 主力净流出 > 50亿 且 散户净流入 → 主力撤退散户接盘 (bearish, -0.7)
- 主力净流出 > 50亿 → 主力资金偏空 (bearish, -0.5)

---

## 8. 东方财富 (via AKShare) — 龙虎榜

### stock_lhb_detail_em

```python
df = ak.stock_lhb_detail_em(start_date="20260701", end_date="20260702")
```

返回指定日期范围内所有龙虎榜上榜股票的买卖明细，用于游资情绪和活跃资金方向检测。

**检测逻辑**:
- 汇总净买入占比 > 55% 且总净额 > 5亿 → 游资偏多 (bullish, +0.6)
- 汇总净卖出占比 > 55% 且总净额 < -5亿 → 游资偏空 (bearish, -0.6)
- 数据不足或无显著方向 → 中性不触发

---

## 9. 东方财富 (via AKShare) — 新高新低

### stock_a_high_low_statistics

```python
df = ak.stock_a_high_low_statistics(symbol="all")
```

返回全A股每日创N日新高/新低的股票数量统计，用于市场广度确认。

**检测逻辑**:
- 20日新高占比 > 65% 且 60日确认 → 市场广度偏多 (bullish, +0.6)
- 20日新低占比 > 65% 且 60日确认 → 市场广度偏空 (bearish, -0.6)
- 20日与60日方向背离 → 减弱信号强度
- 数据不足 → 中性不触发

---

## 10. HKEX — 港交所补充数据

从港交所 CSV 获取北向资金成交额补充数据。**best-effort**，用于交叉验证东方财富数据。

---

## 11. FlowAccumulator — 北向流向累积

内部模块，持久化北向资金方向历史：

```python
from core.flow_accumulator import FlowAccumulator

accumulator = FlowAccumulator(cache_dir="cache")
accumulator.update(date, direction_data)  # 追加每日方向
history = accumulator.load()              # 加载完整历史
direction_sum = accumulator.get_direction_sum()  # 近期方向累积
```

**存储**: `cache/nb_flow_history.parquet`（持久化，跨运行保留）

**优先级**: FlowAccumulator（≥10日数据） > 北向净买入 > CSI300代理

---

## 12. LLM 宏观研判

### DeepSeek / Claude API

通过 Anthropic SDK 调用，支持指数退避重试 + 规则引擎备选：

```python
# 使用 DeepSeek
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_MODEL=deepseek-v4-pro
export ANTHROPIC_AUTH_TOKEN=your-deepseek-token

# 使用 Claude
export ANTHROPIC_API_KEY=sk-ant-xxx
export ANTHROPIC_MODEL=claude-sonnet-4-6
```

**容错机制**:
- tenacity 指数退避重试（最多3次，间隔2s→4s→8s）
- 可重试异常: RateLimitError, APIConnectionError, InternalServerError, APITimeoutError
- HTTP 级别重试: 2次
- 超时: 120s 可配置
- 全部失败 → 规则引擎备选（含精确指标提取）

---

## 13. 容灾路径

```
融资融券数据:
  pdd.get_margin() ──┬── 成功 → df.attrs["source"] = "pandadata"
                     └── 失败 → ak.stock_margin_detail_sse/szse()
                                 → df.attrs["source"] = "eastmoney"

北向资金数据:
  ak.stock_hsgt_hist_em() ──┬── 成功, ak.stock_hsgt_fund_flow_summary_em() 成功
                             │   → df.attrs["source"] = "eastmoney"
                             ├── 仅汇总成功
                             │   → nb_summary.attrs["source"] = "degraded"
                             ├── 仅流向成功
                             │   → nb_flow.attrs["source"] = "degraded"
                             └── 全部失败
                                 → empty df, attrs["source"] = "degraded"

北向流向历史:
  FlowAccumulator (优先) ──┬── ≥10日数据 → direction_sum 方向判定
                           └── <10日或无 → net_buy_amount → market_value diff → CSI300 proxy

股指期货:
  ak.futures_main_sina(IF/IC/IH) ──┬── 全部成功 → 基差+持仓+共振
                                    └── 部分失败 → 可用指数参与计算

申万行业分类:
  主缓存(30天) ──┬── 命中 → 直接返回
                  └── 过期 → ak.stock_board_industry_name_em()
                                ├── 成功 → 更新缓存 + 离线备份
                                └── 失败 → 离线备份(shenwan_backup.parquet)

股票信息:
  pdd.get_trade_list() + pdd.get_stock_detail() ──┬── 成功
                                                    └── 失败 → 空 df（非阻塞）

LLM分析:
  DeepSeek/Claude API ──┬── 成功 → AI研判
                        └── 重试耗尽 → 规则引擎备选（含精确指标提取）
```

---

## 14. 数据源标签

每个信号的 `detail["data_source"]` 使用标准化标签，在报告中以图标展示：

| 标签值 | 图标 | 含义 |
|--------|------|------|
| `direct_nb` | 📡 | 北向直连数据（net_buy_amount/market_value 有效） |
| `market_value_diff` | 📊 | 持股市值差分 |
| `csi300_proxy` | 📈 | CSI300 指数代理（北向数据不可用时的替代） |
| `nb_flow_accumulated` | 📋 | FlowAccumulator 方向累积 |
| `pandadata` | 🏢 | Pandadata 实时接口 |
| `akshare_eastmoney` | 🌐 | AKShare 东方财富数据 |
| `akshare_sina` | 🌐 | AKShare 新浪数据 |
| `akshare_realtime` | 🌐 | AKShare 实时数据 |
| `none` | — | 无数据 |
| `unknown` | ❓ | 未知来源 |

### 各检测器数据源分配

| 维度 | 检测器 | 数据源 |
|------|--------|--------|
| 北向 | 净流向趋势 | 📈CSI300 / 📋流累积 (智能优先级) |
| 北向 | 流向趋势 | 📋流累积 (FlowAccumulator direction_sum) |
| 北向 | 单日异常 | 📈CSI300 / 📊市值差 |
| 北向 | 板块偏好 | 📈CSI300 / 📊市值差 |
| 北向 | 市场流向 | 🌐东方财富 (stock_hsgt_fund_flow_summary_em) |
| 北向 | 累计趋势 | 📈CSI300 (MA20/MA60) |
| 北向 | 重仓股变动 | 📊市值差 |
| 融资 | 融资余额趋势 | 🏢Panda / 🌐东方财富 |
| 融资 | 融资买入比 | 🏢Panda / 🌐东方财富 |
| 融资 | 杠杆极端区间 | 🏢Panda / 🌐东方财富 |
| 融资 | 融券趋势 | 🏢Panda / 🌐东方财富 |
| 融资 | 融资融券比 | 🏢Panda / 🌐东方财富 |
| 融资 | 融资重仓股 | 🏢Panda |
| 融资 | 融资类型分布 | 🏢Panda |
| 期货 | 期货基差 | 🌐新浪 |
| 期货 | 持仓量趋势 | 🌐新浪 |
| 期货 | 基差持仓共振 | 🌐新浪 |
| 量价 | 指数动量 | 🌐东方财富 (CSI300) |
| 量价 | 波动率区间 | 🌐东方财富 (CSI300) |
| 微观 | 涨跌比 | 🌐东方财富 |
| 微观 | 指数量能趋势 | 🌐新浪 |
| 微观 | 成交额趋势 | 全市场(沪+深) / CSI300替代 |
| 微观 | 涨跌停统计 | 🌐AK实时 |
| 微观 | 主力资金流向 | 🌐东方财富 (stock_market_fund_flow) |
| 微观 | 龙虎榜活动 | 🌐东方财富 (stock_lhb_detail_em) |
| 微观 | 新高新低广度 | 🌐AK实时 (stock_a_high_low_statistics) |

---

## 15. 已知数据问题

1. **北向资金净买入 (net_buy_amount)**: 2024年8月监管新规后为 NaN，检测器使用 CSI300 指数变动 + FlowAccumulator 替代
2. **北向持仓市值 (market_value)**: 2026年4月后全为 0
3. **个股北向持仓**: 不可用（东方财富 `stock_hsgt_individual_em` 数据停在 2024 年），板块分析基于汇总数据推算
4. **融资买入比**: 总成交额不可用，使用基于融资买入额的启发式估算
5. **涨跌停数据**: `stock_zt_pool_em` 偶尔返回空，标注为 best-effort
