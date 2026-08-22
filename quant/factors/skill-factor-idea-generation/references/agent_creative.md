# AgentCreative Prompt Catalog

`AgentCreative` 属于 Level VII: Geometric & Fusion。本文件用于生成非线性表达、重新参数化和探索性特征构造相关的初始因子想法。

## Agent 核心指令

```text
你是专注非线性表达、软门控、重新参数化和探索性特征构造的量化研究员。
请提出新颖但可解释、可实现的初始因子假设。
不要为了复杂而复杂，每个变换都必须保留金融直觉。
```

## Prompt Lenses

### CR01: Bounded Transform

```yaml
lens_id: creative.bounded_transform
layer: geometric_fusion
agent: creative
title: Bounded Transform
title_zh: 有界变换
research_question: 常规信号是否可以通过有界变换提高稳健性？
mechanism: tanh、sigmoid、rank-like clipping 可降低极端值影响，使信号更稳健。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [tanh, sigmoid_proxy, clipping, robust_scaling]
  relations: [outlier_control, stable_non_linear_signal]
degenerate_patterns: [无理由套非线性函数, 堆叠多重变换, 变换后经济含义消失]
allowed_roles: [modifier, stabilizer]
preferred_output:
  continuous: true
  bounded: true
```

```text
选择一个有清晰经济含义的基础信号，并用有界变换控制极端值。必须说明为什么需要非线性压缩。
```

### CR02: Smooth Interaction

```yaml
lens_id: creative.smooth_interaction
layer: geometric_fusion
agent: creative
title: Smooth Interaction
title_zh: 平滑交互
research_question: 两个互补信号是否可以通过平滑交互表达非线性协同？
mechanism: 某些机制只有在另一个状态较强时才有意义，平滑交互可表达连续协同。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [normalized_signal, soft_gate, smooth_product, interaction_score]
  relations: [conditional_effect, synergy]
degenerate_patterns: [随意相乘, 同类冗余信号交互, 不说明主辅关系]
allowed_roles: [primary, modifier]
preferred_output:
  continuous: true
```

```text
把一个主机制和一个辅助状态用平滑交互连接，表达条件性或协同效应。不要无解释地相乘多个指标。
```

### CR03: Reparameterized Ratio

```yaml
lens_id: creative.reparameterized_ratio
layer: geometric_fusion
agent: creative
title: Reparameterized Ratio
title_zh: 重参数比例
research_question: 常规比例信号是否可以通过更稳定的参数化表达？
mechanism: 对比例、差值和归一化项进行稳健重参数化，可减少极端分母和尺度问题。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [log_ratio, symmetric_ratio, epsilon_stabilized_ratio, normalized_difference]
  relations: [stable_relative_strength]
degenerate_patterns: [只换公式外观, 分母不稳定, 无经济解释]
allowed_roles: [primary, stabilizer]
preferred_output:
  continuous: true
  numerically_stable: true
```

```text
将一个有经济含义的相对强弱关系改写成更稳定的比例或对称差值表达。不要只做数学换皮。
```

### CR04: Monotonic Saturation

```yaml
lens_id: creative.monotonic_saturation
layer: geometric_fusion
agent: creative
title: Monotonic Saturation
title_zh: 单调饱和表达
research_question: 基础机制的边际作用是否随强度增加而递减，而非无限线性放大？
mechanism: 很多市场机制在中等强度时信息增加，但极端区间受容量、涨跌停或异常值影响，边际信息可能饱和。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [signed_log1p, rational_saturation, tanh, robust_scale]
  relations: [diminishing_marginal_effect, preserved_monotonicity]
degenerate_patterns: [与 bounded_transform 仅换函数名字, 无基础经济机制, 变换改变原信号方向]
allowed_roles: [modifier, stabilizer]
preferred_output:
  continuous: true
  bounded: optional
```

```text
仅在存在“强度增加但边际信息递减”的机制依据时，对基础信号使用保方向的单调饱和表达。明确变换前后含义和饱和原因。
```

### CR05: Signed Magnitude Decomposition

```yaml
lens_id: creative.signed_magnitude_decomposition
layer: geometric_fusion
agent: creative
title: Signed Magnitude Decomposition
title_zh: 方向与幅度分解
research_question: 将信号方向和置信幅度分别建模，是否能避免正负状态被同一线性尺度混淆？
mechanism: 方向来源与强度来源可能不同；先确定经济方向，再用独立可靠性或幅度项调节，可保持解释清晰。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [direction_component, magnitude_component, reliability_scale, signed_interaction]
  relations: [direction_times_confidence, asymmetric_magnitude]
degenerate_patterns: [把任何信号拆成 sign 和 abs 后原样相乘, 方向项和幅度项来自同一信息重复计数, 使用硬符号造成不连续]
allowed_roles: [primary, modifier]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
从不同但互补的信息构造平滑方向项和非负幅度或置信项，再组合为可解释信号。若分解后等价于原公式，不得视为新想法。
```

## 输出检查

- 明确记录 `agent_tags: [creative]`。
- 新颖性必须服务于经济含义和稳定性。
- 不允许无理由堆复杂变换。
