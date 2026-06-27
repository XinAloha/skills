---
description: 跨平台版修改工作流 - 从需求澄清、实现边界到验证和交付摘要，覆盖 Claude Code 与 Codex 工具调用
type: sub-document
applies-to: [claude-code, codex]
auto_execution_mode: 2
---

# 修改工作流

## Step 0: 任务追踪决策

> 不是所有任务都要开任务列表；不要把单步任务包成 task list 来表演进度。

| 任务规模 | 处理 |
|---------|------|
| 单文件 1-2 处编辑 | 直接做，不开 task / plan |
| 多文件协作或 ≥3 步 | **Claude Code:** 用 `TaskCreate` 拆分；开始时 `TaskUpdate status=in_progress`；完成时 `TaskUpdate status=completed`。若当前环境提供 `TodoWrite`，用同等语义维护 `pending / in_progress / completed`。<br>**Codex:** 用 `update_plan` 拆分；每次只保留一个 `in_progress`；完成时标记 `completed`。 |
| 用户列出多项要求 | 立即把每项落成 task / plan item：**Claude Code:** `TaskCreate` / `TodoWrite`；**Codex:** `update_plan`。 |
| 探索/研究类 | 不必开 task / plan，但保留待办待用户确认后再开：**Claude Code:** 可先说明待确认项，必要时再 `TaskCreate` / `TodoWrite`；**Codex:** 可先说明待确认项，必要时再 `update_plan`。 |

## Step 1: 需求落点

先把用户请求归入一个具体落点：

| 类型 | 判断标准 | 输出物 |
|-----|---------|--------|
| Bug 修复 | 已有行为错误、测试失败、数据异常 | 最小修复 + 回归测试 |
| 新功能 | 新数据源、新表、新 CLI 模式、新字段 | 实现 + 单元/集成测试 + 文档 |
| 重构 | 行为不变，改善结构或去重 | 小步提交式修改 + 原行为测试 |
| 审查 | 用户明确说 review/检查 | 发现项优先，不直接改代码，除非用户要求修复 |
| 诊断 | 网络、数据库、依赖、数据质量问题 | 可复现命令 + 根因判断 + 修复建议或补丁 |

判断不清时，提供 2-3 个具体选项并等待用户确认，**不要**含糊地“先做了再说”。

- **Claude Code:** 使用 `AskUserQuestion` 提供 2-3 个具体选项；没有该工具时，直接向用户提问并暂停修改。
- **Codex:** 直接向用户提出 2-3 个具体选项并等待确认；不要先改代码。

## Step 2: 变更边界

修改前确认：

- [ ] 哪些 public API、CLI 参数或表结构会变化？
- [ ] 是否需要保持旧字段名、旧配置名或旧命令兼容？
- [ ] 是否影响真实网络请求和真实数据库？
- [ ] 是否需要更新 README、`docs/core_features.md` 或数据库文档？
- [ ] 是否存在用户未提交或非本任务的改动需要避开？
- [ ] 是否会触发不可逆操作（drop 表、删分支、强推、删除文件）？涉及时**先与用户确认**。

边界确认时的常用工具调用：

| 目的 | Claude Code | Codex |
|-----|-------------|-------|
| 查看当前改动 | `Bash command="git status --short"` / `Bash command="git diff -- <path>"` | `run_terminal_cmd` 执行 `git status --short` / `git diff -- <path>` |
| 查找文件 | `Glob pattern="**/*.py"` 或按目录限定 `Glob path="..." pattern="..."` | `rg --files`，再用 `rg "\.py$"` / `Select-String` 过滤 |
| 搜索引用 | `Grep pattern="..." path="..." output_mode="content"` | `rg "..." <path>` 或 PowerShell `Select-String -Path <path> -Pattern "..."` |
| 读取文件 | `Read file_path="/absolute/path"` | PowerShell `Get-Content -Raw <path>` 或 `Get-Content <path> -TotalCount N` |

## Step 3: 实现原则

- 优先复用当前项目已有模式，不新增不必要依赖。
- 对 Python 代码保持类型注解、清晰异常路径和小函数边界。
- 对采集逻辑保持“获取原始数据 -> 标准化 -> 校验 -> 写入/返回”的顺序。
- 对配置项保持 `config/default.yaml` 默认值 + 环境变量覆盖。
- 对数据库写入保持幂等，优先考虑唯一约束和重复数据处理。
- **不做未被请求的“顺手”改动**：不补 docstring、不加 type hint、不重排 import、不抽工具函数，除非任务明确要求。
- 改文件前必须先读文件，不能凭印象修改：**Claude Code:** 先 `Read` 再 `Edit` / `Write`；**Codex:** 先 `Get-Content -Raw <path>` 或 `rg` 定位并读取上下文，再用 `apply_patch` 修改。

实现时的工具调用规则：

| 场景 | Claude Code | Codex |
|-----|-------------|-------|
| 精确替换已有内容 | 先 `Read file_path="..."`，再 `Edit old_string="..." new_string="..."`；确保 `old_string` 唯一且包含准确缩进。 | 先 `Get-Content -Raw <path>` 读取，再用 `apply_patch` 精确替换；patch 上下文必须足够小且能唯一定位。 |
| 新建或整体重写文件 | `Write file_path="..." content="..."`；覆盖已有文件前必须先 `Read`。 | 用 here-string / PowerShell 写入，或用 `apply_patch` 新增文件；覆盖已有文件前必须先 `Get-Content`。 |
| 多文件关联修改 | 可用 `TaskCreate` / `TodoWrite` 记录步骤；必要时用 `Agent` 子代理做只读搜索或并行调查（仅 Claude Code 适用）。 | 用 `update_plan` 记录步骤；用 `rg` / `Get-Content` 自行搜索，不把实现拆成平台大段。 |
| 运行命令 | `Bash command="..." description="..."`。 | `run_terminal_cmd` 执行 PowerShell / shell 命令。 |
| 长耗时命令 | `Bash run_in_background=true`，完成后再读取结果。 | `run_terminal_cmd` 设置合理超时；若环境支持后台任务，启动后轮询结果。 |

（仅 Claude Code 适用）使用 `Agent` 子代理时，只委派独立的只读探索、跨文件搜索或可并行调查；不要让子代理直接做用户未授权的写入、提交、推送或不可逆操作。子代理结论要回收到主线程后再决定是否修改。

## Step 4: 验证顺序

按变更相关性从小到大验证。命令本身一致，执行入口按平台区分：

- **Claude Code:** 通过 `Bash command="..." description="..."` 执行；测试时长可能较长时使用 `Bash run_in_background=true`，并在完成后再读取结果。
- **Codex:** 通过 `run_terminal_cmd` 执行；Windows / PowerShell 环境下可直接运行同等命令，必要时设置工作目录和超时。

```bash
# 语法与导入
python -m compileall data_collection test

# 与变更最相关的单元测试
pytest test/unit/test_xxx.py -v --tb=short

# 受影响的集成测试
pytest test/integration/test_xxx.py -v --tb=short

# 涉及字段或表时运行数据质量测试
pytest test/data_quality -v --tb=short
```

验证选择规则：

- Bug 修复：至少运行直接覆盖该 bug 的测试；没有测试时，先补最小回归测试或说明无法补测原因。
- 新功能：运行新增测试 + 受影响模块的现有测试。
- 重构：运行原行为测试，确保行为不变。
- 诊断：给出可复现命令、观察结果和根因判断；如改代码，再运行对应回归验证。
- 涉及字段或表：运行 `pytest test/data_quality -v --tb=short`。

## Step 5: 交付摘要

最终回复包含：

- 改了哪些文件和行为；**Claude Code:** 用 `path:line` 引用；**Codex:** 也尽量用 `path:line` 引用，若未取得行号则至少给出精确文件路径和函数 / 配置名。
- 跑了哪些验证命令，结果如何。
- 未验证的部分和原因。
- 对用户下一步有用的命令或注意事项。

避免输出大段 diff；用户需要时再提供具体片段。**不要在回复末尾粘贴所有改动后的文件内容**——用户可以自己看 diff。

## Git 操作纪律

- **不主动**执行 `git commit` / `git push` / `git tag`，除非用户明确要求。
- 写 commit message 时使用 HEREDOC 格式，参考 [`../git/git-commit-convention.md`](../git/git-commit-convention.md)。
  - **Claude Code:** 用 `Bash` 执行 HEREDOC 形式的 `git commit` 命令。
  - **Codex:** 用 `run_terminal_cmd` / PowerShell 执行等价 HEREDOC 或临时 message file 方式，避免交互式编辑器。
- 任何 force push、`git reset --hard`、删分支等不可逆操作都必须先确认。
- 不修改 `.git/config`、`user.name`、`user.email`。
- 不在 commit message、PR body 中泄露 `.env` 内容或 token。
