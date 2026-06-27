---
description: 计划质询（轻量版） - 沿决策树逐分支问，每问给推荐答案
type: workmode
parent: dev-guidelines.md
auto_execution_mode: 2
source: Matt Pocock skills - productivity/grill-me
adapted-for: A 股量化数据采集系统 (Python / pytest / PostgreSQL)
---

# Grill Me - 质询我

> 触发：用户希望计划 / 设计被压力测试，但**不需要**更新 CONTEXT.md / ADR（那种用 [grill-with-docs](../methodology/grill-with-docs/SKILL.md)）。

## 单段指令

不停问我关于这个方案的每一个方面，直到我们达成共识。**沿决策树每个分支走，逐项解决依赖**。每个问题，给出**你推荐的答案**。

**一次问一个问题**。

如果一个问题可以通过浏览代码库回答，**直接去看代码，不要问我**。

## 在本项目的执行细则

启动器问题清单（按需挑）：

- 这个变更的**最小可验证范围**是什么？
- 影响哪些表 / schema？要写迁移吗？
- 哪些采集器会被改？是否要降级链调整？
- 测试覆盖到哪一层？unit / integration / data_quality？
- 有性能 / 限流影响吗？
- 是否需要更新 `docs/core_features.md` / README 目录树？
- 命名 / 接口形状是不是已经在用别的词了？（与 [grill-with-docs](../methodology/grill-with-docs/SKILL.md) 区别：只问，不动文档）
- 这件事**不在范围内**的什么是值得显式声明的？

## 与 grill-with-docs 的差别

| 维度 | grill-me | grill-with-docs |
|-----|---------|----------------|
| 更新 CONTEXT.md | 否 | 是（当场） |
| 提议 ADR | 否 | 是（满足三条件） |
| 与代码交叉验证 | 鼓励 | 必须 |
| 适合场景 | 临时方案、原型、不需要长期记忆 | 真实功能、需要语言一致 |

## 相关 skill

- [grill-with-docs](../methodology/grill-with-docs/SKILL.md) —— 完整版（更新 CONTEXT.md / ADR）
- [project-manager](../governance/project-manager.md) —— 需求抽象评审、流程矛盾清理
- [new-feature-process](../engineering/new-feature-process.md) —— 新功能开发完整流程
