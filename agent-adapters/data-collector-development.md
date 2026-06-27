---
description: 数据采集器开发规范 - 数据源适配、字段标准化、降级策略、写入边界（跨平台版）
type: sub-document
applies-to: [claude-code, codex]
auto_execution_mode: 2
---

# 数据采集器开发

> 与 `.claude` / `.codex` / `.devin` 同名 skill 保持规则一致；本文档为跨平台版，统一描述数据采集器开发流程，并在涉及实际工具调用时同时给出 Claude Code 与 Codex 的对应做法。

## 平台工具调用对照原则

除非特别标注“仅某平台适用”，本文所有流程、检查项和约束同时适用于 Claude Code 与 Codex。涉及工具时必须按下列对应关系执行，不要只写一种平台的调用方式：

| 意图 | Claude Code | Codex |
|-----|-------------|-------|
| 读取文件 | `Read: file_path="..."` | `Get-Content <path>`，或通过 `run_terminal_cmd` 执行 PowerShell `Get-Content -Raw <path>` |
| 搜索文件名 | `Glob: pattern="..."` | `rg --files | rg "..."`，或通过 `run_terminal_cmd` 执行对应命令 |
| 搜索内容 | `Grep: pattern="..." path="..."` | `rg "..." <path>`，或通过 `run_terminal_cmd` 执行对应命令 |
| 编辑现有文件 | `Edit` / `Write`（仅在完整覆盖或新建时用 `Write`） | `apply_patch`；必要时用 PowerShell 脚本辅助，但优先保持补丁可审查 |
| 运行测试/脚本 | `Bash: command="..."` | `run_terminal_cmd` 执行 PowerShell、pytest、python 或项目脚本 |
| 大范围探索 | `Agent` / `TaskCreate`（仅 Claude Code 适用；用于并行搜索或复杂调查） | 使用 `rg`、`Get-Content`、`run_terminal_cmd` 分步完成；不要伪造子代理能力 |

## 采集器职责

采集器只做三件事：

1. 调用外部数据源或 SDK。
2. 将返回结果标准化为项目字段。
3. 把可恢复错误转成清晰日志和空结果/失败状态。

采集器不直接决定全局调度顺序，不隐藏写入多个表的副作用，不读取真实 token 以外的业务配置。

## 开发前必读

在新增/修改采集器前，先读以下文件，确认注册方式、编排入口、字段约束和配置约定：

- `data_collection/collectors/__init__.py` — 采集器注册位置与导出约定
- `data_collection/core/stock_collector.py` — 编排层如何调用采集器
- 任意一个最近活跃的采集器（如 `tushare_client.py` / `akshare_daily_collector.py`）作为模板
- `data_collection/database/schema.sql` — 表结构与字段约束
- `config/default.yaml` — 限速、并发、token 名等

平台调用要求：

| 任务 | Claude Code | Codex |
|-----|-------------|-------|
| 读取必读文件 | `Read: file_path="data_collection/collectors/__init__.py"`，依次读取上述文件 | `Get-Content data_collection/collectors/__init__.py`，或 `run_terminal_cmd` 执行 `Get-Content -Raw data_collection/collectors/__init__.py`，依次读取上述文件 |
| 列举所有采集器 | `Glob: pattern="data_collection/collectors/*.py"` | `rg --files data_collection/collectors | rg "\.py$"` |
| 选择 1-2 个相近模板 | 对 `Glob` 结果中最相近文件使用 `Read` | 对 `rg --files` 结果中最相近文件使用 `Get-Content` |
| 大范围不确定定位（仅 Claude Code 可用子代理） | 可用 `Agent` / `TaskCreate` 并说明搜索目标，如“查找已有 fallback/router 和相似采集器” | 用多轮 `rg` / `Get-Content` / `run_terminal_cmd` 完成同等搜索 |

> 必须先列举现有采集器，再读取 1-2 个最相近的对照实现；不要凭记忆新增采集器结构。

## 字段标准化

新增数据源时必须定义字段映射：

```python
COLUMN_MAPPING = {
    "外部字段": "project_field",
}
```

检查项：

- [ ] DataFrame 为空时返回结构稳定的空 DataFrame。
- [ ] 日期字段统一为项目已有格式。
- [ ] 股票代码格式与现有工具一致，不在多个文件重复拼接。
- [ ] 数值字段做类型转换，无法转换时记录原因。
- [ ] 字段映射测试覆盖缺字段、额外字段、空数据。

平台调用要求：

| 任务 | Claude Code | Codex |
|-----|-------------|-------|
| 查找已有字段映射 | `Grep: pattern="COLUMN_MAPPING|rename\(|project_field" path="data_collection/"` | `rg "COLUMN_MAPPING|rename\(|project_field" data_collection/` |
| 读取相似映射实现 | `Read` 相似采集器文件 | `Get-Content` 相似采集器文件 |
| 修改字段映射 | `Edit` 精确替换；新增文件或完整覆盖时才用 `Write` | `apply_patch` 修改对应片段 |
| 运行字段映射测试 | `Bash: command="pytest <test_path>"` | `run_terminal_cmd` 执行 `pytest <test_path>` |

字段标准化规则：

- 外部 API 字段名只能在采集器边界层出现，进入项目内部前必须转换为项目字段。
- 缺字段必须显式处理：能降级的记录日志并返回稳定结构，不能降级的让数据质量测试失败。
- 额外字段不得直接透传到数据库层；确需保留时先更新 schema、文档和测试。
- 日期、股票代码、数值类型转换必须复用项目已有工具；新增工具前先搜索是否已有实现。
- 搜索已有工具：Claude Code 用 `Grep: pattern="format.*code|normalize.*code|trade_date|to_datetime" path="data_collection/"`；Codex 用 `rg "format.*code|normalize.*code|trade_date|to_datetime" data_collection/`。

## 降级策略

多源逻辑优先集中在已有 fallback/router 组件中：

| 情况 | 推荐处理 |
|-----|---------|
| 主源限流 | 指数退避或限速器 |
| 主源返回空 | 判断是合法空数据还是源异常 |
| 主源字段变化 | 数据质量测试失败，禁止静默吞掉 |
| 备用源启用 | 日志记录源切换和原因 |
| 所有源失败 | 返回明确失败状态，不伪造成功 |

每次新增“降级路径”前，必须先扫已有统一组件：

| 任务 | Claude Code | Codex |
|-----|-------------|-------|
| 搜索 fallback/router/降级 | `Grep: pattern="fallback|router|降级" path="data_collection/"` | `rg "fallback|router|降级" data_collection/` |
| 读取已有组件 | `Read` 命中的 fallback/router 文件 | `Get-Content` 命中的 fallback/router 文件 |
| 接入已有组件 | `Edit` 修改现有 router/fallback 注册或调用点 | `apply_patch` 修改现有 router/fallback 注册或调用点 |
| 验证降级行为 | `Bash: command="pytest <fallback_test_path>"` | `run_terminal_cmd` 执行 `pytest <fallback_test_path>` |

> 如果已有 fallback/router 组件，就接进去；不要新写一份。只有确认没有统一组件且当前需求确实需要时，才新增降级抽象。

降级实现要求：

- 主源限流时优先复用已有限速器或指数退避实现，不在采集器里散落 `sleep` 常量。
- 主源返回空数据时必须区分“交易日无数据/查询范围为空”等合法空结果与“接口异常/字段变化”等源异常。
- 主源字段变化必须让数据质量测试失败，禁止通过宽泛 `try/except` 静默吞掉。
- 备用源启用时日志必须包含主源名称、备用源名称、切换原因和请求关键参数。
- 所有源失败时返回明确失败状态或稳定空结果，不伪造成功、不写入半成品数据。

## 数据库写入边界

- 写入逻辑优先放在 `core/` 或 `database/` 层。
- 表结构变更必须同步 `schema.sql`、数据库文档和数据质量测试。
- 批量写入应复用 `StreamInserter` 或现有 backend 能力。
- 所有写入路径必须考虑唯一键、重复记录和部分失败。

平台调用要求：

| 任务 | Claude Code | Codex |
|-----|-------------|-------|
| 修改 schema 前读取表结构 | `Read: file_path="data_collection/database/schema.sql"` | `Get-Content data_collection/database/schema.sql`，或 `run_terminal_cmd` 执行 `Get-Content -Raw data_collection/database/schema.sql` |
| 查找数据库文档 | `Glob: pattern="docs/database_documentation*.md"` | `rg --files docs | rg "database_documentation.*\.md$"` |
| 查找批量写入能力 | `Grep: pattern="StreamInserter|insert.*batch|bulk|backend" path="data_collection/"` | `rg "StreamInserter|insert.*batch|bulk|backend" data_collection/` |
| 修改 schema/文档/测试 | `Edit`；完整新增文件时才用 `Write` | `apply_patch` |
| 运行数据库或数据质量测试 | `Bash: command="pytest <db_or_quality_test_path>"` | `run_terminal_cmd` 执行 `pytest <db_or_quality_test_path>` |

新增表/字段时，必须按 `docs/database_documentation*.md` 的格式同步文档，并补充数据质量测试。不得只改采集器而跳过 schema、文档或测试。

写入边界规则：

- 采集器可以返回标准化 DataFrame/对象，但不应直接隐藏多表写入副作用。
- 唯一键冲突、重复记录、部分失败必须有明确处理路径和测试覆盖。
- 批量写入优先复用 `StreamInserter` 或现有 backend；新增写入器前先搜索确认没有可复用能力。
- schema 变更必须同时覆盖迁移/初始化脚本、数据库文档和数据质量测试。

## 新采集器最小清单

- [ ] `data_collection/collectors/xxx_collector.py`
- [ ] 必要时更新 `data_collection/collectors/__init__.py`
- [ ] 单元测试：成功、空数据、API 异常、字段缺失、类型转换
- [ ] 集成测试：只在确实需要真实 API 时标记 network/slow
- [ ] 文档：README 或 `docs/core_features.md`
- [ ] 配置：`config/default.yaml` 和 `.env.example` 中的新增项

平台调用要求：

| 任务 | Claude Code | Codex |
|-----|-------------|-------|
| 新建采集器文件 | `Write: file_path="data_collection/collectors/xxx_collector.py"`（仅新文件） | `apply_patch` 新增 `data_collection/collectors/xxx_collector.py` |
| 更新导出/注册 | `Edit: file_path="data_collection/collectors/__init__.py"` | `apply_patch` 修改 `data_collection/collectors/__init__.py` |
| 查找测试目录和命名 | `Glob: pattern="tests/**/*collector*.py"` 或 `Glob: pattern="test/**/*collector*.py"` | `rg --files tests test | rg "collector.*\.py$|test_.*collector.*\.py$"` |
| 新增/修改测试 | `Edit` / 新文件用 `Write` | `apply_patch` |
| 更新配置 | `Edit` 修改 `config/default.yaml` 和 `.env.example` | `apply_patch` 修改 `config/default.yaml` 和 `.env.example` |
| 运行最小测试集 | `Bash: command="pytest <unit_test_path>"`；必要时再跑相关集成测试 | `run_terminal_cmd` 执行 `pytest <unit_test_path>`；必要时再跑相关集成测试 |

新增采集器执行顺序：

1. 读取必读文件和相似采集器。
2. 确认字段映射、日期格式、代码格式、数值转换规则。
3. 确认是否已有 fallback/router、限速器、写入器可复用。
4. 实现采集器，保持职责单一。
5. 更新 `data_collection/collectors/__init__.py` 注册或导出。
6. 补充单元测试：成功、空数据、API 异常、字段缺失、类型转换。
7. 仅在确实需要真实 API 时补充 network/slow 集成测试，并保证普通测试不依赖真实网络。
8. 若新增配置，同步 `config/default.yaml` 和 `.env.example`。
9. 若新增/修改表字段，同步 `schema.sql`、数据库文档和数据质量测试。
10. 运行最小相关测试集，并记录失败原因或跳过原因。

## 通达信（pytdx）专项

本项目计划集成通达信免费数据源，遵循以下额外约束：

- pytdx 行情 IP 列表必须可配置（`config/default.yaml`），不在代码硬编码。
- `.day` / `.lc1` / `.lc5` 二进制解析逻辑放在 `data_collection/utils/tdx_parser.py`，不放采集器内。
- 通达信日 K 与 Tushare/AKShare 写同一张 `daily_kline` 表前，必须做交叉校验测试（`test/data_quality/test_tdx_vs_tushare.py`）。
- 通达信路径（如 `D:/Sofeware/TongDaXin`）只能从配置读取，不写死在代码里。
- 离线读 `.day` 文件时使用 `pathlib.Path`，不要拼字符串路径。

平台调用要求：

| 任务 | Claude Code | Codex |
|-----|-------------|-------|
| 查找通达信/pytdx 现有实现 | `Grep: pattern="pytdx|通达信|tdx|\.day|\.lc1|\.lc5" path="data_collection/"` | `rg "pytdx|通达信|tdx|\.day|\.lc1|\.lc5" data_collection/` |
| 读取/新增解析工具 | `Read` / 新文件用 `Write: file_path="data_collection/utils/tdx_parser.py"` | `Get-Content` / `apply_patch` 新增或修改 `data_collection/utils/tdx_parser.py` |
| 更新配置 | `Edit: file_path="config/default.yaml"`，必要时更新 `.env.example` | `apply_patch` 修改 `config/default.yaml`，必要时更新 `.env.example` |
| 增加交叉校验测试 | `Write` 或 `Edit: file_path="test/data_quality/test_tdx_vs_tushare.py"` | `apply_patch` 新增或修改 `test/data_quality/test_tdx_vs_tushare.py` |
| 运行交叉校验测试 | `Bash: command="pytest test/data_quality/test_tdx_vs_tushare.py"` | `run_terminal_cmd` 执行 `pytest test/data_quality/test_tdx_vs_tushare.py` |

通达信专项补充规则：

- pytdx 行情 IP 列表、通达信本地路径和启用开关都必须来自配置；代码中不得出现硬编码默认路径或固定 IP 列表。
- `.day` / `.lc1` / `.lc5` 解析逻辑属于通用工具层，采集器只负责调用和标准化结果。
- 离线路径处理统一使用 `pathlib.Path`，不得用字符串拼接 Windows 路径。
- 写入 `daily_kline` 前必须通过与 Tushare/AKShare 的字段、日期、代码和价格精度交叉校验。

## Claude Code 子代理与任务拆分（仅 Claude Code 适用）

当需要跨多个目录确认采集器、fallback/router、schema、配置和测试时，可用 `Agent` / `TaskCreate` 做只读并行调查，但最终修改仍由主流程完成并复核。

建议用法：

| 场景 | Claude Code 调用 | Codex 对应做法 |
|-----|------------------|----------------|
| 搜索相似采集器 | `Agent` / `TaskCreate`: “查找 data_collection 下与 <数据源/频率> 最相近的采集器和测试” | 用 `rg --files`、`rg "<数据源>|collector|daily_kline"`、`Get-Content` 分步完成 |
| 搜索统一降级组件 | `Agent` / `TaskCreate`: “查找 fallback/router/限速器实现和调用点” | 用 `rg "fallback|router|rate|limit|限速|降级" data_collection/` |
| 搜索写入路径 | `Agent` / `TaskCreate`: “查找 StreamInserter、批量写入和 daily_kline 写入路径” | 用 `rg "StreamInserter|daily_kline|insert|bulk" data_collection/` |

约束：

- 子代理只用于调查和归纳，不替代主流程的最终阅读和判断。
- 子代理返回结论后，主流程仍需用 `Read` 打开关键文件确认。
- Codex 不使用子代理概念；必须用显式 `rg` / `Get-Content` / `run_terminal_cmd` 保持可追踪。

## 常见反模式

- 在 `daily_job.py` 里直接写具体数据源优先级。
- 一个函数同时采集股票列表、日 K、复权因子和概念板块。
- 外部 API 字段名直接穿透到数据库层。
- 测试依赖真实网络才能通过。
- 捕获 `Exception` 后只打印日志并继续伪装成功。
- 通达信路径写死在采集器构造函数默认值中。

反模式排查工具调用：

| 反模式 | Claude Code | Codex |
|-------|-------------|-------|
| 调度层硬编码数据源优先级 | `Grep: pattern="tushare|akshare|tdx|pytdx|fallback|priority" path="data_collection/"` 后重点读 `daily_job.py` | `rg "tushare|akshare|tdx|pytdx|fallback|priority" data_collection/` 后 `Get-Content` 重点文件 |
| 单函数职责过大 | `Grep: pattern="def .*collect|class .*Collector" path="data_collection/collectors/"` 并 `Read` 可疑文件 | `rg "def .*collect|class .*Collector" data_collection/collectors/` 并 `Get-Content` 可疑文件 |
| 外部字段穿透数据库 | `Grep: pattern="外部字段名|COLUMN_MAPPING|to_sql|insert" path="data_collection/"` | `rg "外部字段名|COLUMN_MAPPING|to_sql|insert" data_collection/` |
| 测试依赖真实网络 | `Grep: pattern="requests|akshare|tushare|pytdx|network|slow" path="test/ tests/"` | `rg "requests|akshare|tushare|pytdx|network|slow" test/ tests/` |
| 宽泛异常伪成功 | `Grep: pattern="except Exception|return .*True|return .*empty|logger\.error" path="data_collection/collectors/"` | `rg "except Exception|return .*True|return .*empty|logger\.error" data_collection/collectors/` |
| 通达信路径硬编码 | `Grep: pattern="TongDaXin|通达信|D:/|C:/|tdx" path="data_collection/ config/"` | `rg "TongDaXin|通达信|D:/|C:/|tdx" data_collection/ config/` |

发现反模式后，优先复用已有工具层、配置层、fallback/router 和数据库写入层；不要在采集器内部用局部补丁掩盖架构问题。
