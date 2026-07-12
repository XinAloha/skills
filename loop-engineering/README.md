# Loop Engineering Skills

`loop-engineering/` 专门管理项目级智能体循环工程。八个 Skill 可独立调用，也可由 `design-loop-project` 按阶段编排。所有设计建议必须来自项目证据或 `loop_references/`，未知能力先探测而不假设。

## 能力地图

| Skill | 职责 | 典型产物 |
|---|---|---|
| [`design-loop-project`](design-loop-project/) | 总入口与工程编排 | 可运行的 `.loop/` 骨架 |
| [`qualify-loop-task`](qualify-loop-task/) | 判断任务是否适合循环化 | 适配结论、边界与最小试点 |
| [`specify-loop-contract`](specify-loop-contract/) | 定义目标与防护栏 | 触发、证据、预算、停止和升级契约 |
| [`design-loop-state`](design-loop-state/) | 设计跨轮次状态和记忆 | 状态模型、日志、检查点与恢复策略 |
| [`build-loop-harness`](build-loop-harness/) | 构建指南与反馈控制 | 检查、观测、权限和修正顺序 |
| [`audit-loop-project`](audit-loop-project/) | 上线前审计 | 阻断项、演练证据与试运行结论 |
| [`operate-loop-run`](operate-loop-run/) | 运行与恢复 | 分流、隔离、验证、交接与恢复记录 |
| [`verify-loop-delivery`](verify-loop-delivery/) | 独立代码审核 | 只读验证实施代理产物并输出可追溯裁决 |
| [`improve-loop-system`](improve-loop-system/) | 持续改良 | 规则、传感器、文档、记忆和指标的演化 |

## 推荐流程

新项目直接调用 `$design-loop-project`。专项任务可分别调用对应 Skill，标准顺序为：

`qualify-loop-task → specify-loop-contract → design-loop-state → build-loop-harness → operate-loop-run → verify-loop-delivery → audit-loop-project → improve-loop-system`

只有任务适合循环化、阻断项清零且人工闸门明确时，才进入受控试运行。参考资料放在各 Skill 的 `references/` 中按需加载；确定性动作放在 `scripts/` 中执行。循环结束不等于系统完成：将已验证的失败教训沉淀为项目控制，才形成长期闭环。
