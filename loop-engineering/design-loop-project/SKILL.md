---
name: design-loop-project
description: 设计或重构项目级智能体 Loop Engineering 系统，覆盖任务筛选、循环架构、契约、状态、工具集、运行编排、验证与持续改良。用于搭建 agent loop、Ralph loop、目标驱动编码循环、定时分流循环或无人值守工程流程；不用于一次性脚本或无法验收的开放式探索。
---

# 设计 Loop Engineering 项目

## 先固定事实，再设计

1. 检查仓库、现有测试/CI、权限、可用连接器与运行环境；把每项结论标为“已验证”“用户声明”或“待验证”。不要假设平台命令、MCP、工作树或生产权限存在。
2. 读取 [references/evidence-policy.md](references/evidence-policy.md)，将目标、约束、风险和验收证据写入设计记录；没有证据的能力不进入自动化路径。
3. 调用 `$qualify-loop-task`。未通过可验证性、可控副作用或恢复能力门槛时，交付人工流程或确定性自动化建议并停止。

## 组装工程

4. 读取 [references/architecture-selection.md](references/architecture-selection.md)，从 ReAct 起步；仅在有明确收益时升级 Reflexion、Ralph、Plan-and-Execute、OODA、内外循环或多角色。
5. 依次调用 `$specify-loop-contract`、`$design-loop-state`、`$build-loop-harness` 和 `$operate-loop-run`。为每个工作项保留契约、状态、证据、恢复入口与人工闸门。
6. 在空目标或确认不覆盖既有 `.loop/` 后运行 `python scripts/scaffold_loop.py <project-root>`；用真实命令、阈值、权限和负责人替换模板值。
7. 调用 `$audit-loop-project` 进行隔离演练。只有阻断项清零后才允许受控试运行；长期运行后调用 `$improve-loop-system`。

## 交付与边界

交付可版本化工件，不只交付说明：`contract.json`、状态、运行手册、分流队列、证据日志、验证命令和升级路径。明确“自动通过”“独立模型判断”“人工批准”三种决策边界。

需要来源追溯时读取 [references/reference-map.md](references/reference-map.md)。

