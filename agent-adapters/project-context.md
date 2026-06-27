---
description: 项目上下文读取规范 - 目录、入口、配置、分层边界和敏感文件约束（跨平台版）
type: sub-document
applies-to: [claude-code, codex]
auto_execution_mode: 2
---

# 项目上下文

## 进入任务前先确认

先用平台原生的读文件/列文件/搜内容能力建立项目上下文，避免把“读取上下文”误做成无约束 shell 操作。每条规则都必须按当前平台选择等价调用。

| 目的 | Claude Code | Codex |
|-----|-------------|-------|
| 列出所有文件 | `Glob pattern="**/*"`，或按后缀收窄如 `Glob pattern="**/*.py"` | `rg --files`，或按后缀收窄如 `rg --files  rg "\.py$"` |
| 列出所有 Python 文件 | `Glob pattern="**/*.py"` | `rg --files  rg "\.py$"` |
| 完整阅读 README | `Read file_path="README.md"` | `Get-Content -Raw -Encoding UTF8 README.md` |
| 完整阅读默认配置 | `Read file_path="config/default.yaml"` | `Get-Content -Raw -Encoding UTF8 config/default.yaml` |
| 完整阅读数据库 schema | `Read file_path="data_collection/database/schema.sql"` | `Get-Content -Raw -Encoding UTF8 data_collection/database/schema.sql` |
| 搜索内容关键字/正则 | `Grep pattern="..." path="..."` | `rg "..." <path>` |

Claude Code 中应优先使用专用工具，避免 Bash：

```text
Glob: pattern="**/*.py"                                      # 列出所有 Python 文件
Read: file_path="README.md"                                 # 完整阅读 README
Read: file_path="config/default.yaml"                       # 完整阅读默认配置
Read: file_path="data_collection/database/schema.sql"       # 完整阅读数据库 schema
Grep: pattern="..." path="..."                              # 搜索内容关键字/正则
```

Codex 中使用终端/PowerShell 调用：

```powershell
rg --files
rg --files | rg "\.py$"
Get-Content -Raw -Encoding UTF8 README.md
Get-Content -Raw -Encoding UTF8 config/default.yaml
Get-Content -Raw -Encoding UTF8 data_collection/database/schema.sql
rg "..." <path>
```

> Claude Code：不要使用 `Bash: rg --files` / `Bash: cat README.md` / `Bash: ls` 做上下文读取；改用 `Glob` / `Read`，需要内容搜索时用 `Grep`。只有跑测试、跑命令、git 操作等确实需要 shell 的场景才用 `Bash`。
>
> Codex：使用 `run_terminal_cmd` 执行 `rg --files`、`rg "..."`、`Get-Content -Raw -Encoding UTF8 ...`、PowerShell 命令；不要用交互式命令，不要把敏感环境变量打印到输出。

## 按任务继续读取

| 任务类型 | 优先读取 | Claude Code 调用 | Codex 调用 |
|---------|---------|------------------|------------|
| CLI/调度 | `main.py`, `data_collection/core/daily_job.py` | 对每个文件用 `Read file_path="..."` | 对每个文件用 `Get-Content -Raw -Encoding UTF8 ...` |
| 核心采集 | `data_collection/core/stock_collector.py` | `Read file_path="data_collection/core/stock_collector.py"` | `Get-Content -Raw -Encoding UTF8 data_collection/core/stock_collector.py` |
| 新数据源 | `data_collection/collectors/`, `data_collection/collectors/__init__.py` | `Glob pattern="data_collection/collectors/**/*"`；再 `Read file_path="data_collection/collectors/__init__.py"` 和相关文件 | `rg --files data_collection/collectors`；再 `Get-Content -Raw -Encoding UTF8 data_collection/collectors/__init__.py` 和相关文件 |
| 配置 | `data_collection/config.py`, `config/default.yaml`, `.env.example` | 对每个文件用 `Read file_path="..."` | 对每个文件用 `Get-Content -Raw -Encoding UTF8 ...` |
| 数据库 | `data_collection/database/schema.sql`, `data_collection/database/backend.py`, `docs/database_documentation*.md` | `Read` 已知文件；`Glob pattern="docs/database_documentation*.md"` 找文档 | `Get-Content -Raw -Encoding UTF8 ...` 读已知文件；`rg --files docs | rg "database_documentation.*\.md$"` 找文档 |
| 测试 | `pytest.ini`, `test/conftest.py`, 对应 `test/unit` / `test/integration` / `test/data_quality` | `Read` 已知文件；`Glob pattern="test/unit/**/*"` / `Glob pattern="test/integration/**/*"` / `Glob pattern="test/data_quality/**/*"` 找相关测试 | `Get-Content -Raw -Encoding UTF8 ...` 读已知文件；`rg --files test/unit test/integration test/data_quality` 找相关测试 |
| 通达信集成 | `D:/Sofeware/TongDaXin/vipdoc/{sh,sz,bj}/lday/`, `D:/Sofeware/TongDaXin/T0002/hq_cache/base.dbf` | 用 `Glob path="D:/Sofeware/TongDaXin/vipdoc" pattern="{sh,sz,bj}/lday/**/*"` 或分别按目录 `Glob`；已知文件用 `Read`（二进制/DBF 仅在工具可读时读取） | 用 PowerShell/`rg --files` 分别列 `D:/Sofeware/TongDaXin/vipdoc/sh/lday`, `.../sz/lday`, `.../bj/lday`；`base.dbf` 为二进制/DBF 时不要用纯文本方式强读 |

## 何时使用 Agent（仅 Claude Code 适用，Codex 没有 subagent 概念）

Claude Code 可以在大范围探查或并行调查时使用 `Agent`，尤其是 `subagent_type=Explore`。Codex 没有 subagent 概念，遇到同类需求时在主流程中用 `rg --files`、`rg`、`Get-Content -Raw -Encoding UTF8` 和 PowerShell 分阶段完成。

| 场景 | Claude Code 选择 | Codex 等价做法 |
|-----|------------------|----------------|
| 已知具体文件名/路径 | `Read file_path="..."` 直接打开 | `Get-Content -Raw -Encoding UTF8 ...` 直接打开 |
| 已知关键字、单次正则可定位 | `Grep pattern="..." path="..."` | `rg "..." <path>` |
| 已知通配文件模式 | `Glob pattern="..."` | `rg --files <path>  rg "..."` 或 PowerShell 文件枚举 |
| 不确定关键字、需多轮探查、跨多目录 | `Agent` 启动 `Explore`，并指明 thoroughness：quick / medium / very thorough | 不启 subagent；在主流程中先 `rg --files` 建索引，再多轮 `rg` 缩小范围，必要时分目录读取 |
| 需要并行多份独立调查 | 同一条消息内启多个 `Agent` | 没有 subagent 并行；按独立问题拆分搜索命令和读取步骤，逐项记录结论 |

Claude Code 只在搜索预计需要 **3 次以上**关键字组合时才用 `Agent`，否则直接 `Grep`。Codex 中同样遵循“少量明确搜索直接 `rg`，多轮不确定搜索先列文件再分阶段 `rg`”的原则。

## 分层边界

| 层级 | 应做 | 避免 |
|-----|------|------|
| `collectors/` | 调用外部 API、字段标准化、返回 DataFrame | 直接调度全流程、写死数据库路径、执行批量调度 |
| `core/` | 编排采集流程、组合降级策略、进度控制 | 把字段映射散落到多个入口 |
| `database/` | schema、连接后端、表检查、迁移辅助 | 调用外部数据源 |
| `utils/` | 无业务状态的通用能力 | 放入需要理解具体数据表生命周期的逻辑 |
| `scripts/` | 运维、诊断、一次性工具 | 替代可测试的核心模块 |

## 敏感信息

- `.env` 只能读取，不能把其中内容写入文档、日志、测试快照、commit message、Claude/Codex 的回复正文或任何可持久化输出。
- Tushare token、数据库密码、真实 API key 不进入代码示例。
- 测试默认使用 mock、临时 SQLite 或 `.env.example` 中的占位值。
- 发现硬编码密钥时优先迁移到环境变量，并同步 `.env.example`。
- 只读 `.env`：Claude Code 可用 `Read file_path=".env"` 且不得复述内容；Codex 可用 `Get-Content -Raw -Encoding UTF8 .env` 且不得复述内容。
- 不要在 Claude Code 的 `Bash` 里 `echo $TUSHARE_TOKEN`，也不要在 Codex/PowerShell 里输出 `$env:TUSHARE_TOKEN`；不要在回复里展示任何真实密钥内容。

## 读上下文的停止条件

- 找到实际调用链和被测入口。
- 明确变更是否影响 schema、配置、文档和测试。
- 知道最小可运行验证命令。
- 能区分任务相关文件和无关文件。

## 跨工具边界

| 行为 | Claude Code 工具/调用 | Codex 工具/调用 |
|-----|------------------------|-----------------|
| 读单个文件 | `Read file_path="..."` | `Get-Content -Raw -Encoding UTF8 ...` |
| 读多个文件并行（无依赖） | 同一条消息内多次 `Read` | 在同一轮中按文件分别调用 `Get-Content -Raw -Encoding UTF8 ...`，或用 PowerShell 明确列出多个文件逐个读取 |
| 找文件名/扩展名/glob | `Glob pattern="..."` | `rg --files` 后接 `rg "..."` 过滤，或 PowerShell 文件枚举 |
| 找文件内容（关键字/正则） | `Grep pattern="..." path="..."`（不要用 `Bash: grep` / `Bash: rg` 做上下文搜索） | `rg "..." <path>` |
| 改单文件局部 | `Edit file_path="..." old_string="..." new_string="..."` | 用编辑工具/补丁方式局部替换；必要时 PowerShell 只做精确替换并保留编码 |
| 创建新文件 | `Write file_path="..." content="..."` | 用编辑工具/重定向/PowerShell 写入新文件；明确目标路径和 UTF-8 编码 |
| 跑测试、跑命令、git 操作 | `Bash command="..."` | `run_terminal_cmd` 执行对应 shell/PowerShell/git/pytest 命令 |
| 复杂多步任务追踪 | `TaskCreate` + `TaskUpdate` | 使用计划/步骤列表在当前会话中追踪；Codex 没有 `TaskCreate` / `TaskUpdate` 等价工具时，用明确 checklist 维护状态 |
| 大范围探查 / 并行调查 | `Agent subagent_type="Explore"`；需要并行时同一条消息内启多个 `Agent` | 无 subagent；用 `rg --files`、多轮 `rg`、`Get-Content -Raw -Encoding UTF8` 和 PowerShell 分阶段完成 |
