# Layer 3: Price-Volume Dynamics

## 论文对齐范围

这一层关注价格与成交量如何相互确认、背离、传导或失效，包含四个 Agent：

- `AgentLiquidity`：流动性代理、价格冲击、交易摩擦。
- `AgentOrderImbalance`：用日频 OHLCV 推断方向性参与压力。
- `AgentPriceVolumeCoherence`：价格与成交量同步、背离和能量一致性。
- `AgentVolumeStructure`：成交量结构、参与节奏和成交聚集。

## Agent Prompt 目录

- `AgentLiquidity`：读取 [agent_liquidity.md](agent_liquidity.md)。
- `AgentOrderImbalance`：读取 [agent_order_imbalance.md](agent_order_imbalance.md)。
- `AgentPriceVolumeCoherence`：读取 [agent_price_volume_coherence.md](agent_price_volume_coherence.md)。
- `AgentVolumeStructure`：读取 [agent_volume_structure.md](agent_volume_structure.md)。

## 层内组合原则

- 同时选中两个 Agent 时，一个必须提供主机制，另一个只做确认、门控或强度调节。
- 推荐组合：`price_volume_coherence.volume_exhaustion` + `order_imbalance.close_location_pressure`，用收盘位置确认量能衰竭方向。
- 推荐组合：`liquidity.price_impact_per_volume` + `volume_structure.volume_concentration`，用成交集中度解释价格冲击是否脆弱。
- 不得声称拥有真实盘口、订单流、换手率或资金流字段，除非用户明确提供。

## 常见坑

- 只算价格和成交量相关系数，没有解释其经济含义。
- 混淆“低量确认”和“流动性缺失”。
- 用单一窗口度量所有量价关系。
- 把真实订单簿概念写进 OHLCV-only 输入。
