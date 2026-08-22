# PandaData 接入

## 接入结论

- 模式：**混合接入**
- 可用方法：`get_stock_daily`、`get_stock_min`、`get_future_daily`、`get_future_min`、`get_option_daily`
- 覆盖范围：PandaData 可提供历史成交量、成交额、价格与波动率样本，用于估计 ADV 和压力前市场容量。
- 必须补充：持仓市值、赎回情景和真实 bid-ask spread 属于用户/经纪商数据；若用高低价差等代理，必须标记为 proxy 并做敏感性分析。

## 调用原则

1. 用户已经提供符合输入契约的 CSV 时，直接审计该文件，不为重复取数调用 PandaData。
2. 用户未提供市场数据、且任务落在上述覆盖范围时，使用兄弟 Skill `pandadata-api`。
3. 先读取 `pandadata-api/references/method-index.md`，再加载目标方法在 `api-docs.md` 中的完整参数与响应字段；不要凭记忆编造参数。
4. 先做单标的、短窗口 smoke test，检查 `shape`、列名、数据日期、单位和空结果原因，再扩大查询。
5. 将 API 结果写入新的规范化 CSV，再运行本 Skill 的分析脚本；不要在原始 DataFrame 上就地覆盖。
6. 在最终报告记录方法名、参数、查询时间、最新数据日期、原始行数、标准化行数和字段映射。

## 方法与规范字段映射

| 数据需要 | PandaData 方法/来源 | 规范化规则 |
|---|---|---|
| A 股容量 | `get_stock_daily`,`get_stock_min` | `amount`,`volume`,`close` → adv,volatility；spread 仅可做代理 |
| 期货容量 | `get_future_daily`,`get_future_min` | 按合约与乘数统一成交额口径 |
| 期权容量背景 | `get_option_daily` | `volume`,`amount`,`open_interest` → 容量背景，不是盘口价差 |
| 组合私有输入 | 用户提供 | `symbol`,`position_value`,`spread_bps` 与情景参数 |

## 失败与降级

- SDK、凭证或服务未配置时，明确返回 `insufficient-evidence`，列出缺少的配置；不要回退到伪造数据。
- 空结果时先检查交易日、日期格式、标的代码、接口窗口和必要筛选条件。
- PandaData 只覆盖部分字段时，保留已取到的市场证据，并向用户索取缺失的私有字段。
- 代理变量必须写入 `assumptions` 和 `limitations`，不得把代理指标描述为真实盘口、真实成交或完整事件历史。
