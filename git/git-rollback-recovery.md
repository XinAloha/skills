---
description: Git 回滚与恢复 - 常见回滚场景、数据安全
type: sub-document
parent: git-version-control.md
auto_execution_mode: 2
---

# 回滚与恢复

## 常见回滚场景

### 1. 撤销未暂存的本地修改

```bash
# 单个文件
git checkout -- <file>

# 全部未暂存修改（慎用）
git checkout -- .
```

### 2. 撤销已暂存但未提交的修改

```bash
# 取消暂存
git reset HEAD <file>

# 取消暂存并丢弃修改
git reset --hard HEAD
```

### 3. 撤销已提交（仅本地）

```bash
# 保留修改到工作区
git reset --soft HEAD~1

# 保留修改到暂存区
git reset --mixed HEAD~1

# 彻底丢弃（慎用）
git reset --hard HEAD~1
```

### 4. 回滚已推送到远程的提交

**首选方式：revert（安全，保留历史）**

```bash
# 生成一个新的提交，反转指定提交的变更
git revert <commit-hash>
git push origin main
```

**备选方式：reset + force push（仅用于紧急清理）**

```bash
# 必须先确认无其他协作者在此之后提交
git reset --hard <commit-hash>
git push --force-with-lease origin main
```

### 5. 恢复已删除的分支

```bash
# 查看 reflog 找回 hash
git reflog

# 恢复分支
git checkout -b <branch-name> <commit-hash>
```

## 数据安全红线

### 禁止提交的内容

- `.env` 文件（已加入 `.gitignore`）
- 数据库连接字符串含密码
- API Token / Secret Key
- 个人密钥文件（`.pem`, `.key`）
- 大型数据文件（`.csv`, `.db`, `.parquet`）
- 日志文件（`logs/` 已加入 `.gitignore`）

### 敏感信息误提交后的处理

```bash
# 1. 立即撤销敏感文件追踪（但不删除本地文件）
git rm --cached <file>

# 2. 确认 .gitignore 已包含该文件
echo ".env" >> .gitignore

# 3. 如果已推送到远程，使用 BFG Repo-Cleaner 或 git-filter-repo 清理历史
# （此操作会重写历史，需团队同步）
```

## 数据库相关回滚

采集系统涉及数据库迁移，回滚时需注意：

- **代码回滚** ≠ **数据回滚**
- 若变更涉及 `schema.sql` 或迁移脚本，回滚代码后需评估数据库结构兼容性
- 生产环境回滚前必须备份数据库

## 协作安全

- 个人分支可以随意 `rebase` / `amend`
- **已推送到远程的共享分支禁止 `rebase -i` 修改历史**
- 使用 `git push --force-with-lease` 替代 `--force`
