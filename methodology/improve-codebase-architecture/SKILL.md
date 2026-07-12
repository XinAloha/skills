---
name: improve-codebase-architecture
description: 找代码库的深度化机会 - 深模块、locality、leverage，受 CONTEXT.md 与 ADR 影响
type: methodology
parent: dev-guidelines.md
auto_execution_mode: 2
source: Matt Pocock skills - engineering/improve-codebase-architecture
---

# Improve Codebase Architecture - 改进代码库架构

> 触发：用户希望改进架构、找重构机会、合并紧耦合模块、让代码库更可测、更易被 AI 导航。

暴露架构摩擦点，提出**深度化机会**——把浅模块变深的重构。目标是**可测性**和**可被 AI 导航**。

## 术语表

每条建议**严格使用以下术语**。一致的语言就是关键——不要漂移到 "component / service / API / boundary"。完整定义见 [LANGUAGE.md](LANGUAGE.md)。

- **Module（模块）** — 任何"接口 + 实现"的东西（函数、类、包、跨层切片都算）。
- **Interface（接口）** — 调用方使用模块时必须了解的一切：类型、不变量、错误模式、顺序、配置。不只是类型签名。
- **Implementation（实现）** — 模块内部的代码。
- **Depth（深度）** — 接口处的杠杆：少接口背后藏多行为。**深** = 高杠杆。**浅** = 接口几乎和实现一样复杂。
- **Seam（接缝）** — 接口所在的位置；可在不修改原地的情况下改变行为的地方。**用这个词，不要用 "boundary"**。
- **Adapter（适配器）** — 在 seam 处满足接口的具体实现。
- **Leverage（杠杆）** — 调用方因深度获得的收益。
- **Locality（局部性）** — 维护者因深度获得的收益：变更、bug、知识集中在一个位置。

关键原则：

- **删除测试**：想象删掉这个模块。复杂度消失了 → 它是透传。复杂度跨 N 个调用方重现 → 它在挣它的工资。
- **接口就是测试面**。
- **一个适配器 = 假想 seam；两个适配器 = 真 seam**。

这门 skill **被项目领域模型告知**：领域语言给好的 seam 命名；ADR 记录的决策不要被 skill 重新挑战。

## 流程

### 1. 探索

先读项目领域词汇（`CLAUDE.md` / `docs/core_features.md` / 任何 `CONTEXT.md`）和你要碰的区域里相关的 ADR。

然后用 Agent 工具（`subagent_type=Explore`）走代码库。**不要按死规则——有机地走，记下你哪里感到摩擦**：

- 哪里理解一个概念要在很多小模块间反复跳？
- 哪里**浅**——接口几乎和实现一样复杂？
- 哪里纯函数被抽出只为可测，但真实 bug 藏在调用方式里（无 **locality**）？
- 哪里紧耦合模块跨 seam 漏耦合？
- 哪部分代码不被测，或难以通过现有接口测？

对怀疑浅的东西用**删除测试**：删掉它会集中复杂度，还是只是把复杂度搬走？"集中"才是你要的信号。

### 2. 候选清单展示为 HTML 报告

写一个自包含 HTML 文件到操作系统 temp 目录，**不要**落进 repo。

- Linux: `$TMPDIR` → fallback `/tmp`
- Windows: `%TEMP%`

文件名 `<tmpdir>/architecture-review-<timestamp>.html`，每次跑刷新文件。打开它给用户看（`xdg-open` / `open` / `start`），告诉他们绝对路径。

报告：**Tailwind via CDN** 排版，**Mermaid via CDN** 画图（关系图、调用图、时序图），其他视觉用手写 CSS/SVG。每个候选都有**前 / 后对比图**。要视觉化。

每个候选一张卡：

- **Files** —— 涉及哪些文件 / 模块。
- **Problem** —— 当前架构哪里造成摩擦。
- **Solution** —— 大白话说会改成什么样。
- **Benefits** —— 用 locality / leverage 解释，以及测试会如何改善。
- **Before / After** —— 并排手绘，画出浅与深。
- **Recommendation strength** —— `Strong` / `Worth exploring` / `Speculative`，徽章。

报告末尾给一段 **Top recommendation**：你最先动哪个、为什么。

**用 `CONTEXT.md` 的领域语言谈领域**，**用 [LANGUAGE.md](LANGUAGE.md) 的架构语言谈架构**。如果 `CONTEXT.md` 定义了"采集器"，就说"采集器入口模块"——不是 "FooBarHandler"，也不是 "采集服务"。

**ADR 冲突**：候选若与既有 ADR 矛盾，**只在摩擦真的大到值得重审 ADR 时再列**，并用警示框标注（"与 ADR-0007 矛盾——但摩擦大到值得重开"）。不要列出所有理论上被 ADR 禁止的重构。

详见 [HTML-REPORT.md](HTML-REPORT.md) 完整脚手架与样式。

**先不要提议接口**。文件写好后，问用户："你想深入哪一个？"

### 3. 质询循环

用户挑了候选后，进入**质询对话**。和他们走设计树——约束、依赖、深化模块的形状、seam 后面是什么、哪些测试存活。

副作用在决策成形时**当场发生**：

- **要给一个 `CONTEXT.md` 没有的概念命名？** 当场写进 `CONTEXT.md`——和 [grill-with-docs](../grill-with-docs/SKILL.md) 同一套纪律（[CONTEXT-FORMAT.md](../grill-with-docs/CONTEXT-FORMAT.md)）。文件不存在就懒创建。
- **对话中锐化了一个模糊词？** 立刻更新 `CONTEXT.md`。
- **用户用一个有分量的理由拒绝候选？** 提议写 ADR：「要不要把这个记成 ADR，让以后的架构评审不再重复提议？」**只在理由会被未来的探索者需要、能避免再次被提议时**才提。临时性理由（"现在不值得"）和自明的理由（"显然不该这么做"）不要写。格式见 [ADR-FORMAT.md](../grill-with-docs/ADR-FORMAT.md)。
- **想为深化模块探索备选接口？** 见 [INTERFACE-DESIGN.md](INTERFACE-DESIGN.md)。

## 本项目典型深化候选

- **采集器降级链**：当前 Tushare → AKShare → adata 在每个采集器里写过一遍 → 抽 `FallbackChain` 深模块，每个数据源是一个 adapter。
- **字段标准化**：`normalize_kline` / `normalize_basic` / `normalize_adj` 都重复"重命名 + 类型转换 + 空值处理" → 抽 `FieldMapper` 配 schema。
- **限流 + 重试**：每个采集器手写 `time.sleep` + `try/except` → 抽 `RateLimitedClient` 装饰器或 mixin。

## 相关 skill

- [refactoring-checklist](../../governance/refactoring-checklist.md) - 分析 / 提取 / 重构三阶段
- [design-patterns](../../engineering/design-patterns.md) - 策略、工厂、模板方法
- [extensibility](../../engineering/extensibility.md) - 接口设计、插件架构
- [reusable-patterns](../../engineering/reusable-patterns.md) - 已沉淀的可复用模式
- [tdd](../tdd/SKILL.md) - 深化后写新接口测试
