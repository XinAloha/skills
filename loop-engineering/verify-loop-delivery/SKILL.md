---
name: verify-loop-delivery
description: 独立审核 Loop 中实施代理产出的代码、配置、测试和运行证据，并给出可追溯的 pass、reject 或 escalate 裁决。用于源码写入任务在草稿 PR、合并或发布前的独立验证；验证者不得实施同一任务的代码、修改工作树、提交、推送、创建 PR 或合并。
---

# 独立验证 Loop 交付

1. 读取契约、任务状态、基线/变更差异、实施证据和项目规则。确认 `review.implementer_identity` 与 `review.verifier_identity` 不同；相同或无法确认时裁决 `escalate`。
2. 保持只读：不得编辑文件、运行会写入的命令、提交、推送、创建/更新 PR 或合并。需要修复时只能给出拒绝理由与下一步。
3. 读取 [references/review-checklist.md](references/review-checklist.md)，再加载项目指定的扩展检查表；按真实风险排序执行可验证检查。优先运行测试、类型/静态检查、结构检查、接口或 UI/API 行为验证，而非凭阅读意图通过。
4. 把每一项检查的命令/查询、结果、证据位置和未覆盖风险写入裁决。只有所有必需检查通过且没有未处理阻断项时才 `pass`。
5. 输出 `pass`、`reject` 或 `escalate`，格式遵循 [references/verdict-contract.md](references/verdict-contract.md)。将裁决交回运行状态；由实施代理决定是否修复，验证者不代为实现。

## 成功标准

任何人可从裁决复现“为何通过或拒绝”。验证者未执行真实检查、与实施者身份相同、或缺少关键证据时不得给出 `pass`。

