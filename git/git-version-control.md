---
description: Git 版本控制 - 索引入口，按需加载子文档
type: sub-document
parent: dev-guidelines.md
auto_execution_mode: 2
---

# Git 版本控制

> **核心理念**：规范化提交、分支隔离、可回滚、可审查
> **文件定位**：此文件仅作索引，详细规则通过 `/load-skill` 按需加载

## 标准 Git 流程

| 阶段 | 动作 | 加载命令 |
|------|------|----------|
| 提交 | 编写符合规范的 commit message | `/load-skill git-commit-convention` |
| 分支 | 创建、合并、发布分支 | `/load-skill git-branch-workflow` |
| 审查 | PR / MR 审查流程 | `/load-skill git-code-review` |
| 恢复 | 回滚、 cherry-pick、数据恢复 | `/load-skill git-rollback-recovery` |

## 全局约束

- **默认分支**：`main`
- **远程仓库**：`git@github.com:XinAloha/QuantAlpha.git`
- **提交前必须**：代码可运行、测试通过、敏感信息已排除
- **禁止操作**：`git push --force` 到 `main`（除非紧急回滚并经过确认）

## 快速参考

```bash
# 查看状态
git status

# 提交规范示例
git commit -m "feat(concurrent): Tushare 全量采集器支持多线程并发"

# 创建功能分支
git checkout -b feature/gap-filler-optimization

# 推送到远程
git push -u origin feature/gap-filler-optimization

# 安全的强制推送（仅用于 rebase 后的个人分支）
git push --force-with-lease
```
