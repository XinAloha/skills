# PandaData 接入

## 接入结论

- 模式：**直接接入**
- 可用方法：`get_index_weights`、`get_index_daily`、`get_stock_daily`、`get_trade_cal`
- 覆盖范围：PandaData 的指数权重历史包含 index_symbol/date/stock_symbol/weight，可通过相邻快照差分识别纳入、剔除和权重变化。
- 必须补充：若研究要求官方公告时间而不仅是权重快照变化，仍需补充指数公司公告；不得把首次观测日期冒充 announcement_date。

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
| 成分和权重变化 | `get_index_weights` | 相邻 date 的 stock_symbol/weight 差分 → add/delete/weight_change |
| 指数基准收益 | `get_index_daily` | `date`,`close`,`pre_close` → benchmark_return |
| 成分股收益与成交 | `get_stock_daily` | `date`,`symbol`,`close`,`pre_close`,`volume`,`amount` → return,volume_ratio |
| 交易日映射 | `get_trade_cal` | 把生效日和事件窗映射到有效交易日 |

## 失败与降级

- SDK、凭证或服务未配置时，明确返回 `insufficient-evidence`，列出缺少的配置；不要回退到伪造数据。
- 空结果时先检查交易日、日期格式、标的代码、接口窗口和必要筛选条件。
- PandaData 只覆盖部分字段时，保留已取到的市场证据，并向用户索取缺失的私有字段。
- 代理变量必须写入 `assumptions` 和 `limitations`，不得把代理指标描述为真实盘口、真实成交或完整事件历史。
