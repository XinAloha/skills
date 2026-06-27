# 写 Agent Brief

agent brief 是 issue 移到 `ready-for-agent` 时贴在 issue 上的结构化评论。它是 AFK agent 据以工作的**权威规格**。原 issue body 与讨论是**上下文**——agent brief 是**契约**。

## 原则

### 耐久性 > 精确性

issue 可能在 `ready-for-agent` 待几天甚至几周，期间代码会变。**写 brief 时让它在文件被改名 / 移动 / 重构后仍然有用**。

- **要**：描述接口、类型、行为契约。
- **要**：命名 agent 应去找 / 修改的具体类型、函数签名、配置形状。
- **不要**：引用文件路径——会过时。
- **不要**：引用行号。
- **不要**：假设当前实现结构会保持。

### 行为，不是过程

描述系统**应该做什么**，不描述**怎么做**。Agent 会自己探索代码、做实现决策。

- **好**：「`CollectorConfig` 类型应接受可选的 `schedule` 字段，类型 `CronExpression`」
- **坏**：「打开 `data_collection/config.py` 在第 42 行加 schedule 字段」
- **好**：「用户跑 `/triage` 不带参数时，应看到需要注意的 issue 摘要」
- **坏**：「在主 handler 里加个 switch」

### 完整的验收标准

agent 需要知道**何时算干完了**。每条 brief 必须有具体、可测的验收标准。每条独立可验证。

- **好**：「跑 `pytest test/integration/test_pipeline.py -k schedule` 通过」
- **坏**：「分诊应正常工作」

### 显式的范围边界

**写明什么不在范围内**。防止 agent 做"顺手优化"或对相邻功能做假设。

## 模板

```markdown
## Agent Brief

**Category：** bug / enhancement
**Summary：** 一句话说要发生什么

**Current behavior：**
描述现在发生什么。bug 是坏行为。enhancement 是新功能要建在其上的现状。

**Desired behavior：**
描述 agent 干完后应该发生什么。对边界情况和错误条件要具体。

**Key interfaces：**
- `TypeName` —— 要改什么、为什么
- `function_name()` 的返回类型 —— 当前 vs 应该
- 配置形状 —— 任何新配置项

**Acceptance criteria：**
- [ ] 具体可测的标准 1
- [ ] 具体可测的标准 2
- [ ] 具体可测的标准 3

**Out of scope：**
- 不应被改 / 不该在这个 issue 里处理的东西
- 看着相关但其实独立的相邻功能
```

## 本项目示例（bug）

```markdown
## Agent Brief

**Category：** bug
**Summary：** 停牌日采集器把前一日 close 写成当日 close

**Current behavior：**
当采集器在停牌日（如 600145.SH 在 20251010）调用 `fetch_daily()` 时，
返回的 DataFrame 第 close 列填的是前一交易日的收盘价，而不是 None。
这导致 daily_kline 表里出现"假装在交易"的虚假行情。

**Desired behavior：**
停牌日返回的 DataFrame 行：
- close / open / high / low / volume 全部为 None
- 一条标记字段（如 `suspended=True`）
- date 字段保留为停牌当日

**Key interfaces：**
- `BaseCollector.fetch_daily()` 的返回 DataFrame schema
  —— 不变，但增加 suspended 列（或在已有 schema 上对齐）
- 数据源 client 处理停牌响应的 normalize 函数

**Acceptance criteria：**
- [ ] `pytest test/data_quality/test_suspended_handling.py` 全绿
- [ ] 至少覆盖 Tushare、AKShare 两个 fixture
- [ ] daily_kline 表的 schema 不破坏（向后兼容）

**Out of scope：**
- 复牌后历史数据回填（独立 issue）
- 停牌检测的事件触发机制
```

## 反例（坏 brief）

```markdown
## Agent Brief

**Summary：** 修分诊 bug

**What to do：**
分诊那个东西坏了。看主文件里改一下。
那个 150 行附近的函数有问题。

**Files to change：**
- src/triage/handler.ts (line 150)
- src/types.ts (line 42)
```

为什么坏：

- 没类别。
- 描述含糊。
- 引用会过时的文件路径与行号。
- 没有验收标准。
- 没有范围边界。
- 没说当前 vs 期望行为。
