# AgentVolatilityRegime Prompt Catalog

`AgentVolatilityRegime` 属于 Level I: Market Structure & Cycle。本文件用于生成波动状态相关的初始因子想法，不直接声称因子有效。

## 来源边界

- 论文定义：识别平静与剧烈波动状态之间的转换，刻画波动聚集和 regime persistence。
- Appendix C.1 没有给出该 Agent 的逐字 Prompt；下面的 Lens 是对论文描述和当前工程 prompt 的研究化拆分。
- Lens 数量由可区分的波动状态机制决定，不预设固定数量。

## Agent 职责

VolatilityRegime 要回答的核心问题是：

> 当前历史路径处于怎样的波动状态？这种状态是在延续、衰减，还是正在切换？

它应输出连续的 regime score、状态转换强度或状态可靠性，而不是离散的“高波动/低波动”标签。

## 与相邻 Agent 的边界

| 内容 | 归属 |
|---|---|
| 当前波动状态、波动聚集、状态持续性 | `VolatilityRegime` |
| 周期相位、周期能量、结构拐点 | `MarketCycle` |
| high-low range 的局部形态与区间压缩扩张 | `RangeVol` |
| 崩盘前压力累积和脆弱平静 | `CrashPredictor` |
| 下行尾部暴露和负冲击传播 | `TailRisk` |

VolatilityRegime 可以使用 range 或收益波动，但必须解释为“状态识别和状态切换”，而不是预测某个具体崩盘事件。

## Agent 核心指令

当 Skill 选中 `volatility_regime` tag 时，将下面的核心指令与一张或两张 Lens 组合：

```text
你是专注日频 OHLCV 波动状态识别的量化研究员。
请提出连续、可计算、可解释的初始因子假设，用历史收益波动、range 波动、波动变化率、波动聚集或状态持续性表征 calm/turbulent regime。
不要输出硬分类标签，不要只生成普通历史波动率或 ATR 换名版本。
只使用用户允许的当前及历史字段，不使用未来信息。
```

## Prompt Lenses

每个 Lens 使用半结构化字段，便于选择、组合、检查和统计覆盖度。

### VR01: Calm-Turbulence Transition

```yaml
lens_id: volatility_regime.calm_turbulence_transition
layer: market_structure_cycle
agent: volatility_regime
title: Calm-Turbulence Transition
title_zh: 平静剧烈状态转换
research_question: 历史波动状态是否正在从平静切向剧烈，或从剧烈回落到平静？
mechanism: >
  波动状态切换往往改变趋势、反转和风险因子的生效环境。平静到剧烈的转换可能代表
  信息冲击开始被定价，剧烈到平静的转换可能代表冲击释放和状态修复。
construction_space:
  inputs: [close, high, low, returns, range]
  transforms:
    - realized_volatility
    - range_volatility
    - short_long_volatility_ratio
    - volatility_zscore
    - regime_change_speed
  relations:
    - calm_to_turbulent_shift
    - turbulent_to_calm_decay
    - short_state_vs_long_state
degenerate_patterns:
  - 只输出短期历史波动率
  - 只判断当前波动率高低
  - 用二值阈值标签代替连续状态分数
allowed_roles: [primary, gate, modifier]
preferred_output:
  continuous: true
  bounded: optional
  state_interpretable: true
```

```text
从历史收益波动或 high-low range 的短长状态差异出发，刻画平静状态向剧烈状态切换、或剧烈状态向平静状态衰减的连续强度。因子应表达状态转换过程，而不是普通历史波动率或硬阈值标签。
```

### VR02: Regime Persistence

```yaml
lens_id: volatility_regime.regime_persistence
layer: market_structure_cycle
agent: volatility_regime
title: Regime Persistence
title_zh: 波动状态持续性
research_question: 当前波动状态是否具有持续性，还是频繁翻转、难以稳定识别？
mechanism: >
  波动具有聚集性，持续的 calm 或 turbulent 状态会影响信号可靠性。状态频繁翻转时，
  单一趋势或反转逻辑可能更容易失效。
construction_space:
  inputs: [close, high, low, returns, range]
  transforms:
    - rolling_state_score
    - state_autocorrelation
    - sign_persistence
    - volatility_rank_stability
    - transition_frequency
  relations:
    - same_state_duration
    - state_flip_rate
    - persistence_adjusted_regime
degenerate_patterns:
  - 把连续上涨或下跌误当成波动状态持续
  - 只计算波动均值，不衡量状态是否稳定
  - 使用未来窗口确认状态持续
allowed_roles: [primary, stabilizer, confirmation]
preferred_output:
  continuous: true
  reliability_interpretable: true
```

```text
研究历史波动状态本身的持续性、翻转频率和稳定程度，将其表达为连续的 regime persistence 或 state reliability 分数。重点是状态是否稳定延续，而不是价格方向是否持续。
```

### VR03: Vol-of-Vol Acceleration

```yaml
lens_id: volatility_regime.vol_of_vol_acceleration
layer: market_structure_cycle
agent: volatility_regime
title: Vol-of-Vol Acceleration
title_zh: 波动的波动加速
research_question: 波动率自身的变化速度和二阶变化，是否预示状态不稳定或状态切换？
mechanism: >
  波动水平可能尚未极端，但波动自身的加速变化可提前反映环境不稳定。vol-of-vol 上升
  表示市场对信息的定价节奏变得不稳定。
construction_space:
  inputs: [close, high, low, returns, range]
  transforms:
    - volatility_change
    - volatility_acceleration
    - vol_of_vol
    - range_change_dispersion
    - normalized_second_difference
  relations:
    - accelerating_uncertainty
    - volatility_instability
degenerate_patterns:
  - 只比较两个窗口波动率高低
  - 把单日大波动误写成 vol-of-vol
  - 不做尺度归一化导致高价股或高波动股天然更大
allowed_roles: [primary, modifier, confirmation]
preferred_output:
  continuous: true
  scale_normalized: true
```

```text
从历史收益波动或 range 波动的一阶变化、二阶变化和波动的波动出发，刻画市场环境是否正在变得不稳定。因子应关注波动状态变化速度，而不是当前波动水平本身。
```

### VR04: Volatility Clustering

```yaml
lens_id: volatility_regime.volatility_clustering
layer: market_structure_cycle
agent: volatility_regime
title: Volatility Clustering
title_zh: 波动聚集
research_question: 大波动或小波动是否在历史上呈现聚集结构，从而影响后续状态延续？
mechanism: >
  波动聚集意味着冲击影响可能持续，近期大波动的连续性或小波动的连续性都可能改变
  后续收益分布和因子可靠性。
construction_space:
  inputs: [close, high, low, returns, range]
  transforms:
    - absolute_return_clustering
    - range_clustering
    - rolling_autocorrelation_proxy
    - burstiness
    - quietness_concentration
  relations:
    - high_vol_cluster
    - low_vol_cluster
    - cluster_break
degenerate_patterns:
  - 只输出平均绝对收益
  - 只用一个极端日代表聚集
  - 不区分持续聚集与单点冲击
allowed_roles: [primary, stabilizer, gate]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
研究绝对收益或 high-low range 是否出现连续聚集、安静聚集或聚集破裂，将其表达为波动状态的路径依赖分数。因子必须区分连续聚集和单日异常。
```

### VR05: Regime-Adjusted Signal Reliability

```yaml
lens_id: volatility_regime.regime_adjusted_signal_reliability
layer: market_structure_cycle
agent: volatility_regime
title: Regime-Adjusted Signal Reliability
title_zh: 波动状态调整的信号可靠性
research_question: 某类价格信号在不同波动状态下是否应被增强或削弱？
mechanism: >
  同一价格信号在 calm、transition、turbulent 状态下可能含义不同。波动 regime 可以
  作为软门控或可靠性权重，帮助下游因子避免在不适配状态中过度激活。
construction_space:
  inputs: [close, high, low, returns, range]
  transforms:
    - smooth_gate
    - volatility_rank
    - regime_confidence
    - instability_penalty
    - reliability_weight
  relations:
    - signal_weight_by_regime
    - instability_discount
degenerate_patterns:
  - 把 gate 写成生硬 if-else
  - 直接混入多个主信号导致解释失焦
  - 未说明被调节的主机制
allowed_roles: [gate, modifier, stabilizer]
preferred_output:
  continuous: true
  bounded: true
```

```text
把波动状态转化为连续软门控、可靠性权重或不稳定惩罚，用于调节其他主信号的强度。该 Lens 通常作为辅助机制使用，必须说明被调节的主机制，不应独立堆叠成复杂混合因子。
```

## 同 Agent 内组合

默认只使用一张 Lens。如果使用两张，必须明确一个主机制和一个辅助机制。

优先考虑：

- `calm_turbulence_transition` + `regime_persistence`：用状态持续性确认状态切换。
- `vol_of_vol_acceleration` + `volatility_clustering`：用聚集结构确认环境不稳定。
- `calm_turbulence_transition` + `regime_adjusted_signal_reliability`：把状态转换作为软门控权重。

应避免：

- 把所有 Lens 都写成短长波动率比。
- 同时堆叠波动率、range、成交量、趋势和反转而失去 regime 主线。
- 用未来是否发生大涨大跌来定义当前 regime。

## 输出检查

VolatilityRegime 候选至少应满足：

- 明确记录 `agent_tags: [volatility_regime]` 和实际使用的 `prompt_lens_ids`。
- 输出是连续 regime score、状态转换强度或可靠性权重。
- 只使用用户允许的当前和历史字段。
- 不把波动状态硬编码成未来结果标签。
- 明确区分其与 `MarketCycle`、`RangeVol`、`CrashPredictor` 的边界。
