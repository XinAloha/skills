# AgentHerding Prompt Catalog

`AgentHerding` 属于 Level VII: Geometric & Fusion。本文件用于生成拥挤行为、方向一致性和市场共识强度相关的初始因子想法。

## Agent 核心指令

```text
你是专注 OHLCV 动态中的拥挤行为、方向一致性和市场共识强度的量化研究员。
如果允许横截面计算，可使用同日 date 分组构造市场共识 proxy；否则使用个股内部连续同向压力近似。
不要使用真实持仓、新闻或订单簿数据。
```

## Prompt Lenses

### HD01: Cross-Sectional Directional Alignment

```yaml
lens_id: herding.cross_sectional_directional_alignment
layer: geometric_fusion
agent: herding
title: Cross-Sectional Directional Alignment
title_zh: 横截面方向一致
research_question: 同日多数股票方向是否高度一致，个股是否跟随这种共识？
mechanism: 横截面方向一致性高时，个股信号可能包含拥挤顺势或拥挤反转风险。
construction_space:
  inputs: [date, close, volume]
  transforms: [date_group_return_sign, market_alignment, stock_vs_market_direction]
  relations: [crowded_direction, against_consensus]
degenerate_patterns: [把 date 数值化, 未声明允许横截面, 使用指数或成分外数据]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
```

```text
在允许横截面计算时，用同日股票方向一致性构造市场共识强度，再衡量个股是否顺从或背离共识。
```

### HD02: Volume-Weighted Crowd Pressure

```yaml
lens_id: herding.volume_weighted_crowd_pressure
layer: geometric_fusion
agent: herding
title: Volume-Weighted Crowd Pressure
title_zh: 成交加权拥挤压力
research_question: 同方向价格变化是否伴随成交量集中，形成拥挤压力？
mechanism: 方向一致且成交放大可能代表更多参与者集中在同一方向。
construction_space:
  inputs: [close, volume]
  transforms: [signed_volume_proxy, rolling_crowd_pressure, volume_weighted_direction]
  relations: [crowded_buy_pressure, crowded_sell_pressure]
degenerate_patterns: [声称真实持仓, 只看成交量, 不区分方向]
allowed_roles: [primary, modifier]
preferred_output:
  continuous: true
```

```text
用有符号成交量代理构造连续拥挤压力，既可用于横截面，也可用于个股时间序列近似。
```

### HD03: Consensus Exhaustion

```yaml
lens_id: herding.consensus_exhaustion
layer: geometric_fusion
agent: herding
title: Consensus Exhaustion
title_zh: 共识衰竭
research_question: 连续同向压力后，成交或价格推进是否开始衰竭？
mechanism: 拥挤交易持续后，如果成交或价格效率下降，可能表示共识边际买盘/卖盘衰竭。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [directional_streak, volume_decay, progress_efficiency_decay, exhaustion_score]
  relations: [crowded_trend_exhaustion]
degenerate_patterns: [只统计连涨连跌, 不衡量衰竭, 直接等同于反转]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
```

```text
研究连续同向压力后，成交量或价格推进效率是否开始下降，构造拥挤共识衰竭分数。不要直接承诺反转。
```

### HD04: Crowding Acceleration

```yaml
lens_id: herding.crowding_acceleration
layer: geometric_fusion
agent: herding
title: Crowding Acceleration
title_zh: 拥挤加速度
research_question: 同方向参与压力正在加速还是减速，其变化是否反映共识形成或成熟？
mechanism: 拥挤水平相同但增长速度不同，可能分别对应共识快速形成、稳定维持和边际参与衰竭。
construction_space:
  inputs: [close, volume]
  transforms: [signed_volume_pressure, pressure_slope, acceleration, bounded_crowding]
  relations: [crowd_building, crowd_decelerating]
degenerate_patterns: [只做 signed volume 二阶差分, 不平滑噪声, 把加速直接等同于未来延续]
allowed_roles: [primary, modifier, confirmation]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
从方向性成交压力的历史水平、斜率和稳健加速度出发，区分拥挤形成、成熟和衰减。不得把二阶差分噪声直接作为因子。
```

### HD05: Cross-Sectional Dispersion Collapse

```yaml
lens_id: herding.cross_sectional_dispersion_collapse
layer: geometric_fusion
agent: herding
title: Cross-Sectional Dispersion Collapse
title_zh: 横截面分散度收缩
research_question: 同日股票收益分散度快速收缩并方向趋同时，是否表明市场共识或系统性拥挤上升？
mechanism: 横截面差异消失且方向一致，可能意味着个股信息被共同因子压制，系统性拥挤增强。
construction_space:
  inputs: [date, close, volume]
  transforms: [date_group_return_dispersion, directional_breadth, dispersion_change, consensus_score]
  relations: [dispersion_collapse_with_alignment, idiosyncratic_dispersion]
degenerate_patterns: [未声明横截面可用, 只算市场平均收益, 把 date 数值化, 在单股票输入上伪造横截面]
allowed_roles: [primary, confirmation, gate]
preferred_output:
  continuous: true
  cross_section_required: true
```

```text
仅在允许同日横截面计算时，联合衡量股票收益分散度变化和方向一致性，构造系统性共识强度。单股票输入时不得使用此 Lens。
```

### HD06: Crowding Fragility

```yaml
lens_id: herding.crowding_fragility
layer: geometric_fusion
agent: herding
title: Crowding Fragility
title_zh: 拥挤脆弱性
research_question: 同方向参与压力较高但价格推进效率下降时，拥挤状态是否变得脆弱？
mechanism: 共识仍强但边际价格响应减弱，可能表示同方向新增交易难以继续推动价格，退出风险上升。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [crowd_pressure, progress_efficiency, marginal_response_decay, fragility_score]
  relations: [strong_crowd_weak_progress, resilient_consensus]
degenerate_patterns: [与 consensus_exhaustion 完全重复, 只用成交量除收益, 直接预测拥挤崩溃]
allowed_roles: [primary, modifier, confirmation]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
联合衡量方向性参与压力水平和价格边际推进效率，刻画拥挤共识在高位时的脆弱程度。与共识衰竭不同，本 Lens 强调当前压力水平与效率的条件关系。
```

## 输出检查

- 明确记录 `agent_tags: [herding]`。
- 如果使用横截面，必须说明需要 `date` 分组且不把 date 当数值信号。
- 不使用真实持仓、新闻、订单簿或外部共识数据。
