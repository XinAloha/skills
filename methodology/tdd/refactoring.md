# 重构候选

TDD 一轮 GREEN 之后找：

- **重复** → 抽函数 / 类。
- **长方法** → 拆成私有 helper（测试仍走公开接口）。
- **浅模块** → 合并或深化（见 [deep-modules.md](deep-modules.md)）。
- **特性嫉妒**（一个模块大量调用另一个模块的数据）→ 把逻辑挪到数据所在地。
- **原始类型痴迷**（到处用 str / dict 表示领域概念）→ 引入值对象。
- **新代码暴露的既有代码问题**——顺手记录、必要时单独提 issue。

## 本项目常见重构

- 多个采集器都在重复"重试 + 限流 + 错误转换"逻辑 → 抽一个 `RateLimitedClient` mixin 或装饰器。
- 多处 `dict["close"]` / `dict["pct_chg"]` → 引入 `KlineRecord` dataclass（仅在内部边界，DataFrame 仍是首选 IO 类型）。
- `data_collection.utils.helpers` 累积成大杂烩 → 按主题拆（`time_utils.py` / `trading_calendar.py`）。

## 与既有 skill 联动

- [refactoring-checklist](../../governance/refactoring-checklist.md) - 完整重构检查清单（分析 / 提取 / 重构三阶段）。
- [improve-codebase-architecture](../improve-codebase-architecture/SKILL.md) - 找系统级深化机会。
- [reusable-patterns](../../engineering/reusable-patterns.md) - 已沉淀的可复用模式库。
