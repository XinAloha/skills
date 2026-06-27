---
description: Claude Code git 守卫 - PreToolUse 钩子拦截 git push / reset --hard / clean -f 等危险命令
type: misc
parent: dev-guidelines.md
auto_execution_mode: 2
source: Matt Pocock skills - misc/git-guardrails-claude-code
adapted-for: A 股量化数据采集系统 (Python / pytest / PostgreSQL)
---

# Git Guardrails for Claude Code - Git 守卫

> 触发：用户希望阻止破坏性 git 操作、加 git 安全钩子、阻止 Claude Code 跑 `git push` / `git reset` 等。

设置 `PreToolUse` 钩子，**在 Claude 执行前拦截危险 git 命令**。

> 本项目 `CLAUDE.md` 已声明"git commit / push / tag / 强推 / drop 表 / 删大量文件"必须用户明确授权。本 skill 用 Claude Code 钩子机制把这条声明**机械化**，避免漏网。

## 拦截哪些命令

- `git push`（包括 `--force`）
- `git reset --hard`
- `git clean -f` / `git clean -fd`
- `git branch -D`
- `git checkout .` / `git restore .`

被拦截时，Claude 看到一条提示，告知它无权执行该命令。

## 步骤

### 1. 问范围

问用户：装在**仅本项目**（`.claude/settings.json`）还是**所有项目**（`~/.claude/settings.json`）？

### 2. 复制钩子脚本

捆绑脚本路径：[scripts/block-dangerous-git.sh](scripts/block-dangerous-git.sh)（按需创建）。

复制到目标位置：

- 项目：`.claude/hooks/block-dangerous-git.sh`
- 全局：`~/.claude/hooks/block-dangerous-git.sh`

`chmod +x` 给执行权限。

### 3. 加进 settings

**项目** `.claude/settings.json`：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/block-dangerous-git.sh"
          }
        ]
      }
    ]
  }
}
```

**全局** `~/.claude/settings.json`：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/block-dangerous-git.sh"
          }
        ]
      }
    ]
  }
}
```

settings 文件已存在，**合并** `hooks.PreToolUse` 数组——不要覆盖。

### 4. 问定制

问用户要不要从拦截清单加 / 减模式。改脚本相应位置。

### 5. 验证

```bash
echo '{"tool_input":{"command":"git push origin main"}}' | <script-path>
```

应以 exit code 2 退出，stderr 打印 BLOCKED 提示。

## 钩子脚本骨架（参考）

```bash
#!/bin/bash
# block-dangerous-git.sh
INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# 拦截规则（用 grep -E 而不是字面匹配，覆盖各种参数顺序）
if echo "$CMD" | grep -qE '^git\s+(push|reset\s+--hard|clean\s+-[f]+|branch\s+-D)'; then
  echo "BLOCKED: 危险 git 命令需要用户显式授权。" >&2
  exit 2
fi
exit 0
```

## 与本项目工作流的关系

本项目 `CLAUDE.md` 已声明"不主动执行 git commit / push / tag / 强推 / drop 表 / 删大量文件"。**这门 skill 不替代该约束**，它是把约束**机械化**——在 Claude Code 真要执行时再多一层拦截。三方 Agent 都接受同样的硬性约束（见 `.devin/workflows/dev-guidelines.md` 与 `.codex/workflows/codex-guidelines.md`）。

## 相关 skill

- [git-rollback-recovery](../git/git-rollback-recovery.md) - 回滚场景与数据安全
- [git-version-control](../git/git-version-control.md) - Git 索引入口
- [security](../engineering/security.md) - 密钥管理、敏感信息保护
