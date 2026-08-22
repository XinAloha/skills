# Layer 1: Market Structure & Cycle

## 论文对齐范围

这一层从宏观时间结构观察日频 OHLCV，包含两个 Agent：

- `AgentMarketCycle`：长周期转换、相位变化、隐藏市场节奏和结构性拐点。
- `AgentVolatilityRegime`：平静与剧烈波动状态的切换、持续性和聚集。

不要把这一层泛化为所有趋势、反转和均值回归问题。`DailyTrend` 和 `Reversal` 属于 Level IV。

## Agent Prompt 目录

- `AgentMarketCycle`：读取 [agent_market_cycle.md](agent_market_cycle.md)。
- `AgentVolatilityRegime`：读取 [agent_volatility_regime.md](agent_volatility_regime.md)。

## 层内组合原则

- 只选一个 Agent 时，保持其专业边界。
- 同时选中 `MarketCycle` 和 `VolatilityRegime` 时，一个必须提供主机制，另一个只做状态确认或强度调节。
- 推荐组合：`market_cycle.phase_divergence` + `volatility_regime.regime_persistence`，用波动状态稳定性确认周期相位信号。
- 推荐组合：`market_cycle.compression_expansion_turn` + `volatility_regime.calm_turbulence_transition`，区分周期转换节奏和当前波动状态转换。
- 不得因为两者都使用滚动波动统计量，就将两个 Agent 视为同一方向。

## 常见坑

- 只做简单动量、均线交叉或换窗口重复品。
- 把当前高低波动状态误写成市场周期。
- 用未来峰谷或未来反转标注当前周期位置。
- 同时堆叠太多节奏、能量、门控和确认信号，失去核心假设。
