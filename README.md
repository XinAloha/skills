# AgentSkills

AI 越强，你反而越累--每次开新会话它都从零开始：不懂你项目的 Git 分支怎么提，写出来一股 AI 味，搜完资料也不会发到公众号。不是它笨，是你每次都得重新交代一遍那些“行业规矩”。这个仓库把规矩写成一份份开箱即用的 skill，挂进 AI 的 skill 目录，它下次就按规矩干活、不再即兴发挥；挑一个挂或整组装都行。

## 🔁 loop-engineering：让智能体循环可验证、可恢复

**是什么**：`loop-engineering/` 是本仓库原生的一套子系统。循环工程就是用系统设计取代“你本人亲自去提示智能体”这个角色--你设计一套系统，让它来提示智能体并自己决定下一步做什么。Claude Code 负责人 Boris Cherny 说得更直接：“我不再提示 Claude 了……是它们在提示 Claude 并自己决定下一步做什么。我的工作是写循环。” 一个循环只需两样东西：触发器 + 可验证目标，智能体持续运行直到目标达成、无需人工提示。

**为什么**：没有防护栏的循环必然会失败，而且不是边缘情况。让智能体自己决定何时“完成”，会让你在想清楚之前就耗尽令牌上限（Uber 曾四个月烧光年度 AI 预算）；让写代码的智能体给自己打分，它几乎永远在夸自己（“点头循环”）；结果只活在上下文里、刷新就忘（“失忆循环”）；循环交付得越快，代码库与你理解之间的“理解债务”越深。循环是个放大器--放大判断力也放大惰性，而“完成了”始终是一个主张、不是证明。

**怎么做**：这套 skill 把上述失败模式逐个堵死--用迭代/支出/无进展上限做断路器，用制造者与检查者分离（独立 `verify-loop-delivery`）取代自我批准，用落盘状态取代上下文记忆，用可验证停止条件取代"模型觉得完成了"。9 个 skill 由 `design-loop-project` 按阶段编排：`qualify-loop-task -> specify-loop-contract -> design-loop-state -> build-loop-harness -> operate-loop-run -> verify-loop-delivery -> audit-loop-project -> improve-loop-system`；只有任务适合循环化、阻断项清零、人工闸门明确时才进入受控试运行。完整能力地图见 [`loop-engineering/README.md`](loop-engineering/README.md)，底层论述与案例见 [`loop_references/`](loop_references/)。

## ⭐ 让 AI 替我追：向上管理 · 技术认知债务

刚接触本仓库的话，推荐从 `workmode/` 下这两个开始，覆盖打工人的双线沟通：

| skill | 守住的战线 | 一句话 |
|---|---|---|
| [tame-vibe-coding](workmode/tame-vibe-coding.md) | 对代码的掌控 | AI 当实习生、你当 mentor；生成慢于理解，合并前先复述验收 |
| [manage-upward](workmode/manage-upward.md) | 对项目和上级的掌控 | 三件事汇报法 + 2 小时风险上报原则 |

## 能干什么

| 目录 | 能干什么 | 代表 skill |
|---|---|---|
| `workmode/` | 工作模式：控制 AI 编程认知债务、向上管理汇报、目标澄清、慢即快诊断、最小代码阶梯 | `tame-vibe-coding`、`manage-upward`、`ponytail`、`goal-clarify`、`slowisfast` |
| `content/` | 写作与发布：排版、翻译、去 AI 痕迹、PPT、社交卡片、配图、漫画、传播策略、多平台发布（微信/微博/X/小红书） | `humanizer-zh`、`format-markdown`、`guizang-ppt`、`post-to-wechat` 等 |
| `productivity/` | 效率工具：网页/YouTube/推文转 Markdown、微信群摘要、AI 热点、图片压缩、存储分析、NotebookLM | `url-to-markdown`、`youtube-transcript`、`wechat-summary` 等 |
| `business/` | 商业诊断套件：商业诊断、行动诊断、基准对标、路由分发、状态管理集群 | `diagnosis`、`benchmark`、`dbs-router`、`state-save` |
| `engineering/` | 工程规则：代码风格、接口设计、文档规范、外部集成、安全、Mermaid 图表、Electron 逆向 | `code-style`、`security`、`diagram`、`electron-extract` |
| `loop-engineering/` | 智能体循环工程：任务适配、契约、状态、防护栏、运行恢复、独立审核、持续改良（9 个 skill 链式编排，详见上方专节） | `design-loop-project`、`verify-loop-delivery` 等 |
| `testing/` | 测试策略：分层测试（单元/集成/数据质量）、数据库测试、故障恢复、管线测试 | `test-strategy`、`data-quality`、`fault-recovery` |
| `git/` | Git 工作流：分支策略、code review、commit 规范、回滚恢复、版本发布 | `git-branch-workflow`、`git-code-review`、`release-workflow` |
| `governance/` | 项目治理：自动清理、避坑清单、项目管理员、重构检查、参考分析 | `auto-cleanup`、`avoid-pitfalls`、`refactoring-checklist` |
| `methodology/` | 方法论：好问题、决策系统、解构分析、学习计划、HV 分析、聊天室研讨、TDD、原型法 | `good-question`、`decision-system`、`deconstruct`、`tdd` |
| `domain/` | 领域 skill：A 股数据采集（股票列表、日K线、板块、复权因子、降级策略） | `a-stock-data` |
| `ai-backends/` | AI 提供商适配：多渠道绘图聚合（Codex / DashScope / Replicate 等）、Gemini Web API | `image-gen`、`gemini-web` |
| `agent-adapters/` | 平台适配层：跨平台工作流（Claude Code / Codex 工具对照）、Agent 工作台迁移 | `agent-migration`、`tools-discipline` |
| `meta/` | 元能力：多会话教学、创建新 skill 模板、知识库整洁 | `teach`、`write-a-skill`、`neat-freak` |
| `misc/` | 低频辅助：Git 安全护栏、迁移工具、脚手架练习、pre-commit | `git-guardrails-claude-code`、`setup-pre-commit` |

> 完整 skill 清单见 [`INDEX.md`](INDEX.md)，维护者指南见 [`_meta/`](_meta/)。

## 怎么用

**用软链接，别复制。** 用 Codex / Claude Code 这类 Agent 写代码，skill 管理最烦的就是：全局放一份吧，项目 git 不全、换电脑全丢；每个项目复制一份吧，改一处要改八处、bug 满天飞。解法是软链接——一个仓库管所有 skill，每个项目建一个软链接指过去，源仓库改一次、所有项目同步更新。

三步搞定：① 这个仓库统一收纳所有 skill；② 在项目里建软链接指过去（命令如下）；③ 在项目的 `CLAUDE.md`（Claude Code）或 `AGENTS.md`（Codex）里写一行入口告诉 Agent。

```bash
# Linux/macOS
ln -s /abs/path/to/skills/content/humanizer-zh /your-project/.claude/skills/humanizer-zh
```

```powershell
# Windows（Junction，无需管理员）
New-Item -ItemType Junction `
  -Path .\.claude\skills\humanizer-zh `
  -Target E:\path\to\skills\content\humanizer-zh
```

Claude Code 用 `.claude/skills/`，Codex 用 `.agents/skills/`，把路径里的目录名换一下即可。好处直接拉满：`git pull` 一下新机器全套就位；修 bug 顺手 PR 反哺社区；连命令都不用敲——Agent 自己就会建软链接。整组挂载（按 category 批量）见 [`_meta/symlink-mount.md`](_meta/symlink-mount.md)。
