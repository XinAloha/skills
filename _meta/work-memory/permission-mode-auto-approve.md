# 记忆项：权限模式限制与自动授权

**slug:** `permission-mode-auto-approve` · **类型:** feedback · **相关:** [[skills-import-pipeline]] [[git-commit-co-authored-by]] [[ide-git-constraints]]

工具在用户选定的权限模式下运行，决定哪些工具调用需用户确认、哪些可自动放行（approve）：

- **被拒绝的调用**表示用户不同意——要**调整方案**，不要原样重试。
- **对难以撤销或对外的动作**（提交、推送、发布、删除、发送到外部服务）即使已有授权也**先确认**再执行，除非明确授权；一次上下文授权不延伸到下一次。
- **删除/覆盖前先查看目标**；若与描述不符或非本人所建，先指出再行动。
- 与 [[skills-import-pipeline]]（导入会触发授权）、[[git-commit-co-authored-by]] / [[ide-git-constraints]]（提交前确认）相关。

**Why:** 尊重授权边界，避免在未授权时执行破坏性/对外操作。
**How to apply:** 留意权限提示；被拒后调整而非重试；破坏性/对外动作先向用户确认。
