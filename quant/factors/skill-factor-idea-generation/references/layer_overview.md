# Layer Overview

这个 skill 用七层研究视角组织初始因子想法。它们不是固定公式库，而是七种不同的“观察市场”的方式。

## 七层总览

1. `market_structure_cycle`
   关注趋势、反转、通道、位置、阶段切换和局部周期。
2. `extreme_risk_fragility`
   关注极端波动、脆弱状态、挤压、恐慌、失衡与尾部风险。
3. `price_volume_dynamics`
   关注量价配合、成交确认、放量失效、缩量漂移和资金参与度。
4. `price_volatility_behavior`
   关注波动压缩、波动释放、收益与波动联动、波动不对称。
5. `multiscale_complexity`
   关注不同时间尺度上的一致性、冲突、粗糙度和结构复杂性。
6. `stability_regime_gating`
   关注市场状态识别、稳定期与失稳期、信号开关和 regime gating。
7. `geometric_fusion`
   关注 K 线几何形态、上下影线、实体结构，以及多特征融合。

## 如何选择

- 用户没有指定方向：可从所有适用 Lens 中随机选择，不额外施加 Layer 覆盖配额。
- 用户强调“市场阶段/趋势逻辑”：优先 1、6。
- 用户强调“风险、崩塌、脆弱性”：优先 2、4。
- 用户强调“量价关系”：优先 3。
- 用户强调“多周期共振或冲突”：优先 5。
- 用户强调“K 线形态或多特征组合”：优先 7。

## 当前 Lens 目录

| Layer | Agent 数 | Lens 数 |
|---|---:|---:|
| `market_structure_cycle` | 2 | 10 |
| `extreme_risk_fragility` | 2 | 10 |
| `price_volume_dynamics` | 4 | 22 |
| `price_volatility_behavior` | 5 | 29 |
| `multiscale_complexity` | 2 | 13 |
| `stability_regime_gating` | 2 | 12 |
| `geometric_fusion` | 4 | 23 |
| **合计** | **21** | **119** |

这些数字描述当前目录，不是每轮生成的抽样配额。Lens 数量可以随新的、可区分的经济机制继续扩充。

用户提供的 Research Context 和 Custom Lens Pack 不计入内置 `119` 个 Lens。它们先按 `custom_lens_schema.md` 校验，再临时合并到本轮目录；默认不会修改本表。
