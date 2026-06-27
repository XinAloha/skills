---
description: 一次性原型答疑 - 逻辑分支（终端交互）/ UI 分支（多变体路由）
type: methodology
parent: dev-guidelines.md
auto_execution_mode: 2
source: Matt Pocock skills - engineering/prototype
adapted-for: A 股量化数据采集系统 (Python / pytest / PostgreSQL)
---

# Prototype - 原型

> 触发：用户希望"原型一下 / 让我玩玩 / 试几种设计 / sanity-check 数据模型 / 试试这个状态机"。

原型 = **回答一个问题的一次性代码**。**问题决定形状**。

## 选分支

识别要回答的问题——从用户提示、周围代码，或问用户：

- **「这个逻辑 / 状态模型对吗？」** → [LOGIC.md](LOGIC.md)。一个能驱动状态机的小型交互式终端 app。
- **「这个应该长什么样？」** → [UI.md](UI.md)。同一路由上几个根本不同的 UI 变体，floating bar 切换。

> 本项目以 Python 后端为主，**默认 LOGIC 分支**。UI 分支在做"回测可视化界面"等少数场景才用。

两个分支产出非常不同的产物——**搞错就废了整个原型**。如果问题真的歧义、用户不在场，按周围代码默认分支（后端模块 → 逻辑；页面 / 组件 → UI），并在原型顶部声明假设。

## 对两个分支都适用的规则

1. **从第一天起就是一次性的，并且**显眼地**标注**。把原型代码放在它将来真正会用到的地方旁边（紧邻目标模块或页面），上下文一目了然——但**命名要让随手翻代码的人立刻看出这是原型**。本项目用 `prototype_*.py` 前缀或放进 `scripts/prototypes/`。
2. **一条命令能跑**。本项目用 `python scripts/prototypes/<name>.py`。用户开起来不需要思考。
3. **默认无持久化**。状态住内存。持久化是原型**要检验**的东西，不该被原型依赖。如果问题就是关于数据库——用临时 SQLite 文件，名字带"PROTOTYPE — wipe me"。
4. **跳过抛光**。**不要写测试**、不要写超出"能跑"的错误处理、不要抽象。**学到东西然后删掉**。
5. **暴露状态**。每次动作（逻辑）后或每次切换变体（UI）后，**打印 / 渲染整段相关状态**，让用户看到改了什么。
6. **完成后删除或吸收**。原型答完问题，**要么删，要么把验证过的决策折回真实代码**——别让它在 repo 里腐烂。

## 完成后

原型唯一值得留下的是**答案**。捕获到耐久的位置（commit message、ADR、issue、原型旁的 `NOTES.md`），写下问题与答案。如果用户在场，那就一段对话；如果不在场，留占位符让他们（或下次的你）填，**填完再删原型**。

## 本项目典型原型问题

### 逻辑（LOGIC 分支）

- "采集失败的重试 + 降级状态机我想清楚了吗？"——做一个终端 app，按键 `f` 模拟 Tushare 失败、`a` AKShare 失败、`d` adata 失败、`r` 重试；屏幕上显示当前状态机状态。
- "全量历史回填 + 增量日更的去重逻辑——边界对吗？"——做一个 reducer，操作 `fill 2015-2024`、`daily 20260615`、`re-fill 2024-04`，看最终 DataFrame。

### UI（UI 分支）

- "回测报告页面——我想看 3 种布局"。Streamlit / Dash 上 3 个变体路由，floating bar 切换。

## 相关 skill

- [reference-analysis](../../governance/reference-analysis.md) - 看参考项目时有时也能直接做原型
- [reusable-patterns](../../engineering/reusable-patterns.md) - 验证过的逻辑可入沉淀模式库
- [tdd](../tdd/SKILL.md) - 原型答完问题后用 TDD 重写
- [grill-with-docs](../grill-with-docs/SKILL.md) - 不能用原型回答的问题，去质询
