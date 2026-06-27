---
description: Git 代码审查 - PR 规范、review 检查清单
type: sub-document
parent: git-version-control.md
auto_execution_mode: 2
---

# 代码审查

## PR 规范

### PR 标题格式

```
[<type>] <简明描述>
```

示例：
- `[feat] Tushare 全量采集器支持并发模式`
- `[fix] 修复 StreamInserter 多线程竞态条件`

### PR 描述模板

```markdown
## 变更内容
- 做了什么
- 为什么做

## 测试验证
- [ ] 本地 pytest 通过
- [ ] 集成测试通过
- [ ] 手动验证通过

## 影响范围
- 涉及模块：
- 数据库变更（如有）：
- 配置变更（如有）：

## 关联 Issue
Closes #123
```

## Review 检查清单

### 功能正确性
- [ ] 变更符合需求描述
- [ ] 边界条件已处理
- [ ] 错误处理路径已覆盖

### 代码质量
- [ ] 符合 `code-style` 规范（导入顺序、命名、类型注解）
- [ ] 无硬编码敏感信息
- [ ] 无遗留调试代码
- [ ] 异常处理符合规范（特定异常优先，不裸 catch）

### 测试覆盖
- [ ] 新增功能附带单元测试
- [ ] 修改功能更新对应测试
- [ ] 测试能独立运行（不依赖外部 API 时）

### 性能与并发
- [ ] 数据库连接正确关闭
- [ ] 线程/并发代码有锁保护
- [ ] 批量操作使用流式写入

### 文档与注释
- [ ] 公共 API 有 docstring
- [ ] 复杂逻辑有行内注释
- [ ] README / docs 已同步更新

## Review 评论规范

- **Approval**：`LGTM` / `Approve`
- **建议**：`Nit: `（微不足道的问题）
- **疑问**：`Question: `（需要作者确认）
- **阻塞**：`Blocking: `（必须修复才能合并）

## 合并前最终检查

```bash
# 1. 拉取 PR 分支并本地运行测试
git fetch origin pull/<PR_NUMBER>/head:pr-<NUMBER>
git checkout pr-<NUMBER>
pytest

# 2. 检查代码风格
# 如有 ruff / black，先格式化

# 3. 确认无冲突后合并
```
