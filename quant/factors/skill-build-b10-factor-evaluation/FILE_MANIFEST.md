# B10 交付包 — 文件清单与作用说明

> 最终交付版本：**v1.5.0（2026-06-07）**
> 测试：**38/38 通过**；红线 grep（panda_data 调用 / 硬编码盘符 / 跨 track import）**全部 0 命中**。

下表覆盖交付包内**全部 37 个文件**。每个文件标明其在 BUILD 体系里的作用、删了会怎样。

---

## 顶层（B10 子项目根目录）

| 文件 | 作用 | 是否必需 |
|---|---|:---:|
| `.gitignore` | 排除 `__pycache__/`、`*.pyc`、`reports/` 临时文件、`demo_output/`、`.claude/settings.local.json` 等不入库内容 | 必需 |
| `HOW_TO_DEMO.md` | 给评审/同事看的演示话术：测试 → 一键演示 → 看 HTML → 红线复检的 5 分钟流程 | 必需 |
| `FILE_MANIFEST.md` | 本文件：交付包文件清单与作用说明 | 必需 |

## 开发产物 / 顶层

| 文件 | 作用 | 是否必需 |
|---|---|:---:|
| `开发产物/SKILL.md` | BUILD 主说明书：定位、输入输出、`result_json` 全部模块说明、HTML 报告、调用方式、代码结构、配置项、依赖、股票池模块、运行测试与一键演示命令 | **必需** |
| `开发产物/skill.json` | BUILD 元数据（version=1.4.1、entrypoint、inputs/outputs schema、生产 Parquet 路径、scheduler 路径） | **必需** |
| `开发产物/demo.mp4` | 人工录制的演示视频（706 KB），不通过代码生成 | 可选 |

## 开发产物 / references（参考资料）

| 文件 | 作用 | 是否必需 |
|---|---|:---:|
| `references/api_guide.md` | API 详细文档：数据来源说明、PandaAI 桥接接入方式、标准入口签名、模块职责表、配置项详解、HTML 报告章节说明、命令行调度示例、异常行为 | **必需** |
| `references/CHANGELOG.md` | 按时间倒序的版本变更日志（最新 1.4.1 → 1.4.0 → 1.3.0 → 1.2.0 → 1.1.0 → 1.0.0），每版列出红线/工程拆分/性能/收口/文档影响 | **必需** |
| `references/sample_factor.csv` | 演示输入样本（12 MB，全 A 股若干日因子面板），可被 `tests/test_run_metrics.test_run_accepts_file_path` 直接读 | **必需** |
| `references/sample_factor.close_to_close_untradable.csv` | 历史口径对比样本（close-to-close 不可交易收益），保留用于回归 | 可选 |
| `references/sample_factor.legacy.csv` | 旧 schema 对照样本（683 字节），证明字段映射兼容老版本 | 可选 |

## 开发产物 / reports（HTML 报告输出位置）

| 文件 | 作用 | 是否必需 |
|---|---|:---:|
| `reports/.gitkeep` | 占位文件，让空的 `reports/` 目录被 git 跟踪；实际 HTML 报告产物在 `.gitignore` 排除范围内 | 必需 |

## 开发产物 / scripts（核心代码）

### 主入口与编排

| 文件 | 作用 | 行数 |
|---|---|---:|
| `scripts/__init__.py` | `scripts` 包标记（一行 docstring），使 `from scripts.build import run` 这种外部调用可用 | 1 |
| `scripts/build.py` | **BUILD 标准入口**：`run(input_data, config)` 跑一次评估、`validate_input/validate_output` 输入输出校验、`write_production` 写生产 Parquet（支持 overwrite/append + 主键 upsert + 原子写）。从 `visual_report` 重导出 `render_report_html / write_report` | 218 |
| `scripts/daily_runner.py` | **命令行调度入口**：单次 `validate_input → make_report → build_result_row → 同时落生产 Parquet + 渲染 HTML`，结构化日志写入文件或 stderr | 263 |
| `scripts/demo.py` | **一键演示入口**：合成 60 天 × 200 股因子面板（不联网），跑 `run + write_production + write_report`，产物落到 `开发产物/demo_output/`。支持 `--bootstrap-n / --cost-grid-bps / --group-mode` 等高级诊断开关 | 202 |

### 数据 I/O 与常量

| 文件 | 作用 | 行数 |
|---|---|---:|
| `scripts/data_io.py` | 输入读取（DataFrame/记录列表/CSV/Parquet/XLSX）、字段别名（`date→trade_date` 等）、`config["columns"]` 自定义映射、类型校验（NaN/inf 拒绝）、`target_kind=binary_success` 时 0/1 校验、主键去重、空白 ts_code 拦截 | 218 |
| `scripts/constants.py` | BUILD 编号、字段集合、股票池标签与别名、有效因子方向、有效 target_kind、HTML 报告配色 | 31 |
| `scripts/utils.py` | `safe_float` / `round_metric` / `json_safe` 等数值与序列化辅助函数 | 39 |

### 评估指标核心

| 文件 | 作用 | 行数 |
|---|---|---:|
| `scripts/metrics.py` | **核心评估**：横截面 IC/RankIC、ICIR、Newey-West HAC t、IC 时间稳定性、分布诊断、分层回测、单调性、换手率（Jaccard 距离）、衰减曲线、达标表与质量预警；`compute_panel_base + apply_layer` 性能拆分；末尾从 `research_diagnostics` 重导出研究层（避免循环 import） | 990 |
| `scripts/stats.py` | 统计严谨性：Newey-West HAC（含 Andrews 经验滞后阶）、`bootstrap_rank_ic_baseline`（日内 shuffle 噪声基线、双侧 p 值、95% 置信区间）、`transaction_cost_adjusted_ls + cost_sweep`（按换手扣减成本算净指标） | 256 |
| `scripts/neutralize.py` | 横截面行业 + 风格中性化：每个 `trade_date` 独立做 OLS 残差，行业 dummy + 风格 z-score 回归 `factor_value`。**B10 不联网**——必须由调用方传入 `industry_panel / style_panel`，缺失直接 `ValueError`（红线测试锁住） | 257 |
| `scripts/research_diagnostics.py` | V7 研究层：子因子 IC、子因子分层、反向因子检验、仓位状态分段、月度稳定性、跨收益口径对比 6 张表，全部按 `config["group_count"]` 出表与主报告对齐 | 258 |

### HTML 可视化报告

| 文件 | 作用 | 行数 |
|---|---|---:|
| `scripts/visual/__init__.py` | `visual` 子包入口，re-export 三层公开符号 | 37 |
| `scripts/visual/svg_charts.py` | 纯 SVG 图表工具：`svg_line_chart` / `svg_bar_chart` / `svg_histogram`、`axis_range`、坐标投影、`format_number/format_percent` | 181 |
| `scripts/visual/sections.py` | 把 report dict 渲染成 HTML 各章节片段：核心 8 张图（IC 时序、累计 IC、分层累计、单调性柱、换手率、衰减、因子分布、RankIC 直方图）、达标表、研究诊断表、metric_card | 419 |
| `scripts/visual/document.py` | HTML 文档组装：`render_html_report / write_report / make_group_reports`、股票池下拉、五/十分组下拉、CSS 内嵌、`available_stock_pools` 多池切换 | 246 |
| `scripts/visual_report.py` | 历史薄入口（`from visual_report import render_report_html`）：透传 `visual/` 子包；保留 `metrics.compute_panel_base / metrics.apply_layer` 转发，因为测试 `test_make_group_reports_reuses_panel_base` 用 monkeypatch 打补丁 | 95 |

### 测试

| 文件 | 作用 | 行数 |
|---|---|---:|
| `scripts/test.py` | 测试聚合入口：动态发现 `tests/` 子目录里全部 `test_*` 函数并执行，等价于 `python -m pytest scripts/tests`（向后兼容历史 `python scripts/test.py` 调用） | 85 |
| `scripts/tests/__init__.py` | `tests` 包标记 + 路径注入，使子目录测试能 import 顶层 `build/metrics/data_io` 等 | 14 |
| `scripts/tests/fixtures.py` | 共享样本生成：`make_sample` / `make_pool_sample` / `make_research_sample` | 74 |
| `scripts/tests/test_data_io.py` | 输入校验、字段映射、类型边界、主键去重、binary_success 校验 | 157 |
| `scripts/tests/test_run_metrics.py` | `run()` 输出 schema、IC/分层语义、方向调整（pos/neg/auto）、binary_success、bootstrap、cost sweep、`make_report` 与 `compute_panel_base + apply_layer` 拆分按位等价 | 232 |
| `scripts/tests/test_visual_report.py` | HTML 渲染、图表占位、性能拆分（`make_group_reports` 复用 base 的复用次数锁） | 87 |
| `scripts/tests/test_research_diagnostics.py` | V7 研究层输出 + supplied panel 中性化路径；**含红线测试** `test_neutralization_without_supplied_panels_raises`——`neutralize=True` 但缺暴露面板必须 `ValueError` | 89 |
| `scripts/tests/test_write_production.py` | 生产写入往返、`mode="append"` upsert、`daily_runner._select_current_result_row`、demo 面板的 RankIC 显著性锁 | 132 |

## 生产产物（评估结果落地侧）

| 文件 | 作用 | 是否必需 |
|---|---|:---:|
| `生产产物/SKILL.md` | 生产读取端说明：结果文件路径、主键、字段说明、`result_json` 模块清单、读取规则与示例代码、写入语义（overwrite/append + 主键 upsert + 原子写）、禁止行为 | **必需** |
| `生产产物/数据库.parquet` | 生产结果 Parquet（28 KB），每行一条评估摘要（含完整 `result_json`）。当前包内为示例数据；运行 `daily_runner.py --output 生产产物/数据库.parquet --mode append` 会按主键 upsert 累积 | 必需（即便为空也要保留路径） |

---

## 关键文件 (核心 BUILD 入口) 之间的调用关系

```
外部调用方
    │
    ▼
build.py  ──────────►  data_io.validate_input ──► metrics.make_report ──► visual_report.write_report
   run()                                              │                          │
   write_production()                                 ├─► metrics.compute_panel_base   visual.document
                                                      │      └─► metrics.daily_ic        ├─► sections
                                                      │      └─► stats.newey_west_t_stat │     └─► svg_charts
                                                      │      └─► metrics.turnover        │
                                                      │      └─► metrics.decay_curve     └─► svg_charts
                                                      │      └─► stats.bootstrap_rank_ic
                                                      └─► metrics.apply_layer
                                                             └─► metrics.layer_backtest
                                                             └─► research_diagnostics.make_research_diagnostics
                                                             └─► neutralize.apply_neutralization
                                                             └─► stats.cost_sweep

daily_runner.py ──► validate_input + make_report + _build_result_row + _write_production_atomic + render_html_report
demo.py        ──► _make_demo_panel + run + write_production + write_report
test.py        ──► tests/* 全部 test_* 函数
```

---

## 删除了什么（vs 上一版）

本轮（v1.5.0）整理删除的内容（不是新做的功能改动，而是已有冗余代码）：

| 类别 | 项 |
|---|---|
| 死代码 | `metrics.compound_forward_return` / `metrics.compound_target`（孤儿函数） |
| 死代码 | `metrics.py` 顶部对 `transaction_cost_adjusted_ls` 的未使用 import |
| 死代码 | `neutralize.py` 中只挂 NullHandler 而无任何调用的 `logger` + `import logging` |
| 死代码 | `demo.py::main` 的 `argv if argv is None else _parse_args()` 等价分支 |
| 死代码 | `tests/test_run_metrics.py` 未使用的 `import numpy as np` |
| 过度 re-export | `visual_report.py` 的 8 个外部从未引用的转发符号（`BUILD_NAME / CHART_COLORS / STOCK_POOL_LABELS / json_safe / safe_float / validate_input / make_report / validate_config`） |
| 临时产物 | 全部 `__pycache__/` 目录 + `demo_output/` 临时演示产物 |
| 注释翻译 | `__init__.py / build.py / stats.py` 残留的英文 docstring 与英文章节注释 |

**未删除**：
- `references/sample_factor*.csv` 三个样本——是测试与演示输入，删了 `test_run_accepts_file_path` 会挂。
- HTML 报告中 SVG 图表的英文标题（`Pearson IC` / `Cumulative IC` / `RankIC Decay Curve` 等）——是科研报告里的图表 title 文本，由 3 个测试断言引用，且属于"显示文本"不是"代码注释"，按"注释用中文"原则不在翻译范围。
- `开发产物/demo.mp4`——人工录制的演示视频，按 SKILL.md 路径规范保留。

---

## 红线复检（提交前最后一道闸）

```powershell
cd "build track\build-b10-factor-evaluation\开发产物"

# 1) 全 B10 代码里搜 panda_data 调用——0 命中
findstr /S /R "panda_data\.[a-z_]*(" scripts\*.py

# 2) 找硬编码绝对路径——0 命中
findstr /S "E:\\量枢院" scripts\*.py

# 3) 找跨 track import——0 命中
findstr /S /R "from alpha\|from a01" scripts\*.py
```

或者更直接：**断网跑 `python -X utf8 scripts/demo.py`**——能完整出报告，就是"B10 不联网"的最强证明。
