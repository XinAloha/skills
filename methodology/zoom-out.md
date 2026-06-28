---
description: 抽象层提升 - 给陌生模块画地图，用项目 CONTEXT.md 词汇
type: methodology
parent: dev-guidelines.md
auto_execution_mode: 2
source: Matt Pocock skills - engineering/zoom-out
---

# Zoom Out - 抽象层提升

> 触发：用户说"zoom out / 给我看大图 / 这块代码我不熟，先给我讲讲全貌"。

## 单段指令

> 我对这部分代码不熟。**抽一层**。给我一份所有相关模块和调用方的地图，用项目 `CONTEXT.md` 的领域语言描述。

## 在本项目的执行细则

1. 用 `Glob` / `Grep` 找出涉及的入口、主文件、相关测试。
2. 画出"调用谁 / 被谁调用"的链条（最少层级，覆盖最相关的模块）。本项目核心是：
   ```
   main.py -> data_collection.core.scheduler -> data_collection.collectors.* -> data_collection.database.writer
   ```
3. 用本项目术语：**采集器（Collector）/ 数据源（Tushare / AKShare / adata / 通达信）/ 标准化（normalize） / 写入（writer）/ 数据质量校验（data_quality）**——不要用"组件 / 服务"这类含糊词。
4. 标出与 ADR / `docs/core_features.md` / `docs/database_documentation.md` 中已有决策的关联，避免重新讨论既定决策。
5. 末尾给一句话总结："这块的核心责任是 X，主要风险点是 Y"。

## 适合用 zoom-out 的场景

- 接手一个不熟的采集器 / 调度链。
- 评审一个跨多文件的 PR 前先建立心智模型。
- bug 复现前要先理清"这个数据是从哪儿来的"。

## 相关 skill

- [project-context](../agent-adapters/project-context.md) - 项目结构速览（跨平台版）
- [reference-analysis](../governance/reference-analysis.md) - 参考项目分析流程
- [improve-codebase-architecture](improve-codebase-architecture/SKILL.md) - zoom-out 之后想动结构时
