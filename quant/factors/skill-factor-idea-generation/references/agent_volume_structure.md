# AgentVolumeStructure Prompt Catalog

`AgentVolumeStructure` 属于 Level III: Price-Volume Dynamics。本文件用于生成成交活动形态、集中度和参与节奏相关的初始因子想法。

## Agent 职责

VolumeStructure 要回答的核心问题是：

> 成交量在历史窗口内是稳定积累、异常爆发，还是由少数极端日主导？

## Agent 核心指令

```text
你是专注日频成交量结构、参与节奏和成交聚集的量化研究员。
请提出连续、可计算、可解释的初始因子假设，用成交量集中度、burst、短长量能比和持续性描述参与结构。
不要只输出普通成交量均线或 volume z-score。
```

## Prompt Lenses

### VS01: Volume Concentration

```yaml
lens_id: volume_structure.volume_concentration
layer: price_volume_dynamics
agent: volume_structure
title: Volume Concentration
title_zh: 成交集中度
research_question: 近期成交量是否由少数异常日主导？
mechanism: 成交集中度高说明参与并不稳定，价格信号可能受单点冲击影响更大。
construction_space:
  inputs: [volume]
  transforms: [volume_share, top_day_concentration, rolling_concentration, entropy_proxy]
  relations: [concentrated_participation, diffuse_participation]
degenerate_patterns:
  - 只计算成交量均值
  - 不区分稳定高成交和少数爆发日
  - 使用复杂不可解释熵公式
allowed_roles: [primary, stabilizer]
preferred_output:
  continuous: true
  bounded: optional
```

```text
衡量窗口内成交量是否集中在少数异常日，区分稳定参与和脉冲式参与。因子应保持可解释和可实现。
```

### VS02: Volume Burstiness

```yaml
lens_id: volume_structure.volume_burstiness
layer: price_volume_dynamics
agent: volume_structure
title: Volume Burstiness
title_zh: 成交爆发性
research_question: 成交活动是否出现短期爆发，并可能改变价格行为？
mechanism: 成交 burst 表示参与突然集中，可能对应信息冲击、拥挤交易或压力释放。
construction_space:
  inputs: [volume, close]
  transforms: [volume_spike, burst_duration, burst_decay, price_response_to_burst]
  relations: [participation_burst, burst_with_price_progress]
degenerate_patterns:
  - 只输出成交量 z-score
  - 不衡量 burst 持续或衰减
  - 不结合价格响应
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
研究成交量是否突然爆发、持续或衰减，并结合价格响应判断 burst 的含义。不要只生成普通成交量异常值。
```

### VS03: Multi-Horizon Volume Energy

```yaml
lens_id: volume_structure.multi_horizon_volume_energy
layer: price_volume_dynamics
agent: volume_structure
title: Multi-Horizon Volume Energy
title_zh: 多周期量能
research_question: 短期成交能量相对中长期成交能量是否发生转移？
mechanism: 量能从长周期稳定参与转向短周期爆发，可能表示市场关注和交易节奏正在变化。
construction_space:
  inputs: [volume]
  transforms: [short_long_volume_ratio, volume_energy, volume_trend, participation_shift]
  relations: [short_volume_dominance, long_volume_dominance]
degenerate_patterns:
  - 只做短长成交均线差
  - 不解释量能转移方向
  - 忽略异常成交日影响
allowed_roles: [primary, modifier]
preferred_output:
  continuous: true
  scale_normalized: true
```

```text
构造短期与中长期成交能量的相对关系，刻画参与节奏是否正在向短周期或长周期转移。不要退化为普通成交均线交叉。
```

### VS04: Participation Persistence

```yaml
lens_id: volume_structure.participation_persistence
layer: price_volume_dynamics
agent: volume_structure
title: Participation Persistence
title_zh: 参与持续性
research_question: 成交活跃是连续维持，还是仅由短暂脉冲驱动？
mechanism: 稳定持续的参与和单日成交爆发代表不同的信息扩散与交易结构。
construction_space:
  inputs: [volume]
  transforms: [volume_baseline, active_day_share, run_length_proxy, persistence_decay]
  relations: [broad_persistent_participation, transient_activity]
degenerate_patterns: [只用成交量均线, 与 volume_burstiness 仅符号相反, 用离散连续天数标签]
allowed_roles: [primary, confirmation, stabilizer]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
从活跃成交日占比、持续程度和衰减速度区分广泛持续参与与单点爆发。输出连续参与持续分数，不只统计连续放量天数。
```

### VS05: Expansion-Contraction Asymmetry

```yaml
lens_id: volume_structure.expansion_contraction_asymmetry
layer: price_volume_dynamics
agent: volume_structure
title: Expansion-Contraction Asymmetry
title_zh: 量能扩缩不对称
research_question: 成交量扩张和收缩的速度是否不对称，暗示参与进入和退出节奏不同？
mechanism: 参与快速涌入、缓慢退出与缓慢积累、快速消失对应不同的注意力和拥挤过程。
construction_space:
  inputs: [volume]
  transforms: [positive_volume_change, negative_volume_change, expansion_speed, contraction_speed]
  relations: [fast_in_slow_out, slow_in_fast_out]
degenerate_patterns: [只算成交量变化率, 不分扩张和收缩路径, 用单日异常替代历史节奏]
allowed_roles: [primary, modifier, confirmation]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
分别估计历史成交量扩张与收缩的幅度、速度和持续性，构造参与进入退出的不对称分数。不要退化为普通 volume momentum。
```

### VS06: Volume Rhythm Regularity

```yaml
lens_id: volume_structure.volume_rhythm_regularity
layer: price_volume_dynamics
agent: volume_structure
title: Volume Rhythm Regularity
title_zh: 成交节奏规则性
research_question: 成交活动的起伏是否呈现稳定节奏，还是处于无序跳变状态？
mechanism: 稳定的参与起伏可能反映持续信息扩散，无序爆发则更可能由偶发冲击主导。
construction_space:
  inputs: [volume]
  transforms: [volume_change, lag_consistency, local_variation, rhythm_stability]
  relations: [regular_participation_rhythm, erratic_activity]
degenerate_patterns: [盲目寻找周期频率, 使用复杂频谱拟合, 与成交持续性只换名称]
allowed_roles: [primary, stabilizer, confirmation]
preferred_output:
  continuous: true
  numerically_stable: true
```

```text
用少量历史滞后的一致性和局部变化稳定度描述成交节奏规则性。重点是活动变化的节奏，不是成交水平是否持续偏高。
```

## 输出检查

- 明确记录 `agent_tags: [volume_structure]`。
- 关注成交结构和参与节奏，不只看成交量水平。
- 不把成交量结构直接等同于单向收益预测。
