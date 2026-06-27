---
description: 自动化代码清理 - 扫描冗余、架构违规、文档不一致并自动修复
type: sub-document
parent: dev-guidelines.md
auto_execution_mode: 2
---

# 自动化代码清理

> **触发指令**：`扫描文件解决冗余和违规问题`、`代码清理`、`自动清理`、`扫描架构违规`
>
> **核心理念**：生成速度上来了，清理速度必须跟上。定期扫描、自动修复、防止项目被自己的产物拖垮。

## 扫描范围

```
data_collection/      # 核心源码
docs/               # 项目文档
test/               # 测试代码
*.py                # 所有 Python 文件
```

## 三大扫描维度

### 1. 冗余代码 (Redundancy)

| 检查项 | 规则 | 修复动作 |
|--------|------|---------|
| **重复代码块** | 相同逻辑在 2+ 文件出现 | 提取到 `utils/` 或基类 |
| **未使用导入** | `import` 后无引用 | 删除 |
| **死代码** | 函数/类/变量无任何引用 | 删除，先搜索确认 |
| **重复常量** | 相同字面量在多处硬编码 | 提取到模块级常量或配置 |
| **重复异常处理** | 相同的 `try-except` 模式复制粘贴 | 提取为装饰器或辅助函数 |

**典型目标文件**：
- `data_collection/collectors/` - 采集器间常存在重复的分页、写入、日志逻辑
- `data_collection/core/` - 重复的工具函数

### 2. 架构违规 (Architecture Violation)

| 检查项 | 规则 | 修复动作 |
|--------|------|---------|
| **跨层引用** | 采集器直接调用其他采集器的私有方法 | 通过核心调度层间接调用 |
| **硬编码配置** | URL、Token、路径写死在代码中 | 迁移到 `config/` 或环境变量 |
| **职责溢出** | 采集器混入分析/可视化/ORM 逻辑 | 剥离到对应模块 |
| **循环导入** | `a.py` import `b.py`，`b.py` 又 import `a.py` | 提取公共接口到独立模块 |
| **外部适配器位置** | 第三方系统适配器放在 `data_collection/` 内 | 移到项目根或独立包 |
| **数据库操作下沉** | 采集器直接执行 SQL | 通过 `database/` 层封装 |

### 3. 文档不一致 (Doc Inconsistency)

| 检查项 | 规则 | 修复动作 |
|--------|------|---------|
| **README 过期** | 目录树、技术栈、功能列表与代码不符 | 同步更新 |
| **core_features.md 缺失** | 新增核心功能未在 `docs/core_features.md` 记录 | 补充 Feature 区块 |
| **模块 docstring 与实现不符** | docstring 描述的函数/参数已变更 | 同步更新 |
| **CHANGELOG 缺失** | 本次变更是 Added/Changed/Fixed 但未记录 | 补充条目 |
| **类型注解与文档矛盾** | docstring 写 `str`，注解写 `int` | 以代码为准修正文档 |

## 执行步骤

### Step 1: 全局扫描（只读分析）

```bash
# 收集所有 Python 文件
# 按模块分组，识别跨文件重复代码段 (>5 行相似度 >80%)
# 检查每个文件的导入使用情况
# 扫描 docs/ 与代码的对应关系
```

**输出**: `cleanup_scan_report.md`（临时）

### Step 2: 分类定级

| 级别 | 定义 | 处理策略 |
|------|------|---------|
| **P0 - 阻塞** | 安全违规（密钥硬编码）、循环导入导致崩溃 | 立即修复 |
| **P1 - 高风险** | 重复代码 >3 处、核心文档严重过期 | 本次清理 |
| **P2 - 中风险** | 未使用导入、轻微文档偏差 | 批量修复 |
| **P3 - 低风险** | 格式不一致、注释缺失 | 可选，不阻塞 |

### Step 3: 自动修复（按优先级）

**禁止行为**（先确认再执行）：
- ❌ 删除有副作用的"死代码"（如导入时注册钩子、全局状态修改）
- ❌ 修改正在运行的核心调度逻辑
- ❌ 删除测试中的 `mock` 或 `patch` 导入

**自动执行**：
- ✅ 删除确认无引用的未使用导入
- ✅ 将重复常量提取到模块级
- ✅ 同步 docstring 与函数签名
- ✅ 更新 README 目录树

### Step 4: 验证

- [ ] 所有测试通过 `pytest`
- [ ] 无新增循环导入 `python -m compileall .`
- [ ] 关键采集器可正常导入 `python -c "from data_collection.collectors import X"`
- [ ] 文档链接有效

### Step 5: 生成清理摘要

```markdown
## 清理摘要 [日期]

### 冗余代码
- 删除未使用导入: X 处
- 提取重复逻辑: Y 处 → 新文件/函数: `xxx`

### 架构违规
- 迁移硬编码配置: Z 处
- 修复跨层引用: N 处

### 文档不一致
- 更新 README: 目录树/技术栈
- 补充 core_features.md: X 个 Feature

### 风险项（未自动修复，需人工确认）
- [ ] `xxx.py:line` 疑似死代码，但可能运行时反射调用
- [ ] `yyy.py:line` 跨模块引用，需设计接口
```

## 采集器专项清理规则

本项目采集器密集，重复模式最多，重点扫描：

**重复模式清单**：
1. **分页采集模板** - `offset/limit` 循环 → 提取到 `core/paginated_fetcher.py`
2. **限流等待** - `time.sleep` + `_last_request_time` → 提取到 `core/rate_limiter.py`
3. **数据库安全写入** - `INSERT OR IGNORE` 逐行回退 → 提取到 `database/safe_writer.py`
4. **进度条/日志** - tqdm + logger 组合 → 提取到 `core/progress_tracker.py`
5. **ts_code 转换** - `to_ts_code` / `from_ts_code` → 已封装，检查是否仍有多处手动拼接

**违规红线**：
- 采集器直接 `import requests` 发请求（应通过 `RetryableDataClient`）
- 采集器直接 `create_engine(db_url)`（应注入 engine）
- 采集器内写死表名做 `DELETE/TRUNCATE`（应通过 DAO 层）

## 执行频率建议

| 触发条件 | 动作 |
|---------|------|
| **每次 PR 合并后** | 扫描本次变更引发的文档不一致 |
| **每周五** | 全量扫描冗余代码和架构违规（OpenAI 模式） |
| **里程碑版本前** | 强制全量清理，生成清理摘要 |

## 与现有 Skill 的关联

- 发现设计模式误用 → `/load-skill design-patterns`
- 发现需要重构的模块 → `/load-skill refactoring-checklist`
- 发现安全违规 → `/load-skill security`
- 发现文档缺失 → `/load-skill documentation`
