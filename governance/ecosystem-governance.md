---
description: 生态治理 - 跨项目对齐、共享输出、记忆分级、收尾审计。触发词：生态治理、跨项目对齐、生态收尾、ecosystem governance、governance closeout。
type: governance
parent: dev-guidelines.md
auto_execution_mode: 2
---

# 生态治理 —— 跨项目工作流

> 治理 `E:\Project\Quantitative_Trading` 多项目、多 Agent 生态的共享工作流。事实源：`governance/`（渐进式披露：L0 全局 → L1 项目对齐 → L2 项目内部）。

## 触发场景
- 新项目加入生态
- 跨项目协作任务
- 生态级收尾 / 审计
- Agent 需要了解其它项目

## 工作流

### 1. 认知对齐（每次跨项目操作前）
1. 读 `governance/ECOSYSTEM.md` ← 生态身份 / 共享铁律（L0）
2. 读 `governance/projects/<目标项目>_ALIGNMENT.md` ← 目标项目对齐（L1）
3. 按需深读目标项目 L2 入口（CLAUDE.md / RULES.md / docs/manifest.yaml）

### 2. 跨项目协作
1. 从 ALIGNMENT.md 确认对方的 **PUBLISHES / CONSUMES** 接口
2. 按约定格式读取 / 写入对方发布的数据或文档
3. 产出写入共享输出区：
   - 跨项目决策 → `governance/outputs/decisions/`
   - 项目间交接 → `governance/outputs/handoffs/`
   - 跨项目通用教训 → `governance/outputs/lessons/`
4. 若 PUBLISHES / CONSUMES 变化，更新本项目的 ALIGNMENT.md（frontmatter `last_updated`）

### 3. 记忆分级输出
- 生态级事实 → `governance/memory/`（L0 共享），并在 `governance/memory/MEMORY.md` 登记一行
- 项目间接口变更 → `outputs/decisions/` + 更新相关 ALIGNMENT.md
- 项目内部教训 → 本项目的 RULES.md §8（L2）
- 跨项目通用教训 → `outputs/lessons/`（从 RULES.md §8 毕业）

### 4. 生态收尾
- 加载 `skills/meta/neat-freak` 做六面事实矩阵（code/runtime/docs/rules/memory/workspace）治理收尾
- 加载 `skills/governance/project-manager` 做四维需求评审（Abstraction/Flow/Responsibility/Semantics）
- 更新 `governance/memory/MEMORY.md` 索引
- 更新受影响的 ALIGNMENT.md

## 渐进式披露记忆分层

| 层 | 范围 | 谁读 | 放什么 |
|---|---|---|---|
| L0 | 全生态 | 所有 agent | 生态身份、项目清单、共享铁律、agent 角色 |
| L1 | 单项目、他项目读 | 其它项目的 agent | PUBLISHES / CONSUMES / 状态 / 红线 / L2 指针 |
| L2 | 单项目、本项目 agent 读 | 仅本项目 agent | 项目自身 CLAUDE.md / RULES.md / docs/ / memory/ |

**晋级**：L2→L1（稳定接口被其它项目消费→上架 PUBLISHES）；L2→L0（跨项目通用教训→`outputs/lessons/`）；L1→L0（跨项目模式成共享铁律→ECOSYSTEM.md）。

## 读取其它 Agent 产出（示例）

- **读 QuantDataCollectionSystem 的**：
  - 数据健康 → `QuantDataCollectionSystem/logs/quality/quality_report_*.md`
  - 当日进度 → `git show main:docs/agents/progress/progress.md`（§18 规则，从 main 读）
  - 共享教训 → `QuantDataCollectionSystem/RULES.md §8`
- **读 worldquantAlpha-dev 的**：
  - 文档清单 → `worldquantAlpha-dev/docs/manifest.yaml`
  - 运行时记忆 → `worldquantAlpha-dev/memory/<tag>/failure_patterns.json`
  - 迭代记录 → `worldquantAlpha-dev/CHANGELOG.md`

## 约束
- 不修改任何项目内部（改他人项目走对方 PR 流程）
- 量化策略核心 IP（策略代码/参数/因子/模型权重）不入库、不上传 GitHub
- `governance/` 为普通共享文件夹，不建 git；各项目自行维护自己的 ALIGNMENT.md 与 L2
