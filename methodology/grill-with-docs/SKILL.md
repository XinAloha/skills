---
description: 计划质询 + CONTEXT.md / ADR 内联更新 - 在领域模型上压力测试方案
type: methodology
parent: dev-guidelines.md
auto_execution_mode: 2
source: Matt Pocock skills - engineering/grill-with-docs
---

# Grill With Docs - 文档质询

> 触发：用户希望让方案在项目语言 / 已记录决策上接受压力测试。

## 做什么

不停问我关于这个方案的每一个方面，直到我们达成共识。**沿决策树每个分支走，逐项解决依赖**。每个问题，给出你**推荐的答案**。

**一次问一个问题，等我反馈再继续**。

如果一个问题可以通过浏览代码库回答，**直接去看代码，别问我**。

## 支撑信息

### 领域感知

探索代码库时，同时找已有的项目语言文档：

#### 文件结构

大多数仓库是单一上下文：

```
/
├── CONTEXT.md
├── docs/
│   └── adr/
│       ├── 0001-tushare-为主要数据源.md
│       └── 0002-postgres-为生产存储.md
└── data_collection/
```

如果根目录存在 `CONTEXT-MAP.md`，仓库有多个上下文，map 指出每个上下文的位置（本项目目前只有单一上下文，未启用 map）。

**懒创建**：只有要写第一条术语时才创建 `CONTEXT.md`；只有要写第一份 ADR 时才创建 `docs/adr/`。

### 会话期间

#### 与术语表对抗

当用户用的词与 `CONTEXT.md` 已有定义冲突，**当场叫停**：

> "你的术语表把'前复权'定义为 X，但你刚才好像在说 Y——是哪一个？"

#### 锐化模糊用语

模糊或多义词，提议精确的标准词：

> "你说'账号'——是指 Tushare 账号还是 PostgreSQL 角色？这俩不一样。"

#### 用具体场景压测

讨论领域关系时，用具体场景压一压。发明能戳到边界的场景，强迫对方对概念边界精确表态。

例（本项目）：
- "假设 600519.SH 在 20251010 停牌全天，你这个'每日采集器'返回什么？空 DataFrame？带 NaN 的一行？"
- "假设 Tushare 限流，AKShare 也降级，那 adata 也失败——这是数据缺失还是采集失败？schema 里怎么标？"

#### 与代码交叉验证

用户陈述某事如何工作时，**对照代码看**。如果矛盾，挑出来：

> "你说采集器整单订单全量取消，但代码 `data_collection/collectors/tushare.py:142` 看起来支持部分取消——哪个对？"

#### 当场更新 CONTEXT.md

某术语解决了，**当场更新 `CONTEXT.md`**。不要批量。格式见 [CONTEXT-FORMAT.md](CONTEXT-FORMAT.md)。

`CONTEXT.md` **不放任何实现细节**。它不是规格、不是草稿本、不是实现决策仓库——它是术语表，仅此而已。

#### 谨慎给 ADR

只有三件事都满足时再给 ADR：

1. **难以反悔** —— 改主意的成本可观。
2. **没有上下文会觉得意外** —— 未来读者会想"为什么这么干？"。
3. **真有取舍** —— 真存在替代方案，你出于具体理由选了这个。

任一不满足，跳过。格式见 [ADR-FORMAT.md](ADR-FORMAT.md)。

## 本项目典型问题清单（启动器）

- 这个新数据源是主源、备源还是降级源？降级链是什么？
- 字段是否需要进 standardized schema？影响哪些下游表？
- 是否影响 `data_collection.database.schema`？要写迁移吗？
- pytest 哪一层覆盖？unit / integration / data_quality？
- 是否需要 `docs/core_features.md` 新增段落？
- 是否触发既有 ADR 的修订？

## 相关 skill

- [project-manager](../../governance/project-manager.md) - 需求抽象评审、流程矛盾清理
- [new-feature-process](../../engineering/new-feature-process.md) - 新功能开发完整流程
- [grill-me](../../workmode/grill-me.md) - 非代码版本的质询
- [diagnose](../diagnose.md) - 修 bug 时也可触发
