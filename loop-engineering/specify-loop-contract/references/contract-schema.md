# Contract Schema

`contract.json` 必需字段：

- `id`, `schema_version`, `mode`, `architecture`
- `trigger.kind`, `trigger.dedupe_key`, `trigger.concurrency`
- `goal.statement`, `goal.evidence[]`, `goal.verifier`
- `allowed_actions.read/write/external`
- `budgets.max_iterations/max_minutes/max_cost/max_tool_retries`
- `stop_rules.success/no_progress/hard_stops/escalate_to`
- `approval_gates[]`

证据项应包含 `command` 或 `query`、预期阈值、输出保存位置及验证者。不能执行的检查只能作为人工闸门，不能作为自动成功条件。

状态转换至少包括：`ready → running → verifying → completed|blocked|escalated|cancelled`。连续无进展或同一失败指纹超过阈值时，转 `blocked` 或重置策略，不能继续原样重试。

