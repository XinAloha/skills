# Layer 2: Extreme Risk & Fragility

## 论文对齐范围

这一层关注极端状态和系统脆弱性，包含两个 Agent：

- `AgentTailRisk`：下行敏感性、尾部风险暴露、负面冲击传播。
- `AgentCrashPredictor`：崩盘前兆、压力累积、流动性枯竭和结构脆弱性。

不要把这一层泛化为所有反转、波动或回撤问题。`Reversal` 属于 Level IV，`Drawdown` 属于 Level V，`VolatilityRegime` 属于 Level I。

## Agent Prompt 目录

- `AgentTailRisk`：读取 [agent_tail_risk.md](agent_tail_risk.md)。
- `AgentCrashPredictor`：读取 [agent_crash_predictor.md](agent_crash_predictor.md)。

## 适合的原始信号

- 极端日收益
- 高波动区间
- 异常长上影或下影
- 放量与大幅波动共振
- 弱收盘位置
- 成交量枯竭或价格冲击上升

## 层内组合原则

- 只选一个 Agent 时，保持其专业边界。
- 同时选中 `TailRisk` 和 `CrashPredictor` 时，一个必须作为主机制，另一个只做确认或压力调节。
- 推荐组合：`tail_risk.downside_semivariance_concentration` + `crash_predictor.stress_accumulation`，用压力累积确认下行尾部暴露。
- 推荐组合：`crash_predictor.fragile_calm` + `tail_risk.left_tail_asymmetry`，用左尾不对称确认脆弱平静是否偏向下行风险。
- 不得用未来 crash、未来最大回撤或未来收益路径定义当前信号。

## 常见坑

- 把所有极端波动都当成反转
- 忽略系统性风险下的持续踩踏
- 忽略成交量确认，误把低流动性噪声当成 fragility
- 把已经发生的大跌检测器写成 crash precursor
- 把尾部风险暴露和崩盘前兆混成一个不可解释的大杂烩
