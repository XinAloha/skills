# AgentDailyTrend Prompt Catalog

`AgentDailyTrend` 属于 Level IV: Price-Volatility Behavior。本文件用于生成日频方向持续和趋势强度相关的初始因子想法。

## Agent 核心指令

```text
你是专注日频趋势持续、多日动量和方向强度的量化研究员。
请提出连续、可计算、可解释的初始因子假设，用历史收益、斜率、方向一致性和波动调整后的趋势强度刻画可持续价格运动。
不要只输出普通 N 日收益率。
```

## Prompt Lenses

### DT01: Directional Persistence

```yaml
lens_id: daily_trend.directional_persistence
layer: price_volatility_behavior
agent: daily_trend
title: Directional Persistence
title_zh: 方向持续性
research_question: 多日收益方向是否持续一致，而非由单日跳变驱动？
mechanism: 趋势信号若来自连续小幅同向推进，可能比单日大涨跌更稳定。
construction_space:
  inputs: [close]
  transforms: [return_sign, sign_consistency, rolling_return, persistence_score]
  relations: [steady_direction, jump_vs_drift]
degenerate_patterns: [只输出 N 日收益率, 不区分连续漂移和单日跳变, 使用未来方向确认趋势]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
```

```text
从历史收益方向一致性和多日累计收益出发，构造趋势持续分数。重点区分连续漂移和单日跳变。
```

### DT02: Volatility-Adjusted Trend

```yaml
lens_id: daily_trend.volatility_adjusted_trend
layer: price_volatility_behavior
agent: daily_trend
title: Volatility-Adjusted Trend
title_zh: 波动调整趋势
research_question: 趋势强度在扣除路径噪声后是否仍然显著？
mechanism: 同样收益幅度下，低噪声趋势通常比高波动路径更可信。
construction_space:
  inputs: [close, high, low]
  transforms: [rolling_return, realized_volatility, range_noise, signal_to_noise_ratio]
  relations: [trend_strength_vs_noise]
degenerate_patterns: [只做收益除以波动但不解释, 不处理除零, 混入反转逻辑]
allowed_roles: [primary, modifier]
preferred_output:
  continuous: true
  scale_normalized: true
```

```text
用历史收益除以波动或路径噪声，构造波动调整后的趋势强度。因子应表达趋势质量，而不是单纯收益幅度。
```

### DT03: Slope Consistency

```yaml
lens_id: daily_trend.slope_consistency
layer: price_volatility_behavior
agent: daily_trend
title: Slope Consistency
title_zh: 斜率一致性
research_question: 平滑价格或收益轨迹的斜率是否稳定延续？
mechanism: 稳定斜率代表趋势形态更顺滑，可能减少噪声造成的伪动量。
construction_space:
  inputs: [close]
  transforms: [rolling_slope, ema_slope, slope_stability, slope_change]
  relations: [stable_slope_trend, weakening_slope]
degenerate_patterns: [只做均线差, 不衡量斜率稳定性, 用未来点拟合斜率]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
```

```text
从平滑价格轨迹或累计收益的历史斜率出发，衡量趋势推进是否稳定。不要退化为简单均线交叉。
```

### DT04: Path Efficiency

```yaml
lens_id: daily_trend.path_efficiency
layer: price_volatility_behavior
agent: daily_trend
title: Path Efficiency
title_zh: 趋势路径效率
research_question: 价格净位移相对于累计路径长度是否足够高，表明趋势推进有效？
mechanism: 相同累计收益可来自顺滑单向推进或高频往返，净位移占路径长度越高，趋势结构越完整。
construction_space:
  inputs: [close]
  transforms: [net_displacement, absolute_return_path, efficiency_ratio, signed_efficiency]
  relations: [smooth_directional_progress, noisy_round_trip]
degenerate_patterns: [只输出累计收益, 不保留方向, 分母为零不处理]
allowed_roles: [primary, confirmation, gate]
preferred_output:
  continuous: true
  bounded: true
```

```text
比较历史窗口内价格净位移与逐日绝对移动总和，构造带方向的趋势路径效率。因子应区分高效单向推进和高噪声往返。
```

### DT05: Trend Acceleration Decay

```yaml
lens_id: daily_trend.trend_acceleration_decay
layer: price_volatility_behavior
agent: daily_trend
title: Trend Acceleration and Decay
title_zh: 趋势加速与衰减
research_question: 趋势斜率正在加速、稳定还是衰减，其变化是否比静态动量更有信息？
mechanism: 趋势水平相同但斜率变化不同，可能分别对应趋势启动、成熟和衰竭阶段。
construction_space:
  inputs: [close]
  transforms: [rolling_slope, slope_change, momentum_difference, acceleration_score]
  relations: [trend_acceleration, trend_deceleration]
degenerate_patterns: [只做短期收益减长期收益, 把二阶差分噪声直接当信号, 不结合趋势方向]
allowed_roles: [primary, modifier, confirmation]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
在历史趋势方向基础上衡量斜率或动量的变化速度，区分同向加速、同向衰减和反向转折。对二阶变化做稳健平滑，避免噪声放大。
```

### DT06: Trend Contribution Concentration

```yaml
lens_id: daily_trend.trend_contribution_concentration
layer: price_volatility_behavior
agent: daily_trend
title: Trend Contribution Concentration
title_zh: 趋势贡献集中度
research_question: 多日趋势是否主要由极少数交易日贡献？
mechanism: 相同累计收益若由少数跳变驱动，其延续逻辑与多数交易日稳定漂移不同。
construction_space:
  inputs: [close]
  transforms: [signed_return_contribution, top_contribution_share, concentration_penalty, drift_share]
  relations: [distributed_trend_evidence, jump_dominated_trend]
degenerate_patterns: [与方向持续性完全重复, 只删除最大收益日, 使用未来窗口判断贡献]
allowed_roles: [primary, stabilizer, confirmation]
preferred_output:
  continuous: true
  bounded: optional
```

```text
衡量历史累计趋势由多少交易日共同贡献，并区分广泛漂移和少数跳变主导。不要只统计同号天数，也不要机械删除极端日。
```

## 输出检查

- 明确记录 `agent_tags: [daily_trend]`。
- 不只输出普通 N 日收益或均线交叉。
- 所有 rolling 和 shift 只使用当前及历史数据。
