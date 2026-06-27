---
description: Git 提交规范 - commit message 格式、版本号规则
type: sub-document
parent: git-version-control.md
auto_execution_mode: 2
---

# 提交规范

## Commit Message 格式

采用 **Conventional Commits** 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型

| 类型 | 含义 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(tushare): 添加融资融券明细采集` |
| `fix` | 修复 bug | `fix(db): 修复批量插入时连接池泄漏` |
| `refactor` | 重构（不改变行为） | `refactor(collector): 提取公共重试逻辑` |
| `perf` | 性能优化 | `perf(concurrent): 日K线采集速度提升 40%` |
| `test` | 测试相关 | `test(integration): 补充 AKShare 日更表测试` |
| `docs` | 文档更新 | `docs(api): 补充实时行情接口说明` |
| `chore` | 构建/工具/杂项 | `chore(deps): 升级 pandas 到 2.2.0` |
| `style` | 代码格式（无逻辑变更） | `style: 统一 import 排序` |

### Scope 范围

可选，建议使用模块名：

- `collector` / `tushare` / `akshare` / `db` / `config` / `test` / `docs`

### Subject 主题

- 使用祈使句，首字母小写
- 不超过 50 个字符
- 结尾不加句号

### Body 正文

- 说明 **为什么** 变更，而非 **做了什么**（diff 已说明做了什么）
- 可包含 breaking change 说明

### Footer 页脚

- `Closes #123` - 关联关闭 issue
- `BREAKING CHANGE:` - 破坏性变更说明

## 提交频率

- **原子性**：每次 commit 只做一件事
- **及时性**：功能完成即提交，不要积攒大量变更
- **独立性**：每个 commit 应能独立通过测试

## 禁止事项

- ❌ `git commit -m "update"` / `git commit -m "fix bug"`
- ❌ 提交包含敏感信息（token、密码、数据库连接串）
- ❌ 提交包含本地调试代码（`print`、`pdb`、临时文件）
- ❌ 提交大型二进制文件（数据文件、日志、`.pyc`）

## 本地提交前检查清单

```bash
# 1. 检查变更范围
git diff --cached --name-only

# 2. 检查是否包含敏感信息
grep -E "(password|token|secret|api_key)" $(git diff --cached --name-only) || true

# 3. 运行测试
pytest -q
```
