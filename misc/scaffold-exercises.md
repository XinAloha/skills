---
description: 参考项目分析练习目录脚手架 - 章节 / 问题 / 解答 / 解释器结构
type: misc
parent: dev-guidelines.md
auto_execution_mode: 2
source: Matt Pocock skills - misc/scaffold-exercises（已改写：从 TS 课程脚手架 → Python / 量化项目"参考分析练习"）
---

# Scaffold Exercises - 练习目录脚手架

> 触发：用户希望为参考项目分析建练习目录、做参考项目对照学习，或为新成员准备入门练习。

> **改写说明**：原 Matt Pocock skill 是为 TS 课程平台（`pnpm ai-hero-cli`）设计的。本项目改写为：**为 `references/` 下参考项目的分析建标准化练习目录**，与 [reference-analysis](../governance/reference-analysis.md) / [refactoring-checklist](../governance/refactoring-checklist.md) 联动。

## 目录命名

- **章节**：`XX-section-name/`，放在 `references/exercises/` 下（如 `01-akshare-collector-design`）。
- **练习**：`XX.YY-exercise-name/`，放在章节里（如 `01.03-akshare-rate-limiting`）。
- 章节号 `XX`，练习号 `XX.YY`。
- 名字 dash-case（小写、连字符）。

## 练习变体

每个练习至少一个子目录：

- `problem/` —— 学员工作区，含 TODO。
- `solution/` —— 参考实现。
- `explainer/` —— 概念材料，无 TODO。

**Stub 时默认 `explainer/`**，除非计划另指定。

## 必需文件

每个子目录（`problem/` / `solution/` / `explainer/`）需要一个 `readme.md`：

- **非空**（必须有真实内容，单行标题也行）。
- **无失效链接**。

stub 时建一份最小 readme：

```md
# 练习标题

描述。
```

子目录有代码就需要一个**主文件**（本项目用 `main.py`，>1 行）。stub 状态下"只有 readme"也合法。

## 工作流

1. **解析计划** —— 抽出章节名、练习名、变体类型。
2. **建目录** —— 每个路径 `mkdir -p`。
3. **建 stub readme** —— 每个变体目录一个 `readme.md`，标题级别。
4. **运行 lint** —— 简单脚本检查（见下文）。
5. **修错** —— 迭代直到通过。

## 简易 lint 规则（本项目版）

不再依赖 `pnpm ai-hero-cli`。本项目用一段 Python 脚本验证：

- 每个练习有至少一个变体子目录。
- `readme.md` 存在且非空。
- 无 `.gitkeep`。
- 主文件存在且 >1 行（如果不是 readme-only）。
- readme 内的相对链接指向真实存在的文件。

```python
# scripts/lint_exercises.py
from pathlib import Path
import sys

ROOT = Path("references/exercises")
errors = []

for section in sorted(ROOT.iterdir()):
    if not section.is_dir(): continue
    for exercise in sorted(section.iterdir()):
        if not exercise.is_dir(): continue
        variants = [v for v in exercise.iterdir() if v.is_dir()]
        if not variants:
            errors.append(f"{exercise} 无变体子目录")
            continue
        for v in variants:
            readme = v / "readme.md"
            if not readme.exists() or readme.stat().st_size == 0:
                errors.append(f"{v} readme.md 缺失或空")

if errors:
    print("\n".join(errors))
    sys.exit(1)
```

## 移动 / 重命名练习

**用 `git mv`，不用 `mv`** —— 保留 git 历史。

```bash
git mv references/exercises/01-akshare/01.03-rate-limiting references/exercises/01-akshare/01.04-rate-limiting
```

重命名后再跑 lint。

## 例：从计划做 stub

计划：

```
章节 05：参考项目深度分析 - QUANTAXIS
- 05.01 项目结构总览（explainer）
- 05.02 数据源适配层（explainer + problem + solution）
- 05.03 数据库访问层（explainer）
```

建：

```bash
mkdir -p references/exercises/05-quantaxis-deep-dive/05.01-project-structure/explainer
mkdir -p references/exercises/05-quantaxis-deep-dive/05.02-data-source-layer/{explainer,problem,solution}
mkdir -p references/exercises/05-quantaxis-deep-dive/05.03-database-layer/explainer
```

stub readme：

```
references/exercises/05-quantaxis-deep-dive/05.01-project-structure/explainer/readme.md → "# 项目结构总览"
references/exercises/05-quantaxis-deep-dive/05.02-data-source-layer/explainer/readme.md → "# 数据源适配层"
... 其余同理
```

## 相关 skill

- [reference-analysis](../governance/reference-analysis.md) - 参考项目分析流程
- [refactoring-checklist](../governance/refactoring-checklist.md) - 分析 / 提取 / 重构三阶段
- [reusable-patterns](../engineering/reusable-patterns.md) - 已沉淀的可复用模式
