# Claude Code Guidelines — Claude Code 平台入口

> 本文件是 Claude Code 进入本项目时的**入口说明**。真实 skill 内容不在此处，全部以 Junction 形式挂载在 `.claude/workflows/skill/`，指向仓库根 `skills/` 目录。

## skill 挂载路径

所有 skill 通过 Junction 挂载到 `.claude/workflows/skill/<category>/`：

```text
.claude/workflows/skill/
  engineering/   -> skills/engineering
  testing/       -> skills/testing
  git/           -> skills/git
  governance/    -> skills/governance
  methodology/  -> skills/methodology
  workmode/     -> skills/workmode
  meta/         -> skills/meta
  misc/         -> skills/misc
  domain/       -> skills/domain
  agent-adapters/ -> skills/agent-adapters
  content/      -> skills/content
  productivity/  -> skills/productivity
  business/     -> skills/business
  ai-backends/   -> skills/ai-backends
```

引用 skill 时写相对路径：`skill/<category>/<skill-name>/SKILL.md`。

## 工作流规则

跨平台工作流规则写在 `skill/agent-adapters/` 下，Claude Code 与 Codex 共用。按任务类型查阅：

| 任务 | 文档 |
|------|------|
| 进入任务前读上下文 | `skill/agent-adapters/project-context.md` |
| 修改/实现工作流 | `skill/agent-adapters/change-workflow.md` |
| 工具使用纪律 | `skill/agent-adapters/tools-discipline.md` |
| 数据采集器开发 | `skill/agent-adapters/data-collector-development.md` |
| 测试与验证 | `skill/agent-adapters/testing-and-verification.md` |
| 审查与清理 | `skill/agent-adapters/review-and-cleanup.md` |
| 版本发布检查清单 | `skill/agent-adapters/release-checklist.md` |
| Agent 工作台迁移 | `skill/agent-adapters/agent-migration/SKILL.md` |

## Claude Code 工具调用快速对照

| 意图 | 调用 |
|------|------|
| 读取文件 | `Read file_path="..."` |
| 列出文件 | `Glob pattern="..."` |
| 搜索内容 | `Grep pattern="..." path="..."` |
| 编辑文件 | `Edit`（先 `Read`）；新建/整体重写用 `Write` |
| 运行命令/测试 | `Bash command="..."` |
| 长耗时命令 | `Bash run_in_background=true` |
| 任务跟踪 | `TaskCreate` / `TaskUpdate`（或 `TodoWrite`） |
| 大范围探索 | `Agent`（`subagent_type=Explore`，指明 quick/medium/very thorough） |

> 仅在搜索预计需要 3 次以上关键字组合时才用 `Agent`；少量明确搜索直接 `Grep`。

## Python 解释器

本项目 `python` 默认指向 Windows Store 桩（exit 49 静默失败）。所有 Python 命令用：

```bash
/d/Developer_Tools/Anaconda/python.exe
```

## Git 纪律

- **不主动**执行 `git commit` / `git push` / `git tag`，除非用户明确要求。
- commit message 参考 `skill/git/git-commit-convention.md`，用 HEREDOC 格式。
- 不可逆操作（force push / reset --hard / 删分支）必须先确认。
- 不修改 `.git/config`、`user.name`、`user.email`。
