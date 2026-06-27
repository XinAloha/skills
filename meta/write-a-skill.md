---
description: 创建新 Agent skill - 结构、frontmatter、渐进披露、捆绑资源
type: meta
parent: dev-guidelines.md
auto_execution_mode: 2
source: Matt Pocock skills - productivity/write-a-skill
adapted-for: A 股量化数据采集系统 (Python / pytest / PostgreSQL)
---

# Write a Skill - 写新 skill

> 触发：用户希望创建、写、做一个新 skill。

## 流程

1. **收集需求** —— 问用户：
   - 这个 skill 覆盖什么任务 / 领域？
   - 应处理哪些具体用例？
   - 需要可执行脚本，还是只要指令？
   - 有没有要附带的参考材料？

2. **草稿 skill** —— 创建：
   - `SKILL.md` 写简洁指令
   - 内容超 500 行就拆出参考文件
   - 要确定性操作就加工具脚本

3. **与用户回顾** —— 给草稿，问：
   - 覆盖你的用例了吗？
   - 缺什么或不清楚的？
   - 哪段要更详细 / 更精简？

## 结构

```
skill-name/
├── SKILL.md           # 主指令（必需）
├── REFERENCE.md       # 详细文档（如需）
├── EXAMPLES.md        # 用例（如需）
└── scripts/           # 工具脚本（如需）
    └── helper.py
```

## SKILL.md 模板

```markdown
---
description: 简短描述能力。Use when [具体触发条件]。
type: methodology | workmode | meta | misc
parent: dev-guidelines.md
auto_execution_mode: 2
---

# Skill Name

## 快速开始

[最小可工作示例]

## 工作流

[复杂任务的步骤式流程，含 checklist]

## 高级特性

[链到独立文件：按需创建 `REFERENCE.md` 后再链接]
```

## description 要求

description 是**Agent 决定加载哪个 skill 时唯一看到的东西**。它会出现在系统提示里和所有其他 skill 并列。Agent 读 description 决定要不要触发本 skill。

**目标**：让 Agent 刚好够判断：

1. 这个 skill 提供什么能力。
2. 何时 / 为什么触发（具体关键词、上下文、文件类型）。

**格式**：

- 上限 1024 字符。
- 第三人称写。
- 第一句：**做什么**。
- 第二句：「Use when [具体触发]」。

**好例**：

```
从 PDF 文件提取文本与表格、填表、合并文档。Use when 用户在处理 PDF 文件，
或提到 PDF / 表单 / 文档抽取。
```

**坏例**：

```
帮你处理文档。
```

坏例不让 Agent 区分这个和其他文档 skill。

## 何时加脚本

操作满足：

- 确定性（验证、格式化）。
- 同样代码会被重复生成。
- 错误需要明确处理。

脚本省 token、提高可靠性，胜过即兴生成代码。

## 何时拆文件

满足：

- `SKILL.md` 超 100 行。
- 内容跨多个独立领域（金融 schema vs 销售 schema）。
- 高级特性很少被需要。

## 草稿后检查清单

- [ ] description 包含触发条件（"Use when ..."）。
- [ ] `SKILL.md` 主体不超 100 行（超出拆出去）。
- [ ] 无时效信息（具体日期、版本号）。
- [ ] 术语一致。
- [ ] 含具体示例。
- [ ] 引用只下一层（不嵌套链）。

## 本项目额外约定

本项目所有 skill 共享 frontmatter 字段：

```yaml
---
description: <一句话简体中文描述>
type: methodology | workmode | meta | misc | <既有共享分类>
parent: dev-guidelines.md     # Devin / Codex
                              # 或 claude-guidelines.md（Claude 专属时）
auto_execution_mode: 2
source: <如改编自外部，写来源 URL>          # 可选
adapted-for: A 股量化数据采集系统 ...        # 可选
---
```

**新增 skill 的位置规则**（2026-06-27 重构后）：
- **共享工程规则** → 按功能写入 `skills/engineering/`、`skills/testing/`、`skills/git/`、`skills/governance/` 等分类目录，三方 Agent 自动可用。
- **Agent 工具栈适配** → 写入 [`skills/agent-adapters/`](../agent-adapters/) 下的 `<skill>.md`，frontmatter 加 `applies-to: [claude-code, codex]`，并在涉及具体工具调用的段落里同时给出两套平台的对应做法；只属于某一平台的子规则用「（仅 Claude Code 适用）」等行内限定即可，不再用 `*.claude.md` / `*.codex.md` 分文件。
- **领域工具集** → 写入 [`skills/domain/`](../domain/)。
- **禁止**再在 `.devin/.codex/.claude/workflows/skill/` 下创建副本——那些目录已永久废弃。

## 相关 skill

- [documentation](../engineering/documentation.md) - 文档规范（注释、docstring、README）
- [code-style](../engineering/code-style.md) - 代码风格
- [reference-analysis](../governance/reference-analysis.md) - 分析参考项目，提取可改造的模式
