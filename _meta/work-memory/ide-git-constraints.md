# 记忆项：IDE 场景下的 Git 操作约束

**slug:** `ide-git-constraints` · **类型:** feedback · **相关:** [[git-commit-co-authored-by]] [[skills-import-pipeline]]

Claude 作为 VSCode 原生扩展运行时，操作 Git 的约束：

- **交互式 flag 不可用**：`git rebase -i`、`git add -i` 等交互式命令不被支持（无 TTY），须改用非交互式等价命令。
- **提交/推送仅在用户明确要求时**才做；若在默认分支，先建分支再操作。
- 用 `gh` CLI 处理 GitHub 操作（PR/issue/API），而非裸 git。
- 提交信息格式见 [[git-commit-co-authored-by]]；与导入流水线 [[skills-import-pipeline]] 相关（导入完成后的提交也受此约束）。

**Why:** IDE 环境无 TTY，交互式 Git 命令无法工作；GitHub 操作走 gh 更可靠。
**How to apply:** 避免交互式 Git 命令；提交前确认用户意图；GitHub 操作用 `gh`。
