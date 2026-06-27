---
description: 工程方法论 skill 索引 - 诊断、TDD、质询、架构改进、原型、分诊、抽象层提升
type: methodology
parent: dev-guidelines.md
auto_execution_mode: 2
source: Matt Pocock skills (https://github.com/aihero-dev/skills)
adapted-for: A 股量化数据采集系统 (Python / pytest / PostgreSQL)
---

# 工程方法论分组

本分组收录基于 Matt Pocock 公开 skills 整合的工程方法论 skill，覆盖"日常做真实工程"的 7 个核心动作：诊断、TDD、计划质询、架构改进、原型、分诊、抽象层提升。

## 何时用哪个

| 场景 | skill | 一句话 |
|------|------|------|
| 修硬 bug / 性能回归 | [diagnose](diagnose.md) | 反馈循环优先，6 阶段：复现→最小化→假设→工具→修复→回归 |
| 加新功能 / 修 bug 用测试驱动 | [tdd/SKILL.md](tdd/SKILL.md) | 红绿重构 + 垂直切片 |
| 计划 / 方案模糊时 | [grill-with-docs/SKILL.md](grill-with-docs/SKILL.md) | 逐分支质询，更新 CONTEXT.md / ADR |
| 代码越改越乱 | [improve-codebase-architecture/SKILL.md](improve-codebase-architecture/SKILL.md) | 找 shallow 模块，深度化 |
| 设计不确定，想跑一下试试 | [prototype/SKILL.md](prototype/SKILL.md) | 一次性原型答疑（逻辑 / UI 双分支） |
| issue 评审、需求评审 | [triage/SKILL.md](triage/SKILL.md) | 状态机：needs-triage → ready-for-agent / human / wontfix |
| 看不懂某段代码 | [zoom-out.md](zoom-out.md) | 抽一层，给模块地图 |

## 与现有共享 skill 的对照

| 本组 skill | 共享 skill 互补关系 |
|----------|--------|
| diagnose | [fault-recovery](../testing/fault-recovery.md)、[test-strategy](../testing/test-strategy.md) |
| tdd | [test-strategy](../testing/test-strategy.md)、[collector-testing](../testing/collector-testing.md)、[database-testing](../testing/database-testing.md) |
| grill-with-docs | [project-manager](../governance/project-manager.md)、[new-feature-process](../engineering/new-feature-process.md) |
| improve-codebase-architecture | [refactoring-checklist](../governance/refactoring-checklist.md)、[design-patterns](../engineering/design-patterns.md)、[extensibility](../engineering/extensibility.md) |
| prototype | [reference-analysis](../governance/reference-analysis.md)、[reusable-patterns](../engineering/reusable-patterns.md) |
| triage | [project-manager](../governance/project-manager.md)、[git-code-review](../git/git-code-review.md) |

## 使用顺序建议

1. **新需求**：`grill-with-docs` → `triage` → `tdd`（开发） → `diagnose`（修 bug）
2. **重构**：`improve-codebase-architecture` → `grill-with-docs` → `tdd`
3. **不确定**：`prototype` → 验证 → 删除原型 → `tdd` 重写
4. **接手陌生模块**：`zoom-out` → `improve-codebase-architecture`
