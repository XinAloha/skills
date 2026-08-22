# AgentReversal Prompt Catalog

`AgentReversal` 属于 Level IV: Price-Volatility Behavior。本文件用于生成短期过度反应修正和均值回归相关的初始因子想法。

## Agent 核心指令

```text
你是专注短期反转、过度反应修正和均值回归结构的量化研究员。
请提出连续、可计算、可解释的初始因子假设，用短期极端收益、range 扩张、成交量冲击和压力衰减刻画修正可能性。
不要把所有负动量简单取反。
```

## Prompt Lenses

### RV01: Overreaction Stretch

```yaml
lens_id: reversal.overreaction_stretch
layer: price_volatility_behavior
agent: reversal
title: Overreaction Stretch
title_zh: 过度反应拉伸
research_question: 短期价格是否偏离自身近期路径过远，存在修正压力？
mechanism: 短期极端收益可能包含流动性冲击或情绪过度反应，后续存在均值回归可能。
construction_space:
  inputs: [close, high, low]
  transforms: [short_return, rolling_zscore, range_adjusted_stretch, clipping]
  relations: [extreme_short_move, stretched_from_recent_path]
degenerate_patterns: [简单负 N 日收益, 不做波动归一化, 把趋势回撤误写成反转]
allowed_roles: [primary, gate]
preferred_output:
  continuous: true
```

```text
用短期收益相对近期波动或 range 的拉伸程度刻画过度反应。因子应解释为什么该拉伸可能修正，而不是简单反向动量。
```

### RV02: Pressure Decay Reversal

```yaml
lens_id: reversal.pressure_decay_reversal
layer: price_volatility_behavior
agent: reversal
title: Pressure Decay Reversal
title_zh: 压力衰减反转
research_question: 冲击之后成交量或 range 压力是否衰减，暗示边际卖压/买压释放？
mechanism: 过度反应后的压力衰减可能代表主动交易力量耗尽，修正概率上升。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [shock_score, volume_decay, range_decay, post_shock_stabilization]
  relations: [sell_pressure_exhaustion, buy_pressure_exhaustion]
degenerate_patterns: [只用缩量, 不结合初始冲击, 使用未来修复确认]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
```

```text
结合初始价格冲击和后续历史中的量能/range 衰减，构造压力释放后的反转候选。不要把缩量本身直接解释为反转。
```

### RV03: Intraday Rejection

```yaml
lens_id: reversal.intraday_rejection
layer: price_volatility_behavior
agent: reversal
title: Intraday Rejection
title_zh: 日内冲高/下探失败
research_question: 日内极端位置被收回，是否代表短期过度反应被拒绝？
mechanism: 长上影或长下影结合收盘位置可表示冲击方向被市场否定，可能引发短期修正。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [upper_shadow, lower_shadow, close_location_value, volume_confirmation]
  relations: [upside_rejection, downside_rejection]
degenerate_patterns: [只命名 K 线形态, 不做连续化, 不处理窄 range]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  bounded: true
```

```text
用影线、实体和收盘位置构造日内冲击被拒绝的连续分数，并结合成交量确认。不要输出离散 K 线标签。
```

### RV04: Failed Continuation

```yaml
lens_id: reversal.failed_continuation
layer: price_volatility_behavior
agent: reversal
title: Failed Continuation
title_zh: 延续失败
research_question: 强方向冲击之后价格无法继续推进，是否表明原方向力量衰竭？
mechanism: 若前期冲击显著但后续净位移、收盘位置或成交效率迅速下降，原有方向可能缺乏新增参与支持。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [prior_shock, follow_through, close_location, progress_decay]
  relations: [up_move_failed_follow_through, down_move_failed_follow_through]
degenerate_patterns: [只对前期收益取反, 未定义延续窗口, 看到停滞就断言反转]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
先识别已经发生的方向冲击，再衡量随后历史区间内是否缺乏同向跟进，构造延续失败程度。它表达修正压力，不承诺下一期必然反转。
```

### RV05: Overnight-Intraday Rejection

```yaml
lens_id: reversal.overnight_intraday_rejection
layer: price_volatility_behavior
agent: reversal
title: Overnight-Intraday Rejection
title_zh: 隔夜冲击日内否定
research_question: 开盘相对前收的隔夜冲击被当日价格路径否定时，是否反映信息过度反应？
mechanism: 隔夜定价包含非交易时段信息，若日内收益系统性抵消开盘跳变，可能表明初始冲击未被持续接受。
construction_space:
  inputs: [open, close]
  transforms: [overnight_return, intraday_return, offset_ratio, rejection_strength]
  relations: [gap_up_rejected, gap_down_recovered]
degenerate_patterns: [把当日 open 与同日 close 混为未来信息, 只输出 gap 大小, 忽略隔夜和日内方向关系]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
用当日 open 相对上一交易日 close 的跳变与当日 open-to-close 路径之间的抵消关系，刻画隔夜信息被接受或否定的程度。
```

### RV06: Reversal Maturity

```yaml
lens_id: reversal.reversal_maturity
layer: price_volatility_behavior
agent: reversal
title: Reversal Maturity
title_zh: 反转条件成熟度
research_question: 过度延伸、边际减速和压力衰减是否共同表明修正条件逐步成熟？
mechanism: 极端偏离本身不足以产生反转；偏离形成后推进减速、压力减弱才表示原方向力量可能接近耗尽。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [historical_stretch, progress_deceleration, pressure_decay, maturity_score]
  relations: [immature_stretch, mature_exhaustion]
degenerate_patterns: [堆叠三个独立反转指标, 用未来反弹确认成熟, 把高成熟度写成必然反转]
allowed_roles: [primary, gate, confirmation]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
把反转视为历史过程：先有偏离，再观察同向推进是否减速及压力是否衰减。用最少分量表达成熟阶段，不得用未来修复确认。
```

## 输出检查

- 明确记录 `agent_tags: [reversal]`。
- 说明为什么是过度反应修正，不是普通趋势。
- 不使用未来修复结果。
