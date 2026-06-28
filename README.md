# Skills — 多源 Skill 集合大全

`skills/` 既是本仓库（Quantitative_Trading 项目）所有 Agent skill 的事实源，也作为一个 **可单独维护、可被多个项目软链接复用** 的 skill 大全 —— 它把社区里若干优秀开源 skill 项目按功能归并到统一目录树，每个 skill 都保留对其上游的指针，便于持续追踪。

> 后续这里会继续接入社区其它 skill 项目；当前已包含 **108 个 skill**：54 个从外部仓库导入 + 54 个本仓库原生。完整清单见 [`INDEX.md`](INDEX.md)。

## ⭐ 置顶推荐 — 打工人协作双子 skill

本仓库目前最优先推荐两个 **协作类 skill**，覆盖打工人的双线沟通——**一个对人，一个对 AI**。建议常驻开启。

### 1️⃣ [workmode/tame-vibe-coding.md](workmode/tame-vibe-coding.md) — Vibe Coding 债务控制（人 ↔ AI）

让你从"AI 代码生成器的下游工人"扳回"AI 代码的审查员和架构师"。

- **认知债务 vs 技术债务**：技术债务是代码烂账，认知债务是**你自己不懂自己的项目**了——AI 时代的新风险，比技术债务更隐蔽。
- **AI 审查员工作流**：AI 当实习生，你是 mentor。**生成速度必须慢于理解速度**。
- **强制"复述验收"**：合并 AI 代码前用三句话讲清意图/逻辑/边界，说不出来就不许合。
- **TDD 优先**：先让 AI 写测试用例，**我审测试**，再让 AI 写实现；测试是技术债务的安全网。
- **知识沉淀**：维护 `Rules.md` 项目规则文件 + 关键功能的"生成轨迹/决策日志"，对抗 AI 上下文遗忘。
- **自动化护栏**：`ruff` / `mypy` / `pytest` / CI / SonarQube 兜底，护栏不到位时不大量生成代码。
- **思维转变**：从"生成"到"理解"，从"能用"到"可维护"，你是架构师、AI 是工程师。

启用：说 *"vibe coding / 认知债务 / 提醒我别让 AI 跑偏 / 我有点看不懂这段代码了"* 或调用 `/tame-vibe-coding`。

### 2️⃣ [workmode/manage-upward.md](workmode/manage-upward.md) — 向上管理模式（人 ↔ 人）

让"执行者 ↔ 合作者"互相督促，把 AI 和用户都拉到合格打工人状态。

- **核心理念**：向上管理 ≠ 拍马屁，本质是**用你的可控性，去覆盖对方的不确定感和焦虑感**。
- **三件事汇报法**：每次同步只讲清 *进度 / 风险 / 需要的支持* 这三件事。
- **2 小时风险上报原则**：硬扛不超 2h，超时立刻带"已尝试 + 临时结论"上报，杜绝闷头干。
- **汇报问题必带方案**：哪怕方案不成熟，也比当传声筒强。
- **摆脱学生思维**：少看多干、工作留痕、及时沟通，多用"我们"代替"我"和"你"。
- **双向**：AI 主动按这些原则提醒用户，用户也用同样原则要求 AI。

启用：说 *"向上管理 / 打工人模式 / 督促我"* 或调用 `/manage-upward`。

> **为什么并列**：两个 skill 是同一套打工人哲学的两条战线——`tame-vibe-coding` 守住你**对代码的掌控**（别被 AI 推着走），`manage-upward` 守住你**对项目和上级的掌控**（别被进度推着走）。两个都失守，认知 + 项目双线崩盘。

---

## skill 形态分类

每个 skill 有一个 **kind**（描述它本身长什么样）。多个 skill 之间还可以有 **cluster**（描述它们怎么搭配）。这两个维度正交。

### 三种 kind（描述单个 skill）

| kind | 含义 | 举例 |
|---|---|---|
| `atomic` | 单文件 `SKILL.md`，一招一动作。**普攻**。 | `workmode/caveman.md`、`business/diagnosis/`、`methodology/good-question/` |
| `composite` | `SKILL.md` + 内置 `scripts/` / `references/` / `assets/`，单次调用自带一套流水线。**一招一整套**。 | `content/guizang-ppt/`、`productivity/notebooklm/`、`engineering/diagram/` |
| `composite-danger` | composite，但依赖逆向 / 非官方 API，**上游随时可能失效**。 | `ai-backends/gemini-web/`、`productivity/x-to-markdown/` |

### 一种组合机制（描述多个 skill 怎么串）

| 机制 | 含义 | 举例 |
|---|---|---|
| `pipeline-cluster` | 多个独立 skill 设计上互相串联使用。集群名见 [`_meta/clusters.md`](_meta/clusters.md)。 | `dbs-state` (state-save → state-restore → state-report)、`humanizer`、`slide`、`card`、`extract`、`publish`、`visual`、`chatroom` |

每个 skill 既有 kind（atomic / composite / composite-danger 三选一），又**可能**属于某个 cluster（也可能不属于）。详见 [`_meta/atomic-vs-composite.md`](_meta/atomic-vs-composite.md)。

## 目录结构

| 目录 | 定位 |
|---|---|
| `engineering/` | 工程规则：代码风格、接口、文档、外部集成、安全、新功能流程，以及导入的 `diagram` / `electron-extract` |
| `testing/` | 测试与质量规则 |
| `git/` | Git 工作流，含导入的 `release-workflow` |
| `governance/` | 项目治理 |
| `methodology/` | 方法论 skill（含导入的 `hv-analysis`、`good-question`、`decision-system`、`deconstruct`、`learning-plan`、`chatroom`、`chatroom-austrian` 等） |
| `workmode/` | 工作模式（含导入的 `goal-clarify`、`slowisfast`） |
| `meta/` | 元能力（含导入的 `neat-freak`） |
| `misc/` | 低频辅助 skill |
| `domain/` | 领域 skill（A 股数据等） |
| `agent-adapters/` | 平台适配层：同一职责在 Claude Code / Codex 下的不同工具栈写在**同一个跨平台 md** 里（frontmatter `applies-to: [claude-code, codex]`），具体工具调用按平台内联给出；含导入的 `agent-migration/` |
| `content/` | **新增** — 写作、排版、翻译、配图、PPT、社交卡片、发布相关 skill |
| `productivity/` | **新增** — URL/视频抽取、存储清理、NotebookLM、新闻摘要、微信群摘要 |
| `business/` | **新增** — dontbesilent 商业诊断套件 |
| `ai-backends/` | **新增** — AI 提供商适配（image-gen, gemini-web） |
| `_meta/` | **新增** — 仓库自身的架构说明、import manifest、构建脚本 |

## 平台入口

平台自身工作目录只保留软链接入口，真实内容仍在 `skills/`：

| Agent | 入口说明 | skill 作用路径 |
|---|---|---|
| Codex | `.codex/workflows/codex-guidelines.md` | `.codex/workflows/skill/` |
| Devin | `.devin/workflows/dev-guidelines.md` | `.devin/workflows/skill/` |
| Claude Code | `.claude/workflows/claude-guidelines.md` | `.claude/workflows/skill/` |

示例（Windows 用 Junction）：

```text
.codex/workflows/skill/engineering -> skills/engineering
.codex/workflows/skill/content     -> skills/content
.claude/workflows/skill/business   -> skills/business
```

跨项目挂载用法见 [`_meta/symlink-mount.md`](_meta/symlink-mount.md)。

## 外部来源仓库

本次（2026-06-27）导入的 7 个上游项目：

| 上游仓库 | 提供 skill 数 | 类型概览 |
|---|---|---|
| [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh) | 1 | 中文文本去 AI 痕迹 |
| [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) | 22 | 内容创作 / 发布 / 图像 / 抓取一整套 |
| [dontbesilent2025/dbskill](https://github.com/dontbesilent2025/dbskill) | 23 | 商业诊断 / 思维方法 / 内容引擎一整套 |
| [op7418/guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill) | 1 | 单 HTML 横滑 web PPT |
| [op7418/guizang-social-card-skill](https://github.com/op7418/guizang-social-card-skill) | 1 | Guizang 风格社交卡片 |
| [KKKKhazix/khazix-skills](https://github.com/KKKKhazix/khazix-skills) | 5 | AI 新闻、研究方法、文风、知识库清理、存储分析 |
| [PleasePrompto/notebooklm-skill](https://github.com/PleasePrompto/notebooklm-skill) | 1 | NotebookLM 浏览器自动化 |

每个导入的 skill 在自己的目录下都有一个 [`SOURCE.md`](business/diagnosis/SOURCE.md)（任一示例），写明上游链接、原始路径、kind、cluster、导入日期、软链接挂载片段、更新流程。后期更新只需跟着 SOURCE.md 的 `Updating from upstream` 走。

## 如何使用

### 在本仓库

平台说明文件里写平台本地路径，例如 `skill/content/humanizer-zh/SKILL.md`。

### 在其他项目挂载

```bash
# Linux/macOS
ln -s /abs/path/to/skills/content/humanizer-zh /your-project/.claude/skills/humanizer-zh

# Windows PowerShell (Junction，无需管理员)
New-Item -ItemType Junction `
  -Path .\.claude\skills\humanizer-zh `
  -Target E:\Project\Quantitative_Trading\skills\content\humanizer-zh
```

整组挂载见 [`_meta/symlink-mount.md`](_meta/symlink-mount.md)。

## 维护规则

1. **新增 skill** 时先判断它属于哪个 category；属于 atomic 就是单文件，属于 composite 就建子目录。命名用 kebab-case。
2. **从外部导入新的 skill** 走 `_meta/import-manifest.tsv` + `_meta/import_skills.py`：在 manifest 加一行 → 跑 import 脚本 → 跑 `_meta/build_index.py` 重生 `INDEX.md`。
3. **同源/同任务多份 skill** 的并轨原则见 [`_meta/merge-policy.md`](_meta/merge-policy.md)：短期 siblings，长期把同粒度指令逐渐合并到一份，*指令越具体越好*。
4. **修改本地 skill** 时如果改的是导入而来的，必须在该 skill 目录的 `SOURCE.md` 的 `Local modifications` 段记录；这样上游更新时知道哪里有冲突。
5. **平台 `workflows/skill/`** 下只放目录链接，不放手工复制文件。Windows 用 Junction。
6. **移动 / 改名 skill** 时同步检查相对链接、SOURCE.md 里的 sibling 引用、`INDEX.md`、`_meta/clusters.md`。

## 自动化脚本

| 脚本 | 作用 |
|---|---|
| `_meta/import_skills.py` | 按 manifest 把 `_external_skills/` 内容复制到目标目录，并生成每个 skill 的 `SOURCE.md` |
| `_meta/build_index.py` | 扫描所有 category 和 manifest，重生 `INDEX.md` |
| `_meta/import-manifest.tsv` | 导入清单：`source_subpath / target_subpath / kind / repo / repo_path / cluster / notes` |

两个脚本都用本机 `python` 跑（开发机上是 Anaconda 的 Python 3.11）。

## 迁移背景

2026-06-27 之前 skill 按平台和历史来源分散。当前迁移目标：

- **单一事实源 + 平台软链接** —— 已完成。
- **吸纳社区优秀 skill** —— 当前共导入 54 个；后续可加更多来源（在 manifest 添行即可）。
- **可被其他项目软链接挂载** —— 每个 skill 自包含，相对路径全在自己目录里解析。
- **同任务多源的合并策略** —— 见 `_meta/merge-policy.md`。短期 siblings 并存，长期把同粒度指令逐步合并、做到指令越详细越好。

后续如果要让本目录独立成仓库上 GitHub 动态维护，结构已经具备条件。
