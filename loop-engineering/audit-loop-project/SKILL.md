---
name: audit-loop-project
description: 审计智能体 Loop Engineering 项目的运行就绪度，验证契约、状态、权限、隔离、停止、恢复、独立验证、观测与持续反馈。用于试运行前、失控/停不下来的 loop 复盘、或无人值守上线评审；输出可复现阻断项，不替代业务所有者对高风险动作的批准。
---

# 审计 Loop 工程

1. 找到 `.loop/contract.json`、状态、运行手册、分流队列、证据日志、执行入口和检查命令；将缺失项列为阻断。
2. 运行 `python scripts/audit_loop.py <project-root>` 与契约校验脚本。脚本只做静态一致性检查，不能据此宣称运行安全。
3. 按 [references/audit-checklist.md](references/audit-checklist.md) 核查目标证据、预算、断路器、状态、权限、工作树/隔离、观测、独立验证和改良闭环。
4. 按 [references/drill-playbook.md](references/drill-playbook.md) 在非生产环境演练成功、检查失败、无进展、工具重试耗尽、中断恢复、重复触发、验证者拒绝和人工闸门。
5. 输出阻断/重要/改进项及证据、复现方式、责任人、最小修复与复验条件。仅当阻断项清零才标记“可受控试运行”。

## 成功标准

既证明“应停止时能停止”，也证明“执行者声称完成时不会误完成”。任何未演练的高风险路径都不能标记为已验证。

