# AgentLiquidity Prompt Catalog

`AgentLiquidity` 属于 Level III: Price-Volume Dynamics。本文件用于生成流动性、价格冲击和交易摩擦相关的初始因子想法。

## Agent 职责

Liquidity 要回答的核心问题是：

> 当前价格变化是否是在高流动性下顺畅完成，还是在低流动性/高冲击成本下脆弱完成？

只能使用 OHLCV 代理，不得声称拥有订单簿深度、真实买卖盘或成交明细。

## Agent 核心指令

```text
你是专注日频 OHLCV 流动性代理、价格冲击和交易摩擦的量化研究员。
请提出连续、可计算、可解释的初始因子假设，用历史成交量、range、收益和收盘位置推断流动性压力。
不要使用真实订单簿、盘口深度或未提供的换手率字段。
```

## Prompt Lenses

### LQ01: Price Impact Per Volume

```yaml
lens_id: liquidity.price_impact_per_volume
layer: price_volume_dynamics
agent: liquidity
title: Price Impact Per Volume
title_zh: 单位成交价格冲击
research_question: 单位成交量对应的价格移动是否异常偏大，暗示交易摩擦上升？
mechanism: 成交量不足或市场深度变浅时，同样交易规模可能引发更大价格冲击。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [abs_return, range_per_volume, volume_scaled_move, robust_ratio]
  relations: [impact_under_volume, fragile_price_move]
degenerate_patterns:
  - 只输出成交量倒数
  - 不处理 volume 为零或极小值
  - 声称使用订单簿深度
allowed_roles: [primary, modifier]
preferred_output:
  continuous: true
  numerically_stable: true
```

```text
从单位成交量对应的收益或 high-low range 出发，构造价格冲击强度。因子必须处理成交量极小值和除零风险，并明确它只是 OHLCV 流动性代理。
```

### LQ02: Liquidity Dry-Up

```yaml
lens_id: liquidity.liquidity_dry_up
layer: price_volume_dynamics
agent: liquidity
title: Liquidity Dry-Up
title_zh: 流动性枯竭
research_question: 成交量持续低于自身历史水平时，价格路径是否更脆弱？
mechanism: 参与度下降可能降低冲击吸收能力，使后续价格更容易受小冲击影响。
construction_space:
  inputs: [volume, close, high, low]
  transforms: [volume_zscore, volume_rank, low_participation_duration, range_under_low_volume]
  relations: [dry_up_with_range_pressure, quiet_liquidity_risk]
degenerate_patterns:
  - 只计算成交量均线
  - 把低成交量直接解释为看涨或看跌
  - 忽略价格状态
allowed_roles: [primary, gate, confirmation]
preferred_output:
  continuous: true
  bounded: optional
```

```text
研究成交参与度是否持续下降，并结合价格 range 或收益变化判断低流动性环境下的脆弱性。不要把低成交量本身写成单向 alpha。
```

### LQ03: High-Volume Inefficiency

```yaml
lens_id: liquidity.high_volume_inefficiency
layer: price_volume_dynamics
agent: liquidity
title: High-Volume Inefficiency
title_zh: 高成交低效率
research_question: 高成交量下价格推进不足，是否代表分歧、吸收或摩擦上升？
mechanism: 若大量成交无法推动价格延续，可能意味着买卖双方分歧增强或流动性被消耗。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [volume_shock, body_efficiency, close_location_value, range_normalization]
  relations: [high_volume_low_progress, absorption_or_disagreement]
degenerate_patterns:
  - 只用放量信号
  - 不衡量价格是否有效推进
  - 把吸收和趋势确认混为一谈
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
衡量成交量异常放大时，实体、收盘位置或净价格推进是否不足。因子应刻画成交活跃但价格效率低下的状态，而不是普通放量因子。
```

### LQ04: Liquidity Recovery Resilience

```yaml
lens_id: liquidity.liquidity_recovery_resilience
layer: price_volume_dynamics
agent: liquidity
title: Liquidity Recovery Resilience
title_zh: 流动性恢复韧性
research_question: 价格冲击后，单位成交量冲击是否快速回落，表明流动性吸收能力恢复？
mechanism: 同等方向冲击发生后，价格冲击率逐步下降可能表示交易对手重新进入、市场吸收能力修复。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [impact_decay, post_shock_half_life, rolling_recovery_slope, robust_scaling]
  relations: [impact_shock_to_recovery, resilient_vs_persistent_illiquidity]
degenerate_patterns: [只比较冲击前后成交量, 用未来窗口确认恢复, 把价格反转直接等同于流动性恢复]
allowed_roles: [primary, confirmation, stabilizer]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
从历史价格冲击之后单位成交量价格影响的衰减路径出发，刻画流动性吸收能力恢复的速度和完整度。恢复必须由已发生的历史路径定义，不得使用未来确认。
```

### LQ05: Marginal Volume Elasticity

```yaml
lens_id: liquidity.marginal_volume_elasticity
layer: price_volume_dynamics
agent: liquidity
title: Marginal Volume Elasticity
title_zh: 边际成交弹性
research_question: 成交活动增加时，价格推进效率是改善还是恶化？
mechanism: 成交增加带来的边际价格推进可区分健康的流动性供给与高摩擦下的无效成交。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [delta_volume, delta_price_efficiency, rolling_covariance, elasticity_proxy]
  relations: [volume_added_to_progress, volume_added_to_friction]
degenerate_patterns: [只做收益除成交量, 把相关系数当作因果弹性, 不控制价格和成交量尺度]
allowed_roles: [primary, modifier, confirmation]
preferred_output:
  continuous: true
  scale_normalized: true
```

```text
研究历史窗口内成交活动的边际变化与价格推进效率变化之间的关系，构造稳定的弹性代理。重点区分新增成交促进价格发现，还是只增加摩擦和分歧。
```

## 输出检查

- 明确记录 `agent_tags: [liquidity]` 和实际 `prompt_lens_ids`。
- 只使用 OHLCV 代理，不声称拥有订单簿或真实成交方向。
- 对成交量极小值做数值稳定处理。
