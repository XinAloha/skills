---
name: tdd
description: 测试驱动开发 - 红绿重构 + 垂直切片，行为而非实现
type: methodology
parent: dev-guidelines.md
auto_execution_mode: 2
source: Matt Pocock skills - engineering/tdd
---

# Test-Driven Development - 测试驱动开发

> 触发：用户说要"用 TDD / 红绿重构 / test-first / 写集成测试"做新功能或修 bug。

## 哲学

**核心原则**：测试通过**公开接口**验证**行为**，不验证实现细节。代码可以彻底改，测试不该改。

**好测试**是集成式的：跑真实代码路径、走公开 API、描述系统**做什么**而不是**怎么做**。一个好测试读起来像一份规格说明——"采集器在停牌日返回 None 而非前一日 close"——一眼就知道有什么能力。这种测试在重构后存活，因为它不在乎内部结构。

**坏测试**和实现耦合：mock 内部协作者、测私有方法、绕开接口直接查数据库。警告信号——你重构后测试挂了，但行为没变。如果重命名一个内部函数会让测试失败，那它在测实现，不在测行为。

详见 [tests.md](tests.md)（好测试 vs 坏测试示例）和 [mocking.md](mocking.md)（mock 边界）。

## 反模式：水平切片

**不要**先把所有测试写完，再把所有实现写完。这是"水平切片"——把 RED 当作"写完所有测试"、把 GREEN 当作"写完所有代码"。

它产出**烂测试**：

- 批量写的测试测的是**想象出来的行为**，不是**真实行为**。
- 你最后在测**形状**（数据结构、函数签名），不是用户能感知到的行为。
- 测试对真实变化变得不敏感——行为坏了它通过，行为正常它失败。
- 在还没理解实现之前就锁死了测试结构。

**正确做法**：垂直切片，曳光弹模式。**一个测试 → 一个实现 → 重复**。每个测试都基于上一轮学到的东西。因为你刚写完代码，你确切知道什么行为重要、怎么验证。

```
错（水平）：
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

对（垂直）：
  RED→GREEN: test1→impl1
  RED→GREEN: test2→impl2
  RED→GREEN: test3→impl3
  ...
```

## 工作流

### 1. 规划

读项目领域词汇（`CLAUDE.md` / `docs/core_features.md` / `docs/database_documentation.md`），保证测试名和接口词汇与项目语言一致；尊重相关 ADR。

写代码前：

- [ ] 与用户确认需要哪些接口变更。
- [ ] 与用户确认要测哪些行为（按重要性排序）。
- [ ] 找[深模块](deep-modules.md)的机会（小接口、深实现）。
- [ ] 为[可测性](interface-design.md)设计接口。
- [ ] 列出要测的**行为**（不是实现步骤）。
- [ ] 让用户批准计划。

问："公开接口长什么样？最重要的行为是哪些？"

**不可能测试一切**。和用户对齐"哪些行为最重要"。把测试精力投在关键路径和复杂逻辑，不是每一个边界情况。

### 2. 曳光弹（第一颗）

写一个测试，验证系统的一件事：

```
RED:   写第一个行为的测试 → 失败
GREEN: 写最少代码让它通过 → 通过
```

这就是你的曳光弹——证明端到端通路打通了。

### 3. 增量循环

每一个剩下的行为：

```
RED:   写下一个测试 → 失败
GREEN: 最少代码让它通过 → 通过
```

规则：

- 一次一个测试。
- 只写够当前测试通过的代码。
- 不预测未来测试。
- 测试聚焦在**可观察行为**。

### 4. 重构

所有测试通过后，找[重构候选](refactoring.md)：

- [ ] 抽出重复。
- [ ] 深化模块（把复杂度藏到简单接口后）。
- [ ] 在自然处应用 SOLID。
- [ ] 思考新代码暴露了既有代码的什么问题。
- [ ] 每一步重构后跑测试。

**RED 的时候永远不要重构**。先到 GREEN。

## 每轮检查清单

```
[ ] 测试描述行为，不描述实现
[ ] 测试只走公开接口
[ ] 测试在内部重构后能存活
[ ] 代码刚好够当前测试用
[ ] 没有未被测试要求的"未来准备"代码
```

## 本项目适配示例

新增"采集器支持 ST 股票字段"——按垂直切片走：

**Cycle 1**（最小行为）：

```python
# RED
def test_collector_marks_st_stock():
    df = collector.fetch_basic_info("600519.SH")
    assert df.iloc[0]["is_st"] is False

# GREEN: 在 normalize 里加 is_st = False（默认）
```

**Cycle 2**：

```python
# RED
def test_collector_marks_real_st_stock():
    df = collector.fetch_basic_info("600145.SH")  # 实际 ST 股票
    assert df.iloc[0]["is_st"] is True

# GREEN: 实际查 Tushare name 字段是否含 "ST"
```

**Cycle 3**：边界——`*ST`、复牌等。每轮一个新断言、一段最小实现。

## 相关 skill

- [test-strategy](../../testing/test-strategy.md) - 分层、覆盖率、CI
- [collector-testing](../../testing/collector-testing.md) - 采集器专项测试模板
- [database-testing](../../testing/database-testing.md) - 数据库集成测试
- [data-quality](../../testing/data-quality.md) - 字段、表结构、完整性
- [diagnose](../diagnose.md) - 修 bug 时与 TDD 联动
- [improve-codebase-architecture](../improve-codebase-architecture/SKILL.md) - 重构阶段
