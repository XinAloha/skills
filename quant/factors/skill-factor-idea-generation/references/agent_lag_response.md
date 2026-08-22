# AgentLagResponse Prompt Catalog

`AgentLagResponse` 属于 Level IV: Price-Volatility Behavior。本文件用于生成滞后响应和延迟反馈相关的初始因子想法。

## Agent 核心指令

```text
你是专注历史冲击滞后影响、延迟调整和跨变量反馈的量化研究员。
请提出连续、可计算、可解释的初始因子假设，用过去的收益、成交量或波动冲击解释当前信号状态。
只能使用正向历史滞后项，不得使用负 shift 或未来信息。
```

## Prompt Lenses

### LR01: Volume-to-Return Lag

```yaml
lens_id: lag_response.volume_to_return_lag
layer: price_volatility_behavior
agent: lag_response
title: Volume-to-Return Lag
title_zh: 成交量到收益滞后
research_question: 过去成交量冲击是否对当前价格行为产生滞后影响？
mechanism: 成交量异常可能代表信息进入市场，但价格调整可能分阶段完成。
construction_space:
  inputs: [close, volume]
  transforms: [lagged_volume_shock, current_return_state, decay_weight, delayed_response_score]
  relations: [volume_leads_price, delayed_adjustment]
degenerate_patterns: [使用未来收益, 只做 volume zscore, 不说明滞后方向]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
```

```text
研究过去成交量冲击对当前价格状态的滞后影响，所有滞后项必须来自历史数据。
```

### LR02: Volatility-to-Return Lag

```yaml
lens_id: lag_response.volatility_to_return_lag
layer: price_volatility_behavior
agent: lag_response
title: Volatility-to-Return Lag
title_zh: 波动到收益滞后
research_question: 过去波动冲击是否预示当前价格延迟调整或修复？
mechanism: 波动冲击可能先反映不确定性，价格方向调整随后展开。
construction_space:
  inputs: [close, high, low]
  transforms: [lagged_range_shock, lagged_volatility_shock, current_return, response_decay]
  relations: [volatility_leads_return, delayed_repricing]
degenerate_patterns: [使用未来窗口确认, 只输出波动率, 混入 crash 标签]
allowed_roles: [primary, modifier]
preferred_output:
  continuous: true
```

```text
使用历史 range 或收益波动冲击作为滞后输入，刻画当前价格是否正在延迟反应。不要使用未来窗口。
```

### LR03: Return Reversal Lag

```yaml
lens_id: lag_response.return_reversal_lag
layer: price_volatility_behavior
agent: lag_response
title: Return Reversal Lag
title_zh: 收益反应滞后
research_question: 过去收益冲击是否以延迟形式影响当前反转或延续？
mechanism: 市场对冲击的消化可能有延迟，不同滞后窗口的响应可揭示调整速度。
construction_space:
  inputs: [close]
  transforms: [lagged_return, multi_lag_decay, response_slope, delayed_reversal_score]
  relations: [slow_reaction, delayed_reversal]
degenerate_patterns: [简单负 momentum, 不区分滞后窗口, 使用未来收益]
allowed_roles: [primary, contrast]
preferred_output:
  continuous: true
```

```text
比较不同历史滞后收益对当前状态的影响，构造延迟反应或延迟反转分数。不要把它写成普通短期反转。
```

### LR04: Delayed Price-Volume Adjustment

```yaml
lens_id: lag_response.delayed_price_volume_adjustment
layer: price_volatility_behavior
agent: lag_response
title: Delayed Price-Volume Adjustment
title_zh: 价量延迟调整
research_question: 成交活动先变化而价格响应后出现时，延迟长度是否反映信息吸收速度？
mechanism: 参与度冲击可能先出现，价格随后分阶段调整；响应滞后越稳定，越可能代表结构性吸收节奏而非偶然相关。
construction_space:
  inputs: [close, volume]
  transforms: [lagged_volume_change, future_free_current_return, lag_profile, response_peak]
  relations: [volume_leads_price_adjustment, delayed_absorption]
degenerate_patterns: [用负 shift 构造未来收益特征, 只挑表现最好的滞后造成过拟合, 与单一 volume_to_return_lag 重复]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
比较多个预先限定的历史成交冲击滞后与当前价格响应，刻画响应峰值位置和延迟稳定性。所有特征在当前时点必须可得。
```

### LR05: Shock Response Half-Life

```yaml
lens_id: lag_response.shock_response_half_life
layer: price_volatility_behavior
agent: lag_response
title: Shock Response Half-Life
title_zh: 冲击响应半衰期
research_question: 价格或波动冲击对后续历史状态的影响衰减快慢，是否代表调整效率差异？
mechanism: 影响快速衰减可能表示冲击被吸收，长期残留则可能代表信息消化缓慢或状态黏性。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [shock_score, lagged_decay_profile, weighted_memory, half_life_proxy]
  relations: [fast_absorption, persistent_shock_memory]
degenerate_patterns: [等待未来样本估计半衰期, 使用无限滞后, 与简单自相关完全相同]
allowed_roles: [primary, modifier, stabilizer]
preferred_output:
  continuous: true
  numerically_stable: true
```

```text
用当前时点以前已经完成的冲击及其历史响应轨迹估计影响衰减速度，形成有限窗口半衰期代理。不要用未来路径确认当前冲击。
```

### LR06: Response Asymmetry

```yaml
lens_id: lag_response.response_asymmetry
layer: price_volatility_behavior
agent: lag_response
title: Response Asymmetry
title_zh: 滞后响应不对称
research_question: 相近幅度的正负冲击是否产生不同速度或强度的延迟响应？
mechanism: 市场对利好和利空、上行与下行波动的吸收速度可能不同，滞后差异可反映行为和流动性不对称。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [positive_shock_lags, negative_shock_lags, response_strength, lag_asymmetry]
  relations: [fast_negative_slow_positive, asymmetric_adjustment]
degenerate_patterns: [与静态上下行波动比重复, 事后挑选不同最优滞后, 使用未来响应]
allowed_roles: [primary, modifier, confirmation]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
用预先限定的历史滞后比较正负冲击与当前状态的响应强度，构造调整速度不对称。不得用未来收益定义当前响应。
```

## 输出检查

- 明确记录 `agent_tags: [lag_response]`。
- 所有 shift 必须是历史滞后，禁止负向未来 shift。
- 说明谁滞后影响谁。
