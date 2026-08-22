# AgentBarShape Prompt Catalog

`AgentBarShape` 属于 Level VII: Geometric & Fusion。本文件用于生成 K 线几何结构相关的初始因子想法。

## Agent 核心指令

```text
你是专注日频 K 线几何、实体、影线、收盘位置和形态持续性的量化研究员。
请提出连续、可计算、可解释的初始因子假设，将 bar shape 编码为行为代理。
不要输出离散 K 线形态名字。
```

## Prompt Lenses

### BS01: Shadow Balance

```yaml
lens_id: bar_shape.shadow_balance
layer: geometric_fusion
agent: bar_shape
title: Shadow Balance
title_zh: 影线平衡
research_question: 上下影线比例是否反映日内冲击被拒绝或承接？
mechanism: 长上影可能表示上方卖压，长下影可能表示下方承接，需结合收盘位置解释。
construction_space:
  inputs: [open, high, low, close]
  transforms: [upper_shadow, lower_shadow, shadow_ratio, close_location_value]
  relations: [upper_rejection, lower_absorption]
degenerate_patterns: [只命名锤子线/吊颈线, 不连续化, 不处理 high=low]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  bounded: true
```

```text
用上下影线和收盘位置构造连续形态分数，解释日内冲击是被拒绝还是被承接。
```

### BS02: Body Strength

```yaml
lens_id: bar_shape.body_strength
layer: geometric_fusion
agent: bar_shape
title: Body Strength
title_zh: 实体强度
research_question: 实体相对 range 的大小是否代表方向推进完整度？
mechanism: 大实体表示从开盘到收盘方向推进更完整，可能反映更强日内共识。
construction_space:
  inputs: [open, high, low, close]
  transforms: [signed_body, body_to_range, close_location_value, body_persistence]
  relations: [strong_body_move, weak_body_noise]
degenerate_patterns: [只用 open-close 收益, 不做 range 归一化, 不区分方向]
allowed_roles: [primary, modifier]
preferred_output:
  continuous: true
```

```text
衡量实体方向和实体占 range 的比例，构造连续方向推进强度。不要退化成 open-close 收益。
```

### BS03: Shape Persistence

```yaml
lens_id: bar_shape.shape_persistence
layer: geometric_fusion
agent: bar_shape
title: Shape Persistence
title_zh: 形态持续性
research_question: 某类 K 线几何压力是否在历史窗口中持续出现？
mechanism: 单日形态噪声较大，形态压力连续出现时可能更有信息。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [shape_score, rolling_persistence, volume_confirmation, decay_weight]
  relations: [persistent_rejection, persistent_absorption]
degenerate_patterns: [堆叠多个形态名字, 只看单日, 不解释持续性]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
```

```text
把单日形态分数扩展为历史持续性或衰减分数，区分偶发形态和持续行为压力。
```

### BS04: Gap-Body Decomposition

```yaml
lens_id: bar_shape.gap_body_decomposition
layer: geometric_fusion
agent: bar_shape
title: Gap-Body Decomposition
title_zh: 跳空与实体分解
research_question: 当日价格变化由隔夜跳空还是日内实体贡献，两者方向一致性是否表达信息接受程度？
mechanism: 隔夜定价与日内交易是两个阶段；同向延续、日内抵消和方向冲突反映不同的信息吸收路径。
construction_space:
  inputs: [open, close]
  transforms: [overnight_component, intraday_component, component_share, directional_alignment]
  relations: [gap_confirmed_intraday, gap_rejected_intraday]
degenerate_patterns: [只输出隔夜收益, 不使用上一交易日 close, 把同日 close 当作开盘时可知信息]
allowed_roles: [primary, confirmation, contrast]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
将已经完成交易日的 close-to-close 变化分解为前收至开盘和开盘至收盘两部分，比较贡献和方向一致性。使用时明确该日因子最早在收盘后可得。
```

### BS05: Shadow-Body Tension

```yaml
lens_id: bar_shape.shadow_body_tension
layer: geometric_fusion
agent: bar_shape
title: Shadow-Body Tension
title_zh: 影线实体张力
research_question: 实体推进方向与影线拒绝方向冲突时，日内力量张力是否包含信息？
mechanism: 大实体与反方向长影线并存，可能表示方向推进虽完成但遭遇显著对手压力，其含义不同于单独实体或影线。
construction_space:
  inputs: [open, high, low, close]
  transforms: [signed_body_ratio, opposing_shadow_ratio, close_location, tension_score]
  relations: [advance_under_rejection, weak_body_strong_rejection]
degenerate_patterns: [简单相加实体和影线, 输出离散 K 线名称, 不区分支持影线和反向影线]
allowed_roles: [primary, modifier, confirmation]
preferred_output:
  continuous: true
  bounded: true
```

```text
构造实体方向与反方向影线压力之间的连续张力，区分顺畅推进、受阻推进和完全拒绝。不要退化为形态标签。
```

### BS06: Close-Location Migration

```yaml
lens_id: bar_shape.close_location_migration
layer: geometric_fusion
agent: bar_shape
title: Close-Location Migration
title_zh: 收盘位置迁移
research_question: 收盘位置是否在多日内持续从区间下部向上部迁移，或反向迁移？
mechanism: 单日收盘位置噪声较大，连续迁移可表达日内争夺结果逐步改变和主导力量转移。
construction_space:
  inputs: [high, low, close]
  transforms: [close_location_value, rolling_slope, migration_persistence, bounded_change]
  relations: [upward_close_migration, downward_close_migration]
degenerate_patterns: [只用单日 close location, 等同于普通收盘价趋势, 不处理窄幅日]
allowed_roles: [primary, confirmation, modifier]
preferred_output:
  continuous: true
  bounded: optional
```

```text
先构造每日连续收盘位置，再衡量其历史迁移方向、速度和持续性。重点是日内争夺结果的跨日变化，不是收盘价格本身的趋势。
```

## 输出检查

- 明确记录 `agent_tags: [bar_shape]`。
- 输出连续几何分数，不输出离散形态标签。
- 对 high 等于 low 做保护。
