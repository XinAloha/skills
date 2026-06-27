---
description: 审查与清理规范 - code review、冗余扫描、架构违规和文档一致性（跨平台版）
type: sub-document
applies-to: [claude-code, codex]
auto_execution_mode: 2
---

# 审查与清理

## Code Review 输出顺序

用户要求 review 时，先列问题，再给摘要：

1. 按严重程度排序的发现项，必须包含文件和行号；Claude Code 写成 `path:line`，Codex 同样写清 `文件:行号`。
2. 开放问题或假设。
3. 简短变更摘要或测试缺口。

无问题时明确说明未发现阻塞问题，并指出剩余风险。

> Review 模式下不要直接改代码，除非用户明确说“修复”或“按 review 结果改”。Claude Code 不调用 `Edit`/`Write`/`Bash` 改写文件；Codex 不调用 `apply_patch`/编辑器写入/`run_terminal_cmd` 改写文件，除非用户明确授权修复。

## 扫描维度

### 1. 行为风险

- [ ] 新逻辑是否改变 CLI 默认行为？
- [ ] 空数据是否会覆盖已有数据？
- [ ] 降级源失败时是否仍被记录为成功？
- [ ] 批量写入是否可能产生重复记录？
- [ ] 真实 API 限流是否会导致测试或任务不稳定？

### 2. 架构风险

- [ ] 采集器是否越权写库或调度全流程？
- [ ] `core/` 是否直接硬编码第三方字段细节？
- [ ] 数据库层是否调用外部数据源？
- [ ] 是否新增循环导入或跨层私有方法调用？
- [ ] 配置是否散落在代码常量中？

### 3. 冗余与可维护性

- [ ] 是否重复实现重试、分页、限流、字段映射？
- [ ] 是否存在未使用导入、废弃函数、重复常量？
- [ ] 是否有过宽的 `except Exception` 吞错？
- [ ] 是否把诊断脚本逻辑复制进核心模块？

### 4. 文档一致性

- [ ] README 目录树和功能列表是否反映当前代码？
- [ ] `docs/core_features.md` 是否记录新增核心行为？
- [ ] 数据库 schema 文档是否同步字段或表变化？
- [ ] `.env.example` 是否包含新增环境变量占位说明？

## 常用只读扫描

只读扫描应按平台选择对应调用；不要把某个平台的命令直接套到另一个平台。Claude Code 优先用内置搜索工具；Codex 优先用终端里的 `rg`/PowerShell 只读命令。

| 扫描目标 | Claude Code 调用 | Codex 调用 |
|---|---|---|
| 查找硬编码敏感词 | `Grep pattern="token|password|secret|api_key|TUSHARE" path="data_collection config test docs"` | `rg -n "token|password|secret|api_key|TUSHARE" data_collection config test docs` |
| 查找宽泛异常处理 | `Grep pattern="except Exception|except:" path="data_collection test"` | `rg -n "except Exception|except:" data_collection test` |
| 查找直接数据库写入 | `Grep pattern="to_sql|INSERT|DELETE|TRUNCATE|create_engine" path="data_collection"` | `rg -n "to_sql|INSERT|DELETE|TRUNCATE|create_engine" data_collection` |
| 查找未同步文档线索 | `Grep pattern="TODO|FIXME|deprecated|兼容|临时" path="data_collection docs test"` | `rg -n "TODO|FIXME|deprecated|兼容|临时" data_collection docs test` |

补充工具规则：

- 搜索文件名或目录结构：Claude Code 用 `Glob pattern="..." path="..."`；Codex 用 `rg --files`、`Get-ChildItem` 或等价只读 `run_terminal_cmd`。
- 读取具体文件：Claude Code 用 `Read file_path="..."`；Codex 用 `Get-Content` 或只读 `run_terminal_cmd`。
- Claude Code 中不要用 `Bash: rg` 做上述内容搜索，应用 `Grep` 工具；Codex 中应用 `rg -n` 或 PowerShell 只读命令。
- 需要并行的大范围只读调查时，Claude Code 可用 `Agent`/`TaskCreate` 委派只读搜索（仅 Claude Code 适用）；Codex 不使用 Claude 子代理，改用多条 `rg`/PowerShell 只读命令分批执行。

## 自动修复边界

可以直接修（前提是用户已经授权修复，而不是仅要求 review）：

- 未使用导入、明显重复常量、过期 docstring。
- README 中明确过期的目录或命令。
- 缺失的测试标记、测试命名和 fixture 复用。

修复时的平台调用必须明确：Claude Code 用 `Edit` 做局部替换、用 `Write` 创建或整体覆盖必要文件、用 `Bash` 运行格式化/测试命令；Codex 用 `apply_patch` 做局部补丁、用编辑器写入创建或整体覆盖必要文件、用 `run_terminal_cmd`/PowerShell 运行格式化/测试命令。

需要谨慎或先解释：

- 删除可能被反射、CLI 或外部脚本调用的函数。
- 改变数据库 schema 或迁移历史数据。
- 改变真实数据源优先级和降级语义。
- 删除诊断脚本或历史数据文件。

涉及谨慎项时，先说明影响范围和回滚方式，再征求用户确认；Claude Code 不直接 `Edit`/`Write`/`Bash` 执行破坏性改动，Codex 不直接 `apply_patch`/写文件/`run_terminal_cmd` 执行破坏性改动。

## 与 .codex / .devin 的协作

- 三方共享规则的唯一事实源是 `skills/` 下的功能分类目录。如发现共享规则与当前 agent-adapters 适配版 [`./`](./) 产生语义冲突，以共享版为准并向用户报告。
- 除用户明确授权的工作流维护/迁移外，不主动改写 `.codex/` 与 `.devin/` 下的入口规则；Claude Code 不调用 `Edit`/`Write` 修改这些入口，Codex 不调用 `apply_patch`/写文件修改这些入口。
- 新增规则优先放入跨平台版的 `agent-adapters/<skill>.md`（`applies-to: [claude-code, codex]`），并在涉及实际工具调用的段落里同时给出 Claude Code 与 Codex 的对应做法；只属于单一平台的规则，可在同一文件里加平台限定（如「（仅 Claude Code 适用）」）。共享、平台无关的规则按功能放入 `skills/engineering/`、`skills/testing/`、`skills/governance/` 等分类目录。

## 清理触发频率

| 触发条件 | 动作 | 平台调用要求 |
|---------|------|--------------|
| 用户说“清理代码 / 扫描冗余 / auto-cleanup” | 读 [`../governance/auto-cleanup.md`](../governance/auto-cleanup.md)，按其流程执行 | Claude Code 用 `Read file_path=".../skills/governance/auto-cleanup.md"`；Codex 用 `Get-Content .../skills/governance/auto-cleanup.md` 或等价只读 `run_terminal_cmd` |
| 每个 PR 合并前 | 至少跑一次“行为风险”和“文档一致性”扫描 | Claude Code 用本文件表格中的 `Grep`/`Glob`/`Read`；Codex 用本文件表格中的 `rg -n`/`Get-ChildItem`/`Get-Content` |
| 里程碑前 | 全量扫描，输出清理摘要供用户确认 | Claude Code 可用 `Agent`/`TaskCreate` 做只读 fan-out（仅 Claude Code 适用），并用 `Grep` 汇总；Codex 用多条 `rg -n`/PowerShell 只读命令汇总 |
