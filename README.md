# Skills — 给 AI 加上专业能力的 Skill 大全

你的 AI 助手能写代码，但不懂 Git 分支规范；能写文章，但写出来一股 AI 味；能搜资料，但不会发到微信公众号。本仓库就是补这些能力缺口的——一套开箱即用的 Agent skill 集合，让 AI 按专业流程干活，而不是即兴发挥。

每个 skill 是一份结构化指令（有的带脚本），放进 AI 的 skill 目录就能用。你可以只挑需要的一个挂上去，也可以整组装。

## 能干什么

| 你想让 AI 帮你做的事 | 对应 skill |
|---|---|
| 写代码时不跑偏——先审再合、TDD 优先、认知债务控制 | `workmode/tame-vibe-coding` |
| 汇报工作讲清进度/风险/需求，不闷头干 | `workmode/manage-upward` |
| 把 AI 味浓重的中文改回人话 | `content/humanizer-zh` |
| 文章一键排版成可读的 Markdown | `content/format-markdown` |
| 生成单 HTML 横滑 PPT | `content/guizang-ppt` |
| 生成小红书/社交平台风格卡片图 | `content/guizang-social-card` |
| 把文章发到微信/微博/X/小红书 | `content/post-to-wechat` 等 |
| 多渠道 AI 绘图（Codex / DashScope / Replicate 聚合） | `ai-backends/image-gen` |
| 把网页/YouTube/推文转成 Markdown | `productivity/url-to-markdown` 等 |
| 诊断商业问题、做基准对标 | `business/diagnosis` |
| A 股数据采集（K线/板块/复权因子） | `domain/a-stock-data` |
| Git 分支/code review/commit 规范 | `git/git-branch-workflow` 等 |
| 分层测试策略（单元/集成/数据质量） | `testing/test-strategy` |
| 好问题框架、决策系统、解构分析等方法论 | `methodology/good-question` 等 |
| 为项目建立可验证、可恢复的智能体循环工程 | `loop-engineering/design-loop-project` |

## 怎么用

每个 skill 自包含，挑你需要的挂到项目的 skill 目录即可：

```bash
# Linux/macOS
ln -s /abs/path/to/skills/content/humanizer-zh /your-project/.claude/skills/humanizer-zh

# Windows PowerShell (Junction，无需管理员)
New-Item -ItemType Junction `
  -Path .\.claude\skills\humanizer-zh `
  -Target E:\Project\Quantitative_Trading\skills\content\humanizer-zh
```

整组挂载（按 category 批量）见 [`_meta/symlink-mount.md`](_meta/symlink-mount.md)。

## ⭐ 推荐入门

刚接触本仓库的话，推荐从 `workmode/` 下这两个开始，覆盖打工人的双线沟通：

| skill | 守住的战线 | 一句话 |
|---|---|---|
| [tame-vibe-coding](workmode/tame-vibe-coding.md) | 对代码的掌控 | AI 当实习生、你当 mentor；生成慢于理解，合并前先复述验收 |
| [manage-upward](workmode/manage-upward.md) | 对项目和上级的掌控 | 三件事汇报法 + 2 小时风险上报原则 |

## 目录结构

| 目录 | 能做什么 |
|---|---|
| `workmode/` | 工作模式：AI 编程债务控制、向上管理、目标澄清、慢即快、最小代码阶梯（ponytail 6 件） |
| `content/` | 写作与发布：排版、翻译、去 AI 痕迹、PPT、社交卡片、配图、多平台发布（微信/微博/X/小红书）、漫画、传播策略 |
| `productivity/` | 效率工具：网页/YouTube/推文转 Markdown、微信群摘要、AI 热点新闻、图片压缩、存储分析、NotebookLM |
| `business/` | 商业诊断套件：商业诊断、行动诊断、基准对标、路由分发、状态管理集群 |
| `engineering/` | 工程规则：代码风格、接口设计、文档规范、外部集成、安全、Mermaid 图表、Electron 逆向 |
| `testing/` | 测试策略：分层测试（单元/集成/数据质量）、数据库测试、故障恢复、管线测试 |
| `git/` | Git 工作流：分支策略、code review、commit 规范、回滚恢复、版本发布 |
| `governance/` | 项目治理：自动清理、避坑清单、项目管理员、重构检查、参考分析 |
| `methodology/` | 方法论：好问题、决策系统、解构分析、学习计划、HV 分析、聊天室研讨、TDD、原型法 |
| `domain/` | 领域 skill：A 股数据采集（股票列表、日K线、板块、复权因子、降级策略） |
| `ai-backends/` | AI 提供商适配：多渠道绘图聚合、Gemini Web API |
| `agent-adapters/` | 平台适配层：跨平台工作流（Claude Code / Codex 工具对照）、Agent 工作台迁移 |
| `meta/` | 元能力：多会话教学、创建新 skill 模板、代码整洁 |
| `misc/` | 低频辅助：Git 安全护栏、迁移工具、脚手架练习、pre-commit |

> 完整 skill 清单见 [`INDEX.md`](INDEX.md)，维护者指南见 [`_meta/`](_meta/)。
