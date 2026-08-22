# AgentComposite Prompt Catalog

`AgentComposite` 属于 Level VII: Geometric & Fusion。本文件用于生成多信号融合、去冗余和协同表达相关的初始因子想法。

## Agent 核心指令

```text
你是专注复合因子构造、信息融合和去冗余的量化研究员。
请提出由 2 个互补机制组成的简洁复合 seed idea，并明确主信号、辅助信号和组合算子。
不要简单平均一堆普通指标。
```

## Prompt Lenses

### CMP01: Orthogonal Confirmation

```yaml
lens_id: composite.orthogonal_confirmation
layer: geometric_fusion
agent: composite
title: Orthogonal Confirmation
title_zh: 正交确认
research_question: 一个主信号是否能被信息来源不同的辅助信号确认？
mechanism: 来自价格、成交量、波动或形态的不同信息源若一致，信号可信度可能更高。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [normalize, confirmation_score, smooth_product, reliability_weight]
  relations: [price_confirmed_by_volume, trend_confirmed_by_shape]
degenerate_patterns: [简单平均多个指标, 组合高度同质信号, 不说明主辅关系]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
```

```text
选择一个主机制，再选择一个信息来源不同的确认机制，构造简洁复合信号。必须说明为什么两者互补。
```

### CMP02: De-Redundant Fusion

```yaml
lens_id: composite.de_redundant_fusion
layer: geometric_fusion
agent: composite
title: De-Redundant Fusion
title_zh: 去冗余融合
research_question: 多个相关信号如何融合而不重复计数？
mechanism: 同类信号高度相关时，直接相加会重复计数，去冗余融合应保留共同方向同时降低重复噪声。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [normalized_component, residual_proxy, capped_weight, de_redundant_score]
  relations: [avoid_double_counting, complementary_components]
degenerate_patterns: [堆叠多个同类窗口, 复杂回归残差不可实现, 无解释权重]
allowed_roles: [primary, stabilizer]
preferred_output:
  continuous: true
```

```text
融合两个相关但不完全相同的信号时，说明如何避免重复计数，并保持公式可实现。不要做无解释的大杂烩。
```

### CMP03: Regime-Weighted Composite

```yaml
lens_id: composite.regime_weighted_composite
layer: geometric_fusion
agent: composite
title: Regime-Weighted Composite
title_zh: 状态加权复合
research_question: 不同市场状态下，两个子信号的权重是否应动态变化？
mechanism: 趋势、反转、风险或形态信号可能只在特定状态下更可靠，状态权重可提升解释一致性。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [regime_score, smooth_weight, weighted_sum, gated_component]
  relations: [dynamic_weight_by_state]
degenerate_patterns: [硬切换, 权重过多, 不说明状态和子信号关系]
allowed_roles: [primary, gate]
preferred_output:
  continuous: true
  bounded: optional
```

```text
用一个连续状态分数在两个互补子信号之间平滑调权。复合结构必须简洁，最多两个核心子信号。
```

### CMP04: Reliability-Weighted Fusion

```yaml
lens_id: composite.reliability_weighted_fusion
layer: geometric_fusion
agent: composite
title: Reliability-Weighted Fusion
title_zh: 可靠性加权融合
research_question: 两个互补信号能否根据各自当前可靠性动态分配权重？
mechanism: 子信号在不同状态下噪声和稳定性不同，可靠性权重可让更可信的机制主导，同时保持最多两个核心来源。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [normalized_component, reliability_score, convex_weight, weighted_fusion]
  relations: [adaptive_reliability_balance]
degenerate_patterns: [用历史未来收益估计权重, 权重本身比信号更复杂, 融合超过两个核心机制]
allowed_roles: [primary, stabilizer]
preferred_output:
  continuous: true
  numerically_stable: true
```

```text
选择两个机制互补的子信号，并仅用当前及历史可观测稳定性构造连续可靠性权重。权重应简单、可解释且总和稳定。
```

### CMP05: Mechanism Tension Composite

```yaml
lens_id: composite.mechanism_tension
layer: geometric_fusion
agent: composite
title: Mechanism Tension Composite
title_zh: 机制张力复合
research_question: 两个方向相反但各自合理的机制之间的张力，是否比简单选择其一更有信息？
mechanism: 趋势推进与反转压力、参与增强与流动性恶化等冲突可刻画状态成熟度和潜在转折。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [normalized_primary, normalized_counterforce, signed_difference, tension_intensity]
  relations: [trend_vs_reversal, participation_vs_fragility]
degenerate_patterns: [随意相减两个指标, 两个机制本质同质, 不说明分数正负方向]
allowed_roles: [primary, contrast]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
选择两个确有经济冲突的机制，在可比尺度上表达主导力量与反向力量的张力。必须说明正负方向和为什么冲突本身值得研究。
```

### CMP06: Sequential Confirmation

```yaml
lens_id: composite.sequential_confirmation
layer: geometric_fusion
agent: composite
title: Sequential Confirmation
title_zh: 时序确认融合
research_question: 主机制先发生、辅助确认随后出现的顺序关系，是否比同时相乘更符合信息演化过程？
mechanism: 冲击、吸收、恢复等机制具有先后顺序；确认信号若在合理历史滞后出现，可区分过程是否按假设发展。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [primary_event_score, lagged_confirmation, sequence_alignment, bounded_product]
  relations: [event_then_confirmation, invalid_sequence]
degenerate_patterns: [使用未来确认, 事后搜索最佳顺序, 把两个同时信号硬拆成先后]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
选择具有明确经济先后关系的两个机制，只使用当前及历史数据构造主事件和滞后确认的顺序一致度。若不存在合理顺序，不得强行使用此 Lens。
```

## 输出检查

- 明确记录 `agent_tags: [composite]`。
- 必须说明主信号、辅助信号和 `composition_operator`。
- 避免简单平均、堆叠和不可解释权重。
