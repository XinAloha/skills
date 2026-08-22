# Layer 7: Geometric & Fusion

## 论文对齐范围

这一层关注 K 线几何结构、多特征融合和拥挤行为，包含四个 Agent：

- `AgentBarShape`：K 线几何、实体、影线、收盘位置。
- `AgentCreative`：非线性表达、软门控、重新参数化。
- `AgentComposite`：复合因子构造、信息融合、去冗余。
- `AgentHerding`：拥挤行为、方向一致性、市场共识强度。

## Agent Prompt 目录

- `AgentBarShape`：读取 [agent_bar_shape.md](agent_bar_shape.md)。
- `AgentCreative`：读取 [agent_creative.md](agent_creative.md)。
- `AgentComposite`：读取 [agent_composite.md](agent_composite.md)。
- `AgentHerding`：读取 [agent_herding.md](agent_herding.md)。

## 层内组合原则

- `BarShape` 提供几何主信号，`Creative` 提供表达变换，`Composite` 提供融合语法。
- `Herding` 只有在允许横截面时才能使用同日 `date` 分组；否则只能用个股内部方向压力近似。
- 推荐组合：`bar_shape.shadow_balance` + `price_volume_coherence.volume_exhaustion`，用量能确认形态吸收。
- 推荐组合：`composite.orthogonal_confirmation` + `creative.bounded_transform`，先确认互补机制，再做稳健压缩。

## 常见坑

- 只描述形态名字，不解释行为机制。
- 把视觉上“像”的图形当成稳健 alpha。
- 融合太多弱信号，最后不可解释。
- Creative 只负责变复杂，而没有经济含义。
