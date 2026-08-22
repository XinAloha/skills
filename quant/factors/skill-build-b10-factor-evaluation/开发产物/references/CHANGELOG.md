# build-b10-factor-evaluation 变更日志

V2 规则 §13：BUILD 逻辑变更必须更新版本号和 `data_version`。本文件按时间倒序记录每次有外部影响的改动。

## 1.5.0 — 2026-06-07（编号重分配：B01 → B10）

### 编号变更
- BUILD 编号从 ``B01`` 重命名为 ``B10``。所有对外暴露的 BUILD ID 全部更新：
  - ``constants.py`` 的 ``BUILD_ID`` 从 ``"B01"`` 改为 ``"B10"``
  - ``skill.json`` 的 ``build_id`` / ``name`` 从 ``B01`` / ``build-b01-factor-evaluation`` 改为 ``B10`` / ``build-b10-factor-evaluation``
  - 所有 ``.py`` 文件的 docstring、日志标识符（``b01.factor_evaluation`` → ``b10.factor_evaluation``、``b01.daily_runner`` → ``b10.daily_runner``）、测试断言中的 ``build_id == "B01"`` → ``"B10"``
  - ``demo.py`` / ``daily_runner.py`` 的默认 ``target_id`` / ``data_version`` 中的 ``b01`` 片段替换为 ``b10``
  - 两份 ``SKILL.md``（开发 + 生产）的 ``name`` 前缀、文档正文中所有 ``B01`` → ``B10``
  - ``api_guide.md`` 的 ``build_id`` 示例值、桥接模块引用（``a01_b01_bridge.py`` → ``a01_b10_bridge.py``）、命令行示例中的 ``--data-version`` / ``--log-file``
  - ``FILE_MANIFEST.md`` / ``HOW_TO_DEMO.md`` 同步更新

### data_version 影响
- 生产 Parquet 中新写入的记录 ``build_id`` 字段为 ``B10``；旧记录仍保留原 ``B01`` 值。
- 下游按 ``build_id`` 查询的 agent / Alpha 需同时兼容 ``B01`` 和 ``B10``，或在过渡期后只查 ``B10``。
- ``result_json`` 内部结构、``result_value`` 口径、所有评估指标完全不变。

### 兼容性
- 对外 API（``run / write_production / write_report / validate_input`` 等）签名与返回结构不变。
- 模块级 logger 名称变更（``b01.*`` → ``b10.*``），如有外部代码按 logger 名过滤需同步更新。

## 1.4.1 — 2026-06-07（最终交付清理）

### 工程清理（不影响对外 API）
- 删除 `metrics.compound_forward_return` / `metrics.compound_target` 两个孤儿函数（``decay_curve`` 已 inline 复利逻辑，全项目无调用方）。
- 删除 `metrics.py` 顶部对 `stats.transaction_cost_adjusted_ls` 的未使用 import（真正调用方在 `stats.cost_sweep` 内部）。
- 删除 `neutralize.py` 中只挂 `NullHandler` 而无任何调用的 logger（连 `import logging` 一并清掉）。
- 简化 `demo.py::main` 的死分支 `argv if argv is None else _parse_args()`。
- 删除 `tests/test_run_metrics.py` 未使用的 `import numpy as np`。
- `visual_report.py` 收紧 re-export 表面：`BUILD_NAME / CHART_COLORS / STOCK_POOL_LABELS / json_safe / safe_float / validate_input / make_report / validate_config` 8 个外部从未通过 `visual_report.<name>` 引用的符号从转发表移除；保留 `visual.* / metrics.compute_panel_base / metrics.apply_layer`（最后两个是测试 monkeypatch 入口）。

### 注释与文档
- 把 `__init__.py / build.py / stats.py` 中残留的英文 docstring 与英文章节注释翻成中文（HTML 报告里的 SVG 图表标题保留英文，便于科研出图，不属于"代码注释"）。
- `skill.json` `version` 从 1.3.0 抬到 1.4.0，与 CHANGELOG 顶条对齐。
- `生产产物/SKILL.md`：`write_production` 签名补 `mode="overwrite" | "append"`，与 `build.py` 真实签名一致。
- `开发产物/SKILL.md` + `api_guide.md`：代码结构表补 `__init__.py`；配置表补 `industry_level`；bootstrap 章节补"`target_kind=binary_success` 时跳过"。
- 1.4.0 条目里"全部 11 个真实文件" 改为 "13 个真实 .py 文件 + visual/ / tests/ 子包"。

### 交付包
- 新增 `scripts/demo.py`（合成因子一键演示）、`HOW_TO_DEMO.md`（演示话术）、`FILE_MANIFEST.md`（文件清单）。
- `.gitignore` 补 `开发产物/demo_output/`。

## 1.4.0 — 2026-06-07

### 红线（A01/B10 边界）
- **彻底切除 B10 联网能力**。删除 `scripts/panda_data_adapter.py`；从 `neutralize.py` 移除 `init_session / fetch_industry_panel_from_panda / fetch_style_panel_from_panda`。`apply_neutralization` 在 `neutralize=True` 但未提供 `industry_panel` / `style_panel` 时直接抛 `ValueError`，不再静默回退到任何在线接口。原"B10 在中性化时主动调 `panda_data.init_token` 拉行业/风格"的行为打脸 SKILL 的"不直接拉取"承诺，本版本把代码与文档对齐到红线原文。新增 `tests/test_research_diagnostics.test_neutralization_without_supplied_panels_raises` 锁住该行为。
- 行业/风格暴露面板的获取移到根目录桥接层职责。如果你之前依赖 B10 自己拉数，需要在调用 B10 前在桥接脚本里准备好 `industry_panel` / `style_panel` 并传入 `config`。

### 工程拆分
- `metrics.py` 拆出 `research_diagnostics.py`：6 个 V7 研究函数（`component_ic / component_bins / reverse_factor / state_segments / monthly_stability / return_target_comparison`）+ `RESEARCH_RETURN_TARGETS` 全部下沉。`metrics.py` 保留 reexport 兼容旧 import（`from metrics import make_research_diagnostics` 仍可用）。
- `visual_report.py` 拆为 `visual/` 子包三层：`svg_charts.py`（纯 SVG 工具）/ `sections.py`（report → HTML 章节）/ `document.py`（HTML 文档组装）。原 `visual_report.py` 收为薄重导出层。
- `test.py` 拆为 `tests/` 子目录五份（`test_data_io / test_run_metrics / test_visual_report / test_research_diagnostics / test_write_production`）+ 共享 `fixtures.py`。顶层 `test.py` 改为聚合入口，等价于 `python -m pytest scripts/tests`，向后兼容 `python scripts/test.py`。

### 性能与一致性
- `metrics.daily_ic` 改为完全向量化（与 `daily_spearman_series` 共用 `_pairwise_corr_per_day` 闭式公式），千日级面板上比原 Python loop 快 5–20×。
- `stats._spearman_per_day` 不再独立实现，统一调 `metrics.daily_spearman_series`（保留同名薄壳兼容旧 import）。三份独立 Spearman 实现归并为单一来源。
- 修复 `_factor_summary` 的分组数不一致 bug：原 `component_ic_analysis` 写死 5、`reverse_factor_analysis` 用 `group_count`、`state/monthly/return_target_comparison` 用 `min(5, group_count)`，导致同一 result_json 内子表分组数不齐。修正后所有研究表统一按 `config["group_count"]` 出表。

### 收口与精简
- `factor_reverse` 二义性收口：从 `data_io.DIAGNOSTIC_OPTIONAL_COLUMNS` 移除 `factor_reverse`（原本作为可选输入列保留，与 `reverse_factor_analysis` 用 `-factor_value` 重算冲突）。`reverse_factor_analysis` 始终自造反向因子，不再读上游字段。如果调用方面板里仍有 `factor_reverse` 列，会被 `research_component_columns` 当作 sub-factor 走 `component_ic`，与反向检验通道清晰分离。
- 删除 `build.py` 顶部的 `__main__` demo block：与 `tests/fixtures.make_sample` 同质且不能保证回归。`python scripts/build.py` 现在只打印一行使用说明，引导到 `test.py` 或 `daily_runner.py`。
- `daily_runner.py` 不再"`write_production` + `write_report`"两次跑 evaluate：一次 `make_report` → 同时构造 BUILD schema 行 upsert 写库 + `render_html_report` 渲染 HTML。
- `.gitignore` 补 `.claude/settings.local.json` / `.pytest_cache/` / `.mypy_cache/` / `.ipynb_checkpoints/`。`build track/.claude/settings.local.json` 中含开发机盘符（`E:\量枢院\...`）的允许项已清空为相对路径与帮助命令。

### 文档
- `SKILL.md`：代码结构表覆盖到全部 13 个真实 .py 文件 + `visual/` / `tests/` 子包；`result_json` 章节补 `bootstrap_baseline / transaction_cost / neutralization / research_diagnostics` 4 块输出；显式声明 "B10 不联网"。
- `references/api_guide.md`：模块职责表对齐当前结构；中性化章节移除"否则需要 PANDA_DATA_USERNAME/PASSWORD"的旧描述；配置表新增 `neutralize_industry / research_diagnostics / return_targets / enable_*_selector`。
- 新增 `scripts/demo.py` 一键演示入口（合成 60 天 × 200 股因子，不联网，跑全链路），新增 `build track/build-b10-factor-evaluation/HOW_TO_DEMO.md` 演示话术；`SKILL.md` 代码结构表 + 运行命令章节同步更新；`tests/test_write_production.test_demo_panel_is_valid_b10_input` 锁住 demo 面板的合法性与 RankIC 显著性。

### data_version 影响
- **不影响** `result_value` 与 `result_json` 主结构（IC/分层/换手/衰减口径均不变）。研究层各表 `group_count` 从混合 5/10/min(5,10) 统一为 `config["group_count"]`，**会改变 sub-factor 表的分组数**——如果旧 result_json 的 `research_diagnostics.state_segments` 等字段下游有用，重新评估时建议覆盖（`mode="overwrite"`）。
- 新增子模块 import 路径：`from research_diagnostics import ...` / `from visual import ...` / `from tests.fixtures import make_sample`，旧路径仍兼容。

## 1.3.0 — 2026-06-05

### 数据质量
- `validate_input` 对 `forward_return_{n}d` 多周期收益列执行严格数值校验；非数字、NaN 伪装值和 Inf 不再静默转成缺失。
- `validate_input` 拒绝空白 `ts_code`，避免空标的代码进入主键、股票池筛选和分层回测。
- `validate_output` 将 `trade_date`、`target_id`、`source_data_date` 纳入非空校验，生产查询主键和溯源字段不再允许空字符串。

### 指标语义
- `transaction_cost.sweep` 改为显式 opt-in：只有配置 `cost_grid_bps` 时才输出交易成本敏感性扫描；空配置不再隐式生成 0bps 行。
- `bootstrap_n` 和传入式中性化面板新增测试覆盖，确保高级诊断可复现且不强依赖在线 PandaAI data。

### 调度
- `daily_runner.py` 在 `mode="append"` 返回合并后全库时，会按本次 `target_id/result_type` 选择当前记录生成日志与 HTML 文件名，避免误取全库最后一行。

### 工程
- 删除 `scripts/make_demo.py`，演示视频改为人工录制流程；保留 `demo.mp4` 文件本身不处理。
- 收紧 `python scripts/build.py` 的命令行演示输出，只打印标准摘要字段和 `result_json` 长度。

### data_version 影响
- 默认 `data_version` 从 `factor-eval-v1` 更新为 `factor-eval-v1.3`。
- `result_value` 口径不变；默认 `result_json.transaction_cost.sweep` 从旧版隐式 0bps 行变为空列表，依赖该字段的下游应显式传入 `cost_grid_bps`。
- 旧数据可以继续读取；重新评估时建议使用新版默认或调用方自定义版本号。

## 1.2.0 — 2026-06-04

### 性能
- `metrics.make_report` 内部拆分为 `compute_panel_base` + `apply_layer`：
  - `compute_panel_base` 一次性算 `daily_ic` / `ic_time_analysis` / `ic_distribution` / `factor_distribution` / `factor_rank_autocorrelation` / `turnover` / `decay_curve`，这些与 `group_count` 无关。
  - `apply_layer` 只重算 `layer_backtest` / `make_research_diagnostics` / `quality_warnings` / `quality_checklist`（依赖 `group_count`）。
- `visual_report.make_group_reports`：每个 stock_pool 调一次 `compute_panel_base`，五分组/十分组共享 base 各跑一次 `apply_layer`。原先 N×2 次完整 `make_report` → N 次 base + 2N 次 layer。
- 实测（60 天 × 200 资产 × 5 stock_pool × 2 group_mode）：`make_group_reports` 22.6s → 14.7s（**-35%**）。

### 兼容性
- 对外 API 完全不变：`run / make_report / write_report / write_production / render_report_html / make_group_reports` 签名与返回值一致。
- 拆分前后报告 JSON 按位等价，由新增 `test_make_report_equivalent_to_split_path` 覆盖（含切到不同 group_count 后 base 缓存字段必须复用、layer 字段必须重算）。
- 复用次数由 `test_make_group_reports_reuses_panel_base` 用计数器锁住：base 调用次数 == pool 数；apply_layer 调用次数 == pool×mode。

### data_version 影响
- 不影响：`result_value`、`result_json` 内容与 1.1.x 完全一致。沿用现有 `data_version` 累积即可，无需重跑历史。

## 1.1.0 — 2026-06-04

### 新增
- `scripts/daily_runner.py`：命令行调度入口，支持 `--input/--target-id/--stock-pool/--mode/--report-dir/--log-file`。
- `write_production` 增加 `mode="append"`，按主键 `(trade_date, build_id, target_id, result_type)` upsert，原子写（tmp → replace）。
- 模块级 logger `b10.factor_evaluation`，库默认 NullHandler，`daily_runner` 设置文件/stderr 日志。
- `skill.json` 扩展 schema：`inputs/outputs/production_artifact/compatible_with/changelog/scheduler`。
- `references/CHANGELOG.md`（本文件）。

### 修复（兼容性向后兼容）
- `validate_output`：`result_value` 等数值字段 NaN/Inf 不再被静默通过，统一抛 `ValueError`。
- `layer_backtest.monotonicity.direction`：原来硬编码 `"increasing"`，现按 `resolved_factor_direction` 输出 `"increasing"` 或 `"decreasing"`。
- `resolve_columns`：`config["columns"]` 严格校验非字符串、目标重复、与已有列冲突，立即报错而非静默忽略。

### 文档
- `SKILL.md`：换手率 tie-break 规则显式声明。

### 工程
- 新增 `.gitignore` 覆盖 `__pycache__/`、`*.pyc`、临时报告与日志。
- 删除已提交到仓库的 `scripts/__pycache__/`。

### data_version 影响
- 不影响：报告 schema 与 `result_value` 含义未变。原 `factor-eval-v1` / 各调用方自定义版本仍可继续累积。
- 但若调用方在 1.0.x 写过的库里有 `direction == "increasing"` 而实际方向是 `negative`，appended 后新旧记录在该字段语义会不同。需要时可重新跑历史评估并 `mode="overwrite"`。

## 1.0.0 — 2026-05-31

### 初始上线
- BUILD 标准入口 `run(input_data, config=None)`、`validate_input`、`validate_output`、`write_production`、`write_report`、`render_report_html`。
- IC / RankIC / ICIR / 累计 IC / IC 自相关 / 因子 Rank 自相关 / 分布诊断 / 分层回测 / 单调性 / 换手率 / 衰减曲线 / 优质因子达标表 / 质量预警。
- 股票池筛选：`all_a / hs300 / zz500 / zz1000 / zz2000`。
- HTML 报告：内嵌 SVG 图表 + 五分组/十分组 + 股票池切换。
- 研究层（V7）：子因子 IC/分组、反向因子、仓位状态分段、月度稳定性、收益口径对比。
- `target_kind=binary_success` 打板接力分支。
- 模块拆分：`build/data_io/metrics/visual_report/constants/utils`。
- 测试 16 个，覆盖正常 / 空 / 缺字段 / 非法配置 / 非法数值 / 重复主键 / 方向调整 / 分组切换 / 股票池 / binary_success / research / 文件路径 / 包级 import / 小截面降级。
