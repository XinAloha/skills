---
description: 工具使用纪律 - 何时用专用文件工具，何时用 Shell，何时用 subagent（跨平台版，覆盖 Claude Code 与 Codex）
type: sub-document
applies-to: [claude-code, codex]
auto_execution_mode: 2
---

# 工具使用纪律

> 不同 agent 平台的可用工具是分层的。错误的工具会让用户难以审查、降低性能、或绕过安全机制。本文档定义本项目中两套主力 agent（Claude Code 与 Codex）的工具选择规则。
>
> **总原则**：能用平台原生的文件/搜索专用工具，就不要走 shell。Claude Code 的 `Read/Edit/Glob/Grep` 与 Codex 的 `apply_patch / rg` 都是为可审查、可权限管控设计的；通用 shell 命令是 fallback。

## 一、文件读写：永远优先专用工具

| 任务 | 在 Claude Code | 在 Codex | 禁止 |
|------|---------------|---------|------|
| 读单个文件 | `Read` | `Get-Content -Raw -Encoding UTF8 <file>`（PowerShell）/ `cat <file>` | Claude Code 下用 `Bash: cat / head / tail / sed -n` |
| 读多个独立文件 | 单条消息内并行多次 `Read` | 一次 `run_terminal_cmd` 里串多个 `Get-Content`，或多次独立调用 | 顺序串行读 |
| 创建新文件 | `Write` | `apply_patch`（`*** Add File: <path>`） | Claude Code 下用 `Bash: cat > / echo > / printf >` |
| 编辑已有文件 | `Edit`（先 `Read`） | `apply_patch`（`*** Update File: <path>`） | Claude Code 下用 `Bash: sed -i / awk` 改文件 |
| 改名 / 删文件 | `Bash: mv / rm` | `run_terminal_cmd` + `Move-Item` / `Remove-Item` 或 `mv / rm` | （这是 shell 合理用途） |

> ⚠️ Claude Code：`Edit` 在使用前**必须**对该文件做过一次 `Read`，否则会报错。
> ⚠️ Codex：`apply_patch` 的 hunk 上下文行如果与磁盘当前内容不一致会失败，先用 `Get-Content` 或 `rg` 核对最新内容。

## 二、查找：用专用搜索工具，不要泛用 shell

| 任务 | 在 Claude Code | 在 Codex | 禁止 |
|------|---------------|---------|------|
| 按文件名 / 扩展名查找 | `Glob: pattern="**/*.py"` | `rg --files \| rg "\.py$"` | Claude Code 下 `Bash: find / ls` |
| 按文件内容关键字查找 | `Grep: pattern="..."` | `rg "..."` | Claude Code 下 `Bash: grep` |
| 同时按内容 + 文件类型过滤 | `Grep: pattern=..., type="py"` | `rg "..." -t py` | — |
| 看匹配上下文 | `Grep: output_mode="content", -C=3` | `rg "..." -C 3` | — |
| 大致统计匹配数 | `Grep: output_mode="count"` | `rg -c "..."` | — |

Claude Code 下 `Grep` / `Glob` 会自动适配权限并能被审查工具识别；Codex 下 `rg` 是默认的高速搜索器。两者都比 `find + grep` 组合快得多，请优先使用。

## 三、Shell 的合理用途

仅用于以下场景（Claude Code 用 `Bash`，Codex 用 `run_terminal_cmd`）：

- 跑测试：`pytest`、`python -m compileall`
- 跑数据库工具：`python -m data_collection.database.inspector --summary`
- 运行 CLI 入口：`python main.py --mode incremental`
- Git 操作：`git status` / `git diff` / `git commit` 等
- 包管理：`pip install -r requirements.txt`
- 系统检查：`python --version`、`echo $PATH`（不可读 token 类变量）
- 文件移动 / 删除：`mv` / `rm` / `Move-Item` / `Remove-Item`
- 启动后台任务：Claude Code 用 `Bash` + `run_in_background=true`；Codex 当前没有原生后台机制，可用 PowerShell `Start-Job` 或日志重定向 `&` / `Start-Process`

## 四、子代理 / 多步研究

**仅 Claude Code 适用**——Codex 没有 subagent 概念，需要多步研究时直接在主对话里多轮 `rg` / `Get-Content` 推进，或者让用户开新会话分工。

| 子代理 (Claude Code `subagent_type`) | 何时使用 |
|-------|---------|
| `Explore` | 不熟悉的代码区域，需要多轮 Glob/Grep/Read 才能定位；在 prompt 里指明 `quick` / `medium` / `very thorough` |
| `Plan` | 需要为大改动产出实施计划但不写代码 |
| `general-purpose` | 多步骤复杂研究（找参考实现、整理外部文档线索）|

**不要用 Agent 做的事：**
- 简单的关键字搜索（直接 `Grep` / `rg`）
- 已知文件路径的读取（直接 `Read` / `Get-Content`）
- 写代码的同时启动 Agent 重复探索（会重复消耗上下文）

**何时并行启动多个 Agent（Claude Code）：**
- 多份完全独立的调查（如：同时分析采集器 A 和采集器 B 的实现差异）
- 同一条消息内放多个 `Agent` 调用块

## 五、任务节奏

**仅 Claude Code 适用**——Codex 没有原生 task 跟踪工具，需要分步时直接在回复中列编号 checklist 即可。

| 时机 | 动作（Claude Code） |
|------|------|
| 用户提多项需求 | 立刻 `TaskCreate` 把每项落成独立 task |
| 开始一个 task | `TaskUpdate status=in_progress` |
| 任务完全做完且测试通过 | `TaskUpdate status=completed` |
| 任务被阻塞 | 保持 `in_progress`，新建一个描述阻塞的 task |
| 任务被替换 | 旧 task `status=deleted`，新 task 用 `TaskCreate` |

> ❌ 不要为一行修改创建任务。
> ❌ 不要批量把所有 task 一次性标记 `completed` 来表演进度。
> ❌ 不要在每条消息开头都列任务（让平台 UI 渲染就够了）。

## 六、向用户提问的边界

**应当问的：**
- 多种可行方案，需要用户做架构 / 口径决策（数据源选哪个、表合并还是新建）
- 需要敏感操作授权（drop 表、强推 main、删大量文件）
- 不可逆操作前的 final confirm

**不应当问的：**
- 应该直接动手就能查清的问题（先读文件再说）
- "我做对了吗？" 类自我怀疑（先做最小验证）
- 可以从 `config/default.yaml` 读到答案的配置项

> Claude Code 用 `AskUserQuestion` 工具发出结构化选项；Codex 直接在对话里列编号问题即可。

## 七、外部资料抓取

| 工具 | 在 Claude Code | 在 Codex | 何时用 |
|------|---------------|---------|--------|
| 抓 URL | `WebFetch` | `run_terminal_cmd curl -sL <url>` 后管入 `rg` / `Get-Content` | 用户给了具体 URL 需要分析 |
| 搜索 | `WebSearch` | `run_terminal_cmd` 调浏览器 / 第三方 CLI | 需要查最新文档 / 版本 / CVE 等知识截止后的信息 |
| 都不要用于 | 同 | 同 | GitHub PR/Issue（用 `gh pr view`）、需要登录的私有页 |

## 八、敏感与破坏性操作

下列操作**必须**先与用户口头确认（不能默认执行）：

- `git push --force` / `git push --force-with-lease` 到 main
- `git reset --hard` / `git clean -fd`
- `DROP TABLE` / `TRUNCATE` / 删除数据库
- `rm -rf` 任何非临时目录
- 修改 `.git/config`、用户全局配置
- 写入或泄露 `.env` 内容到 commit、日志、回复正文
- 上传任何项目代码或数据到第三方网站（pastebin、gist 等）

## 九、并行调用

多个**互相独立**的工具调用应当并行执行：

- **Claude Code**：放在同一条消息内并行调用工具
  ```text
  ✅ 一条消息里同时：
     Read: README.md
     Read: config/default.yaml
     Glob: pattern="data_collection/collectors/*.py"

  ❌ 三条消息分别执行（串行浪费时间）
  ```
- **Codex**：一次 `run_terminal_cmd` 里串多条独立命令（用 `;` 或换行），或者拆成多步——Codex 默认就是串行运行
  ```text
  ✅ run_terminal_cmd:
     rg --files | rg "collectors/.*\.py$"; Get-Content -Raw README.md; Get-Content -Raw config/default.yaml
  ```

依赖前一步结果的工具调用必须串行。
