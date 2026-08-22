# 记忆项：Git 提交时的 Co-Authored-By 尾注

**slug:** `git-commit-co-authored-by` · **类型:** feedback · **相关:** [[ide-git-constraints]] [[skills-import-pipeline]] [[permission-mode-auto-approve]]

所有 Git 提交信息以协作尾注结尾：

```
Co-Authored-By: Claude <noreply@anthropic.com>
```

- PR body 以 `🤖 Generated with [Claude Code](https://claude.com/claude-code)` 结尾。
- 提交/推送**仅在用户明确要求时**执行（见 [[ide-git-constraints]]）。
- 与 [[skills-import-pipeline]] 相关：导入/同步完成后提交时套用此规范。

**Why:** 规范 AI 署名，便于追溯参与；保持提交信息一致。
**How to apply:** 每次 `git commit` 加尾注；写 PR body 时加生成脚注。
