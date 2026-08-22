# PandaData 接入

## 接入结论

- 模式：**直接接入**
- 可用方法：`get_trade_cal`、`get_stock_min`、`get_stock_rt_min`、`get_index_min`、`get_future_min`、`get_future_detail`
- 覆盖范围：PandaData 的股票、指数和期货分钟线包含 datetime 与 OHLCV，可直接标准化为本 Skill 的日内 K 线输入。
- 必须补充：分钟接口不是逐笔成交或 Level-2 盘口；不能用它验证队列位置、撤单或逐笔撮合顺序。

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
| 交易日期 | `get_trade_cal` | 仅判断 `nature_date` 是否交易日并辅助映射前后交易日；该接口不提供盘中交易时段 |
| A 股历史/当日分钟线 | `get_stock_min`,`get_stock_rt_min` | `symbol`,`date`,`datetime`,`open`,`high`,`low`,`close`,`volume` → symbol,trading_date,timestamp,OHLCV；按明确的交易所时段规则生成 morning/afternoon 等 session |
| 指数分钟线 | `get_index_min` | 映射为 symbol,trading_date,timestamp,OHLCV，并按明确的交易所时段规则生成 session |
| 期货分钟线与时段 | `get_future_min`,`get_future_detail` | 分钟线映射为规范字段；用 `trading_hours` 划分 session，并显式处理夜盘自然日与 trading_date 的差异 |

## 失败与降级

- SDK、凭证或服务未配置时，明确返回 `insufficient-evidence`，列出缺少的配置；不要回退到伪造数据。
- 空结果时先检查交易日、日期格式、标的代码、接口窗口和必要筛选条件。
- PandaData 只覆盖部分字段时，保留已取到的市场证据，并向用户索取缺失的私有字段。
- 代理变量必须写入 `assumptions` 和 `limitations`，不得把代理指标描述为真实盘口、真实成交或完整事件历史。
- 标准化结果必须包含 `symbol + trading_date + session`。脚本只在同一组内检查重复与缺口，不能跨午休、跨日或跨夜盘/日盘边界连续比较。
