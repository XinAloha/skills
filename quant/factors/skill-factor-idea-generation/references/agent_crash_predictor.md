# AgentCrashPredictor Prompt Catalog

`AgentCrashPredictor` 属于 Level II: Extreme Risk & Fragility。本文件用于生成崩盘前兆和结构脆弱性相关的初始因子想法，不直接声称因子有效。

## 来源边界

- 论文定义：识别崩盘早期预警信号，包括波动压缩、流动性枯竭和结构脆弱性。
- Appendix C.1 没有给出该 Agent 的逐字 Prompt；下面的 Lens 是对论文描述和当前工程 prompt 的研究化拆分。
- CrashPredictor 关注“压力累积与脆弱状态”，不是在崩盘已经发生后打标签。

## Agent 职责

CrashPredictor 要回答的核心问题是：

> 历史 OHLCV 是否显示出平静但脆弱、压力累积、流动性恶化或结构失稳的早期迹象？

它应输出连续的 fragility、stress accumulation 或 crash precursor score，而不是“明天是否崩盘”的结论。

## 与相邻 Agent 的边界

| 内容 | 归属 |
|---|---|
| 脆弱平静、压力累积、崩盘前兆 | `CrashPredictor` |
| 下行半方差、负冲击传播、尾部暴露 | `TailRisk` |
| 当前波动状态和状态持续性 | `VolatilityRegime` |
| 流动性压力和价格冲击本身 | `Liquidity` |
| 区间压缩扩张的普通波动形态 | `RangeVol` |

CrashPredictor 可以组合波动、成交和价格位置，但必须围绕“latent fragility before breakdown”这一主线。

## Agent 核心指令

当 Skill 选中 `crash_predictor` tag 时，将下面的核心指令与一张或两张 Lens 组合：

```text
你是专注日频 OHLCV 崩盘前兆和结构脆弱性的量化研究员。
请提出连续、可计算、可解释的初始因子假设，用历史波动压缩、压力累积、流动性恶化、弱收盘、range 异常或成交失衡表征 latent fragility。
不要只检测已经发生的大跌，不要用未来 crash 结果定义当前信号。
只使用用户允许的当前及历史字段，不使用未来信息。
```

## Prompt Lenses

### CP01: Fragile Calm

```yaml
lens_id: crash_predictor.fragile_calm
layer: extreme_risk_fragility
agent: crash_predictor
title: Fragile Calm
title_zh: 脆弱平静
research_question: 低波动或窄 range 表面的平静，是否同时伴随弱价格结构或压力积累？
mechanism: >
  崩盘前并不总是表现为高波动，某些路径会先出现低波动压缩和价格承接变弱。
  当平静状态叠加弱收盘、下行偏斜或成交收缩时，可能表示市场结构脆弱。
construction_space:
  inputs: [open, high, low, close, volume, returns, range]
  transforms:
    - low_volatility_score
    - narrow_range_score
    - weak_close_location
    - downside_drift
    - volume_dry_up
    - fragile_calm_interaction
  relations:
    - calm_with_weak_price_structure
    - quiet_but_fragile
degenerate_patterns:
  - 只输出低波动因子
  - 只把窄幅震荡视为安全状态
  - 用未来大跌反推当前平静是否脆弱
allowed_roles: [primary, gate, confirmation]
preferred_output:
  continuous: true
  bounded: optional
  fragility_interpretable: true
```

```text
研究低波动或窄 range 状态是否同时伴随弱收盘、下行漂移、成交收缩或承接变弱，将其表达为“平静但脆弱”的连续分数。因子不得只等同于低波动本身。
```

### CP02: Stress Accumulation

```yaml
lens_id: crash_predictor.stress_accumulation
layer: extreme_risk_fragility
agent: crash_predictor
title: Stress Accumulation
title_zh: 压力累积
research_question: 多个历史压力代理是否在短期内持续累积，而尚未完全释放？
mechanism: >
  崩盘前兆常表现为若干弱信号同时积累：弱收盘、下行 range、成交异常、负收益偏移等。
  单点异常可能只是噪声，持续累积的压力更可能代表结构脆弱。
construction_space:
  inputs: [open, high, low, close, volume, returns, range]
  transforms:
    - rolling_stress_score
    - downside_pressure_count
    - weak_close_persistence
    - adverse_volume_pressure
    - cumulative_fragility
  relations:
    - persistent_minor_stress
    - unrelieved_pressure
degenerate_patterns:
  - 把一个大跌日当成压力累积
  - 同时堆叠过多代理而无法解释
  - 使用未来崩盘确认压力是否释放
allowed_roles: [primary, modifier, confirmation]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
从历史弱收盘、下行 range、成交异常和负收益偏移中提取持续压力累积分数。因子应强调多个小压力的连续积累，而不是已经发生的单日暴跌。
```

### CP03: Liquidity Depletion Stress

```yaml
lens_id: crash_predictor.liquidity_depletion_stress
layer: extreme_risk_fragility
agent: crash_predictor
title: Liquidity Depletion Stress
title_zh: 流动性枯竭压力
research_question: 成交量或流动性代理恶化时，价格是否更容易出现不稳定下行压力？
mechanism: >
  当成交参与下降、单位成交对应价格冲击变大，市场吸收冲击的能力可能下降。
  若流动性恶化同时伴随弱价格结构，崩盘脆弱性可能上升。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms:
    - volume_dry_up
    - price_impact_proxy
    - range_per_volume
    - weak_close_location
    - liquidity_stress_interaction
  relations:
    - drying_liquidity_with_price_stress
    - impact_under_low_volume
degenerate_patterns:
  - 只输出成交量均线
  - 声称有订单簿深度数据
  - 不处理 volume 为零或极小值的除零风险
allowed_roles: [primary, modifier, confirmation]
preferred_output:
  continuous: true
  numerically_stable: true
```

```text
用成交量枯竭、单位成交价格冲击、弱收盘位置等 OHLCV 代理衡量流动性恶化下的结构压力。因子必须说明它是流动性脆弱代理，而不是真实订单簿深度。
```

### CP04: Compression Break Instability

```yaml
lens_id: crash_predictor.compression_break_instability
layer: extreme_risk_fragility
agent: crash_predictor
title: Compression Break Instability
title_zh: 压缩破裂不稳定
research_question: 长时间压缩后的 range 或收益波动扩张，是否表现为不稳定释放而非健康突破？
mechanism: >
  压缩后的扩张可能是趋势启动，也可能是结构破裂。若扩张方向偏下、收盘弱或成交承接不足，
  更可能代表不稳定释放。
construction_space:
  inputs: [open, high, low, close, volume, returns, range]
  transforms:
    - compression_duration
    - expansion_after_compression
    - weak_directional_break
    - close_location_after_break
    - volume_confirmation_failure
  relations:
    - unstable_release_after_compression
    - downside_break_from_quiet_state
degenerate_patterns:
  - 只做普通波动率突破
  - 不区分健康上行突破和脆弱下行破裂
  - 用未来结果判断突破是否失败
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
研究历史压缩状态之后的 range 或收益波动扩张是否伴随弱收盘、下行方向或成交承接不足，将其表达为压缩破裂的不稳定强度。因子不得退化为普通波动率突破。
```

### CP05: Gap-Like Pressure Proxy

```yaml
lens_id: crash_predictor.gap_like_pressure_proxy
layer: extreme_risk_fragility
agent: crash_predictor
title: Gap-Like Pressure Proxy
title_zh: 类跳空压力代理
research_question: 日频 open-close/high-low 结构是否显示隔夜或日内方向性压力正在积累？
mechanism: >
  即使没有更细粒度数据，开盘位置、收盘位置、实体方向和 range 结构也能提供压力代理。
  持续弱开、弱收或实体压力可能反映价格发现中的结构性下行风险。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms:
    - open_to_prev_close_proxy
    - body_pressure
    - close_location_value
    - weak_open_weak_close
    - range_normalized_body
  relations:
    - gap_like_downside_pressure
    - intraday_failure_to_recover
degenerate_patterns:
  - 假设拥有真实盘前或分钟级数据
  - 只用 open-close 单日实体作为崩盘预测
  - 不做 range 或历史尺度归一化
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
利用日频 open、close、high、low 构造类跳空压力、弱开弱收或日内恢复失败的连续代理，刻画结构性下行压力是否正在积累。不要声称使用分钟级或真实隔夜订单信息。
```

## 同 Agent 内组合

默认只使用一张 Lens。如果使用两张，必须明确一个主机制和一个辅助机制。

优先考虑：

- `fragile_calm` + `stress_accumulation`：用压力累积确认平静状态是否脆弱。
- `liquidity_depletion_stress` + `fragile_calm`：用流动性恶化解释低波动平静下的脆弱性。
- `compression_break_instability` + `gap_like_pressure_proxy`：用类跳空压力确认压缩后的不稳定释放。

应避免：

- 只检测已经发生的大跌。
- 把所有高波动或低波动都写成崩盘前兆。
- 依赖未来 crash label、未来最大回撤或未来收益路径。
- 同时堆叠过多风险代理，导致无法解释。

## 输出检查

CrashPredictor 候选至少应满足：

- 明确记录 `agent_tags: [crash_predictor]` 和实际使用的 `prompt_lens_ids`。
- 输出是连续 fragility、stress accumulation 或 crash precursor score。
- 只使用用户允许的当前和历史字段。
- 明确它是在描述“崩盘前压力/脆弱性”，不是承诺预测崩盘。
- 明确说明与 `TailRisk` 和 `VolatilityRegime` 的差别。
