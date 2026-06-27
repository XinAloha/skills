---
description: Git 分支工作流 - 分支模型、合并策略
type: sub-document
parent: git-version-control.md
auto_execution_mode: 2
---

# 分支工作流

## 分支模型（简化 Git Flow）

```
main (保护分支，始终可部署)
  │
  ├── feature/xxx  (功能开发)
  ├── fix/xxx      (热修复)
  └── refactor/xxx (重构)
```

### 分支命名规范

```
feature/<简短描述>          # 新功能
fix/<issue-id>-<描述>       # 修复（关联 issue）
refactor/<描述>             # 重构
hotfix/<描述>               # 紧急修复（基于 main）
docs/<描述>                 # 文档更新
test/<描述>                 # 测试补充
```

### 命名示例

- `feature/tushare-concurrent-collection`
- `fix/42-stream-inserter-race-condition`
- `refactor/extract-retry-decorator`

## 开发流程

### 1. 创建功能分支

```bash
git checkout main
git pull origin main
git checkout -b feature/gap-filler-concurrent
```

### 2. 开发并提交

```bash
git add .
git commit -m "feat(gap-filler): 支持并发模式填补历史缺口"
```

### 3. 同步主分支（推荐 rebase）

```bash
# 方式 A：rebase（保持线性历史）
git fetch origin
git rebase origin/main

# 方式 B：merge（保留分支上下文）
git fetch origin
git merge origin/main
```

### 4. 推送并创建 PR

```bash
git push -u origin feature/gap-filler-concurrent
```

### 5. 审查合并

- 通过 GitHub PR 进行代码审查
- 审查通过后使用 **Squash and Merge** 或 **Rebase and Merge**
- 删除已合并的功能分支

## 合并策略

| 场景 | 推荐策略 | 理由 |
|------|----------|------|
| 功能开发完成 | Squash and Merge | 保持 main 历史简洁，一个功能一个 commit |
| 多人协作分支 | Rebase and Merge | 保留完整开发历史，线性无 merge commit |
| 紧急热修复 | Create a merge commit | 明确记录修复来源 |

## 保护规则（建议配置）

- `main` 分支：
  - 禁止直接推送（Require pull request）
  - 要求至少 1 个审查批准
  - 要求状态检查通过（pytest / lint）
  - 禁止 force push

## 日常同步命令

```bash
# 获取最新主分支
git fetch origin main:main

# 查看分支状态
git branch -vv

# 清理已合并的本地分支
git branch --merged | grep -v "main" | xargs git branch -d

# 清理已合并的远程分支追踪
git remote prune origin
```
