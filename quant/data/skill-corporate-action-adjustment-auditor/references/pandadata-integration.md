# PandaData 接入

## 接入结论

- 模式：**直接接入**
- 可用方法：`get_stock_daily`、`get_stock_daily_pre`、`get_stock_daily_post`、`get_adj_factor`、`get_stock_dividend`、`get_stock_split`、`get_stock_cash_dividend`、`get_stock_allotment`
- 覆盖范围：PandaData 覆盖 A 股原始/前复权/后复权行情、复权因子、分红、拆分与配股，可直接组成复权审计证据链。
- 必须补充：分拆、并购换股、代码迁移等复杂事件若不在返回结果中，必须保留为未覆盖事件，不能据此宣布完整通过。

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
| 原始行情 | `get_stock_daily` | `symbol`,`date`,`close`,`pre_close` → close 与原始收益 |
| 复权行情 | `get_stock_daily_pre`,`get_stock_daily_post` | 按同一 symbol/date 对齐到 adj_close 对照序列 |
| 复权因子 | `get_adj_factor` | `ex_date`,`ex_factor`,`ex_cum_factor`,`announcement_date` → 复权链交叉核验；`ex_factor` 可能同时包含现金与股份事件影响，不能直接当作 `split_factor` |
| 现金分红 | `get_stock_cash_dividend` | 按 `ex_date` 对齐，`cash_dividend = div_cash_gross / round_lot`，先核验币种与分红单位 |
| 股份与其他事件 | `get_stock_dividend`,`get_stock_split`,`get_stock_allotment` | 拆分/送转比例由 `split_factor_post / split_factor_pre` 计算；分红类型与配股按除权日作为事件证据，不把配股比例误当现金分红 |

## 失败与降级

- SDK、凭证或服务未配置时，明确返回 `insufficient-evidence`，列出缺少的配置；不要回退到伪造数据。
- 空结果时先检查交易日、日期格式、标的代码、接口窗口和必要筛选条件。
- PandaData 只覆盖部分字段时，保留已取到的市场证据，并向用户索取缺失的私有字段。
- 代理变量必须写入 `assumptions` 和 `limitations`，不得把代理指标描述为真实盘口、真实成交或完整事件历史。
