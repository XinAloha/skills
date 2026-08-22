# AgentMarketCycle Prompt Catalog

`AgentMarketCycle` 属于 Level I: Market Structure & Cycle。本文件是该 Agent 的第一版 Prompt Lens 目录，用于生成因子想法，不直接声称因子有效。

## 来源边界

- 论文定义：探索价格动态中的长周期转换、相位变化、隐藏市场节奏和结构性拐点。
- Appendix C.1 明确提到五类方向：周期振荡、短长周期相位差、轨迹曲率、波动压缩-扩张转换、短长周期能量/振幅比。
- 下面的 Lens 是对论文方向的工程化拆分，不是论文逐字 Prompt。

Lens 数量由可区分的经济机制决定，不预设每个 Agent 必须有两个或其他固定数量。

## Agent 职责

MarketCycle 要回答的核心问题是：

> 历史 OHLCV 中是否出现了可量化的节奏、相位或周期能量变化，从而表明当前价格轨迹正在延续或接近结构性转折？

它应输出连续、可解释的周期状态或转折强度，而不是离散的“牛市/熊市”标签。

## 与相邻 Agent 的边界

| 内容 | 归属 |
|---|---|
| 短长周期相位、周期能量、轨迹拐点 | `MarketCycle` |
| 当前是平静还是剧烈波动状态 | `VolatilityRegime` |
| 方向是否持续、动量是否稳定 | `DailyTrend` |
| 短期过度反应是否会修复 | `Reversal` |
| high-low range 本身的压缩、扩张和持续性 | `RangeVol` |
| 跨尺度粗糙度和长记忆 | `Fractal` |

MarketCycle 可以使用波动压缩-扩张，但必须把它解释为“周期转折的时序节奏”，而不是只测量当前波动状态。

## Agent 核心指令

当 Skill 选中 `market_cycle` tag 时，将下面的核心指令与一张或两张 Lens 组合：

```text
你是专注日频 OHLCV 市场周期与相位状态的量化研究员。
请提出连续、可计算、可解释的初始因子假设，用历史价格或波动轨迹中的节奏、相位、曲率、能量或周期转换表征结构变化。
不要生成普通 N 日收益、简单均线交叉、单纯趋势持续或短期超买超卖的换名版本。
只使用用户允许的当前及历史字段，不使用未来信息。
```

## Prompt Lenses

每个 Lens 尽量使用半结构化字段，便于后续选择、组合、检查和统计覆盖度。字段含义：

- `lens_id`: 稳定唯一标识。
- `research_question`: 这个 Lens 想研究的市场现象。
- `mechanism`: 为什么这个现象可能有经济含义。
- `construction_space`: 可探索的输入、变换和关系，不是固定公式。
- `degenerate_patterns`: 必须避免的退化形态。
- `allowed_roles`: 在组合中可承担的角色。
- `preferred_output`: 输出形态偏好。
- `prompt`: 真正用于生成想法的 Lens 指令。

### MC01: Phase Divergence

```yaml
lens_id: market_cycle.phase_divergence
layer: market_structure_cycle
agent: market_cycle
title: Phase Divergence
title_zh: 周期相位偏离
research_question: 短周期与长周期价格节奏的相位偏离，是否反映周期衰减、加速或转折？
mechanism: >
  短周期轨迹通常对新信息反应更快，长周期轨迹代表较慢的基础节奏。
  两者在方向、斜率、曲率或归一化位置上的错位，可能表征当前周期正在加速、
  衰减或发生结构性转折。
construction_space:
  inputs: [log_price, returns, high, low, close]
  transforms:
    - rolling_mean
    - ema
    - rolling_slope
    - normalized_distance
    - phase_change
    - curvature
  relations:
    - short_vs_long_position
    - short_vs_long_direction
    - slope_divergence
    - normalized_phase_distance
    - phase_acceleration
degenerate_patterns:
  - 普通二值均线交叉
  - 仅使用短均线减长均线
  - 仅判断短周期高于或低于长周期
  - 用普通动量因子替代相位关系
  - 为了体现“相位”而机械套用三角函数或角度公式
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  bounded: optional
  direction_interpretable: true
```

```text
从短周期与长周期平滑价格或收益轨迹的相位关系出发，探索“同向、错位、衰减、加速、反转”的连续定量表达。因子应刻画相位偏离的程度或相位变化的强度，而非退化为二值均线交叉、简单均线差或普通动量。相位是研究概念，不要求必须使用三角函数或角度公式。
```

### MC02: Trajectory Curvature

```yaml
lens_id: market_cycle.trajectory_curvature
layer: market_structure_cycle
agent: market_cycle
title: Trajectory Curvature
title_zh: 价格轨迹曲率
research_question: 累计收益或平滑价格轨迹的曲率变化，是否可以提前表征结构拐点？
mechanism: >
  市场周期切换常表现为价格路径从加速到减速、从线性推进到弯折。轨迹曲率刻画的是
  价格运动形态的二阶变化，而不是单纯方向或幅度。
construction_space:
  inputs: [log_price, returns, close]
  transforms:
    - rolling_slope
    - second_difference
    - ema_trajectory
    - normalized_curvature
    - acceleration_deceleration
  relations:
    - slope_change
    - curvature_turn
    - trajectory_bending
degenerate_patterns:
  - 把单日涨跌或普通动量直接称为曲率
  - 只计算 N 日收益变化
  - 不做尺度归一化导致价格量纲污染
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  scale_normalized: true
```

```text
从历史累计收益、平滑价格或 EMA 轨迹的曲率出发，研究市场节奏是在加速、减速还是发生结构性弯折。曲率应根据近期价格、收益或波动尺度进行归一化，避免因价格量纲产生伪信号。
```

### MC03: Cycle Energy Balance

```yaml
lens_id: market_cycle.cycle_energy_balance
layer: market_structure_cycle
agent: market_cycle
title: Cycle Energy Balance
title_zh: 周期能量平衡
research_question: 短周期与长周期的波动能量或振幅比例，是否反映市场主导节奏的转移？
mechanism: >
  不同周期尺度上的收益能量或振幅代表不同节奏的主导程度。短周期能量上升可能表示
  新信息或局部冲击开始主导，长周期能量占优可能表示原有慢节奏仍在延续。
construction_space:
  inputs: [close, high, low, returns, range]
  transforms:
    - squared_return_energy
    - absolute_return_energy
    - range_amplitude
    - short_long_energy_ratio
    - energy_concentration
  relations:
    - short_cycle_dominance
    - long_cycle_dominance
    - energy_shift
degenerate_patterns:
  - 只比较两个窗口的平均收益并换名为能量
  - 把普通历史波动率直接称为周期能量
  - 不解释能量从哪个尺度向哪个尺度转移
allowed_roles: [primary, modifier, confirmation]
preferred_output:
  continuous: true
  scale_normalized: true
```

```text
从不同历史尺度上的收益能量、振幅或路径波动强度出发，构造短周期与长周期之间的能量平衡指标。重点解释主导节奏正在向更短或更长尺度转移，而不是只生成另一个波动率因子。
```

### MC04: Compression-Expansion Turn

```yaml
lens_id: market_cycle.compression_expansion_turn
layer: market_structure_cycle
agent: market_cycle
title: Compression-Expansion Turn
title_zh: 压缩扩张转换
research_question: >
  市场是否会反复经历“波动压缩、能量积累、波动释放、扩张衰减”的过程？
  这一转换过程的进度、速度和强度，是否可以刻画周期转折或新周期启动？
mechanism: >
  持续压缩可能意味着价格运动暂时收敛、方向性力量处于积累阶段；
  随后的扩张表示潜在力量开始释放。压缩持续时间、扩张速度以及释放后的
  衰减路径，可能共同反映周期切换阶段。
construction_space:
  inputs: [high, low, close, returns, range]
  transforms:
    - short_long_range_ratio
    - short_long_volatility_ratio
    - compression_duration
    - cumulative_compression
    - range_acceleration
    - release_intensity_after_extreme_compression
    - continuous_state_score
    - multi_window_compression_alignment
degenerate_patterns:
  - 仅判断当前波动率高或低
  - 仅使用短期波动率减长期波动率
  - 退化为普通波动率突破
  - 只描述静态 volatility regime，而不刻画历史转换过程
  - 使用单日异常振幅代替压缩释放结构
allowed_roles: [primary, modifier, confirmation]
preferred_output:
  continuous: true
  path_dependent: true
  bounded: optional
```

```text
研究历史价格、收益或 high-low range 轨迹中“压缩、积累、释放、扩张、衰减”的连续交替节奏，将其表达为周期转换进度、释放强度或转折成熟度。因子必须刻画压缩到扩张的动态过程及历史路径，不得只对当前波动水平进行高低分类，也不得退化为简单的波动率突破或短长波动率差。
```

### MC05: Hidden Oscillation

```yaml
lens_id: market_cycle.hidden_oscillation
layer: market_structure_cycle
agent: market_cycle
title: Hidden Oscillation
title_zh: 隐含振荡节奏
research_question: 去除局部趋势后，收益或对数价格中是否存在可量化的重复振荡或隐藏节奏？
mechanism: >
  局部趋势可能掩盖更细的重复节奏。对收益或价格进行简洁去趋势后，残差中的重复
  正负切换、节奏衰减或振荡稳定性可能提供市场周期状态线索。
construction_space:
  inputs: [log_price, returns, close]
  transforms:
    - detrended_residual
    - smoothed_return_oscillation
    - sign_change_rhythm
    - oscillation_decay
    - simple_harmonic_proxy
  relations:
    - residual_cycle_strength
    - rhythm_stability
    - oscillation_decay
degenerate_patterns:
  - 为了高级而强行使用昂贵、不可解释的频域堆叠
  - 只统计涨跌交替次数而无强度刻画
  - 把普通均值回归换名为隐含振荡
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  interpretable_proxy: true
```

```text
对历史收益或对数价格进行简洁、可解释的去趋势处理，探索残差中的重复振荡、节奏稳定性或振荡衰减。优先提出能用少量历史统计量表达的周期代理，避免不可审计的复杂信号处理。
```

## 同 Agent 内组合

默认只使用一张 Lens。如果使用两张，必须明确一个为主机制，另一个只做确认或强度调节。

优先考虑：

- `phase_divergence` + `cycle_energy_balance`：用能量变化确认相位偏离。
- `trajectory_curvature` + `compression_expansion_turn`：用压缩-释放节奏确认轨迹弯折。
- `hidden_oscillation` + `phase_divergence`：比较残差节奏与价格轨迹相位。

应避免：

- 一次拼接三张以上 Lens。
- 同时堆叠相位、曲率、能量、波动门控和成交量确认。
- 两张 Lens 最终只生成普通动量、均线交叉或换窗口因子。

## 输出检查

MarketCycle 候选至少应满足：

- 明确记录 `agent_tags: [market_cycle]` 和实际使用的 `prompt_lens_ids`。
- 核心假设与选中 Lens 一致。
- 只使用用户允许的当前和历史字段。
- 公式草图可在少量步骤内实现，不靠算子堆叠营造创新感。
- 说明可能的生效阶段和失效条件。
- 不宣称未经评估的 RankIC、收益或实证有效性。
