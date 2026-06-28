---
description: pre-commit 钩子配置（Python 版） - pre-commit + ruff/black + pytest 短测
type: misc
parent: dev-guidelines.md
auto_execution_mode: 2
source: Matt Pocock skills - misc/setup-pre-commit（已改写：从 Husky+lint-staged+Prettier → pre-commit + ruff/black/pytest）
---

# Setup Pre-Commit - 配置 pre-commit 钩子（Python 版）

> 触发：用户希望加 pre-commit 钩子、配置提交时格式化 / lint / 短测。

> **改写说明**：原 Matt Pocock skill 是 Husky + lint-staged + Prettier（TS / 前端栈）。本项目改写为 **pre-commit + ruff + black + pytest**（Python 栈）。

## 配置什么

- **pre-commit** 框架（`pre-commit` Python 包）。
- **ruff**：lint + import 排序（替代 flake8 + isort）。
- **black**：格式化。
- **pytest 快速回归**：仅 `test/unit`，限时 60s，避免拖慢 commit。

## 步骤

### 1. 检查 Python 工具链

```bash
python --version  # >= 3.10
pip --version
```

### 2. 安装依赖

```bash
pip install pre-commit ruff black
# 或加进 requirements-dev.txt 后 pip install -r requirements-dev.txt
```

### 3. 创建 `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks:
      - id: black
        language_version: python3.10

  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest-unit
        entry: pytest test/unit -x --tb=short -q
        language: system
        pass_filenames: false
        stages: [commit]
```

> 选项：跑测试很慢就把 `pytest-unit` 钩子改到 `pre-push` 阶段（`stages: [push]`），commit 时只跑 ruff / black。

### 4. （如缺）创建 `pyproject.toml` ruff/black 配置

```toml
[tool.black]
line-length = 100
target-version = ["py310"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "SIM"]
ignore = ["E501"]  # 行宽交给 black

[tool.ruff.lint.isort]
known-first-party = ["data_collection"]
```

### 5. 安装钩子

```bash
pre-commit install
# 想给 push 也装就：
pre-commit install --hook-type pre-push
```

### 6. 首跑 / 全仓库扫一遍

```bash
pre-commit run --all-files
```

按需修复报错。

### 7. 验证

- [ ] `.pre-commit-config.yaml` 存在
- [ ] `pyproject.toml` 含 ruff/black 配置
- [ ] `.git/hooks/pre-commit` 已被 pre-commit 接管
- [ ] 改一个 .py 文件，故意写歪格式 → `git commit` 时被 black 自动修复 / 阻挡
- [ ] 改一个测试 → `git commit` 时被 pytest 钩子运行

### 8. 提交

把生成的配置文件提交：

```bash
git add .pre-commit-config.yaml pyproject.toml
git commit -m "chore: 配置 pre-commit (ruff/black/pytest)"
```

提交本身就是钩子的烟雾测试。

## 注意

- pre-commit 第一次运行会拉钩子（git clone 各 repo），会比较慢；**后续从缓存跑**。
- pytest 钩子如果项目大，**只跑 `test/unit`**，不要全量；**全量留给 CI**。
- 与 `.codex` / `.devin` / `.claude` 工作流的关系：所有 Agent 在 commit 前都受这套钩子约束，与 [git-guardrails-claude-code](git-guardrails-claude-code.md) 联用形成两道防线（命令拦截 + 内容质量）。

## 相关 skill

- [code-style](../engineering/code-style.md) - 导入顺序、类设计、异常处理（与 ruff/black 强制 enforced）
- [test-strategy](../testing/test-strategy.md) - pytest 分层、覆盖率
- [git-version-control](../git/git-version-control.md) - Git 版本控制入口
- [git-commit-convention](../git/git-commit-convention.md) - Conventional Commits（pre-commit 也可加 commitizen 钩子）
- [git-guardrails-claude-code](git-guardrails-claude-code.md) - Claude Code 命令拦截
