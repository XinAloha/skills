---
description: 会话交接文档 - 把当前对话压缩成另一个 Agent 能接续工作的 handoff 文档
type: workmode
parent: dev-guidelines.md
auto_execution_mode: 2
source: Matt Pocock skills - productivity/handoff
adapted-for: A 股量化数据采集系统 (Python / pytest / PostgreSQL)
argument-hint: 「下个会话用来做什么？」
---

# Handoff - 交接

> 触发：用户希望把当前会话压缩为 handoff 文档，让另一个 Agent（或换 host 后的自己）继续工作。

写一份 handoff 文档总结当前对话，让一个新鲜 Agent 能接续工作。**保存到操作系统的临时目录，不要写进 workspace**。

## 关键要点

- **不要重复其他 artifact 已有的内容**（PRD / 计划 / ADR / issue / commit / diff）。**用路径或 URL 引用**它们。
- **加一节 "建议技能"**：建议下一位 Agent 调用哪些 skill。
- **脱敏**：API key、密码、个人可识别信息——全部 redact。
- 用户给了参数（"下个会话用来做什么"），把它当作下个会话的焦点描述，**让文档围绕它定制**。

## 模板

```markdown
# Handoff - {话题}

> 生成时间：{绝对日期} （TZ）
> 来源会话：本次 Claude Code / Codex / Devin 会话
> 下个会话目标：{用户参数 or 推断}

## 当前状态

- [ ] 已完成：{要点 1}
- [ ] 已完成：{要点 2}
- [ ] 进行中：{要点 3}
- [ ] 未开始：{要点 4}

## 关键决策（仅记录会话期间做出、未在 ADR / commit 中沉淀的）

- {决策} —— {理由}
- {决策} —— {理由}

## 关键文件

- `data_collection/collectors/foo.py` —— {本次改了什么 / 待改}
- `test/unit/test_foo.py` —— {当前覆盖 / 缺失}

## 待办

1. {下一步}
2. {下下步}

## 阻塞 / 待确认

- {问题} —— 等用户回答 {具体问题}

## 建议技能

- [diagnose](../methodology/diagnose.md) —— 如果继续修当前 bug
- [tdd](../methodology/tdd/SKILL.md) —— 如果接下来加新功能
- [project-context](../agent-adapters/project-context.md) —— 接手时先读（跨平台版，同时覆盖 Claude Code 与 Codex）

## 脱敏检查

- [ ] 无 Tushare token / API key
- [ ] 无生产 PostgreSQL URL
- [ ] 无个人邮箱 / GitHub 账号信息
```

## 路径

- Linux/macOS: `$TMPDIR/handoff-<topic>-<timestamp>.md`，fallback `/tmp/`
- Windows: `%TEMP%\handoff-<topic>-<timestamp>.md`

文件写好后，把**绝对路径**告诉用户。

## 本项目特有的脱敏清单

- `TUSHARE_TOKEN`
- `DATABASE_URL` / 生产 PostgreSQL 凭据
- `.env` 文件内容
- 个人 GitHub 账号 / 仓库 SSH key fingerprint
- 任何在 logs 里出现的真实股票账户号 / 客户号

## 相关 skill

- [project-manager](../governance/project-manager.md) - handoff 中"关键决策"段落的内容来源
- [git-commit-convention](../git/git-commit-convention.md) - handoff 不替代 commit；已 commit 的内容只引用
- [project-context](../agent-adapters/project-context.md) - 接手时先读（跨平台版）
