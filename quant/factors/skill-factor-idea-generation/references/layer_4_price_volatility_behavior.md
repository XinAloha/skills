# Layer 4: Price-Volatility Behavior

## 论文对齐范围

这一层关注价格行为与波动行为的联动，包含五个 Agent：

- `AgentDailyTrend`：日频趋势持续、多日动量和方向强度。
- `AgentReversal`：短期过度反应修正和均值回归。
- `AgentRangeVol`：high-low range 和区间波动动态。
- `AgentLagResponse`：滞后响应和延迟反馈。
- `AgentVolAsymmetry`：上下行波动不对称和偏斜风险。

## Agent Prompt 目录

- `AgentDailyTrend`：读取 [agent_daily_trend.md](agent_daily_trend.md)。
- `AgentReversal`：读取 [agent_reversal.md](agent_reversal.md)。
- `AgentRangeVol`：读取 [agent_range_vol.md](agent_range_vol.md)。
- `AgentLagResponse`：读取 [agent_lag_response.md](agent_lag_response.md)。
- `AgentVolAsymmetry`：读取 [agent_vol_asymmetry.md](agent_vol_asymmetry.md)。

## 层内组合原则

- `DailyTrend` 和 `Reversal` 是相反方向的主机制，组合时通常使用 `contrast` 或 `gate`。
- `RangeVol` 和 `VolAsymmetry` 可以作为趋势/反转的确认或风险调节。
- `LagResponse` 必须明确“哪个历史冲击滞后影响当前状态”。
- 推荐组合：`daily_trend.volatility_adjusted_trend` + `range_vol.close_range_efficiency`，用 range 效率确认趋势质量。
- 推荐组合：`reversal.pressure_decay_reversal` + `vol_asymmetry.downside_upside_vol_ratio`，用不对称风险解释压力衰减后的修复。

## 常见坑

- 把波动率高简单等同于风险大或 alpha 强。
- 只做波动率因子，没有和价格状态结合。
- 把趋势、反转、波动、滞后全部塞进一个候选。
- 在 `lag_response` 中使用负向 shift 或未来信息。
