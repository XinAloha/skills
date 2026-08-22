# Layer 6: Stability & Regime-Gating

## 论文对齐范围

这一层关注“什么时候该信、什么时候不该信”，包含两个 Agent：

- `AgentRegimeGating`：自适应门控、状态激活和动态权重。
- `AgentStability`：信号稳定性、时间一致性和稳健调整。

## Agent Prompt 目录

- `AgentRegimeGating`：读取 [agent_regime_gating.md](agent_regime_gating.md)。
- `AgentStability`：读取 [agent_stability.md](agent_stability.md)。

## 层内组合原则

- `RegimeGating` 通常作为 `gate`，`Stability` 通常作为 `stabilizer` 或 `confirmation`。
- 二者都常作为辅助 Lens，而不是独立主 alpha。
- 推荐组合：`regime_gating.trend_regime_gate` + `stability.signal_persistence`，先判断状态，再调整信号可信度。

## 常见坑

- gate 太强，最后几乎没有有效样本。
- regime 定义和主信号逻辑重复。
- 用过多条件造成过拟合。
- 没有说明被 gate 或被稳定化的主信号。
