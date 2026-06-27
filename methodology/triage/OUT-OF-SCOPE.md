# Out-of-Scope 知识库

repo 里的 `.out-of-scope/` 目录持久化记录被拒绝的功能请求。两个目的：

1. **机构记忆** —— 为什么被拒绝；理由不会随 issue 关闭一起消失。
2. **去重** —— 新 issue 撞上旧拒绝时，skill 能拉出之前的决策，**避免重新讨论**。

> 本项目当前用 `docs/out-of-scope/` 作为本地版（无 GitHub label），策略相同。

## 目录结构

```
docs/out-of-scope/   # 或仓库根 .out-of-scope/
├── ui-frontend.md
├── realtime-tick.md
└── futures-support.md
```

**一个文件 = 一个概念**，不是一个 issue。多个 issue 请求同一件事，归到同一个文件。

## 文件格式

写得**像短设计文档而不是数据库条目**。用段落、代码示例、具体用例，让初次撞见的人能读懂。

```markdown
# Realtime Tick Data

本项目不支持 tick 级实时行情采集。

## 为什么不在范围内

本项目专注**日级 / 分钟级周期数据 + 离线回测**。
支持 tick 级会要求：

- 实时 socket / WebSocket 连接管理（当前架构是定时拉取）
- ms 级延迟的写入路径（PostgreSQL 不是 tick 存储的最佳选择）
- 一套全新的数据质量校验维度（ts 顺序、跳秒、broker 端去重）

这是显著的架构变更，与项目"日终 / 周末做研究 + 回测"的定位不符。
tick 采集留给下游交易系统（VNPY / 交易所直连）。

```python
# 当前 BaseCollector 的接口设计前提是定时离散调用：
class BaseCollector:
    def fetch_daily(symbol: str, date: str) -> pd.DataFrame: ...
# tick 流要求的是订阅 + 回调，根本不适合塞进这个抽象。
```

## 已有请求

- 「想加分时 tick 数据」(2025-Q3 对话记录)
- 「能不能秒级采集？」
```

### 文件命名

短、描述性、kebab-case：`ui-frontend.md` / `realtime-tick.md` / `futures-support.md`。名字应让人翻目录时**不打开就大致知道**被拒绝的是什么。

### 写理由

理由要**实质**——不是"我们不想要"，而是**为什么**。好的理由引用：

- 项目范围 / 哲学（"本项目专注 X；Y 是下游的事"）
- 技术约束（"支持这个会要求 Y，与 Z 架构冲突"）
- 战略决策（"我们选 A 而不是 B 是因为..."）

理由要**耐久**。避免临时情境（"现在太忙了"）——那不是真拒绝，是**延后**。

## 何时检查 `out-of-scope/`

分诊期间（步骤 1：收集上下文），读所有文件。评估新 issue 时：

- 检查是否匹配既有概念。
- 匹配按**概念相似**判断，不是关键词——"分时数据"匹配 `realtime-tick.md`。
- 匹配就给维护者：「这与 `docs/out-of-scope/realtime-tick.md` 类似——之前因为 [理由] 被拒绝。仍坚持吗？」

维护者可：

- **确认** —— 新 issue 加到既有文件的"已有请求"，关闭。
- **重新考虑** —— 删除或更新文件，issue 走正常分诊。
- **不同意** —— issue 相关但不同，走正常分诊。

## 何时写到 `out-of-scope/`

**只在 enhancement（不是 bug）被 wontfix 时**。流程：

1. 维护者决定功能请求超出范围。
2. 检查是否已有匹配文件。
3. 有：把新 issue 加到"已有请求"。
4. 没有：建新文件，写概念名、决策、理由、第一条已有请求。
5. issue 上发评论解释决策，链到 `out-of-scope/` 文件。
6. 关闭 issue 并打 wontfix 标签。

## 改主意 / 删除

如果维护者改变对某概念的判断：

- 删 `out-of-scope/` 文件。
- skill 不需要重开旧 issue ——它们是历史记录。
- 触发重新考虑的新 issue 走正常分诊。
