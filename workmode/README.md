---
description: 工作模式 skill 索引 - 极简通信、计划质询、会话交接
type: workmode
parent: dev-guidelines.md
auto_execution_mode: 2
source: Matt Pocock skills (productivity 部分)
---

# 工作模式分组

通用工作流工具，**不针对代码具体内容**，而是改变 Agent 的沟通 / 协作模式。

## skill 列表

| skill | 何时用 |
|------|------|
| [manage-upward](manage-upward.md) | 接到上级 / 合作者任务、汇报进度、判断风险该不该报、申请资源；也用于让 AI 互相督促"打工人模式"（双向） |
| [caveman](caveman.md) | 上下文紧张、想省 token、用户说 "caveman 模式 / 简短点" |
| [grill-me](grill-me.md) | 计划 / 设计模糊，想被质询，但不需要更新 CONTEXT.md / ADR（那是 [grill-with-docs](../methodology/grill-with-docs/SKILL.md)） |
| [handoff](handoff.md) | 当前会话快满 / 需要交给另一个 Agent / 准备 AFK 离开 |

## 与既有 skill 的关系

- `manage-upward` 与 [handoff](handoff.md) 联动——交接文档按"三件事法"组织。
- `manage-upward` 与 [project-manager](../governance/project-manager.md) 联动——主动给上级做 Backup 时用 PM 评审方法。
- `caveman` 与 [code-style](../engineering/code-style.md) 不冲突——caveman 改的是**沟通文字**，code-style 管**代码风格**。
- `grill-me` 是 [grill-with-docs](../methodology/grill-with-docs/SKILL.md) 的轻量版（不强制更新文档），可在向上汇报前用来自我质询。
- `handoff` 与 [project-manager](../governance/project-manager.md) 联动——重要决策记入 handoff 文档。
