# skill-northbound-margin-monitor

A-share 北向资金 + 融资融券 + 股指期货全景监控系统。每日自动采集沪深港通资金流向、两融数据和股指期货数据，通过 **25 个信号检测器** 和 **4 个共振/背离模式**，配合 **LLM 宏观研判**（DeepSeek/Claude），生成综合情绪评分日报（12 节 Markdown + JSON）。

## 功能特性

- **五维信号体系**: 北向(7) + 融资(7) + 期货(3) + 量价(2) + 微观结构(7) = 25 检测器
- **双源容灾**: Pandadata（融资个股）+ AKShare（北向/期货/涨跌停），多级自动降级
- **LLM 宏观研判**: DeepSeek/Claude API（含指数退避重试 + 超时） + 规则引擎备选
- **共振/背离检测**: 4 种跨资产信号模式识别
- **信号衰减**: 半衰期指数衰减，解决连续触发信号虚高问题
- **数据源透明**: 10 种标准化标签，每个信号标注真实数据来源
- **综合评分**: 五维加权 0-100 评分 + 风险惩罚 + ★1-5 风险评级
- **行业中性排名**: Z-score 消除行业规模偏差的融资暴露排名
- **历史对比**: 与上一交易日逐项对比变化
- **双格式输出**: Markdown 12节日报 + JSON 结构化数据
- **日期缓存**: 同日数据自动复用 + 申万离线备份（永不过期）
- **540 个测试**: 101 个测试类覆盖全部模块

## 安装

```bash
# 克隆仓库
cd D:\python\PandaAI\Pandaai_skill_02

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 Pandadata 凭证:
#   DEFAULT_USERNAME=86xxxxxxxxxxx
#   DEFAULT_PASSWORD=your_password

# LLM API Key (可选，无 Key 时使用规则引擎备选)
#   ANTHROPIC_API_KEY=sk-xxx           # Claude
#   ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic  # DeepSeek
```

### 依赖

- Python >= 3.10
- panda_data >= 0.0.9 (融资融券数据)
- akshare >= 1.18.0 (北向/期货/涨跌停数据)
- anthropic >= 0.39.0 (LLM API)
- tenacity >= 8.0 (LLM 重试)
- pandas >= 2.0.0, numpy >= 1.22, < 2.0
- streamlit >= 1.28.0 (仪表盘)

## 使用

```bash
# 默认运行（最新交易日，使用缓存）
python run.py

# 指定日期
python run.py --date 20260630

# 强制拉取最新数据（跳过缓存）
python run.py --date 20260630 --no-cache

# 精简模式（LLM 150-200字摘要）
python run.py --summary

# 自定义 TOP-N 数量 + 详细日志
python run.py --top-n 30 --verbose

# 清理缓存（删除30天前的数据）
python run.py --cleanup-cache 30
```

## 输出

```
output/
  2026-07-02/
    panorama_monitor_20260702.md   # Markdown 日报（12节）
    panorama_monitor_20260702.json # JSON 结构化数据

cache/
  YYYYMMDD/                        # 每日缓存
  nb_flow_history.parquet          # 北向流向累积历史
  sw_industry_mapping.parquet      # 申万行业分类缓存（30天）
  shenwan_backup.parquet           # 申万离线备份（永不过期）
```

### 日报包含

1. **北向资金概览** — 7 信号 + 数据源标签 + 摘要
2. **融资融券概览** — 7 信号 + 宏观数据 + 个股 TOP10
3. **股指期货信号** — 3 信号（基差/持仓/共振）+ 各指数摘要
4. **共振/背离分析** — 4 种跨资产模式
5. **量价确认** — 指数动量 + 波动率区间
6. **微观结构信号** — 涨跌比/量能/成交额/涨跌停/主力资金/龙虎榜/新高新低
7. **综合情绪评估** — 五维分项得分 + 评级 + 风险惩罚
8. **历史对比** — 与上一交易日逐项对比
9. **AI 宏观研判** — LLM 或规则引擎综合分析
10. **板块资金流向** — 行业融资暴露 Z-score 排名
11. **综合风险评估** — 4因子分解 + 风险信号清单
12. **数据溯源** — 每类数据来源 + 状态（✅/⚠️）

## 项目结构

```
core/
  __init__.py
  _types.py             # SignalResult 数据类型 + 信号衰减函数
  cache.py              # 日期分区 Parquet 缓存 + 离线备份
  data_fetcher.py       # 多源数据采集（Pandadata + AKShare + HKEX）
  flow_accumulator.py   # 北向流向日度历史累积器
  northbound.py         # 北向资金 7 信号检测器（合并 flow_trend + flow_direction_trend）
  margin.py             # 融资融券 7 信号检测器（含极端区间检测）
  futures.py            # 股指期货 3 信号检测器
  price_volume.py       # 量价确认 2 信号
  microstructure.py     # 微观结构 7 信号
  resonance.py          # 4 共振/背离模式
  scorer.py             # 综合评分 0-100 + 风险评级 + 行业中性排名
  pipeline.py           # PanoramaPipeline 编排器
  backtest.py           # 历史 IC 回测框架
  reporter.py           # Markdown(12节) + JSON 报告生成
llm/
  analyst.py            # LLMAnalyst: DeepSeek/Claude API + 重试 + 规则引擎备选
dashboard/
  app.py                # Streamlit 仪表盘
mcp_server.py           # MCP Server (stdio + SSE)
run.py                  # CLI 入口
config.json             # 全部阈值和权重配置
tests/                  # 540 个测试用例 (101 个测试类)
  conftest.py           # 共享 fixtures
  test_northbound.py    # 北向检测器测试
  test_margin.py        # 融资检测器测试
  test_futures.py       # 期货检测器测试
  test_price_volume.py  # 量价检测器测试
  test_microstructure.py # 微观结构测试
  test_resonance.py     # 共振分析测试
  test_scorer.py        # 评分器测试
  test_reporter.py      # 报告生成测试
  test_pipeline.py      # 管线集成测试
  test_analyst.py       # LLM 分析测试
  test_backtest.py      # 回测测试
  test_cache.py         # 缓存测试
  test_flow_accumulator.py # 流向累积器测试
  test_data_fetcher.py  # 数据采集测试
```

## 测试

```bash
# 运行全部 540 个测试
python -m pytest tests/ -q

# 按模块
python -m pytest tests/test_northbound.py -q
python -m pytest tests/test_margin.py -q

# 带覆盖率
python -m pytest tests/ --cov=core --cov-report=term-missing
```

## 配置

`config.json` 中可调整所有阈值和权重：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `northbound.consecutive_days_threshold` | 3 | 连续流入/流出天数阈值 |
| `northbound.anomaly_zscore_threshold` | 2.0 | 单日异常 Z-score 阈值 |
| `margin.buy_ratio_hot` | 0.10 | 融资买入比活跃线 |
| `margin.buy_ratio_dangerous` | 0.15 | 融资买入比危险线 |
| `margin.extreme_percentile` | 95 | 极端过热分位数 |
| `margin.ice_point_percentile` | 5 | 极端冰点分位数 |
| `futures.basis_threshold` | 0.3 | 基差方向阈值 |
| `futures.oi_change_threshold` | 2.0 | 持仓量变化阈值 |
| `scoring.northbound_weight` | 0.18 | 北向资金权重（2026-07 由 0.35 重校准） |
| `scoring.margin_weight` | 0.38 | 融资融券权重 |
| `scoring.futures_weight` | 0.20 | 股指期货权重 |
| `scoring.pv_weight` | 0.08 | 量价确认权重 |
| `scoring.micro_weight` | 0.16 | 微观结构权重（2026-07 由 0.05 重校准） |
| `llm.timeout` | 120.0 | LLM API 超时(秒) |
| `llm.max_retries` | 2 | HTTP 级别重试 |
| `llm.llm_retries` | 3 | 指数退避 LLM 重试 |

## 数据源

| 数据 | 主源 | 备源 | 降级策略 |
|------|------|------|----------|
| 融资融券个股 | Pandadata `get_margin()` | AKShare SSE/SZSE | 自动切换 |
| 融资融券宏观 | AKShare `macro_china_market_margin_sh/sz` | — | — |
| 北向资金汇总 | AKShare `stock_hsgt_hist_em` | CSI300 代理 | 4级降级链 |
| 北向资金流向 | AKShare `stock_hsgt_fund_flow_summary_em` | — | 涨跌家数替代 |
| 北向流向历史 | FlowAccumulator 累积 | 实时重建 | — |
| 股指期货 | AKShare `futures_main_sina` + `stock_zh_index_daily` | — | — |
| 股票信息 | Pandadata `get_stock_detail` | — | — |
| 申万行业分类 | AKShare `stock_board_industry_name_em` | 30天缓存 → 离线备份 | 永不过期 |
| HKEX 补充 | 港交所 CSV | — | best-effort |
| 涨跌停统计 | AKShare `stock_zt_pool_em` | — | best-effort |
| LLM 研判 | DeepSeek / Claude API | 规则引擎备选 | 自动降级 |

**已知数据限制**：北向 `net_buy_amount` 自 2024-08 起为 NaN，`market_value` 近 3 月为 0。系统自动使用 FlowAccumulator + CSI300 指数代理。每个信号的报告表格标注了真实数据来源。

## License

GPLv3
