---
name: operate-loop-run
description: 运行已批准的项目级智能体循环：分流工作项、创建隔离执行环境、编排实施与独立验证、管理状态、处理反馈并安全交接。用于启动、恢复、暂停或收尾已有 Loop 工程，不用于绕过契约、权限或人工闸门。
---

# 运行 Loop 工程

1. 读取契约、状态、最近证据和项目规则；先执行只读预检。能力或权限未验证时转为阻断，不尝试猜测平台命令。
2. 对定时或事件循环读取 [references/scheduling-and-oversight.md](references/scheduling-and-oversight.md)，确认调度器、时区、单次超时、每日预算、最大重试和人工入口都已被实际验证。
3. 按 [references/runtime-protocol.md](references/runtime-protocol.md) 接收或创建分流项；用去重键确认未被处理，按契约申请租约/并发槽。
4. 对会写入仓库的任务读取 [references/worktree-and-delivery.md](references/worktree-and-delivery.md)，创建独立工作树和契约指定的任务分支。并行任务不得共享写目录、分支或状态写者；不能隔离则串行。禁止在 `main` 上写入或直接推送远端 `main`。
5. 执行固定轮次：读取 → 定向 → 最小行动 → 观察 → 快速验证 → 状态/证据持久化 → 决策。触发无进展或重复失败时按契约重规划或升级。
6. 将实施者与验证者分离。需要模型或目标驱动终止时读取 [references/reviewer-and-goal.md](references/reviewer-and-goal.md)；验证者仅根据契约、差异、命令输出和运行时证据判定，未通过则把反馈写回任务状态。
7. 通过后仅创建待交接产物（例如补丁、草稿 PR、报告）。除非契约明确声明 `no-source-delivery`，代码交付必须经任务分支和草稿 PR；合并、部署、生产写入、外部通知必须等待批准闸门。
8. 释放租约、归档证据、记录成本/未决风险和下一动作。中断后按 [references/recovery-protocol.md](references/recovery-protocol.md) 对账再恢复。

## 成功标准

每轮可追踪、可恢复、可验证；并行运行不互相覆盖；所有高风险行为都能定位到明确的人类批准记录。


