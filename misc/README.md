---
description: 杂项参考 skill 索引 - git 守卫、参考项目分析脚手架、Python 类型治理参考、pre-commit 钩子
type: misc
parent: dev-guidelines.md
auto_execution_mode: 2
source: Matt Pocock skills (misc 部分，部分针对 TS/JS 的已改写为 Python 工具链)
---

# 杂项参考分组

不常用但留作参考的 skill。

## skill 列表

| skill | 何时用 |
|------|------|
| [git-guardrails-claude-code](git-guardrails-claude-code.md) | 给 Claude Code 装 PreToolUse 钩子，拦截 `git push` / `reset --hard` / `clean -f` 等危险命令 |
| [scaffold-exercises](scaffold-exercises.md) | 为参考项目分析建练习目录脚手架（与 [reference-analysis](../governance/reference-analysis.md) 联动） |
| [migrate-to-shoehorn](migrate-to-shoehorn.md) | **Python 改写参考**：测试中类型断言治理（原 Matt Pocock 是 TS 专属） |
| [setup-pre-commit](setup-pre-commit.md) | **Python 改写参考**：本项目 pre-commit + ruff/black/pytest 钩子配置 |

## 与既有 skill 关系

- `git-guardrails-claude-code` ↔ [git-rollback-recovery](../git/git-rollback-recovery.md)、[git-version-control](../git/git-version-control.md)
- `scaffold-exercises` ↔ [reference-analysis](../governance/reference-analysis.md)、[refactoring-checklist](../governance/refactoring-checklist.md)
- `setup-pre-commit` ↔ [code-style](../engineering/code-style.md)、[test-strategy](../testing/test-strategy.md)
- `migrate-to-shoehorn` —— TS 专属上游 skill，仅作 Python 类比参考，不在主线使用
