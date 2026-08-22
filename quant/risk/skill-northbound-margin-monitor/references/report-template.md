# 全景监控日报模板 + LLM Prompt

## Markdown 日报模板

```
# A股资金面全景监控日报 — {{trade_date}}

> 扫描时间：{{scan_time}} | 数据覆盖：北向/融资/期货/量价/微观 5 大维度 | 信号检测器：25 个

## 1. 北向资金概览

| 检测器 | 状态 | 强度 | 数据源 | 说明 |
|--------|:----:|:----:|--------|------|
| 净流向趋势 | {{nb_flow_status}} | {{nb_flow_strength}} | {{nb_flow_source}} | {{nb_flow_detail}} |
| 流向趋势 | {{flow_trend_status}} | {{flow_trend_strength}} | {{flow_trend_source}} | {{flow_trend_detail}} |
| 单日异常 | {{anomaly_status}} | {{anomaly_strength}} | {{anomaly_source}} | {{anomaly_detail}} |
| 板块偏好 | {{sector_status}} | {{sector_strength}} | {{sector_source}} | {{sector_detail}} |
| 市场流向 | {{market_flow_status}} | {{market_flow_strength}} | {{market_flow_source}} | {{market_flow_detail}} |
| 累计趋势 | {{cumulative_status}} | {{cumulative_strength}} | {{cumulative_source}} | {{cumulative_detail}} |
| 重仓股变动 | {{heavy_status}} | {{heavy_strength}} | {{heavy_source}} | {{heavy_detail}} |

**数据摘要：** {{nb_summary}}

> ⚠️ 自 2024年8月起，北向资金净买入金额不再披露，系统使用 CSI300 指数变动 + FlowAccumulator 方向累积作为替代。实际数据源见各检测器的「数据源」列。

## 2. 融资融券概览

### 信号表格

| 检测器 | 状态 | 强度 | 数据源 | 说明 |
|--------|:----:|:----:|--------|------|
| 融资余额趋势 | {{margin_balance_status}} | {{margin_balance_strength}} | {{margin_balance_source}} | {{margin_balance_detail}} |
| 融资买入比 | {{buy_ratio_status}} | {{buy_ratio_strength}} | {{buy_ratio_source}} | {{buy_ratio_detail}} |
| 杠杆极端区间 | {{leverage_status}} | {{leverage_strength}} | {{leverage_source}} | {{leverage_detail}} |
| 融券趋势 | {{short_status}} | {{short_strength}} | {{short_source}} | {{short_detail}} |
| 融资融券比 | {{ratio_status}} | {{ratio_strength}} | {{ratio_source}} | {{ratio_detail}} |
| 融资重仓股 | {{heavy_margin_status}} | {{heavy_margin_strength}} | {{heavy_margin_source}} | {{heavy_margin_detail}} |
| 融资类型分布 | {{type_status}} | {{type_strength}} | {{type_source}} | {{type_detail}} |

### 宏观数据

| 指标 | 沪市 | 深市 | 合计 |
|------|------|------|------|
| 融资余额（亿） | {{sh_balance}} | {{sz_balance}} | {{total_balance}} |
| 融资买入额（亿） | {{sh_buy}} | {{sz_buy}} | {{total_buy}} |
| 融券余额（亿） | {{sh_short}} | {{sz_short}} | {{total_short}} |
| 融资买入/成交比 | {{sh_ratio}}% | {{sz_ratio}}% | — |

### 融资重仓股 TOP10

| 排名 | 代码 | 名称 | 融资余额（亿） | 融资买入额（亿） | 行业 |
|:----:|------|------|:------------:|:------------:|------|
{{#each top_margin_stocks}}
| {{rank}} | {{code}} | {{name}} | {{balance}} | {{buy}} | {{industry}} |
{{/each}}

## 3. 股指期货信号

| 检测器 | 状态 | 强度 | 数据源 | 说明 |
|--------|:----:|:----:|--------|------|
| 期货基差 | {{basis_status}} | {{basis_strength}} | 🌐新浪 | IF {{if_basis}}% / IC {{ic_basis}}% / IH {{ih_basis}}% |
| 持仓量趋势 | {{oi_status}} | {{oi_strength}} | 🌐新浪 | IF Δ{{if_oi}}% / IC Δ{{ic_oi}}% / IH Δ{{ih_oi}}% |
| 基差持仓共振 | {{resonance_status}} | {{resonance_strength}} | 🌐新浪 | {{resonance_detail}} |

**各指数摘要：**

| 指数 | 期货 | 现货 | 基差 | 基差率 | 持仓量 | OI 5日Δ |
|------|------|------|------|:-----:|:-----:|:------:|
| CSI300 | {{if_futures}} | {{csi300_spot}} | {{if_basis}} | {{if_basis_rate}}% | {{if_oi}} | {{if_oi_change}}% |
| SSE50 | {{ih_futures}} | {{sse50_spot}} | {{ih_basis}} | {{ih_basis_rate}}% | {{ih_oi}} | {{ih_oi_change}}% |
| CSI500 | {{ic_futures}} | {{csi500_spot}} | {{ic_basis}} | {{ic_basis_rate}}% | {{ic_oi}} | {{ic_oi_change}}% |

## 4. 共振/背离分析

| 模式 | 条件 | 状态 | 信号强度 | 说明 |
|------|------|:----:|:----:|------|
| 偏多共振 | 北向流入 + 融资扩张 | {{bull_resonance}} | {{bull_strength}} | {{bull_detail}} |
| 偏空共振 | 北向流出 + 融资收缩 | {{bear_resonance}} | {{bear_strength}} | {{bear_detail}} |
| 谨慎偏多 | 北向流入 + 融资去杠杆 | {{cautious_bull}} | {{cautious_strength}} | {{cautious_detail}} |
| 背离危险 | 北向流出 + 融资加杠杆 | {{divergence}} | {{divergence_strength}} | {{divergence_detail}} |

## 5. 量价确认

| 检测器 | 状态 | 强度 | 数据源 | 说明 |
|--------|:----:|:----:|--------|------|
| 指数动量 | {{momentum_status}} | {{momentum_strength}} | 🌐东方财富 | 20日收益 {{ret_20d}}%，MA20偏离 {{ma20_deviation}}% |
| 波动率区间 | {{vol_status}} | {{vol_strength}} | 🌐东方财富 | HV(20)={{hv}}%，{{vol_regime}} |

## 6. 微观结构信号

| 检测器 | 状态 | 强度 | 数据源 | 说明 |
|--------|:----:|:----:|--------|------|
| 涨跌比 | {{ad_ratio_status}} | {{ad_ratio_strength}} | 🌐东方财富 | 上涨{{up_n}}/下跌{{down_n}}，比={{ad_ratio}} |
| 指数量能趋势 | {{index_vol_status}} | {{index_vol_strength}} | 🌐新浪 | CSI300 量 {{volume_vs_ma20}}% vs MA20 |
| 成交额趋势 | {{turnover_trend_status}} | {{turnover_trend_strength}} | 全市场 | {{market_turnover}}亿，{{turnover_vs_ma20}}% vs MA20 |
| 涨跌停统计 | {{zt_status}} | {{zt_strength}} | 🌐AK实时 | 涨停{{zt_n}}/跌停{{dt_n}}，比={{zt_dt_ratio}} |
| 主力资金流向 | {{main_flow_status}} | {{main_flow_strength}} | 🌐东方财富 | 主力{{main_direction}}{{main_amount}}亿 |
| 龙虎榜活动 | {{lhb_status}} | {{lhb_strength}} | 🌐东方财富 | 净买入/卖出比={{lhb_ratio}} |
| 新高新低广度 | {{hl_status}} | {{hl_strength}} | 🌐AK实时 | 20日新高{{new_high_20}}/新低{{new_low_20}} |

## 7. 综合情绪评估

```
                       看空 ←─────── 中性 ───────→ 看多
                       0         25        50        75       100
                               ├─────────●─────────┤
                                     {{score}}

综合评分：{{score}}/100（{{grade}}）
```

| 维度 | 原始得分 | 权重 | 加权贡献 | 含衰减信号数 |
|------|:------:|:----:|:------:|:----------:|
| 北向综合 | {{nb_score}} | 35% | {{nb_contrib}} | {{nb_active}}/7 |
| 融资综合 | {{margin_score}} | 35% | {{margin_contrib}} | {{margin_active}}/7 |
| 期货综合 | {{futures_score}} | 17% | {{futures_contrib}} | {{futures_active}}/3 |
| 量价综合 | {{pv_score}} | 8% | {{pv_contrib}} | {{pv_active}}/2 |
| 微观综合 | {{micro_score}} | 5% | {{micro_contrib}} | {{micro_active}}/7 |

- 共振修正：{{resonance_bonus:+.2f}}
- 风险惩罚：{{risk_penalty:-.0f}}
- 最终评分：{{final_score}}/100（{{grade}}）

## 8. 历史对比

| 指标 | 上一交易日 ({{prev_date}}) | 本日 ({{trade_date}}) | 变化 |
|------|:----------:|:--------:|:----:|
| 综合评分 | {{prev_score}} | {{score}} | {{score_change}} |
| 北向综合 | {{prev_nb}} | {{nb_score}} | {{nb_change}} |
| 融资综合 | {{prev_margin}} | {{margin_score}} | {{margin_change}} |
| 期货综合 | {{prev_futures}} | {{futures_score}} | {{futures_change}} |
| 风险评级 | {{prev_risk}}★ | {{risk}}★ | {{risk_change}} |

## 9. AI 宏观研判

> {{llm_analysis}}

（{{llm_source}}：{{llm_model}}，{{llm_tokens}} tokens）

## 10. 板块资金流向

| 行业 | 融资余额（亿） | Z-score | 方向 | 说明 |
|------|:----------:|:-----:|:----:|------|
{{#each industry_flows}}
| {{industry}} | {{balance}} | {{zscore}} | {{direction}} | {{note}} |
{{/each}}

## 11. 综合风险评估

| 风险因子 | 权重 | 原始值 | 风险得分 | 说明 |
|----------|:----:|:----:|:------:|------|
| 看空信号比例 | 35% | {{bearish_pct}}% | {{bearish_score}} | {{bearish_n}}/{{total_n}} 个看空信号 |
| 看空信号强度 | 25% | {{bearish_strength}} | {{strength_score}} | 最大看空强度 {{max_bearish}} |
| 共振背离风险 | 20% | {{resonance_risk}} | {{resonance_score}} | {{resonance_desc}} |
| 融资买入热度 | 20% | {{margin_heat}} | {{heat_score}} | 买入比 {{buy_ratio}}% |

**风险等级：** {{risk_stars}}★ / 5★

**风险信号清单：**
{{#each risk_signals}}
- {{icon}} {{description}}
{{/each}}

## 12. 数据溯源

| 数据类别 | 实际来源 | 状态 | 说明 |
|----------|----------|:----:|------|
| 北向资金汇总 | {{nb_actual_source}} | {{nb_status}} | {{nb_source_note}} |
| 北向流向累积 | FlowAccumulator (cache/nb_flow_history.parquet) | {{flow_acc_status}} | {{flow_acc_days}}日历史 |
| 融资融券个股 | {{margin_detail_source}} | {{margin_detail_status}} | — |
| 融资融券宏观 | AKShare macro_china_market_margin_sh/sz | ✅ | — |
| 股指期货 | AKShare futures_main_sina (新浪) | {{futures_status}} | — |
| 现货指数 | AKShare stock_zh_index_daily (新浪) | ✅ | — |
| 申万行业分类 | {{sw_source}} | {{sw_status}} | 缓存{{sw_cache_age}}天 |
| 涨跌停统计 | AKShare stock_zt_pool_em | {{zt_status}} | best-effort |
| 主力资金流向 | AKShare stock_market_fund_flow | {{main_flow_status_ds}} | best-effort |
| 龙虎榜 | AKShare stock_lhb_detail_em | {{lhb_status_ds}} | best-effort |
| 新高新低 | AKShare stock_a_high_low_statistics | {{hl_status_ds}} | best-effort |
| LLM 研判 | {{llm_provider}} ({{llm_model}}) | {{llm_status}} | {{llm_fallback_note}} |

## 免责声明

本报告仅供研究参考，**不构成任何投资建议**。投资者应独立判断并承担交易风险。过往资金流向和信号模式不代表未来市场表现。

---

*报告由 skill-northbound-margin-monitor v{{version}} 生成于 {{scan_time}}*
```

---

## LLM 宏观研判 Prompt

```
你是一位资深 A 股宏观策略分析师，专精资金面分析和跨资产信号研判。
请基于以下多维度资金面信号，撰写一份 300-500 字的宏观研判。

## 北向资金 (权重 35%)
{nb_summary}
{nb_signals_detail}

## 融资融券 (权重 35%)
{margin_summary}
{margin_signals_detail}

## 股指期货 (权重 17%)
{futures_summary}
{futures_signals_detail}

## 量价确认 (权重 8%)
{pv_summary}

## 微观结构 (权重 5%)
{micro_summary}

## 共振/背离模式
{resonance_summary}

## 综合评分
总分：{score}/100（{grade}） | 风险评级：{risk_stars}★/5★
上一交易日：{prev_score}/100（{prev_grade}） | 变化：{score_change:+.1f}

## 要求
1. **定性判断**：当前市场处于什么阶段？（增量驱动/存量博弈/避险模式/分歧加大）
2. **核心驱动**：哪类资金是当前市场的主要矛盾？（北向/融资/期货/散户）
3. **验证逻辑**：多维度信号之间是否相互印证？是否有矛盾点？
4. **风险提示**：当前最大的尾部风险是什么？（杠杆过热/外资撤离/基差异常/广度恶化）
5. **观察要点**：未来 1-3 个交易日最值得关注的指标或阈值。
6. 用「情绪偏暖」「信号偏多」「值得关注」等措辞，**禁止**使用「推荐买入」「加仓」「目标点位」等投资建议表述。
```

### 占位符说明

| 占位符 | 来源 | 说明 |
|--------|------|------|
| `{nb_summary}` | Northbound scorer | 北向维度摘要文字 |
| `{nb_signals_detail}` | 7 northbound detectors | 各信号详情（含数据源标签） |
| `{margin_summary}` | Margin scorer | 融资维度摘要文字 |
| `{margin_signals_detail}` | 7 margin detectors | 各信号详情 |
| `{futures_summary}` | Futures scorer | 期货维度摘要文字 |
| `{futures_signals_detail}` | 3 futures detectors | 各信号详情 |
| `{pv_summary}` | PriceVolume scorer | 量价维度摘要 |
| `{micro_summary}` | Microstructure scorer | 微观结构摘要 |
| `{resonance_summary}` | Resonance analyzer | 4 模式触发状态 |
| `{score}` | Scorer.get_final_score() | 综合评分 0-100 |
| `{grade}` | Scorer.get_grade() | A+ ~ F- |
| `{risk_stars}` | RiskRater.get_stars() | ★1-5 |
| `{prev_score}` | 历史报告 JSON | 上日评分 |
| `{prev_grade}` | 历史报告 JSON | 上日等级 |
| `{score_change}` | 计算 | 评分变动 |

---

## 规则备选分析 (Fallback)

当 LLM 不可用时（无 API Key 或 API 调用全部失败），`LLMAnalyst._fallback_analysis()` 基于规则生成研判：

- **评分 > 75**：多维度信号共振看多，市场情绪偏暖
- **评分 55-74**：信号温和偏多但存在结构性矛盾，建议关注资金切换方向
- **评分 45-54**：多空交织，无明显方向，等待增量信号
- **评分 25-44**：偏空信号增多，注意风险控制
- **评分 < 25**：多维度看空共振，市场情绪偏冷
- **北向+融资同向**：资金面共识度较高
- **北向+融资背离**：内外资分歧加大，短线波动可能加剧
- **基差大幅贴水 + OI上升**：对冲需求增加，谨慎信号
- **融资买入比 > 12%**：杠杆情绪偏高，注意回调风险
- **涨跌停比极端**：市场情绪极端化，反转概率增加
