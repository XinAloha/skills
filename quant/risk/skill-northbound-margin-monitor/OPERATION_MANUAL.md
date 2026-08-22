# 北向资金 + 融资融券 + 股指期货全景监控 — 运维手册 v2.0

## 目录

1. [环境配置](#环境配置)
2. [日常运行](#日常运行)
3. [信号解读](#信号解读)
4. [配置调优](#配置调优)
5. [故障排查](#故障排查)
6. [数据质量说明](#数据质量说明)
7. [高级功能](#高级功能)

---

## 环境配置

### Pandadata 凭证

系统需要 Pandadata API 获取融资融券个股数据和股票信息。配置方式（二选一）：

**方式 1: 环境变量（推荐）**
```bash
export DEFAULT_USERNAME=8613800138000
export DEFAULT_PASSWORD=your_password
```

**方式 2: config.json**
```json
{
  "pandadata": {
    "username": "8613800138000",
    "password": "your_password",
    "base_url": "http://pandadata.pandaaiquant.com"
  }
}
```

> **注意**: 用户名必须加 `86` 前缀。如果 Pandadata 不可用，融资数据自动降级到东方财富。

### LLM API Key（可选）

```bash
# 使用 DeepSeek（推荐国内用户）
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_MODEL=deepseek-v4-pro
export ANTHROPIC_AUTH_TOKEN=your-deepseek-token

# 使用 Claude
export ANTHROPIC_API_KEY=sk-ant-xxx
export ANTHROPIC_MODEL=claude-sonnet-4-6
```

> 无 API Key 时，系统自动使用规则引擎备选生成宏观研判。

### Python 环境

```bash
pip install -r requirements.txt
# panda_data >= 0.0.9
# akshare >= 1.18.0
# anthropic >= 0.39.0
# tenacity >= 8.0
# pandas >= 2.0.0, numpy >= 1.22, < 2.0
# streamlit >= 1.28.0
```

---

## 日常运行

### 基本命令

```bash
# 每个交易日收盘后运行（自动检测最新交易日）
python run.py

# 指定历史日期回溯
python run.py --date 20260630

# 强制重新获取数据（跳过缓存）
python run.py --date 20260630 --no-cache

# 精简模式（LLM 输出 150-200 字）
python run.py --summary

# 自定义 TOP-N 数量 + 详细日志
python run.py --top-n 30 --verbose

# 清理旧缓存
python run.py --cleanup-cache 30
```

### 定时任务

Windows Task Scheduler 或 Linux cron:

```bash
# 每个交易日 15:30 运行（cron 示例）
30 15 * * 1-5 cd /path/to/skill && python run.py >> logs/monitor.log 2>&1
```

### 缓存管理

```bash
# 清理 30 天前的缓存
python run.py --cleanup-cache 30
```

缓存目录结构：
```
cache/
  YYYYMMDD/                       # 每日缓存
    northbound.parquet
    margin.parquet
    margin_detail.parquet
    stock_info.parquet
    futures.parquet
    .cache_meta.json
  nb_flow_history.parquet         # 北向流向累积历史（持久化）
  sw_industry_mapping.parquet     # 申万行业分类缓存（30天）
  shenwan_backup.parquet          # 申万离线备份（永不过期）
```

---

## 信号解读

### 北向资金信号（7个）

| 信号 | 权重 | 触发条件 | 看多含义 | 看空含义 |
|------|:----:|----------|----------|----------|
| 净流向趋势 | 3 | 连续3日同向 | 外资持续流入 | 外资持续流出 |
| 流向趋势 | 3 | FlowAccumulator方向累积 | 北向方向持续偏多 | 北向方向持续偏空 |
| 单日异常 | 2 | Z-score ≥ 2.0 | 单日大幅抢筹 | 单日恐慌撤离 |
| 板块偏好 | 2 | 行业市值变动 | 重点行业获增持 | 重点行业被减持 |
| 市场流向 | 2 | 沪深股通一致 | 两市一致流入 | 两市一致流出 |
| 累计趋势 | 3 | MA20/MA60 交叉 | 加速流入 | 加速流出 |
| 重仓股变动 | 1 | 市值变动 > 0.5% | 重仓股加仓 | 重仓股减仓 |

> **智能优先级**: 净流向趋势和流向趋势使用合并检测器，按 FlowAccumulator（≥10日） → net_buy_amount → CSI300 代理 自动降级。

> **重要**: 由于东方财富 API 近期 `net_buy_amount` 和 `market_value` 字段数据缺失，部分检测器自动降级使用 CSI300 指数变动作为替代指标。**市场流向**（沪股通/深股通方向）是目前最可靠的实时北向指标。每个信号标注了真实数据源。

### 融资融券信号（7个）

| 信号 | 权重 | 触发条件 | 看多含义 | 看空含义 |
|------|:----:|----------|----------|----------|
| 融资余额趋势 | 3 | 当前 vs MA20 | 温和上升（做多情绪） | 过热（>10%）或快速去杠杆 |
| 融资买入比 | 3 | vs 总成交 | 活跃（10-15%） | 过度杠杆（>15%） |
| 杠杆极端区间 | 3 | P95/P5 分位数 | 冰点反弹机会 | 极端过热 → 系统性风险 |
| 融券趋势 | 2 | 5日变化率 | 空头大幅回补 | 看空情绪上升 |
| 融资融券比 | 2 | 比率趋势 | 多头主导 | 空头力量上升 |
| 融资重仓股 | 1 | TOP20 集中度 | — | 集中度 > 40% 系统风险 |
| 融资类型分布 | 1 | 现金/股票占比 | 结构均衡 | 股票担保品过度集中 |

> **杠杆极端区间**（v2.0 新增）：融资余额 > P95 且买入比 ≥ 15% → "杠杆极端过热" (-0.9)；融资余额 < P5 → "杠杆极端冰点" (+0.6)。

### 股指期货信号（3个）

| 信号 | 权重 | 触发条件 | 看多含义 | 看空含义 |
|------|:----:|----------|----------|----------|
| 期货基差 | 3 | 升贴水方向+幅度 | 期货升水（情绪乐观） | 期货贴水（情绪悲观） |
| 持仓量趋势 | 2 | 5日OI变化率 | 持仓增加+价格上涨 | 持仓减少+价格下跌 |
| 基差持仓共振 | 2 | 基差与OI方向 | 两指标相互印证 | 两指标背离 |

> 覆盖 CSI300(IF)、CSI500(IC)、SSE50(IH) 三大股指期货主力合约。

### 量价确认信号（2个）

| 信号 | 权重 | 触发条件 | 含义 |
|------|:----:|----------|------|
| 指数动量 | 2 | 20日收益率 + MA20偏离 | 趋势方向判定 |
| 波动率区间 | 1 | 年化HV vs 阈值 | 高波=风险规避，低波=风险偏好 |

### 微观结构信号（7个）

| 信号 | 权重 | 触发条件 | 含义 |
|------|:----:|----------|------|
| 涨跌比 | 2 | 上涨/下跌家数比 | 市场广度 |
| 指数量能趋势 | 2 | CSI300 成交量 vs MA20 | 放量/缩量 + 价格方向 |
| 成交额趋势 | 2 | 全市场成交额 vs MA20 | 量能热度（双源降级） |
| 涨跌停统计 | 1 | 涨跌停家数比 | 极端情绪检测 |
| 主力资金流向 | 2 | 超大单+大单净流 vs 阈值 | 主力/散户背离，聪明钱方向 |
| 龙虎榜活动 | 2 | 净买入/卖出比 + 净额 | 游资情绪，活跃资金方向 |
| 新高新低广度 | 2 | 20日/60日新高新低比 | 市场广度确认，趋势健康度 |

### 共振/背离模式（4种）

| 模式 | 北向 | 融资 | 含义 | 强度 | 操作参考 |
|------|------|------|------|:----:|----------|
| 偏多共振 | 流入 ↑ | 扩张 ↑ | 内外资同步看多 | 强 | 顺势做多 |
| 偏空共振 | 流出 ↑ | 收缩 ↓ | 内外资同步看空 | 强 | 减仓/观望 |
| 谨慎偏多 | 流入 | 去杠杆 | 聪明钱逆势进场 | 中 | 关注底部信号 |
| 背离危险 | 流出 | 加杠杆 | 外资撤离散户接盘 | 强 | 高度警惕 |

### 信号衰减机制

每个检测器配置 `half_life_days`（半衰期）。连续触发 N 天的信号按 `2^(-N/half_life)` 衰减：
- 新鲜信号（consecutive=1）：衰减系数 ≈ 1.0
- 持续半衰期天数的信号：衰减系数 = 0.5
- 防止"长期持续信号虚高"问题

### 综合评分解读

**五维加权模型**: 北向(35%) + 融资(35%) + 期货(17%) + 量价(8%) + 微观(5%)

```
base = 0.35×北向 + 0.35×融资 + 0.17×期货 + 0.08×量价 + 0.05×微观
with_resonance = base × (1 + 共振修正)    # 共振触发时 ±0.10~0.15
score_0_100 = (with_resonance + 1) × 50    # [-1, 1] → [0, 100]
```

| 分数 | 等级 | 市场含义 |
|------|------|----------|
| 85-100 | A+ | 强烈看多 — 多处信号共振，资金面全面偏多 |
| 75-84 | A | 看多 |
| 65-74 | B+ | 偏多 |
| 55-64 | B | 温和偏多 |
| 45-54 | C | 中性 — 多空均衡，观望为主 |
| 35-44 | D | 中性偏空 |
| 25-34 | E | 偏空 |
| 15-24 | F | 看空 |
| 0-14 | F- | 强烈看空 |

### 风险评级

**4因子加权模型**: 看空信号比例(35%) + 看空信号强度(25%) + 共振背离风险(20%) + 融资买入热度(20%) → ★1-5 星

**风险惩罚**: 触发信号中看空信号比例 ≥38%（高）或 ≥28%（中）且绝对值偏高时，额外扣分（最高 10 分），将极端评分拉向中性。

---

## 配置调优

### 调整信号灵敏度

```json
{
  "northbound": {
    "consecutive_days_threshold": 3,   // 降低→更敏感，提高→更稳健
    "anomaly_zscore_threshold": 2.0,   // 标准正态 95% 置信 = 1.96
    "ma_short_window": 20,
    "ma_long_window": 60
  },
  "margin": {
    "buy_ratio_hot": 0.10,             // 融资活跃阈值
    "buy_ratio_dangerous": 0.15,       // 融资危险阈值
    "trend_short_window": 5,
    "trend_long_window": 20,
    "short_change_days": 5,
    "extreme_percentile": 95,          // 极端过热分位数
    "ice_point_percentile": 5,         // 极端冰点分位数
    "extreme_regime_min_history": 60
  },
  "futures": {
    "basis_threshold": 0.3,            // 基差方向阈值
    "oi_change_threshold": 2.0         // 持仓量变化阈值
  }
}
```

### 调整评分权重

```json
{
  "scoring": {
    "northbound_weight": 0.35,         // 北向权重
    "margin_weight": 0.35,             // 融资权重
    "futures_weight": 0.17,            // 期货权重
    "pv_weight": 0.08,                 // 量价权重
    "micro_weight": 0.05               // 微观权重
  }
}
```

- 如果更关注外资动向：提高 `northbound_weight`
- 如果更关注杠杆情绪：提高 `margin_weight`
- 如果更关注期货定价：提高 `futures_weight`

### LLM 配置

```json
{
  "llm": {
    "model": "claude-sonnet-4-6",
    "max_tokens": 2048,
    "timeout": 120.0,                  // API 超时（秒）
    "max_retries": 2,                  // HTTP 级别重试
    "llm_retries": 3                   // 指数退避 LLM 重试（2s→4s→8s）
  }
}
```

---

## 故障排查

### 常见问题

**1. "Pandadata credentials not configured"**

未配置 Pandadata 凭证。设置环境变量或 config.json 中的凭证。如果暂时无法获取 Pandadata 权限，系统会自动降级到东方财富数据源。

**2. "Empty stock universe for YYYYMMDD"**

Pandadata 对当天日期返回空数据（数据尚未结算）。使用前一个交易日：
```bash
python run.py --date 20260630  # 而非 20260701
```

**3. 融资买入比数值异常大**

已修复 — 旧版本将所有历史行求和导致数值膨胀。确认使用最新代码。

**4. 北向资金显示 "0亿" 或 "-"**

这是正常现象。东方财富 API 的 `market_value` 和 `net_buy_amount` 字段自 2024-08 起存在数据缺失。系统已自动降级使用 CSI300 指数变动 + FlowAccumulator 方向数据作为替代。每个信号的报告表格标注了真实数据来源（📈CSI300 / 📋流累积）。参考**市场流向**指标获取可靠的方向信号。

**5. LLM API 调用失败**

系统有完善的容错机制：
- tenacity 指数退避重试（最多3次，间隔2s→4s→8s）
- HTTP 级别重试 2 次
- 全部失败 → 规则引擎备选（含精确指标提取）

报告第9节会标注研判来源（LLM 或规则引擎）。

**6. 缓存保存失败**

```
WARNING Cache save failed (non-fatal): ...
```

不影响报告生成。原因可能是 Pandadata 返回的某些字段包含字符串 "NaN"。最新版本已加入自动清理逻辑。

**7. 网络超时**

数据采集涉及多轮 API 调用（5186 只股票分 26 批，4 线程并发），首次运行可能需要 3-5 分钟。后续使用缓存只需数秒。

**8. 申万行业分类获取失败**

系统使用三级降级链：30天缓存 → AKShare API → 离线备份（永不过期）。即使 API 完全不可用，仍可从 `shenwan_backup.parquet` 加载历史分类数据。

### 日志级别

```bash
# 正常运行（INFO）
python run.py

# 调试模式（DEBUG）
python run.py --verbose
```

日志输出包含每个阶段的时间戳，方便定位慢查询。

---

## 数据质量说明

### 数据时延

| 数据 | 可用时间 | 备注 |
|------|----------|------|
| 融资融券个股 (Pandadata) | T日 20:00 后 | 需等交易所结算 |
| 融资融券宏观 (东方财富) | T日 18:00 后 | 通常较早可用 |
| 北向资金汇总 (东方财富) | T日 18:00 后 | 净买入字段可能为 NaN |
| 北向资金流向 (东方财富) | T日 18:00 后 | 沪股通/深股通方向可靠 |
| 股票信息 (Pandadata) | 实时 | 行业分类偶尔滞后 |
| 股指期货 (新浪) | T日 15:30 后 | 收盘后即可用 |
| 申万行业分类 | 实时 | 30天缓存 + 离线备份 |

### 已知数据问题

1. **北向资金净买入 (net_buy_amount)**: 2024年8月监管新规后为 NaN，检测器使用 CSI300 替代
2. **北向持仓市值 (market_value)**: 2026年4月后全为 0
3. **个股北向持仓**: 不可用（东方财富 `stock_hsgt_individual_em` 数据停在 2024 年），板块分析基于汇总数据推算
4. **融资买入比**: 总成交额不可用，使用基于融资买入额的启发式估算
5. **涨跌停数据**: `stock_zt_pool_em` 偶尔返回空，标注为 best-effort

### 容灾路径

```
融资融券:
  Pandadata get_margin (主) ──fail──▶ 东方财富 SSE/SZSE (备)

北向资金:
  FlowAccumulator direction_sum (优先)
  → net_buy_amount → market_value diff → CSI300 proxy (4级降级)

北向流向:
  stock_hsgt_fund_flow_summary_em (主) → 涨跌家数替代

股指期货:
  Sina futures_main_sina(IF/IC/IH) — 数据来自新浪，稳定性高

申万行业:
  30天缓存 → AKShare API → 离线备份（永不过期）

LLM分析:
  DeepSeek/Claude API → 指数退避重试(3次) → 规则引擎备选
```

降级模式下报告会标注数据源，数据溯源表会显示 ⚠️ 状态。

---

## 高级功能

### Streamlit 仪表盘

```bash
streamlit run dashboard/app.py
```

可视化展示信号历史、评分趋势和行业分布。

### MCP Server

```bash
python mcp_server.py           # stdio 模式（Claude Code 集成）
python mcp_server.py --sse     # SSE 模式（Web 集成）
```

### 回测框架

```python
from core.backtest import run_ic_backtest

result = run_ic_backtest(nb_history, margin_history, min_window=60)
# result.ic_summary      — IC 汇总统计
# result.detector_ic_stats — 各检测器 IC 表现
# result.by_regime       — 分市场状态 IC
```

### 报告校验

```bash
python scripts/validate_report.py --date 20260630
```
