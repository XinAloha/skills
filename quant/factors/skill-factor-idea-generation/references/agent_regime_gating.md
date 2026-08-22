# AgentRegimeGating Prompt Catalog

`AgentRegimeGating` 属于 Level VI: Stability & Regime-Gating。本文件用于生成自适应门控和状态激活相关的初始因子想法。

## Agent 核心指令

```text
你是专注市场状态门控、信号激活和动态权重的量化研究员。
请提出连续、可计算、可解释的门控因子假设，用波动、趋势、流动性或路径噪声状态调节主信号。
优先使用软门控，不要写生硬 if-else 标签。
```

## Prompt Lenses

### GATE01: Volatility State Gate

```yaml
lens_id: regime_gating.volatility_state_gate
layer: stability_regime_gating
agent: regime_gating
title: Volatility State Gate
title_zh: 波动状态门控
research_question: 某类主信号是否只应在特定波动状态下增强？
mechanism: 趋势、反转、流动性信号在 calm 和 turbulent 状态下含义不同。
construction_space:
  inputs: [close, high, low]
  transforms: [volatility_rank, smooth_gate, tanh_scaling, instability_discount]
  relations: [activate_in_calm, activate_in_turbulence]
degenerate_patterns: [硬阈值开关, 没有主信号, 和 volatility_regime 重复]
allowed_roles: [gate]
preferred_output:
  continuous: true
  bounded: true
```

```text
用历史波动状态构造连续软门控，用于调节另一个主信号的强度。必须说明被门控的主机制。
```

### GATE02: Trend-Regime Gate

```yaml
lens_id: regime_gating.trend_regime_gate
layer: stability_regime_gating
agent: regime_gating
title: Trend-Regime Gate
title_zh: 趋势状态门控
research_question: 当前路径更像趋势还是震荡，从而应如何激活信号？
mechanism: 趋势期和震荡期中，同一个反转或动量信号可能含义相反。
construction_space:
  inputs: [close]
  transforms: [path_efficiency, trendiness_score, choppiness_proxy, smooth_activation]
  relations: [trend_mode_activation, chop_mode_discount]
degenerate_patterns: [硬分类趋势震荡, 主信号和 gate 逻辑重复, 过多条件]
allowed_roles: [gate, modifier]
preferred_output:
  continuous: true
```

```text
用路径效率或趋势性分数构造软 gate，决定主信号在趋势期或震荡期的激活强度。
```

### GATE03: Liquidity State Gate

```yaml
lens_id: regime_gating.liquidity_state_gate
layer: stability_regime_gating
agent: regime_gating
title: Liquidity State Gate
title_zh: 流动性状态门控
research_question: 流动性状态是否影响主信号可靠性？
mechanism: 低流动性下价格信号更可能受噪声影响，应降低或改变主信号权重。
construction_space:
  inputs: [volume, close, high, low]
  transforms: [volume_rank, price_impact_proxy, liquidity_gate, reliability_weight]
  relations: [discount_under_illiquidity, activate_under_sufficient_liquidity]
degenerate_patterns: [只输出低成交量, 不说明主信号, 声称有真实盘口]
allowed_roles: [gate, stabilizer]
preferred_output:
  continuous: true
```

```text
用成交参与度或价格冲击代理构造流动性软门控，用于调节趋势、反转或形态信号可靠性。
```

### GATE04: Stress Transition Gate

```yaml
lens_id: regime_gating.stress_transition_gate
layer: stability_regime_gating
agent: regime_gating
title: Stress Transition Gate
title_zh: 压力转换门控
research_question: 主信号是否应在压力正在形成或正在消退时采用不同权重？
mechanism: 当前压力水平相同，但上升阶段和消退阶段对趋势、反转或流动性信号的含义可能不同。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [stress_score, stress_slope, transition_probability_proxy, soft_gate]
  relations: [stress_building, stress_releasing]
degenerate_patterns: [只按高低波动二值切换, gate 与主信号使用完全相同的信息, 不说明被门控信号]
allowed_roles: [gate, modifier]
preferred_output:
  continuous: true
  bounded: true
```

```text
构造压力状态的连续水平和变化方向，用软门控区分压力形成、维持和消退。必须明确门控对象及为什么转换方向会改变其可靠性。
```

### GATE05: Cross-Scale Agreement Gate

```yaml
lens_id: regime_gating.cross_scale_agreement_gate
layer: stability_regime_gating
agent: regime_gating
title: Cross-Scale Agreement Gate
title_zh: 跨尺度一致门控
research_question: 主信号是否只应在多个时间尺度对当前状态判断一致时增强？
mechanism: 局部状态与中期状态冲突时，单一窗口信号可能不稳定；连续一致度可作为可靠性门控。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [multi_horizon_state, agreement_score, soft_min, reliability_gate]
  relations: [state_consensus, scale_conflict]
degenerate_patterns: [多数投票式硬门控, 随意堆很多窗口, 与主信号重复计数]
allowed_roles: [gate, confirmation]
preferred_output:
  continuous: true
  bounded: true
```

```text
用少量时间尺度对同一状态变量做一致性判断，并形成连续可靠性 gate。不要用离散多数投票，也不要让 gate 重复主信号本身。
```

### GATE06: Signal Freshness Gate

```yaml
lens_id: regime_gating.signal_freshness_gate
layer: stability_regime_gating
agent: regime_gating
title: Signal Freshness Gate
title_zh: 信号新鲜度门控
research_question: 主信号是刚刚形成还是已经持续过久，是否应影响其当前权重？
mechanism: 某些冲击、突破或反转条件具有生命周期，过度陈旧的同一状态可能已被市场消化。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [signal_age, onset_strength, decay_weight, freshness_gate]
  relations: [newly_formed_signal, stale_signal]
degenerate_patterns: [任意固定持有期, 需要未来确认信号起点, 未声明被门控的主信号]
allowed_roles: [gate, modifier]
preferred_output:
  continuous: true
  bounded: true
```

```text
对已定义主信号识别其历史形成时点和持续年龄，构造连续新鲜度权重。生命周期必须来自机制假设，不能只是任意持有期规则。
```

## 输出检查

- 明确记录 `agent_tags: [regime_gating]`。
- 通常作为辅助 Lens 使用，必须说明被 gate 的主信号。
- 优先连续软门控，避免二值标签。
