# AgentRangeVol Prompt Catalog

`AgentRangeVol` 属于 Level IV: Price-Volatility Behavior。本文件用于生成 high-low range 和区间波动动态相关的初始因子想法。

## Agent 核心指令

```text
你是专注日频 high-low range、区间压缩扩张和 range-based volatility 的量化研究员。
请提出连续、可计算、可解释的初始因子假设，用 range/close、true-range proxy、短长 range 比例和区间状态变化刻画价格波动行为。
不要只输出普通历史波动率。
```

## Prompt Lenses

### RG01: Range Compression

```yaml
lens_id: range_vol.range_compression
layer: price_volatility_behavior
agent: range_vol
title: Range Compression
title_zh: 区间压缩
research_question: high-low range 是否持续压缩，暗示后续波动状态变化？
mechanism: range 压缩反映日内价格探索收敛，可能酝酿突破或状态切换。
construction_space:
  inputs: [high, low, close]
  transforms: [range_ratio, short_long_range_ratio, compression_duration, rolling_rank]
  relations: [sustained_narrow_range, compressed_state]
degenerate_patterns: [只输出 ATR, 不衡量持续压缩, 和 MarketCycle 的周期转换混淆]
allowed_roles: [primary, gate]
preferred_output:
  continuous: true
```

```text
用 high-low range 相对价格和历史窗口的压缩程度，构造连续区间压缩分数。重点是 range 状态，不是趋势方向。
```

### RG02: Range Expansion Decay

```yaml
lens_id: range_vol.range_expansion_decay
layer: price_volatility_behavior
agent: range_vol
title: Range Expansion Decay
title_zh: 区间扩张衰减
research_question: range 扩张后是否快速衰减，暗示冲击释放或波动回落？
mechanism: 异常 range 扩张可能是冲击释放，之后的衰减路径可反映波动状态恢复。
construction_space:
  inputs: [high, low, close]
  transforms: [range_shock, range_decay, expansion_persistence, normalized_range_change]
  relations: [shock_release, volatility_cooling]
degenerate_patterns: [只看单日大振幅, 使用未来衰减确认, 不做尺度归一化]
allowed_roles: [primary, confirmation]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
研究异常 high-low range 扩张后，历史上最近几日是否出现衰减或持续，构造区间波动释放分数。
```

### RG03: Close-Range Efficiency

```yaml
lens_id: range_vol.close_range_efficiency
layer: price_volatility_behavior
agent: range_vol
title: Close-Range Efficiency
title_zh: 区间收盘效率
research_question: 给定日内 range，收盘是否有效完成方向推进？
mechanism: 大 range 但净推进弱可能表示波动噪声高，大 range 且收盘方向明确可能表示有效波动。
construction_space:
  inputs: [open, high, low, close]
  transforms: [body_to_range, close_location_value, range_efficiency, signed_efficiency]
  relations: [efficient_range_move, noisy_range_move]
degenerate_patterns: [只用 body/range 不结合方向, 不处理 high=low, 和 BarShape 完全重叠]
allowed_roles: [primary, modifier]
preferred_output:
  continuous: true
```

```text
衡量 high-low range 中有多少转化为有效实体或收盘推进，用于区分有效波动和噪声波动。
```

### RG04: Range Shock Memory

```yaml
lens_id: range_vol.range_shock_memory
layer: price_volatility_behavior
agent: range_vol
title: Range Shock Memory
title_zh: 区间冲击记忆
research_question: 异常 high-low range 的影响会持续多久，当前波动是否仍受历史冲击支配？
mechanism: 波动冲击可能形成短期记忆；快速消散与持续高 range 分别代表冲击吸收和未解决不确定性。
construction_space:
  inputs: [high, low, close]
  transforms: [normalized_range, shock_indicator_soft, decay_weight, persistence_half_life]
  relations: [persistent_range_shock, absorbed_range_shock]
degenerate_patterns: [只做 range 自相关, 用未来衰减确认, 与单纯 range 扩张完全重复]
allowed_roles: [primary, modifier, gate]
preferred_output:
  continuous: true
  path_dependent: true
```

```text
识别已发生的 range 冲击并衡量其在后续历史观察中的衰减速度，构造当前冲击记忆强度。不要只输出当前 range 水平。
```

### RG05: Overnight-Intraday Volatility Allocation

```yaml
lens_id: range_vol.overnight_intraday_allocation
layer: price_volatility_behavior
agent: range_vol
title: Overnight-Intraday Volatility Allocation
title_zh: 隔夜与日内波动分配
research_question: 总价格变化更多发生在隔夜跳变还是日内价格探索中？
mechanism: 隔夜和日内承载不同的信息吸收过程，其相对贡献变化可能反映定价时段和风险暴露结构变化。
construction_space:
  inputs: [open, high, low, close]
  transforms: [overnight_move, intraday_range, intraday_body, normalized_allocation]
  relations: [overnight_dominance, intraday_discovery_dominance]
degenerate_patterns: [只比较两个绝对收益, 忽略尺度归一化, 把时段分配直接解释为方向预测]
allowed_roles: [primary, modifier, confirmation]
preferred_output:
  continuous: true
  bounded: optional
```

```text
比较隔夜跳变与日内 range 或实体对近期总波动的贡献，刻画价格发现发生在哪个时段。该 Lens 表达波动分配，不直接给出看涨看跌结论。
```

### RG06: Range-Direction Coupling

```yaml
lens_id: range_vol.range_direction_coupling
layer: price_volatility_behavior
agent: range_vol
title: Range-Direction Coupling
title_zh: 区间与方向耦合
research_question: range 扩张是否稳定地伴随同一方向净推进，还是主要表现为无方向噪声？
mechanism: 波动扩张若与方向推进耦合，可能代表有效价格发现；扩张但净方向不稳定则更像分歧和噪声。
construction_space:
  inputs: [open, high, low, close]
  transforms: [normalized_range, signed_body, rolling_coupling, coupling_stability]
  relations: [directional_volatility, directionless_range]
degenerate_patterns: [只做 range 乘收益, 与单日 close_range_efficiency 重复, 把高耦合直接等同于未来趋势]
allowed_roles: [primary, confirmation, modifier]
preferred_output:
  continuous: true
  direction_interpretable: true
```

```text
在历史窗口中衡量 range 变化与带方向净推进的耦合程度和稳定性，区分持续方向性波动与无方向价格探索。
```

## 输出检查

- 明确记录 `agent_tags: [range_vol]`。
- 关注 range-based volatility，不要泛化成所有波动状态。
- 对 high 等于 low 做保护。
