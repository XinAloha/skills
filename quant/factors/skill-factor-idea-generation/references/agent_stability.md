# AgentStability Prompt Catalog

`AgentStability` 属于 Level VI: Stability & Regime-Gating。本文件用于生成信号稳定性、时间一致性和稳健调整相关的初始因子想法。

## Agent 核心指令

```text
你是专注信号稳定性、时间一致性和稳健表达的量化研究员。
请提出连续、可计算、可解释的初始因子假设，用持久性、翻转频率、噪声惩罚或可靠性权重调整主信号。
不要把过度平滑做成无效常数。
```

## Prompt Lenses

### ST01: Signal Persistence

```yaml
lens_id: stability.signal_persistence
layer: stability_regime_gating
agent: stability
title: Signal Persistence
title_zh: 信号持续性
research_question: 主信号自身是否在历史上稳定延续，而不是频繁翻转？
mechanism: 持续性高的信号更可能表达稳定状态，频繁翻转的信号更可能是噪声。
construction_space:
  inputs: [close, volume, high, low]
  transforms: [signal_sign_persistence, rolling_consistency, flip_rate, persistence_weight]
  relations: [stable_signal, noisy_signal]
degenerate_patterns: [只做平滑, 没有主信号, 使用未来一致性]
allowed_roles: [stabilizer, confirmation]
preferred_output:
  continuous: true
```

```text
衡量主信号在历史窗口内的方向或强度是否持续，用作可靠性权重。必须说明主信号是什么。
```

### ST02: Noise Penalty

```yaml
lens_id: stability.noise_penalty
layer: stability_regime_gating
agent: stability
title: Noise Penalty
title_zh: 噪声惩罚
research_question: 当前路径噪声是否过高，应该降低信号权重？
mechanism: 高噪声路径下，同样的方向信号可能更不可靠。
construction_space:
  inputs: [close, high, low]
  transforms: [path_noise, range_noise, volatility_noise, reliability_discount]
  relations: [discount_noisy_signal]
degenerate_patterns: [只输出波动率, 过度惩罚导致信号近零, 不说明被惩罚对象]
allowed_roles: [stabilizer, modifier]
preferred_output:
  continuous: true
  bounded: optional
```

```text
用路径噪声或 range 噪声构造主信号的可靠性折扣。该 Lens 通常不单独作为完整 alpha。
```

### ST03: Robust Drift

```yaml
lens_id: stability.robust_drift
layer: stability_regime_gating
agent: stability
title: Robust Drift
title_zh: 稳健漂移
research_question: 小幅但持续一致的漂移是否比单点极端变化更稳健？
mechanism: 稳健因子常来自连续小信号的累积，而不是少数极端点。
construction_space:
  inputs: [close]
  transforms: [small_return_accumulation, outlier_clipping, drift_consistency, robust_sum]
  relations: [persistent_small_drift]
degenerate_patterns: [过度裁剪成常数, 只做 N 日收益, 忽略方向持续性]
allowed_roles: [primary, stabilizer]
preferred_output:
  continuous: true
```

```text
强调连续小幅漂移和异常值抑制，构造稳健方向信号。不要把它写成普通动量或无效平滑。
```

### ST04: Neighboring-Window Robustness

```yaml
lens_id: stability.neighboring_window_robustness
layer: stability_regime_gating
agent: stability
title: Neighboring-Window Robustness
title_zh: 邻近窗口稳健性
research_question: 主信号在相邻合理窗口下是否保持方向和相对强度？
mechanism: 仅在单一精确窗口出现的信号更可能是参数偶然性，相邻窗口一致可提供结构稳健性代理。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [neighbor_window_signals, dispersion, sign_agreement, robustness_weight]
  relations: [parameter_stable_signal, window_sensitive_signal]
degenerate_patterns: [为了稳健性堆大量窗口, 选择事后最优窗口, 直接平均同质信号造成重复计数]
allowed_roles: [stabilizer, confirmation]
preferred_output:
  continuous: true
  bounded: true
```

```text
对主信号使用少量预先约定的邻近窗口，衡量方向一致性和强度离散度，并将其作为稳健权重。该 Lens 不能独立替代主机制。
```

### ST05: Outlier Dependence Penalty

```yaml
lens_id: stability.outlier_dependence_penalty
layer: stability_regime_gating
agent: stability
title: Outlier Dependence Penalty
title_zh: 极端点依赖惩罚
research_question: 当前信号是否主要由窗口内极少数异常观测贡献？
mechanism: 由单个极端日支配的信号通常对样本和窗口敏感，降低极端点贡献可表达信号可靠性。
construction_space:
  inputs: [close, high, low, volume]
  transforms: [top_contribution_share, winsorized_difference, leave_one_out_proxy, concentration_penalty]
  relations: [distributed_evidence, outlier_driven_signal]
degenerate_patterns: [无理由全局截尾, 使用昂贵逐点循环, 把极端风险信号本身全部删除]
allowed_roles: [stabilizer, modifier]
preferred_output:
  continuous: true
  numerically_stable: true
```

```text
衡量主信号在历史窗口内是否由少数极端观测主导，并构造连续可靠性惩罚。保留有经济含义的极端事件，只惩罚无意中的单点依赖。
```

### ST06: Cross-Proxy Consistency

```yaml
lens_id: stability.cross_proxy_consistency
layer: stability_regime_gating
agent: stability
title: Cross-Proxy Consistency
title_zh: 多代理一致性
research_question: 同一经济机制由两种不同 OHLCV 代理衡量时，方向是否一致？
mechanism: 例如趋势同时由净位移和斜率支持，比同一公式换窗口更能提供机制层面的可靠性。
construction_space:
  inputs: [open, high, low, close, volume]
  transforms: [proxy_a, proxy_b, normalized_agreement, disagreement_penalty]
  relations: [mechanism_confirmed_across_proxies, proxy_conflict]
degenerate_patterns: [两个代理本质公式相同, 用多个同窗口版本伪装多代理, 不说明共同经济机制]
allowed_roles: [stabilizer, confirmation]
preferred_output:
  continuous: true
  bounded: true
```

```text
为同一经济机制选择两个计算路径不同的 OHLCV 代理，衡量方向和强度一致性。它只提供可靠性，不得重复主信号信息。
```

## 输出检查

- 明确记录 `agent_tags: [stability]`。
- 如果作为辅助 Lens，必须说明被调整的主信号。
- 不使用未来稳定性确认。
