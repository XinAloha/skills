---
name: skill-northbound-margin-monitor
description: A-share 北向资金+融资融券+股指期货全景监控，25信号检测器+4共振模式+LLM宏观研判+主力资金+龙虎榜+新高新低，每日多维度分析日报
version: 2.2.0
category: quant-skills
triggers:
  - 北向资金
  - 融资融券
  - 全景监控
  - 资金流向
  - 股指期货
  - margin monitor
data_sources:
  - pandadata (融资融券个股 + 股票信息)
  - eastmoney via akshare (北向资金汇总 + 市场流向 + 融资宏观 + 涨跌停 + 主力资金)
  - sina via akshare (股指期货数据)
  - hkex (港交所北向补充数据, best-effort)
  - deepseek/claude (LLM宏观研判)
mcp_tools:
  - run_panorama_monitor: Run full panorama monitoring analysis for a given date
  - get_latest_report: Read the most recent panorama report
  - check_trading_day: Verify if a date is an A-share trading day
output_formats:
  - markdown日报 (12节)
  - json结构化数据
  - streamlit仪表盘
schedule: 每日收盘后 15:45 Asia/Shanghai（盘后固定价格交易 15:05-15:30 结束后执行）
license: GPLv3
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-northbound-margin-monitor
  repository_url: https://github.com/quantskills/skill-northbound-margin-monitor
  project_type: skill
  collection: panorama-monitor
  creator: Tao
quantSkills:
  project_type: skill
  category: monitor
  tags:
  - a-share
  - northbound
  - margin-trading
  - futures
  - fund-flow
  - market-sentiment
  - pandadata
  platforms:
  - claude-code
  - codex
  - hermes
  - openclaw
  - cursor
  status: dev
  validation_level: runnable
  maintainer_type: community
  summary_zh: 每日A股资金面全景监控：25信号检测器（北向7+融资7+期货3+量价2+微观结构7），4共振/背离模式，五维加权0-100评分，LLM宏观研判，Markdown/JSON双格式日报。北向数据退化后权重已自动重校准（北向35%→18%）。
  summary_en: Daily A-share capital flow panorama: 25 signal detectors x 5 dimensions, 4 resonance patterns, 0-100 composite score with risk penalty, LLM macro analysis. NB weight auto-recalibrated after net_buy_amount cancellation.
---

# 北向资金 + 融资融券 + 股指期货全景监控

## 概述

每日监控 A 股资金面全景数据，通过 **25 个信号检测器**（北向7 + 融资7 + 期货3 + 量价2 + 微观结构7）和 **4 个共振/背离模式**，配合 **LLM 宏观研判**（DeepSeek/Claude），生成跨资产综合情绪评分（0-100）、风险评级（★1-5）和 Markdown/JSON 双格式日报。

## Workflow（Agent 执行步骤）

1. **确定目标日期。** 用户未指定时使用最近 A 股交易日。调用 `get_trade_cal` 验证；非交易日返回「今日休市」。
2. **拉取数据**（按依赖顺序）：
   - 股票列表 + 交易日历：Pandadata `get_trade_list` + `get_trade_cal`
   - 融资融券个股：Pandadata `get_margin()` → 失败则降级 AKShare `stock_margin_detail_sse/szse`
   - 融资融券宏观：AKShare `macro_china_market_margin_sh/sz`
   - 北向资金汇总：AKShare `stock_hsgt_hist_em` → 失败则用 CSI300 代理
   - 北向资金流向：AKShare `stock_hsgt_fund_flow_summary_em` + FlowAccumulator 历史累积
   - 股指期货：AKShare `futures_main_sina(IF/IC/IH)` + `stock_zh_index_daily`
   - 申万行业分类：AKShare（30 天缓存 → API → 离线备份）
   - 涨跌停 / 主力资金 / 龙虎榜 / 新高新低：各 AKShare best-effort 接口
3. **运行 25 个信号检测器** 分 5 组并行执行（北向7 / 融资7 / 期货3 / 量价2 / 微观结构7），每组内 registry pattern 逐个执行。每个检测器的 `detail` 包含 `data_source` 标签。
4. **运行 4 个共振/背离模式** 基于北向+融资的方向组合判定跨资产共振。
5. **评分与评级**：五维加权 → 共振修正 → [-1,1]→[0,100] → 风险评级 ★1-5。
6. **LLM 宏观研判**（可选）：DeepSeek/Claude API 生成 300-500 字综合研判。API 不可用时回退规则引擎。
7. **生成报告**：Markdown（12 节）+ JSON 双格式，写入 `output/YYYY-MM-DD/`。
8. **校验报告**（生产模式）：运行 `scripts/validate_report.py --date YYYYMMDD`，检查 12 节结构、数据源标签覆盖率、评分一致性、措辞合规。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 Pandadata 凭证（融资数据必需）
cp .env.example .env
# 编辑 .env 填入 DEFAULT_USERNAME 和 DEFAULT_PASSWORD

# 配置 LLM API Key（可选，无 Key 时使用规则引擎备选）
# ANTHROPIC_API_KEY=sk-xxx
# ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic  (DeepSeek 用户)

# 运行（最新交易日）
python run.py

# 指定日期
python run.py --date 20260630

# 强制刷新（跳过缓存）
python run.py --date 20260630 --no-cache

# 精简模式（LLM 输出 150-200 字）
python run.py --summary

# 调整 TOP-N 数量 + 详细日志
python run.py --top-n 30 --verbose

# 清理旧缓存
python run.py --cleanup-cache 30
```

## 核心架构

```
run.py (CLI)
  └─ PanoramaPipeline.run()
       ├─ CacheManager: 日期分区 Parquet 缓存 + 离线备份
       ├─ DataFetcher:   双源数据获取（Pandadata + AKShare + HKEX）
       │    ├─ 融资明细: Pandadata → AKShare East Money (fallback)
       │    ├─ 北向汇总: AKShare East Money stock_hsgt_hist_em
       │    ├─ 北向流向: AKShare East Money stock_hsgt_fund_flow_summary_em
       │    ├─ 融资宏观: AKShare East Money macro_china_market_margin_sh/sz
       │    ├─ 股指期货: AKShare Sina futures_main_sina + stock_zh_index_daily
       │    ├─ 申万行业: AKShare (30天缓存 + 离线备份)
       │    ├─ HKEX补充: 港交所北向成交额 CSV (best-effort)
       │    └─ 股票信息: Pandadata get_trade_list + get_stock_detail
       ├─ FlowAccumulator: 北向流向日度历史累积
       ├─ Northbound:   7 信号检测器 (registry pattern)
       ├─ Margin:        7 信号检测器 (registry pattern)
       ├─ Futures:       3 信号检测器 (registry pattern)
       ├─ PriceVolume:   2 确认信号 (registry pattern)
       ├─ Microstructure:7 广度/流动性/主力资金/龙虎榜/新高新低信号 (registry pattern)
       ├─ Resonance:     4 跨资产共振/背离模式
       ├─ Scorer:        5维加权综合评分 0-100 + 风险评级 + 行业中性排名
       ├─ LLMAnalyst:    DeepSeek/Claude API (含重试+超时) + 规则引擎备选
       └─ Reporter:      Markdown (12节) + JSON 双输出 + 历史对比
```

## 信号检测器 (25个)

### 北向资金 (7 signals)

| 检测器 | 权重 | 数据源 | 说明 |
|--------|:----:|--------|------|
| 净流向趋势 | 3 | FlowAccumulator 方向累积 → CSI300 指数变动（net_buy_amount 已永久取消） | 连续N日净流入/流出方向检测，智能优先级降级 |
| 流向趋势 | 3 | FlowAccumulator direction_sum（北向方向累积） | 优先使用北向方向累积数据 |
| 单日异常 | 2 | CSI300 指数变动 Z-score（原 net_buy_amount Z-score，已不可用） | 当日 CSI300 变动 Z-score vs 60天分布 |
| 板块偏好 | 2 | CSI300 行业指数变动（原市值/净买入不可用） | 行业持仓变动聚合分析，季度披露后 5 日内信号有效 |
| 市场流向 | 2 | 东方财富 stock_hsgt_fund_flow_summary_em | 沪股通+深股通方向一致/分歧检测，基于涨跌家数 |
| 累计趋势 | 3 | CSI300 指数 MA20/MA60（原累计净买入不可用） | CSI300 累计变动 MA20 vs MA60，加速/减速检测 |
| 重仓股变动 | 1 | 持股市值差分（market_value 季度披露后 5 日内有效，其余时段信号返回 neutral） | 持仓市值 5/20 日变动趋势 |

> **已知限制**：`net_buy_amount` 自2024年8月监管新规后为 NaN，**2026年7月起已永久取消**。`market_value` 自 2026-04 后全为 0（季度披露制度下每日持仓数据不再更新）。系统自动降级使用 CSI300 指数变动 + FlowAccumulator 方向数据作为替代。详见报告"数据溯源"节。
>
> **CSI300 代理信号质量说明：** `净流向趋势`（权重3）、`单日异常`（权重2）、`板块偏好`（权重2）、`累计趋势`（权重3）4 个检测器在 `net_buy_amount` 不可用后已实质性退化为 **CSI300 动量代理信号**——CSI300 上涨在统计上 ≈ 北向"流入"信号。这意味着北向维度（35% 总权重）的独立性已下降，与「量价确认」维度（8%）存在信息重叠。建议在新规后回测中对比：使用纯 CSI300 代理 vs 历史真实北向数据的 IC 差异，量化信号衰减程度。若相关性 > 0.7，考虑降低北向维度权重或将其与量价维度合并。

### 融资融券 (7 signals)

| 检测器 | 权重 | 数据源 | 说明 |
|--------|:----:|--------|------|
| 融资余额趋势 | 3 | East Money / Pandadata | 当前融资余额 vs MA5/MA20，热度评级（温和上升→过热→去杠杆） |
| 融资买入比 | 3 | East Money / Pandadata | 融资买入/总成交，>10%热 >15%危险 |
| 杠杆极端区间 | 3 | East Money / Pandadata | 历史分位数检测：>P95过热 / <P5冰点，结合买入比做二级判定 |
| 融券趋势 | 2 | East Money / Pandadata | 5日融券余额变化率，看空情绪 |
| 融资融券比 | 2 | East Money / Pandadata | 融资/融券总余额比率及5/20日趋势 |
| 融资重仓股 | 1 | Pandadata | TOP20 融资余额/买入额排名 + 集中度分析 |
| 融资类型分布 | 1 | Pandadata | 现金担保 vs 股票担保融资占比分析 |

### 股指期货 (3 signals)

| 检测器 | 权重 | 数据源 | 说明 |
|--------|:----:|--------|------|
| 期货基差 | 3 | Sina futures | CSI300/SSE50/CSI500 基差率（升贴水方向+幅度） |
| 持仓量趋势 | 2 | Sina futures | 5日持仓量变化率，含指数间共识加权 |
| 基差持仓共振 | 2 | Sina futures | 基差方向与OI趋势是否相互印证/背离 |

### 量价确认 (2 signals)

| 检测器 | 权重 | 数据源 | 说明 |
|--------|:----:|--------|------|
| 指数动量 | 2 | CSI300 日线（北向数据） | 20日收益率 + MA20偏离，趋势方向判定 |
| 波动率区间 | 1 | CSI300 日线（北向数据） | 年化HV vs 高/低波阈值，风险偏好评估 |

### 微观结构 (7 signals)

| 检测器 | 权重 | 数据源 | 说明 |
|--------|:----:|--------|------|
| 涨跌比 | 2 | 北向流向数据 | 上涨/下跌家数比，市场广度 |
| 指数量能趋势 | 2 | Sina spot index daily | CSI300 成交量 vs MA20，放量/缩量 + 价格方向 |
| 成交额趋势 | 2 | 融资宏观 / CSI300替代 | 全市场成交额 vs MA20，含双源降级 |
| 涨跌停统计 | 1 | AKShare stock_zt_pool_em | 涨跌停家数比，极端情绪检测。**2026-07-06起：** 主板ST股涨跌幅由±5%→±10%，涨跌停统计口径与普通股统一。ST股也可能批量涨停/跌停，涨跌停比信号可能虚高。建议积累60天新数据后重新校准阈值。当前版本在报告中标注「含ST股」。**API 空数据处理：** `stock_zt_pool_em` 偶尔返回空数据（best-effort），此时检测器返回 neutral（strength=0），报告「数据溯源」节标注 `data_source: "none"`，不阻塞全流程 |
| 主力资金流向 | 2 | AKShare stock_market_fund_flow | 超大单+大单 vs 中单+小单，主力/散户背离检测 |
| 龙虎榜活动 | 2 | AKShare stock_lhb_detail_em | 龙虎榜净买入/卖出比，游资情绪检测 |
| 新高新低广度 | 2 | AKShare stock_a_high_low_statistics | 20日/60日新高新低比，市场广度确认 |

## 共振/背离分析 (4 patterns)

| 模式 | 条件 | 信号 | 强度 |
|------|------|------|:----:|
| 偏多共振 | 北向流入 + 融资扩张 | 强烈看多——内外资共振做多 | 强 |
| 偏空共振 | 北向流出 + 融资收缩 | 强烈看空——内外资共振撤离 | 强 |
| 谨慎偏多 | 北向流入 + 融资去杠杆 | 聪明钱逆势加仓，中期见底信号 | 中 |
| 背离危险 | 北向流出 + 融资加杠杆 | 外资撤离/散户接盘，分布特征 | 强 |

## 评分体系

### 五维加权综合评分

```
base = 0.18 × 北向综合 + 0.38 × 融资综合 + 0.20 × 期货综合 + 0.08 × 量价综合 + 0.16 × 微观综合
with_resonance = base × (1 + 共振修正)    # 共振触发时 ±0.10~0.15
score_0_100 = (with_resonance + 1) × 50    # [-1, 1] → [0, 100]
```

> **2026-07 权重重校准说明：** 北向维度权重由 35%→18%（↓17pp）。原因：4/7 北向检测器因 `net_buy_amount` 永久取消已退化为 CSI300 动量代理，与量价维度（8%）存在信息重叠。重新分配至：融资 +3pp（38%）、期货 +3pp（20%）、微观结构 +11pp（16%）。量价维度权重不变。此校准在 `config.json` 中已生效，无需用户手动调整。

每维综合评分由该维度各检测器的**加权平均**（含信号衰减）计算，权重见上表。

### 信号衰减

每个检测器配置 `half_life_days`（半衰期）。连续触发 N 天的信号按 `2^(-N/half_life)` 衰减：
- 新鲜信号（consecutive=1）：衰减系数 ≈ 1.0
- 持续半衰期天数的信号：衰减系数 = 0.5
- 防止"长期持续信号虚高"问题

### 风险惩罚

触发信号中看空信号比例 ≥38%（高）或 ≥28%（中）且绝对值偏高时，额外扣分（最高 10 分），将极端评分拉向中性。

### 评分等级

| 分数 | 等级 | 含义 |
|------|------|------|
| 85-100 | A+ | 强烈看多 |
| 75-84 | A | 看多 |
| 65-74 | B+ | 偏多 |
| 55-64 | B | 温和偏多 |
| 45-54 | C | 中性 |
| 35-44 | D | 中性偏空 |
| 25-34 | E | 偏空 |
| 15-24 | F | 看空 |
| 0-14 | F- | 强烈看空 |

### 可操作建议 [v2.3]

每个评分的 `summary` 字段现在包含系统性的观察要点（非投资建议），覆盖两个层面：

1. **评分驱动：** 基于总分区间（A+→F-）提供仓位/风险管理的定性观察
2. **维度驱动：** 基于各维度极端信号（如融资过热、期货贴水扩大）提供具体关注点

措辞使用谨慎语言（"可关注""建议观察""可考虑"），不提供具体买卖方向、目标价位或仓位百分比。

### 评分校准 [v2.3]

`core/backtest.py` 新增 `calibrate_score_to_returns()` 函数，将历史评分按 9 档（A+→F-）分桶，计算每档的 1/5/20 日平均前向收益和方向胜率。这回答了"当系统过去说 40/D 时，市场实际发生了什么？"——使评分从抽象数字变为有统计锚定的信号。

### 风险评级

4因子加权模型：看空信号比例(35%) + 看空信号强度(25%) + 共振背离风险(20%) + 融资买入热度(20%) → ★1-5 星

## 报告措辞规则

- 使用中文撰写，除非用户指定其他语言。
- 使用绝对日期如 `2026-07-02`；避免在最终报告中使用模糊的「今天」「昨日」。
- 每个数据信号必须标注实际数据源（见数据源标签列）。
- 使用谨慎语言：「值得关注」「可跟踪」「信号偏多/偏空」「情绪偏暖/偏冷」；**禁止**出现「推荐买入」「推荐卖出」「目标价」「必涨/必跌」「加仓/减仓」等投资建议措辞。
- 单一信号不足以形成判断时，明确标注「信号分化」「多空交织」等中性表述。
- 数据调用失败时，跳过失败的子模块（不终止全流程），并在「数据溯源」节中汇总缺失数据计数。
- JSON 输出必须包含评分分项（五维子分 + 共振修正 + 风险惩罚），确保可审计。

## 交易日感知

- 运行前必须检查 A 股交易日历：`get_trade_cal`（Pandadata）或 AKShare `tool_trade_date_hist_sina`。
- 若目标日期为非交易日（周末/节假日），输出「今日休市」提示，不执行扫描。
- 自动化调度建议：每个交易日 `15:45 Asia/Shanghai` 后触发（2026年7月起盘后固定价格交易至 15:30，需等待数据完全就绪）。
- **盘后数据验证：** 2026-07-06 起盘后固定价格交易（15:05-15:30）扩容至全部 A 股。首次运行后需验证：北向资金汇总数据（东方财富）和股指期货数据（新浪）是否已包含盘后时段更新。若数据在 15:45 仍未就绪，考虑将触发时间进一步推迟到 16:00 或增加数据就绪检查（poll `get_last_trade_date` 直到返回目标日期）。
- **数据新鲜度校验：** 每个数据源拉取后校验最大日期是否匹配目标交易日。融资数据日期 ≤ 目标日期 − 1 → 标记为「T-1 数据」（融资数据通常有 1 日延迟，属正常）。北向/期货数据日期不匹配 → 等待 60s 重试 × 3 次，全部失败后使用降级源。
- **Runtime SLA：** 全维度扫描（融资全量 + 北向 + 期货 + 微观结构）：预期 3–5 分钟（含缓存命中）。>15 分钟 → WARNING。>30 分钟 → 超时退出，输出已完成维度的部分结果。

## 免责声明

本 Skill 输出仅供研究参考，**不构成任何投资建议**。投资者应独立判断并承担交易风险。过往资金流向和信号模式不代表未来市场表现。

## License

GPLv3

## 输出

### 日报结构 (12 节)

1. **北向资金概览** — 信号表格（含数据源标签）+ 数据摘要
2. **融资融券概览** — 信号表格 + 宏观数据 + 个股 TOP10
3. **股指期货信号** — 基差/持仓信号 + 各指数摘要
4. **共振/背离分析** — 跨资产模式识别
5. **量价确认** — 指数动量 + 波动率区间
6. **微观结构信号** — 市场广度/量能/涨跌停/主力资金
7. **综合情绪评估** — 5维分项得分 + 总分 + 风险惩罚
8. **历史对比** — 与上一交易日逐项对比
9. **AI 宏观研判** — LLM 或规则引擎综合分析
10. **板块资金流向** — 行业融资暴露 Z-score 排名
11. **综合风险评估** — 4因子分解 + 风险信号清单
12. **数据溯源** — 每一类数据的来源 + 状态（✅/⚠️）

每个信号表格包含 **数据源标签** 列：📡北向直 / 📊市值差 / 📈CSI300 / 📋流累积 / 🏢Panda / 🌐东方财富 / 🌐新浪 / 🌐AK实时

> 完整的日报模板和 LLM 宏观研判 prompt 见 `references/report-template.md`。

### 文件路径

```
output/YYYY-MM-DD/
  panorama_monitor_YYYYMMDD.md
  panorama_monitor_YYYYMMDD.json

cache/
  YYYYMMDD/                  # 每日缓存
  nb_flow_history.parquet    # 北向流向累积历史
  sw_industry_mapping.parquet # 申万行业分类缓存（30天）
  shenwan_backup.parquet     # 申万离线备份（永不过期）
```

## LLM 宏观研判

支持 Anthropic Claude 和 DeepSeek（通过 Anthropic 兼容端点）。特性：
- **指数退避重试**：针对 RateLimitError / APIConnectionError / InternalServerError / APITimeoutError，最多 3 次（间隔 2s→4s→8s）
- **超时配置**：120s 可配，HTTP 级别重试 2 次
- **规则引擎备选**：无 API Key 或 API 全部失败时，自动使用含精确指标提取的规则引擎生成分析
- **DeepSeek 兼容**：自动处理 `resp.content=None` 和 thinking block 跳过

```bash
# 使用 DeepSeek
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_MODEL=deepseek-v4-pro
export ANTHROPIC_AUTH_TOKEN=your-deepseek-token

# 使用 Claude
export ANTHROPIC_API_KEY=sk-ant-xxx
export ANTHROPIC_MODEL=claude-sonnet-4-6
```

## 配置

编辑 `config.json` 调整所有阈值和权重：

```json
{
  "northbound": {
    "consecutive_days_threshold": 3,
    "anomaly_zscore_threshold": 2.0,
    "ma_short_window": 20,
    "ma_long_window": 60
  },
  "margin": {
    "buy_ratio_hot": 0.10,
    "buy_ratio_dangerous": 0.15,
    "trend_short_window": 5,
    "trend_long_window": 20,
    "short_change_days": 5,
    "extreme_percentile": 95,
    "ice_point_percentile": 5,
    "extreme_regime_min_history": 60
  },
  "futures": {
    "basis_threshold": 0.3,
    "oi_change_threshold": 2.0
  },
  "microstructure": {
    "main_fund_flow_threshold_亿": 50.0
  },
  "scoring": {
    "northbound_weight": 0.18,
    "margin_weight": 0.38,
    "futures_weight": 0.20,
    "pv_weight": 0.08,
    "micro_weight": 0.16
  },
  "llm": {
    "model": "claude-sonnet-4-6",
    "max_tokens": 2048,
    "timeout": 120.0,
    "max_retries": 2,
    "llm_retries": 3
  }
}
```

完整配置项见 `config.json`。

> **2026-07-06 新规后校准：** ST 涨跌幅放宽和盘后交易扩容后，以下信号需要在新规后积累 ≥60 个交易日数据（预计 2026年10月）运行专项回测：
> - 涨跌停统计（ST 股纳入 ±10% 口径，极端情绪阈值可能虚高）
> - 微观结构-主力资金流向（量化机构降频可能导致资金流信号含义变化）
> - 微观结构-新高新低广度（20日/60日新高新低基准变化）
> 运行 `scripts/calibrate_zt_thresholds.py --since 2026-07-06` 和 `core/backtest.py --regime-comparison` 输出前后对比。

## 数据源说明

| 数据类别 | 主源 | 备源 | 降级策略 |
|----------|------|------|----------|
| 融资融券个股 | Pandadata `get_margin()` | AKShare `stock_margin_detail_sse/szse` | 自动切换 |
| 融资融券宏观 | AKShare `macro_china_market_margin_sh/sz` | — | — |
| 北向资金汇总 | AKShare `stock_hsgt_hist_em` | CSI300 指数作为代理 | 4级降级链 |
| 北向资金流向 | AKShare `stock_hsgt_fund_flow_summary_em` | — | 涨跌家数替代净买入 |
| 北向流向历史 | FlowAccumulator 累积 | 实时重建 | 持久化 parquet |
| 股指期货 | AKShare `futures_main_sina` + `stock_zh_index_daily` | — | — |
| 股票信息 | Pandadata `get_stock_detail` | — | — |
| 申万行业分类 | AKShare `stock_board_industry_name_em` | 30天缓存 → 离线备份 | 永不过期备份 |
| HKEX 补充 | 港交所 CSV | — | best-effort |
| 涨跌停统计 | AKShare `stock_zt_pool_em` + `stock_zt_pool_dtgc_em` | — | best-effort |
| 主力资金流向 | AKShare `stock_market_fund_flow` | — | best-effort |
| LLM 研判 | DeepSeek / Claude API | 规则引擎备选 | 自动降级 |

**已知数据限制**：
- 北向资金 `net_buy_amount` 自 2024-08 起为 NaN，**2026年7月北向信息披露新规后已永久取消**。盘后仅公布成交额和资金净流入额（`net_inflow`）
- `market_value` 自 2026-04 后全为 0（季度披露制度下每日持仓数据不再更新）。`重仓股变动` 和 `板块偏好` 检测器仅在季度披露后 5 个交易日内有效
- 系统默认使用 CSI300 指数变动 + FlowAccumulator 方向累积作为替代
- 报告中标注了每个信号的实际数据源（见"数据源标签"列）
- 个股北向持仓明细不可直接获取，板块偏好基于汇总数据推算
- 📡 `direct_nb` 标签已废弃（保留用于历史报告交叉引用）
- **生存偏差：** 回测使用的股票 universe 来自交易日当天的可交易列表，已退市/ST 股票不回溯纳入。跨年度回测中 IC 可能被高估约 0.02–0.05。建议在基准对比时使用固定起点 universe

## 数据源标签

每个信号的 `detail` 包含 `data_source` 字段，在报告中以图标展示：

| 标签 | 含义 |
|------|------|
| 📡 `direct_nb` | ~~北向直连数据（net_buy_amount/market_value 有效）~~ **[已废弃]** 2026年7月起 net_buy_amount 永久取消、market_value 全为0，此标签不再生成。保留用于历史报告交叉引用 |
| 📊 `market_value_diff` | 持股市值差分 |
| 📈 `csi300_proxy` | CSI300 指数代理（北向数据不可用时的替代） |
| 📋 `nb_flow_accumulated` | FlowAccumulator 方向累积 |
| 🏢 `pandadata` | Pandadata 实时接口 |
| 🌐 `akshare_eastmoney` | AKShare 东方财富数据 |
| 🌐 `akshare_sina` | AKShare 新浪数据 |
| 🌐 `akshare_realtime` | AKShare 实时数据 |
| ❓ `unknown` | 未知来源 |
| — `none` | 无数据 |

> 数据源标签的检测器分配详见 `references/data-sources.md` §14。

## 高级功能

| 功能 | 入口 | 文档 |
|------|------|------|
| Streamlit 仪表盘 | `streamlit run dashboard/app.py` | |
| MCP Server | `python mcp_server.py` | |
| 回测框架 | `from core.backtest import run_ic_backtest` | `references/advanced-features.md` |
| 缓存管理 | `python run.py --cleanup-cache 30` | |
| 报告校验 | `python scripts/validate_report.py --date ...` | |

## 测试

```bash
# 全部 540 个测试
python -m pytest tests/ -q

# 按模块
python -m pytest tests/test_northbound.py -q
python -m pytest tests/test_margin.py -q
python -m pytest tests/test_futures.py -q
python -m pytest tests/test_scorer.py -q
```

## 目录结构

```
skill-northbound-margin-monitor/
├── SKILL.md                         # Agent 工作流入口
├── README.md                        # 人类文档
├── OPERATION_MANUAL.md              # 详细操作手册
├── LICENSE                          # GPLv3
├── config.json                      # 运行配置（权重+阈值+LLM参数）
├── pyproject.toml                   # Python 项目元数据
├── .env.example                     # 环境变量模板
├── requirements.txt                 # Python 依赖
├── run.py                           # CLI 入口
├── mcp_server.py                    # MCP 服务（3 tools）
├── core/
│   ├── data_fetcher.py              # 双源数据获取（Pandadata + AKShare + HKEX）
│   ├── flow_accumulator.py          # 北向流向日度历史累积
│   ├── northbound.py                # 北向 7 信号（registry pattern）
│   ├── margin.py                    # 融资 7 信号（registry pattern）
│   ├── futures.py                   # 期货 3 信号（registry pattern）
│   ├── price_volume.py              # 量价 2 确认信号
│   ├── microstructure.py            # 微观结构 7 信号
│   ├── resonance.py                 # 4 跨资产共振/背离模式
│   ├── scorer.py                    # 五维加权评分 + 风险评级
│   ├── reporter.py                  # Markdown + JSON 双输出
│   ├── pipeline.py                  # 端到端流水线
│   ├── cache.py                     # 日期分区 Parquet 缓存
│   └── backtest.py                  # 回测框架（IC + 分层 + 状态分解）
├── llm/
│   └── analyst.py                   # LLM 宏观研判（指数退避 + 规则备选）
├── tests/                           # 测试用例（540个）
├── references/
│   ├── data-sources.md              # 13 数据源详细文档（含容灾路径）
│   ├── report-template.md           # 12 节日报模板 + LLM prompt
│   └── advanced-features.md         # Streamlit / MCP / 回测 / 缓存管理
├── scripts/
│   └── validate_report.py           # 报告完整性校验
├── dashboard/
│   └── app.py                       # Streamlit 仪表盘
├── cache/                           # 数据缓存
└── output/                          # 报告输出
    └── YYYY-MM-DD/
        ├── panorama_monitor_YYYYMMDD.md
        └── panorama_monitor_YYYYMMDD.json
```
