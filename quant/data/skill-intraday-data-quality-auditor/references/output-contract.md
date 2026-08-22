# 输出契约

建议 JSON 顶层字段：

```json
{
  "status": "pass | fail | warning | insufficient-evidence",
  "input_summary": {},
  "assumptions": {},
  "metrics": {},
  "findings": [],
  "limitations": [],
  "next_actions": []
}
```

每个 finding 至少包含：`id`、`severity`、`evidence`、`impact`、`recommended_fix`。

严重度使用：`critical`、`high`、`medium`、`low`、`info`。没有可定位证据时，不得输出 `critical` 或 `high`。
