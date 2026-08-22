# AgentTailRisk Prompt Catalog

`AgentTailRisk` 属于 Level II: Extreme Risk & Fragility。本文件用于生成尾部风险相关的初始因子想法，不直接声称因子有效。

## 来源边界

- 论文定义：量化下行敏感性和尾部事件暴露，刻画负面冲击如何随时间传播。
- Appendix C.1 没有给出该 Agent 的逐字 Prompt；下面的 Lens 是对论文描述和当前工程 prompt 的研究化拆分。
- TailRisk 关注已经可由历史路径观察到的尾部暴露和冲击传播，不使用未来崩盘结果做标签。

## Agent 职责

TailRisk 要回答的核心问题是：

> 当前历史路径是否暴露出更强的下行尾部风险、负冲击传播或左尾不对称？

它应输出连续的 downside exposure、tail pressure 或 shock propagation score，而不是“是否会崩盘”的标签。

## 与相邻 Agent 的边界

| 内容 | 归属 |
|---|---|
| 下行半方差、负收益集中、左尾暴露 | `TailRisk` |
| 崩盘前压力累积、脆弱平静、流动性枯竭 | `CrashPredictor` |
| 当前波动状态高低与持续性 | `VolatilityRegime` |
| 回撤深度、恢复路径和持续时间 | `Drawdown` |
| 短期过度反应后的修正 | `Reversal` |

TailRisk 可以观察极端负收益，但重点是“尾部暴露的连续强度”，不是直接预测或标记未来 crash。

## Agent 核心指令

当 Skill 选中 `tail_risk` tag 时，将下面的核心指令与一张或两张 Lens 组合：

```text
你是专注日频 OHLCV 下行尾部风险的量化研究员。
请提出连续、可计算、可解释的初始因子假设，用历史负收益、下行半方差、左尾集中度、负冲击传播或上下行不对称表征 tail exposure。
不要生成未来崩盘标签，不要只写简单 drawdown flag 或极端收益二值标记。
只使用用户允许的当前及历史字段，不使用未来信息。
```

## Prompt Lenses

### TR01: Downside Semivariance Concentration

```yaml
lens_id: tail_risk.downside_semivariance_concentration
layer: extreme_risk_fragility
agent: tail_risk
title: Downside Semivariance Concentration
title_zh: 下行半方差集中
research_question: 近期波动是否主要由负收益贡献，从而形成左尾风险集中？
mechanism: >
  同样的总波动下，如果波动主要来自负收益，说明价格路径承受更强下行压力。
  下行半方差相对总方差的集中度可作为尾部风险暴露代理。
construction_space:
  inputs: [close, returns]
  transforms:
    - negative_return_clip
    - downside_semivariance
    - total_variance
    - concentration_ratio
    - rolling_rank
  relations:
    - downside_vs_total_volatility
    - negative_variance_share
degenerate_patterns:
  - 只计算普通历史波动率
  - 只计算 N 日收益并取负
  - 用单日大跌替代下行风险集中
allowed_roles: [primary, modifier]
preferred_output:
  continuous: true
  downside_interpretable: true
```

```text
从历史负收益对总波动的贡献出发，构造下行半方差集中度或负向波动占比。因子应刻画左尾暴露强度，而不是普通波动率或单日大跌标签。
```

### TR02: Negative Shock Propagation

```yaml
lens_id: tail_risk.negative_shock_propagation
layer: extreme_risk_fragility
agent: tail_risk
title: Negative Shock Propagation
title_zh: 负冲击传播
research_question: 历史负冲击是否在后续路径中延续、衰减或扩散？
mechanism: >
  负面冲击如果持续传播，说明卖压或风险重新定价尚未结束；若快速衰减，则可能代表
  尾部压力释放。传播路径比单点冲击更能描述当前尾部风险状态。
construction_space:
  inputs: [close, high, low, returns, volume]
  transforms:
    - lagged_negative_return
    - decayed_shock_sum
    - shock_persistence
    - post_shock_range_response
    - post_shock_volume_response
  relations:
    - shock_decay
    - shock_contagion_within_path
    - delayed_downside_pressure
degenerate_patterns:
  - 使用未来收益判断冲击传播
  - 只把最近一天负收益当作传播
  - 把所有负 momentum 都称为尾部风险
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
研究历史负收益冲击在后续若干历史日中的延续、衰减或扩散，将其表达为负冲击传播强度。因子必须只使用当前及过去数据，不得用未来回报确认冲击是否继续。
```

### TR03: Left-Tail Asymmetry

```yaml
lens_id: tail_risk.left_tail_asymmetry
layer: extreme_risk_fragility
agent: tail_risk
title: Left-Tail Asymmetry
title_zh: 左尾不对称
research_question: 下跌日的收益、range 或成交响应是否显著强于上涨日？
mechanism: >
  左尾不对称表明坏消息或卖压带来的路径破坏更强。相比普通波动，该机制强调
  上下行响应不对称，适合刻画偏斜风险。
construction_space:
  inputs: [close, high, low, returns, volume]
  transforms:
    - downside_volatility
    - upside_volatility
    - down_day_range
    - up_day_range
    - volume_on_down_days
    - asymmetry_ratio
  relations:
    - downside_vs_upside_response
    - left_tail_skew_proxy
degenerate_patterns:
  - 只输出负收益均值
  - 不区分上下行波动来源
  - 用硬涨跌标签输出离散信号
allowed_roles: [primary, modifier, confirmation]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
比较历史上涨日和下跌日的收益波动、range 或成交响应差异，构造连续的左尾不对称分数。重点是坏消息路径是否更剧烈，而不是简单看近期是否下跌。
```

### TR04: Tail Event Memory

```yaml
lens_id: tail_risk.tail_event_memory
layer: extreme_risk_fragility
agent: tail_risk
title: Tail Event Memory
title_zh: 尾部事件记忆
research_question: 近期尾部冲击是否仍在历史窗口中留下可量化记忆？
mechanism: >
  极端冲击后的风险影响可能不会立即消失。带衰减权重的尾部事件记忆可以衡量
  当前路径是否仍处在尾部压力阴影中。
construction_space:
  inputs: [close, high, low, returns]
  transforms:
    - extreme_negative_return_score
    - exponential_decay
    - tail_event_count
    - time_since_tail_event
    - decayed_tail_pressure
  relations:
    - recent_tail_memory
    - tail_pressure_decay
degenerate_patterns:
  - 只统计固定阈值下跌次数
  - 使用未来恢复情况定义记忆是否消失
  - 把时间越近简单等同于风险越高而无强度刻画
allowed_roles: [primary, stabilizer, confirmation]
preferred_output:
  continuous: true
  bounded: optional
```

```text
构造历史极端负收益或异常下行 range 的衰减记忆分数，衡量尾部冲击对当前状态的残留影响。因子应同时考虑冲击强度和距离当前的时间衰减。
```

### TR05: Downside Absorption Failure

```yaml
lens_id: tail_risk.downside_absorption_failure
layer: extreme_risk_fragility
agent: tail_risk
title: Downside Absorption Failure
title_zh: 下行承接失败
research_question: 下跌伴随放量或大 range 时，价格是否缺少承接迹象，从而暴露尾部压力？
mechanism: >
  如果负收益、放量和弱收盘位置同时出现，说明下行冲击可能没有被有效吸收。
  这类承接失败可作为尾部压力继续扩散的代理。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms:
    - close_location_value
    - signed_body
    - volume_shock
    - downside_range_pressure
    - absorption_score
  relations:
    - down_move_with_weak_close
    - volume_confirmed_downside_pressure
degenerate_patterns:
  - 只把放量下跌视作尾部风险
  - 不考虑收盘位置或 range 结构
  - 声称使用订单簿或真实买卖盘数据
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  bounded: optional
```

```text
结合下跌方向、日内收盘位置、range 和成交量冲击，衡量下行压力是否被有效承接。因子应使用 OHLCV 代理表达承接失败，不得声称拥有真实订单簿信息。
```

## 同 Agent 内组合

默认只使用一张 Lens。如果使用两张，必须明确一个为主机制，另一个只做确认、稳定或强度调节。

优先考虑：

- `downside_semivariance_concentration` + `left_tail_asymmetry`：用上下行不对称确认下行半方差集中。
- `negative_shock_propagation` + `tail_event_memory`：用尾部事件记忆刻画负冲击传播。
- `downside_absorption_failure` + `negative_shock_propagation`：用承接失败确认负冲击是否延续。

应避免：

- 把所有近期下跌都写成 tail risk。
- 用未来崩盘结果定义当前尾部暴露。
- 同时塞入回撤、崩盘、反转、流动性等多个主机制。

## 输出检查

TailRisk 候选至少应满足：

- 明确记录 `agent_tags: [tail_risk]` 和实际使用的 `prompt_lens_ids`。
- 输出是连续 downside exposure、tail pressure 或 shock propagation score。
- 只使用用户允许的当前和历史字段。
- 不把尾部风险写成未来 crash 标签。
- 明确说明与 `CrashPredictor` 的差别。
