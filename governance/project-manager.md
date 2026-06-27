---
description: 项目经理 - 需求抽象评审与逻辑混乱治理
type: sub-document
parent: dev-guidelines.md
auto_execution_mode: 2
---

# 项目经理 - 需求抽象评审与逻辑混乱治理

> **触发指令**：`评审需求`、`检查逻辑混乱`、`PM 评审`、`清理需求债务`、`流程矛盾分析`
>
> **核心理念**：代码能跑通不代表逻辑正确。项目经理视角要求：需求可独立表述、流程无矛盾、职责有边界、命名与行为一致。

## 一、评审触发条件

| 场景 | 动作 |
|------|------|
| 新功能开发前 | 用"一句话测试"检验需求是否足够独立 |
| 代码 Review 时 | 检查是否引入流程矛盾或职责越界 |
| 发现"扩展数据"、"备用逻辑"等模糊需求时 | 立即启动 PM 评审 |
| 每周五 / 里程碑前 | 全量扫描需求债务，生成整改清单 |

## 二、四大评审维度

### 1. 需求抽象度（Abstraction）

| 检查项 | 通过标准 | 失败示例 |
|--------|---------|---------|
| **一句话测试** | 能用一句话说明白这个需求做什么，不依赖其他模块 | "采集扩展数据"（到底扩展了什么？） |
| **独立性测试** | 该需求可以单独启用/禁用，不影响核心流程 | "全量更新必须连带采集概念板块" |
| **生命周期测试** | 有明确的触发条件、频率、终止条件 | "复权因子建议每季度更新"（只是建议，无 enforcement） |

**本项目的典型反模式**：
- "扩展数据" = 概念板块 + 复权因子 + 龙虎榜（三个完全不同生命周期的东西塞在一起）
- "备用源" = 既在 `full_update` 里作为全量日K来源，又在 `smart_update` 里作为降级逻辑

### 2. 流程逻辑一致性（Flow Consistency）

| 检查项 | 通过标准 | 失败示例 |
|--------|---------|---------|
| **无重复采集** | 同一数据表不会被两个独立流程重复写入 | `full_update`: Tushare 全量日K后又跑 adata 批量日K |
| **无幽灵步骤** | 流程中的每一步都有明确输入输出，不悬空 | `full_update` 步骤4"扩展数据"依赖步骤3完成，但步骤3失败后步骤4仍执行 |
| **新鲜度与采集对齐** | 有检查新鲜度的地方，必须有对应的跳过/采集逻辑 | `extended_update` 无前置新鲜度检查，`smart_update` 才有 |
| **降级逻辑统一** | 主源/备用源/降级源的切换规则在一个地方定义 | `daily_job.py` `_collect_daily_kline_smart` 里写一套，`full_update` 里又写一套 |

### 3. 职责边界清晰度（Responsibility）

| 检查项 | 通过标准 | 失败示例 |
|--------|---------|---------|
| **单一职责** | 一个类/模块只做一类事 | `StockDataCollector` 同时做：股票列表、日K、概念、复权因子、龙虎榜、资金流向 |
| **调度与执行分离** | 调度器只编排，不直接执行业务逻辑 | `daily_job.py` 既是 CLI 入口，又是流程编排器，又直接写 SQL 检测新鲜度 |
| **采集器不越界** | 采集器只负责拉取和标准化，不写库、不调度 | `smart_update` 里 `_update_stock_list_smart` 直接 `to_sql` |

### 4. 命名与语义一致性（Semantics）

| 检查项 | 通过标准 | 失败示例 |
|--------|---------|---------|
| **名实相符** | 函数名/变量名准确描述行为 | `full_update` 里包含"备用源"（全量为什么需要备用？） |
| **语义层级一致** | 同一层级的东西名字结构一致 | `full_update` vs `incremental_update` vs `extended_update` vs `smart_update`（`extended` 不是更新模式，是数据类型） |
| **配置与代码一致** | `config/default.yaml` 里的配置名与代码引用一致 | `daily_job.incremental_days` 只在 `incremental_update` 用，`smart_update` 不读 |

## 三、问题模式清单（Anti-Patterns）

### 模式 A：大杂烩需求（Kitchen Sink）

**特征**：一个需求或函数把多个不相关的东西打包在一起。

**本项目实例**：
```python
# daily_job.py:238
def extended_update(collector):
    """扩展数据采集（概念板块、复权因子、龙虎榜）"""
    # 概念板块（同花顺/东财，月更新）
    # 复权因子（Tushare，季更新）
    # 龙虎榜（Tushare，日更新）
```

**整改要求**：
- [ ] 拆分为 `update_concepts()`、`update_adjust_factors()`、`update_longhu_bang()`
- [ ] 每个子需求独立生命周期（更新频率、数据源、失败策略）
- [ ] `extended_update` 改为纯调度函数，或彻底废除

### 模式 B：流程中的"幽灵采集"（Ghost Collection）

**特征**：主流程已经采集了数据，但后面又冒出来一个"备用"或"补充"采集同一目标表。

**本项目实例**：
```python
# daily_job.py:101-157 full_update
# Step 2: Tushare Pro 全量日K
collector.run_tushare_full_collection()
# Step 3: 批量采集日K数据（备用源）  <-- 幽灵步骤
collector.batch_collect_kline()
```

**整改要求**：
- [ ] 明确 `daily_kline` 的**唯一写入来源**：Tushare 全量 OR adata 批量 OR 增量更新
- [ ] 备用源降级逻辑必须收敛到 `StockDataCollector._fetch_kline_raw()` 内部
- [ ] `full_update` 中删除步骤3的显式备用源调用

### 模式 C：降级逻辑发散（Scattered Fallback）

**特征**：主源失败后的降级策略散落在多个文件、多个函数里。

**本项目实例**：
- `stock_collector.py:_fetch_kline_raw()` 里：Tushare -> fallback -> retry_client -> adata
- `daily_job.py:_update_stock_list_smart()` 里：adata -> akshare -> retry_client
- `daily_job.py:_collect_daily_kline_smart()` 里：adata 主源 -> fallback 采样

**整改要求**：
- [ ] 所有降级逻辑收敛到 `DataSourceRouter` 或 `FallbackManager`
- [ ] `daily_job.py` 只声明"我要日K"，不声明"先用谁再用谁"
- [ ] 降级策略可配置（`config/default.yaml`），不在代码里写死

### 模式 D：需求生命周期绑架（Lifecycle Hijacking）

**特征**：低频次需求被绑架到高频次流程中，或反之。

**本项目实例**：
- `full_update` 强制执行概念板块（月更）和龙虎榜（日更）在同一流程
- `smart_update` 的扩展数据检查全部串行执行，阻塞日K更新

**整改要求**：
- [ ] 每个数据类型标注：`frequency`（更新频率）、`blocking`（是否阻塞主流程）
- [ ] 高频核心流程（日K）与低频扩展流程物理分离
- [ ] 支持独立 CLI 调用：`python daily_job.py --mode concepts`

### 模式 E：语义层级错位（Semantic Mismatch）

**特征**：函数/模块在错误的抽象层级上做错误的事。

**本项目实例**：
```python
# daily_job.py 的 CLI 入口同时包含：
- 参数解析（CLI 层）
- 流程编排（调度层）
- 数据源可用性检测（业务层：_check_datasource_available）
- 新鲜度 SQL 查询（数据层）
- 备用源直接写入（采集层：akshare 结果 to_sql）
```

**整改要求**：
- [ ] CLI 层只解析参数，初始化 Collector，调用调度函数
- [ ] 调度层（`core/scheduler.py`）只决定"先做什么后做什么"
- [ ] 业务层只封装"做什么"，不接触具体 SQL
- [ ] 采集层只拉取数据，返回 DataFrame，不执行 to_sql

## 四、PM 评审检查清单

### 新增功能前（必做）

- [ ] **一句话测试**：能用一句话说明这个功能要做什么，不提及任何实现细节？
- [ ] **独立性测试**：这个功能可以单独启用/禁用，不影响已有核心流程？
- [ ] **生命周期测试**：更新频率、数据源、失败策略是否已明确？
- [ ] **命名测试**：函数/模块名是否准确描述行为，不会引起歧义？
- [ ] **流程测试**：不会在主流程中重复采集同一数据表？

### 代码 Review 时（必做）

- [ ] **职责测试**：新代码是否引入了"又做A又做B"的情况？
- [ ] **降级测试**：备用/降级逻辑是否收敛到统一组件？
- [ ] **新鲜度测试**：新增的数据采集是否有前置新鲜度检查和跳过逻辑？
- [ ] **配置测试**：新增的配置项是否在 `config/default.yaml` 中有声明和默认值？
- [ ] **文档测试**：`docs/core_features.md` 是否同步更新了需求定义？

### 定时全量扫描（每周五 / 里程碑前）

```
1. 扫描所有"采集"类函数的调用链
   - 同一表名是否被 2+ 个顶层流程写入？
   - 写入的列和来源是否一致？

2. 扫描所有"更新"类函数的命名
   - 函数名是否都是"动作+对象"格式？
   - 是否有"扩展"、"辅助"、"其他"等模糊词汇？

3. 扫描 config/default.yaml 与代码引用
   - 配置项是否都有代码读取？
   - 代码中硬编码的阈值是否应迁移到配置？

4. 扫描需求生命周期
   - 每个数据类型是否有明确的 frequency 标注？
   - 高频和低频需求是否物理分离？
```

## 五、整改方案模板

发现逻辑混乱后，按此模板输出：

```markdown
## PM 评审报告 [日期]

### 发现问题
- **位置**：`daily_job.py:138-146`
- **问题**：`full_update` 在 Tushare 全量采集后，又执行 adata 批量日K（备用源）
- **影响**：`daily_kline` 表可能被两个不同来源重复写入，数据冲突

### 根因分析
- 需求抽象不足："全量更新"被等同于"用所有能用的源把数据灌满"
- 职责边界不清：`daily_job` 直接编排采集源，而非委托给采集器

### 整改方案
1. **短期**（本次迭代）：
   - [ ] 在 `full_update` 中删除步骤3的 `batch_collect_kline`
   - [ ] 在 `StockDataCollector._fetch_kline_raw()` 中统一源降级逻辑
2. **中期**（下两周）：
   - [ ] 引入 `DataSourceRouter`，所有源选择逻辑收敛
3. **长期**（下月）：
   - [ ] `daily_job.py` 只保留流程骨架，所有业务逻辑下沉到 `core/` 调度器

### 验证标准
- [ ] `full_update` 只调用一个日K采集入口
- [ ] `daily_kline` 表在全量更新后无重复记录
- [ ] `pytest test/integrity/test_no_duplicate_sources.py` 通过
```

## 六、与现有 Skill 的关联

- 发现职责混乱需要重构 -> `/load-skill refactoring-checklist`
- 发现设计模式误用 -> `/load-skill design-patterns`
- 发现代码质量问题 -> `/load-skill auto-cleanup`
- 发现需要拆分接口 -> `/load-skill extensibility`
