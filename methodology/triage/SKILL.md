---
description: issue 分诊状态机 - 类别 + 状态双轴，配合 agent brief 与 .out-of-scope/ 知识库
type: methodology
parent: dev-guidelines.md
auto_execution_mode: 2
source: Matt Pocock skills - engineering/triage
---

# Triage - 分诊

> 触发：用户希望"创建 issue / 分诊 issue / 评审新 bug 或新功能 / 给 AFK agent 准备 issue / 管理 issue 工作流"。

把 issue 在状态机里推进，由"分诊角色"驱动。

> 本项目当前未启用 GitHub issue 工作流。本 skill 在以下场景下使用：
> - 用户在 GitHub 上手工开了 issue（远期）。
> - 用户在对话里口头列了一批需求，需要分诊（**当前主要场景**）—— 用文件 `docs/triage.md` 或本地 `.out-of-scope/` 替代 issue tracker。

每条分诊期间发到 issue tracker（或对话）的评论 / issue **必须**以这条免责声明开头：

```
> *本条由 AI 在分诊期间生成。*
```

## 参考文档

- [AGENT-BRIEF.md](AGENT-BRIEF.md) —— 如何写耐久的 agent brief
- [OUT-OF-SCOPE.md](OUT-OF-SCOPE.md) —— `.out-of-scope/` 知识库怎么用

## 角色

两个**类别**角色：

- `bug` —— 有东西坏了
- `enhancement` —— 新功能或改进

五个**状态**角色：

- `needs-triage` —— 待维护者评估
- `needs-info` —— 等报告人补信息
- `ready-for-agent` —— 完整规格、可让 AFK agent 接走
- `ready-for-human` —— 需要人工实现
- `wontfix` —— 不会做

每个分诊过的 issue 应**恰好**一个类别 + 一个状态。状态冲突就 flag 给维护者。

状态转移：未 label 的 issue 通常先到 `needs-triage`；从那里到 `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`。`needs-info` 在报告人回复后回到 `needs-triage`。维护者可随时覆盖——异常转移要 flag 询问。

## 调用

维护者调用 `/triage` 用自然语言描述要做什么。例：

- "看一下需要我注意的"
- "看 #42"
- "把 #42 移到 ready-for-agent"
- "agent 可以接哪些"

## 展示需要注意的

查 issue tracker，按时间从老到新分三桶：

1. **未 label** —— 没分诊过。
2. **`needs-triage`** —— 正在评估。
3. **`needs-info` 且报告人在最近一次分诊后有动静的** —— 需重新评估。

显示计数 + 每条一行摘要。等维护者挑。

## 分诊一个具体 issue

1. **收集上下文**。完整读 issue（body / 评论 / labels / 报告人 / 日期）。读已有分诊笔记，**不要重问已解决的问题**。用项目领域词汇浏览代码、尊重相关 ADR。**读 `.out-of-scope/*.md`**，把任何相似的旧拒绝拉出来。

2. **推荐**。给维护者你的类别 + 状态推荐，附理由 + 一段相关代码摘要。等指示。

3. **复现**（仅 bug）。任何质询前先尝试复现：读报告人步骤、追代码、跑测试 / 命令。报告结果——成功复现（含代码路径）、复现失败、信息不足（强 `needs-info` 信号）。**确认的复现 = 强得多的 agent brief**。

4. **质询**（如需）。issue 需要补血肉就跑一轮 [grill-with-docs](../grill-with-docs/SKILL.md)。

5. **应用结果**：
   - `ready-for-agent` —— 发 agent brief 评论（[AGENT-BRIEF.md](AGENT-BRIEF.md)）。
   - `ready-for-human` —— 同样结构，但说明为什么不能委托（判断、外部访问、设计决策、手测）。
   - `needs-info` —— 发分诊笔记（下文模板）。
   - `wontfix`（bug）—— 礼貌解释，关闭。
   - `wontfix`（enhancement）—— 写到 `.out-of-scope/`，评论里链过去，关闭（[OUT-OF-SCOPE.md](OUT-OF-SCOPE.md)）。
   - `needs-triage` —— 应用角色。如果有部分进展，可选评论。

## 快速状态覆盖

维护者说"把 #42 移到 ready-for-agent"，**信他**。直接应用。先确认要做什么（角色变更、评论、关闭），再做。**跳过质询**。如果是移到 `ready-for-agent` 但没经历过质询，问要不要先写 agent brief。

## Needs-info 模板

```markdown
## 分诊笔记

**目前已确认：**

- 点 1
- 点 2

**仍需 @报告人 提供：**

- 问题 1
- 问题 2
```

把质询期间已解决的所有内容写进"已确认"——不要让工作丢失。问题要**具体可执行**，不是"请补充信息"。

## 恢复之前的分诊

如果 issue 上有旧分诊笔记，读它、看报告人是否回答了未决问题，先给一个**更新过的全景**再继续。**不要重问已解决的问题**。

## 本项目典型场景

- 用户口头说"我想加涨跌停字段、修一下停牌处理 bug、再加个 ST 标记"——这是 3 个 issue，分别分诊。
- 修 bug 之前先 [diagnose](../diagnose.md) 一轮，复现状况进 agent brief。
- 拒绝功能时记到 `docs/out-of-scope/`（本地版的 `.out-of-scope/`），下次再有人提同一个就拉出来。

## 相关 skill

- [project-manager](../../governance/project-manager.md) - 需求抽象评审、流程矛盾清理
- [git-code-review](../../git/git-code-review.md) - PR 评审清单
- [grill-with-docs](../grill-with-docs/SKILL.md) - 分诊中的质询环节
- [diagnose](../diagnose.md) - bug 复现作 agent brief 强证据
