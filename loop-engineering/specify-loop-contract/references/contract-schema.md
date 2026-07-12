# Contract Schema

`contract.json` 必需字段：

- `id`, `schema_version`, `mode`, `architecture`
- `trigger.kind`, `trigger.dedupe_key`, `trigger.concurrency`
- `goal.statement`, `goal.evidence[]`, `goal.verifier`
- `allowed_actions.read/write/external`
- `delivery.mode`, `delivery.branch`, `delivery.pr`
- `budgets.max_iterations/max_minutes/max_cost/max_tool_retries`
- `stop_rules.success/no_progress/hard_stops/escalate_to`
- `approval_gates[]`

证据项应包含 `command` 或 `query`、预期阈值、输出保存位置及验证者。不能执行的检查只能作为人工闸门，不能作为自动成功条件。

定时/事件触发还应记录：调度器适配器、时区/频率、单次超时、周期预算、最大重试、去重窗口、无发现收尾和暂停入口。写入任务还应记录人工抽样审阅频率与收件箱/分流路径。

`delivery` 默认值为 `mode: draft-pr-only`、`branch: agent/<task-id>`、`pr: draft-required`。除非任务只写 `.loop/` 等本地运行工件，否则不得使用 `no-source-delivery`。任何模式都禁止直接推送远端 `main` 和自动合并；合并必须是明确记录的人类批准动作。

源码写入任务还必须定义 `review.implementer_identity`、`review.verifier_identity`、`review.checklist_path` 和 `review.verdict_path`。两种身份不得相同；验证者必须使用 `$verify-loop-delivery`，且只有 `pass` 裁决和人工批准都存在时才能进入合并闸门。

状态转换至少包括：`ready → running → verifying → completed|blocked|escalated|cancelled`。连续无进展或同一失败指纹超过阈值时，转 `blocked` 或重置策略，不能继续原样重试。

