---
description: 学习分析流程 - 克隆、结构分析、提取模式、重构实施
type: sub-document
parent: dev-guidelines.md
auto_execution_mode: 2
---

# 学习分析流程

> **references/ 目录结构**
> ```
> references/
> ├── clone/      # 克隆的参考项目源码
> ├── analysis/   # 项目分析文档
> └── snippets/   # 提取的可复用代码片段
> ```

## Phase 1: 项目克隆与概览

```bash
cd references/clone

# 浅克隆，只取最近历史
git clone --depth 1 https://github.com/akfamily/akshare.git
git clone --depth 1 https://github.com/vnpy/vnpy_datamanager.git
```

## Phase 2: 结构分析

分析模板（`analysis/XXX_analysis.md`）：

```markdown
## 1. 项目概览
- 主要功能：
- 技术栈：
- 代码规模：

## 2. 架构分析
### 目录结构
### 核心模块职责
| 模块 | 职责 | 设计亮点 |

## 3. 数据源处理
### 支持的来源
### 采集策略

## 4. 可借鉴的代码
### 代码片段 1
**借鉴点**：

## 5. 对比与改进建议
| 维度 | 本项目现状 | 参考项目做法 | 改进建议 |
```

## Phase 3: 提取可复用模式

将发现的优秀模式提取到 `references/snippets/`：

```
snippets/
├── retry_mechanism.py          # 重试机制
├── caching_strategy.py         # 缓存策略
├── data_validation.py          # 数据验证
├── rate_limiter.py             # 限流控制
├── multi_source_fallback.py    # 多源降级
└── database_orm.py             # 数据库 ORM 模式
```

每个 snippet 文件格式：

```python
"""
来源: akshare/akshare/stock/stock_zh_a_sina.py
功能: 带指数退避的重试机制
适用场景: 网络请求失败后的自动重试
"""

# 代码实现...

# 使用示例
```

## Phase 4: 重构实施

制定重构计划（`analysis/refactoring_plan.md`）：

```markdown
## 当前迭代目标：[具体目标]
## 参考项目：[项目名称]

## 待重构模块
### 1. [模块名]
**现状问题**：
**参考方案**：
**实施步骤**：
1. 
2. 
3. 
**预期收益**：

## 验收标准
- [ ] 代码结构符合新设计
- [ ] 单元测试通过
- [ ] 性能指标满足要求
```

## 参考项目清单

| 项目 | 地址 | 学习重点 | 优先级 |
|------|------|---------|--------|
| **akshare** | https://github.com/akfamily/akshare | 数据源适配、异常处理、多源策略 | P0 |
| **tushare** | https://github.com/waditu/tushare | API 设计、数据标准化 | P1 |
| **vnpy_datamanager** | https://github.com/vnpy/vnpy_datamanager | 数据管理、数据库存储 | P1 |
| **baostock** | https://github.com/baostock | 免费数据源采集 | P2 |
| **quantaxis** | https://github.com/QUANTAXIS/QUANTAXIS | 整体架构设计 | P2 |
| **yfinance** | https://github.com/ranaroussi/yfinance | 简洁 API 设计 | P2 |

## 持续学习节奏

| 周期 | 活动 | 产出 |
|------|------|------|
| **每周** | 分析 1 个参考项目的 1 个模块 | 1 篇分析文档 |
| **每两周** | 提取可复用代码片段 | 2-3 个 snippet |
| **每月** | 实施 1 次重构 | 1 个改进后的模块 |
| **每季度** | 回顾和整理 | 更新的设计规范 |

## 下一步行动

1. 使用避坑清单筛选参考项目（见 `skill/avoid-pitfalls.md`）
2. 克隆通过筛选的第一个项目（推荐 akshare）
3. 完成第一个模块的分析文档
4. 提取第一个代码片段
5. 实施第一次重构
