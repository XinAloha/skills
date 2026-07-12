---
name: specify-loop-contract
description: 将自然语言目标写成可机器校验的 Loop 契约：触发、架构、证据、权限、预算、状态转换、停止、断路器与人工批准。用于新建或修订 agent loop、Ralph loop、定时或事件驱动循环的完成定义；不负责选择存储实现。
---

# 定义 Loop 契约

1. 读取 [references/contract-schema.md](references/contract-schema.md)，创建或更新 `.loop/contract.json`；每个字段使用项目事实，未知字段保留为阻断项而不是编造值。
2. 将目标拆成“声明 + 可执行证据 + 通过阈值 + 证据保存位置”。为语义判断指定独立验证者和人工兜底。
3. 指定触发器类型、去重键、并发策略和工作项粒度；事件触发必须定义过滤条件，计划触发必须定义无发现时的收尾。
4. 定义每轮协议和状态转换。设置迭代、时间、成本、并发、单动作范围和工具重试上限。
5. 分开定义成功、硬停止、无进展、断路器、策略重置和人工升级；不可逆动作必须列入批准闸门。
6. 运行 `python scripts/validate_contract.py <project-root>`，再按 [references/contract-examples.md](references/contract-examples.md) 演练正例和反例。

## 成功标准

陌生操作者可只凭契约作出继续、完成、暂停、重置策略或升级决定。任何“完成”都能定位到外部证据。

