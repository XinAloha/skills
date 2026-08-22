# AgentDrawdown Prompt Catalog

`AgentDrawdown` 属于 Level V: Multi-Scale Complexity。本文件用于生成回撤深度、持续时间和恢复路径相关的初始因子想法。

## Agent 核心指令

```text
你是专注历史回撤路径、恢复速度和价格韧性的量化研究员。
请提出连续、可计算、可解释的初始因子假设，用 rolling peak、当前回撤、回撤持续 proxy 和恢复斜率描述路径韧性。
不要使用未来恢复结果。
```

## Prompt Lenses

### DD01: Drawdown Depth

```yaml
lens_id: drawdown.drawdown_depth
layer: multiscale_complexity
agent: drawdown
title: Drawdown Depth
title_zh: 回撤深度
research_question: 当前价格相对历史滚动峰值的回撤是否代表压力或修复空间？
mechanism: 深回撤刻画历史损失压力，但其含义需结合持续时间和恢复结构解释。
construction_space:
  inputs: [close]
  transforms: [rolling_peak, drawdown_ratio, depth_rank, clipping]
  relations: [current_loss_from_peak]
degenerate_patterns: [使用未来峰值, 只做 N 日收益, 把深回撤固定解释为反转]
allowed_roles: [primary, modifier]
preferred_output:
  continuous: true
```

```text
用历史 rolling peak 计算当前回撤深度，构造连续路径压力分数。不得使用未来峰值或未来恢复结果。
```

### DD02: Drawdown Duration

```yaml
lens_id: drawdown.drawdown_duration
layer: multiscale_complexity
agent: drawdown
title: Drawdown Duration
title_zh: 回撤持续
research_question: 价格处于回撤状态的持续时间是否反映弱势惯性或修复成熟度？
mechanism: 同样深度下，短促回撤和长期无法修复的含义不同，持续时间提供时间韧性线索。
construction_space:
  inputs: [close]
  transforms: [below_peak_indicator, duration_proxy, rolling_count, duration_weighted_depth]
  relations: [persistent_drawdown, fresh_drawdown]
degenerate_patterns: [精确寻找未来恢复日, 只计算回撤深度, 使用复杂循环]
allowed_roles: [primary, stabilizer]
preferred_output:
  continuous: true
```

```text
构造当前仍处于历史峰值下方的持续 proxy，区分新近回撤和长期弱势。优先使用滚动统计近似，避免复杂循环。
```

### DD03: Recovery Geometry

```yaml
lens_id: drawdown.recovery_geometry
layer: multiscale_complexity
agent: drawdown
title: Recovery Geometry
title_zh: 恢复几何
research_question: 回撤后的恢复路径是顺滑、停滞还是再次转弱？
mechanism: 回撤后的恢复斜率和路径效率可反映价格韧性，但只能基于已发生历史路径。
construction_space:
  inputs: [close, high, low]
  transforms: [post_drawdown_slope, recovery_efficiency, path_noise, partial_recovery_score]
  relations: [resilient_recovery, stalled_recovery]
degenerate_patterns: [使用未来完全恢复确认, 不区分恢复和普通趋势, 过度拟合路径形态]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
```

```text
基于当前之前已经发生的回撤和恢复路径，衡量恢复斜率、恢复效率和路径噪声。不要用未来是否完全修复来定义当前因子。
```

### DD04: Underwater Pressure Area

```yaml
lens_id: drawdown.underwater_pressure_area
layer: multiscale_complexity
agent: drawdown
title: Underwater Pressure Area
title_zh: 水下压力面积
research_question: 回撤深度与持续时间的联合累积是否比单独深度或时长更能描述历史压力？
mechanism: 长时间浅回撤和短时间深回撤具有不同路径负担，累计 underwater area 可表达损失压力的联合暴露。
construction_space:
  inputs: [close]
  transforms: [past_running_peak, drawdown_curve, rolling_underwater_area, normalized_duration]
  relations: [deep_short_pressure, shallow_persistent_pressure]
degenerate_patterns: [只把深度乘持续天数, 使用未来峰值, 不区分当前压力和历史累计]
allowed_roles: [primary, modifier, stabilizer]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
基于历史滚动峰值构造已发生的回撤曲线，并汇总其深度-时间压力。保持路径含义，不要机械地把两个标量相乘后失去时间结构。
```

### DD05: Recovery Setback

```yaml
lens_id: drawdown.recovery_setback
layer: multiscale_complexity
agent: drawdown
title: Recovery Setback
title_zh: 修复受挫
research_question: 回撤修复过程中反复失去已恢复幅度，是否代表韧性不足？
mechanism: 从低点反弹后再次回落，且多次无法接近历史峰值，可能反映修复路径脆弱而非稳定复苏。
construction_space:
  inputs: [close]
  transforms: [historical_drawdown, recovery_fraction, setback_depth, recovery_efficiency]
  relations: [stable_recovery, repeated_recovery_failure]
degenerate_patterns: [使用未来低点或未来峰值, 只算二次回撤深度, 把所有受挫直接解释为继续下跌]
allowed_roles: [primary, confirmation, stabilizer]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
在已发生的回撤路径中衡量恢复比例及随后损失的恢复幅度，构造修复受挫程度。所有峰值、低点和恢复状态只能由当前及历史数据确定。
```

### DD06: Drawdown Acceleration

```yaml
lens_id: drawdown.drawdown_acceleration
layer: multiscale_complexity
agent: drawdown
title: Drawdown Acceleration
title_zh: 回撤恶化加速度
research_question: 回撤正在加速恶化、匀速延续还是边际企稳？
mechanism: 当前回撤深度相同，但恶化速度不同，分别对应压力扩散、惯性延续和潜在稳定阶段。
construction_space:
  inputs: [close]
  transforms: [past_peak_drawdown, drawdown_slope, drawdown_curvature, robust_acceleration]
  relations: [accelerating_loss, decelerating_drawdown]
degenerate_patterns: [只做收益二阶差分, 使用未来低点, 不结合当前回撤状态]
allowed_roles: [primary, modifier, gate]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
基于历史滚动峰值形成的回撤曲线，衡量回撤深度的斜率和稳健加速度，区分压力扩散与边际企稳。
```

## 输出检查

- 明确记录 `agent_tags: [drawdown]`。
- 不使用未来峰值、未来谷值或未来恢复。
- 关注回撤路径，不只输出短期收益。
