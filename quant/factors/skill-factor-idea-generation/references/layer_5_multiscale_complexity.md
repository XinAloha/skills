# Layer 5: Multi-Scale Complexity

## 论文对齐范围

这一层关注不同时间尺度之间的一致、冲突、粗糙度和路径复杂结构，包含两个 Agent：

- `AgentDrawdown`：回撤深度、持续时间和恢复几何。
- `AgentFractal`：多尺度粗糙度、长记忆和跨窗口结构。

## Agent Prompt 目录

- `AgentDrawdown`：读取 [agent_drawdown.md](agent_drawdown.md)。
- `AgentFractal`：读取 [agent_fractal.md](agent_fractal.md)。

## 层内组合原则

- `Drawdown` 关注损失路径，`Fractal` 关注跨尺度结构。
- 推荐组合：`drawdown.recovery_geometry` + `fractal.path_roughness`，用路径粗糙度确认恢复质量。
- 推荐组合：`drawdown.drawdown_duration` + `fractal.cross_horizon_consistency`，判断长期回撤中是否出现多尺度修复。

## 常见坑

- 盲目堆多个窗口，复杂但不解释。
- 多尺度信息高度冗余，没有新增机制。
- 使用未来峰谷、未来恢复或昂贵嵌套循环。
