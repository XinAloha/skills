# AgentFractal Prompt Catalog

`AgentFractal` 属于 Level V: Multi-Scale Complexity。本文件用于生成多尺度粗糙度、长记忆和跨窗口结构相关的初始因子想法。

## Agent 核心指令

```text
你是专注多尺度复杂度、路径粗糙度和跨窗口结构的量化研究员。
请提出连续、可计算、可解释的初始因子假设，用不同窗口的收益、波动、range 或路径效率构造复杂度代理。
避免昂贵的嵌套循环 fractal 算法。
```

## Prompt Lenses

### FR01: Cross-Horizon Consistency

```yaml
lens_id: fractal.cross_horizon_consistency
layer: multiscale_complexity
agent: fractal
title: Cross-Horizon Consistency
title_zh: 跨周期一致性
research_question: 短中长窗口的方向或强度是否一致？
mechanism: 多尺度一致可能代表结构更稳定，多尺度冲突可能代表转折或噪声。
construction_space:
  inputs: [close]
  transforms: [multi_window_return, sign_agreement, rank_consistency, scale_alignment]
  relations: [multi_horizon_confirmation, horizon_conflict]
degenerate_patterns: [盲目堆多个窗口, 只做多个收益相加, 不解释窗口关系]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
```

```text
比较短中长窗口收益或趋势方向的一致性，构造多尺度确认或冲突分数。不要只是堆叠多个窗口动量。
```

### FR02: Path Roughness

```yaml
lens_id: fractal.path_roughness
layer: multiscale_complexity
agent: fractal
title: Path Roughness
title_zh: 路径粗糙度
research_question: 价格路径是顺滑推进还是高频折返？
mechanism: 净位移相对路径长度较低表示路径粗糙，信号可能更噪声化。
construction_space:
  inputs: [close]
  transforms: [net_displacement, absolute_path_length, efficiency_ratio, roughness_score]
  relations: [smooth_path, noisy_path]
degenerate_patterns: [复杂不可解释 fractal 公式, 不做除零保护, 和 stability 完全重复]
allowed_roles: [primary, stabilizer]
preferred_output:
  continuous: true
  bounded: true
```

```text
用净位移与绝对路径长度的关系构造路径粗糙度，区分顺滑趋势和反复折返的噪声路径。
```

### FR03: Scaling Ratio

```yaml
lens_id: fractal.scaling_ratio
layer: multiscale_complexity
agent: fractal
title: Scaling Ratio
title_zh: 尺度比例
research_question: 不同窗口下收益或波动的增长是否符合稳定尺度关系？
mechanism: 多尺度波动或收益的比例异常可能代表结构状态变化或复杂度上升。
construction_space:
  inputs: [close, high, low]
  transforms: [short_long_vol_ratio, variance_ratio, range_scaling, normalized_scaling_error]
  relations: [stable_scaling, scaling_break]
degenerate_patterns: [只比较两个波动率, 不解释尺度含义, 使用嵌套循环估计复杂指标]
allowed_roles: [primary, modifier]
preferred_output:
  continuous: true
```

```text
比较不同时间尺度上的收益波动或 range 变化，构造尺度比例或尺度破裂代理。保持公式简洁可审计。
```

### FR04: Multiscale Directional Disagreement

```yaml
lens_id: fractal.multiscale_directional_disagreement
layer: multiscale_complexity
agent: fractal
title: Multiscale Directional Disagreement
title_zh: 多尺度方向分歧
research_question: 短中长时间尺度的方向和强度冲突是否代表结构转折或噪声升高？
mechanism: 局部趋势可能与长期结构相反；分歧的分布和变化速度比单一短长差更能描述尺度间张力。
construction_space:
  inputs: [close]
  transforms: [multi_horizon_return, normalized_direction, disagreement_index, disagreement_change]
  relations: [local_vs_global_conflict, broad_scale_alignment]
degenerate_patterns: [只做短期收益减长期收益, 堆过多任意窗口, 不区分方向冲突和幅度冲突]
allowed_roles: [primary, contrast, gate]
preferred_output:
  continuous: true
  bounded: optional
```

```text
用少量预先定义的短中长窗口构造方向和标准化强度分歧，刻画冲突程度及其变化。不要把多尺度等同于无限堆窗口。
```

### FR05: Scale-Localized Shock

```yaml
lens_id: fractal.scale_localized_shock
layer: multiscale_complexity
agent: fractal
title: Scale-Localized Shock
title_zh: 尺度局部冲击
research_question: 当前异常主要集中在短尺度，还是已经扩散到更长尺度？
mechanism: 只在短尺度显著的冲击可能是局部噪声，跨尺度同步放大则可能表示结构状态已改变。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [scale_specific_energy, normalized_scale_share, concentration_index, propagation_score]
  relations: [short_scale_localization, cross_scale_propagation]
degenerate_patterns: [只做短长波动比, 不衡量能量在尺度间的分配, 使用复杂频域算法而无法实现]
allowed_roles: [primary, modifier, confirmation]
preferred_output:
  continuous: true
  scale_normalized: true
```

```text
将收益、range 或成交冲击的能量分配到少量时间尺度，判断异常是局部集中还是跨尺度扩散。因子应保持简单可实现，不要求复杂频域分解。
```

### FR06: Multiscale Persistence Decay

```yaml
lens_id: fractal.multiscale_persistence_decay
layer: multiscale_complexity
agent: fractal
title: Multiscale Persistence Decay
title_zh: 多尺度持续性衰减
research_question: 方向持续性从短尺度扩展到长尺度时，是保持、增强还是快速消失？
mechanism: 只存在于短尺度的持续性可能是局部噪声，能够跨尺度保留则可能反映更稳定结构。
construction_space:
  inputs: [close]
  transforms: [scale_specific_persistence, persistence_curve, decay_slope, normalized_decay]
  relations: [short_lived_persistence, scale_robust_persistence]
degenerate_patterns: [只比较两个窗口的动量, 堆叠大量窗口, 将持续性衰减写成未来方向预测]
allowed_roles: [primary, confirmation, stabilizer]
preferred_output:
  continuous: true
  scale_normalized: true
```

```text
在少量时间尺度上估计同一方向持续性，并描述其随尺度增加的衰减曲线。重点是结构能否跨尺度保留，而不是短长动量差。
```

### FR07: Trajectory Self-Similarity

```yaml
lens_id: fractal.trajectory_self_similarity
layer: multiscale_complexity
agent: fractal
title: Trajectory Self-Similarity
title_zh: 轨迹自相似性
research_question: 近期标准化价格路径是否重复出现与较长历史子路径相似的几何结构？
mechanism: 跨尺度路径形态的一致可能表明行为过程具有稳定结构，明显失配则可能代表状态变化。
construction_space:
  inputs: [close]
  transforms: [normalized_subpath, coarse_graining, path_distance, self_similarity_score]
  relations: [repeating_path_geometry, structural_break]
degenerate_patterns: [昂贵的全历史模式搜索, 用未来完整路径匹配, 把相似图形直接解释为相同未来]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  computationally_bounded: true
```

```text
使用固定、有限的历史窗口和粗粒化轨迹，比较不同尺度下已发生路径的标准化几何相似度。不得搜索未来结局，也不得承诺相似路径产生相同结果。
```

## 输出检查

- 明确记录 `agent_tags: [fractal]`。
- 不实现昂贵或不可解释的复杂算法。
- 必须说明多尺度关系的经济含义。
