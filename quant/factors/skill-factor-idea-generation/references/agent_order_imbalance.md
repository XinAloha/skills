# AgentOrderImbalance Prompt Catalog

`AgentOrderImbalance` 属于 Level III: Price-Volume Dynamics。本文件用于生成日频 OHLCV 下的方向性参与压力代理。

## Agent 职责

OrderImbalance 要回答的核心问题是：

> 日频 K 线、收盘位置和成交量是否暗示买卖压力不平衡？

它只能构造 signed-volume proxy 或 body-pressure proxy，不能声称使用真实订单流。

## Agent 核心指令

```text
你是专注用日频 OHLCV 推断方向性参与压力的量化研究员。
请提出连续、可计算、可解释的初始因子假设，用实体方向、收盘位置、range 和成交量构造买卖压力代理。
不要声称有真实 order imbalance、逐笔成交或盘口数据。
```

## Prompt Lenses

### OI01: Signed Volume Proxy

```yaml
lens_id: order_imbalance.signed_volume_proxy
layer: price_volume_dynamics
agent: order_imbalance
title: Signed Volume Proxy
title_zh: 有符号成交量代理
research_question: 成交量是否更多伴随同一方向的价格压力？
mechanism: 用 open-close 方向或收盘位置为成交量赋符号，可近似刻画日频方向性参与。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [signed_body, close_location_value, signed_volume, rolling_sum]
  relations: [persistent_buy_pressure, persistent_sell_pressure]
degenerate_patterns:
  - 声称真实买卖成交量可见
  - 只用涨跌方向乘成交量而不做 range 归一化
  - 不处理窄幅日的噪声
allowed_roles: [primary, modifier]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
用实体方向或收盘位置构造日频 signed volume proxy，并观察其滚动累积或衰减。必须说明这是 OHLCV 代理，不是真实订单流。
```

### OI02: Close-Location Pressure

```yaml
lens_id: order_imbalance.close_location_pressure
layer: price_volume_dynamics
agent: order_imbalance
title: Close-Location Pressure
title_zh: 收盘位置压力
research_question: 收盘靠近日内高低位置是否暗示当日买卖压力占优？
mechanism: 收盘位置反映日内争夺结果，若与成交量或实体方向一致，可能代表方向压力增强。
construction_space:
  inputs: [high, low, close, volume]
  transforms: [close_location_value, range_normalization, volume_weighting, rolling_persistence]
  relations: [upper_close_buy_pressure, lower_close_sell_pressure]
degenerate_patterns:
  - 只用 close-low/high-low 的单日值
  - 不处理 high 等于 low 的情况
  - 把收盘位置直接等同于未来方向
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  bounded: true
```

```text
从收盘在日内区间的位置出发，结合成交量或持续性构造方向性压力分数。因子应是连续代理，不做 K 线标签。
```

### OI03: Body-Range Pressure

```yaml
lens_id: order_imbalance.body_range_pressure
layer: price_volume_dynamics
agent: order_imbalance
title: Body-Range Pressure
title_zh: 实体区间压力
research_question: 实体长度相对 range 是否代表方向性力量更集中？
mechanism: 大实体小影线表示价格从开盘到收盘的方向推进更完整，可作为单边参与代理。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [body_ratio, shadow_balance, signed_body_ratio, volume_confirmation]
  relations: [one_sided_participation, body_supported_by_volume]
degenerate_patterns:
  - 只输出实体长度
  - 不区分实体方向
  - 不处理极窄 range
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  bounded: optional
```

```text
用实体长度相对 high-low range 的比例刻画单边推进强度，并可用成交量确认。不要把实体形态写成离散 K 线模式。
```

### OI04: Pressure Persistence Without Progress

```yaml
lens_id: order_imbalance.pressure_without_progress
layer: price_volume_dynamics
agent: order_imbalance
title: Pressure Persistence Without Progress
title_zh: 压力持续但价格停滞
research_question: 方向性成交压力持续存在但价格无法继续推进，是否代表吸收或力量衰竭？
mechanism: 若 signed-volume proxy 长时间同向而净价格位移下降，交易压力可能正在被对手方吸收。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [signed_pressure, pressure_persistence, net_displacement, progress_efficiency]
  relations: [persistent_pressure_low_progress, absorption_under_pressure]
degenerate_patterns: [只计算价量背离, 不定义方向压力, 看到停滞就直接预测反转]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
比较方向性参与压力的累计程度与同期净价格推进，刻画“压力仍在但价格不再响应”的连续吸收分数。不要把吸收直接写成必然反转。
```

### OI05: Pressure Sign Transition

```yaml
lens_id: order_imbalance.pressure_sign_transition
layer: price_volume_dynamics
agent: order_imbalance
title: Pressure Sign Transition
title_zh: 压力方向切换
research_question: 买卖压力代理从一侧主导转向另一侧时，切换速度和完整度是否包含信息？
mechanism: 持续压力的平滑换向比单日涨跌反转更能反映参与者主导权变化。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [signed_pressure, ema_pressure, zero_crossing_distance, transition_speed]
  relations: [buy_to_sell_transition, sell_to_buy_transition]
degenerate_patterns: [只看单日正负号, 使用离散交叉标签, 与普通短期反转完全相同]
allowed_roles: [primary, confirmation, gate]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
用平滑方向压力的水平、变化速度和过零距离表达主导权切换，输出连续转换强度。不得退化为单日阳线阴线切换。
```

## 输出检查

- 明确记录 `agent_tags: [order_imbalance]`。
- 只使用日频 OHLCV 代理。
- 不声称有真实订单簿、逐笔成交或主动买卖数据。
