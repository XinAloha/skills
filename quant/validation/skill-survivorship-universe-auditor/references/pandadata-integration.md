# PandaData 接入

## 接入结论

- 模式：**混合接入**
- 可用方法：`get_trade_cal`、`get_trade_list`、`get_stock_status_change`、`get_stock_daily`
- 覆盖范围：PandaData 可提供逐日可交易股票列表、特殊处理事件和历史行情，用于重建历史股票池及识别退市/停牌附近的数据缺口。
- 必须补充：PandaData 未明确提供标准化退市收益；若研究要求精确 delisting_return，必须由用户或其他权威数据源补充，不能用 0 代替。

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
| 历史可交易集合 | `get_trade_list` | `symbol`,`date` → symbol,date,eligible=1 |
| 交易日对齐 | `get_trade_cal` | 生成应检查的交易日快照 |
| ST/特殊状态变化 | `get_stock_status_change` | `symbol`,`change_date`,`type`,`info_date` → 状态事件证据 |
| 退市附近行情 | `get_stock_daily` | `symbol`,`date`,`close`,`pre_close`,`trade_status` → return/缺口检查 |

## 失败与降级

- SDK、凭证或服务未配置时，明确返回 `insufficient-evidence`，列出缺少的配置；不要回退到伪造数据。
- 空结果时先检查交易日、日期格式、标的代码、接口窗口和必要筛选条件。
- PandaData 只覆盖部分字段时，保留已取到的市场证据，并向用户索取缺失的私有字段。
- 代理变量必须写入 `assumptions` 和 `limitations`，不得把代理指标描述为真实盘口、真实成交或完整事件历史。
