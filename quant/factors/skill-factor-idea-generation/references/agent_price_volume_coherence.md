# AgentPriceVolumeCoherence Prompt Catalog

`AgentPriceVolumeCoherence` 属于 Level III: Price-Volume Dynamics。本文件用于生成价格与成交量同步、背离和能量一致性相关的初始因子想法。

## Agent 职责

PriceVolumeCoherence 要回答的核心问题是：

> 价格变化是否得到成交活动支持，还是出现价量脱钩或背离？

## Agent 核心指令

```text
你是专注日频价格-成交量同步和背离的量化研究员。
请提出连续、可计算、可解释的初始因子假设，用收益、成交量变化、成交量冲击和方向一致性构造 coherence 或 divergence score。
不要只输出普通成交量确认规则。
```

## Prompt Lenses

### PVC01: Price-Volume Synchronization

```yaml
lens_id: price_volume_coherence.price_volume_synchronization
layer: price_volume_dynamics
agent: price_volume_coherence
title: Price-Volume Synchronization
title_zh: 价量同步
research_question: 价格方向与成交量变化是否在历史窗口中同步增强？
mechanism: 价格移动若伴随成交活跃，可能说明信息被更广泛参与者确认。
construction_space:
  inputs: [close, volume]
  transforms: [return_direction, volume_change, rolling_correlation, agreement_score]
  relations: [volume_confirms_price, coherent_move]
degenerate_patterns:
  - 只算相关系数但不解释方向
  - 把所有放量上涨都视作有效
  - 不区分上涨同步和下跌同步
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
研究收益方向、收益幅度和成交量变化是否在历史窗口中同步，输出连续的价量一致性分数。不要退化为单日放量确认。
```

### PVC02: Price-Volume Divergence

```yaml
lens_id: price_volume_coherence.price_volume_divergence
layer: price_volume_dynamics
agent: price_volume_coherence
title: Price-Volume Divergence
title_zh: 价量背离
research_question: 价格推进和成交量支持是否出现背离，暗示趋势脆弱或吸收？
mechanism: 价强量弱可能表示上行动能不足，价弱量强可能表示卖压释放或分歧加大。
construction_space:
  inputs: [close, volume]
  transforms: [return_strength, volume_shock, normalized_mismatch, divergence_score]
  relations: [price_up_volume_weak, price_down_volume_strong]
degenerate_patterns:
  - 只比较价格和成交量涨跌
  - 不说明背离方向的经济含义
  - 同时把背离解释成趋势和反转而无条件
allowed_roles: [primary, contrast]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
构造价格变化强度与成交量变化强度之间的归一化不匹配分数，区分价强量弱、价弱量强等不同背离方向。
```

### PVC03: Volume Exhaustion

```yaml
lens_id: price_volume_coherence.volume_exhaustion
layer: price_volume_dynamics
agent: price_volume_coherence
title: Volume Exhaustion
title_zh: 量能衰竭
research_question: 价格冲击后成交量快速衰减，是否代表边际买卖压力释放？
mechanism: 极端放量后的量能回落可能表示主动压力释放，也可能代表参与意愿枯竭，需要结合价格路径解释。
construction_space:
  inputs: [close, volume]
  transforms: [volume_spike, volume_decay, post_shock_return, pressure_release_score]
  relations: [selling_pressure_decay, buying_pressure_decay]
degenerate_patterns:
  - 只用成交量下降
  - 不结合前期价格冲击方向
  - 把缩量直接当作看涨或看跌
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
研究价格冲击和成交量冲击之后，量能是否快速衰减，并据此刻画边际压力是否释放。因子必须结合冲击方向和量能衰减路径。
```

### PVC04: Coherence Stability

```yaml
lens_id: price_volume_coherence.coherence_stability
layer: price_volume_dynamics
agent: price_volume_coherence
title: Coherence Stability
title_zh: 价量关系稳定性
research_question: 价量关系是稳定持续，还是在短期内频繁翻转？
mechanism: 同样的当前价量同步水平，如果历史关系稳定，其经济含义通常比频繁翻转的关系更可信。
construction_space:
  inputs: [close, volume]
  transforms: [rolling_coherence, sign_persistence, coherence_dispersion, reliability_weight]
  relations: [stable_confirmation, unstable_price_volume_link]
degenerate_patterns: [只计算一个相关系数, 与 signal_persistence 完全重复, 忽略价量方向含义]
allowed_roles: [primary, confirmation, stabilizer]
preferred_output:
  continuous: true
  bounded: optional
```

```text
先构造有方向含义的价量一致性，再衡量该关系在历史窗口中的稳定度或翻转频率。输出当前一致性及其可信度，而不是孤立相关系数。
```

### PVC05: Marginal Volume Confirmation

```yaml
lens_id: price_volume_coherence.marginal_volume_confirmation
layer: price_volume_dynamics
agent: price_volume_coherence
title: Marginal Volume Confirmation
title_zh: 边际量能确认
research_question: 新增成交活动是否仍能带来同方向的边际价格推进？
mechanism: 趋势成熟后，成交继续增加但边际价格响应下降，可能表示确认效力衰减或吸收增强。
construction_space:
  inputs: [close, volume]
  transforms: [incremental_volume, directional_progress, rolling_efficiency, confirmation_decay]
  relations: [volume_supports_progress, confirmation_saturation]
degenerate_patterns: [只看放量上涨, 与单位成交冲击完全相同, 不区分确认增强和确认衰减]
allowed_roles: [primary, confirmation, modifier]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
刻画成交量增加带来的同向价格边际响应，并识别确认效力是增强、稳定还是饱和。不要只使用成交量水平乘收益。
```

### PVC06: Directional Efficiency Mismatch

```yaml
lens_id: price_volume_coherence.directional_efficiency_mismatch
layer: price_volume_dynamics
agent: price_volume_coherence
title: Directional Efficiency Mismatch
title_zh: 方向效率错配
research_question: 成交方向持续一致但价格路径效率下降时，是否意味着价量关系正在失效？
mechanism: 参与压力延续而净价格推进变得曲折，可能表示交易共识尚在但价格承接结构已改变。
construction_space:
  inputs: [open, close, volume]
  transforms: [signed_volume_persistence, path_efficiency, normalized_mismatch, mismatch_change]
  relations: [persistent_participation_weak_progress, efficient_price_volume_alignment]
degenerate_patterns: [与高成交低效率完全相同, 只做成交量乘路径效率, 不区分方向持续和成交水平]
allowed_roles: [primary, confirmation, contrast]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
比较方向性成交参与的持续程度与同期带方向路径效率，构造价量方向效率错配。重点是跨日结构变化，不是单日高成交低实体。
```

## 输出检查

- 明确记录 `agent_tags: [price_volume_coherence]`。
- 说明价量同步或背离的方向含义。
- 不只输出普通相关系数或成交量均线。
