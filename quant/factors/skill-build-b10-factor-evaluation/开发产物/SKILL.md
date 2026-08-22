---
name: build-b10-factor-evaluation
description: 当需要对 Alpha 因子进行 IC 测试与因子评估时，使用此 skill。该 BUILD 提供 IC/RankIC、ICIR、时间稳定性、分布诊断、分层回测、换手率、衰减曲线、股票池筛选和科研级 HTML 可视化报告生成能力，可被 agent 或 Alpha 调用。
tags: [quant, build, development, factor-evaluation]
---

# IC测试与因子评估体系

## 工具定位
- 工具类型：评估体系型 BUILD，混合型交付。
- 解决问题：为 Alpha 因子研发提供统一、可复用、可落地的 IC 测试、因子评估与可视化报告。
- 使用对象：agent / Alpha / 人工分析。
- 模块边界：B10 只接收标准评价面板，不直接 import、调用或依赖任何具体 Alpha 模块。

## 适用场景
- 当用户需要评估单个 Alpha 因子的横截面预测能力时。
- 当 Alpha 研发流程需要复用统一 IC、分层、换手、衰减评估口径时。
- 当生产任务需要把每日评估结果沉淀为 Parquet 供 agent 查询时。

## 输入
BUILD 输入必须来自 PandaAI data 数据拉取库、调用方传入的标准 Python 结构化数据，或项目指定数据源。本工具当前采用“调用方传入的标准结构化数据”方式，要求收益口径已由上游数据源或 Alpha 流程确认。

| 字段 | 类型 | 说明 |
|---|---|---|
| trade_date | date/string | 信号日期 |
| ts_code | string | 标的代码 |
| factor_value | float | 因子值 |
| forward_return | float | 该信号对应的未来收益 |

默认也支持字段别名：`date -> trade_date`、`asset -> ts_code`、`factor -> factor_value`、`return -> forward_return`。

当 `target_kind="return"` 时，`forward_return` 被解释为收益率，报告表头显示“平均收益 / 累计收益”。若信号在收盘后生成，推荐由调用方传入可交易收益，例如 `close[t+2] / close[t+1] - 1`。

当 `target_kind="binary_success"` 时，`forward_return` 被解释为 0/1 成功标签，报告表头显示“成功率”。该口径保留给打板接力研究分支，不是常规选股主报告口径。

可选多周期收益列：

| 字段 | 说明 |
|---|---|
| forward_return_1d | 1 日持有期收益 |
| forward_return_2d | 2 日持有期收益 |
| forward_return_3d | 3 日持有期收益 |
| forward_return_5d | 5 日持有期收益 |
| forward_return_10d | 10 日持有期收益 |
| forward_return_20d | 20 日持有期收益 |

B10 衰减曲线会优先使用这些真实 horizon 收益列；缺失时才回退到基于 `forward_return` 的兼容计算。

## 输出
| 字段 | 类型 | 说明 |
|---|---|---|
| trade_date | string | 报告截止日期 |
| build_id | string | B10 |
| build_name | string | IC测试与因子评估体系 |
| target_id | string | 报告目标 |
| result_type | string | factor_evaluation_report |
| result_value | float | 默认输出 RankIC 均值 |
| result_json | string | 完整 JSON 报告 |
| source_data_date | string | 输入数据截止日期 |
| data_version | string | 数据版本 |
| update_time | string | 更新时间 |

## result_json 报告内容
- 基础层：按交易日横截面计算 Pearson IC、Spearman RankIC、标准差、ICIR、正 IC 占比、t 统计量（含 Newey-West HAC t），并给出 `abs(IC) >= 0.02`、`abs(ICIR) >= 0.5` 等阈值判断。
- 原始与调整后指标：保留 `raw_ic/raw_rank_ic`，并按 `factor_direction` 输出调整方向后的核心 IC 指标。
- 时间层：输出累计 IC、累计 RankIC、IC/RankIC 自相关 lag1/lag5、因子 Rank 自相关 lag1/lag5，以及多周期 RankIC 衰减。
- 分布层：输出 IC/RankIC 偏度和峰度、因子横截面偏度/峰度、极端值占比。
- 分层回测：默认五分组，可通过 `group_mode` 选择五分组或十分组，输出各组日收益、均值收益、累计收益、多空累计收益和多空 IR。
- 分层保护：若横截面标的数不足以切出配置组数，报告会输出实际分组数和质量提示。
- 年化口径：多空 IR 默认按 252 年化，可通过 `annualization_factor` 适配周频、月频或其他项目频率。
- 单调性检验：检验调整方向后的分层平均收益是否随组别递增，并输出 Spearman 分层相关、相邻组改善比例和多空胜率。
- 换手率分析：默认顶部 20% 组合，按排序精确选取 top N，使用相邻日期持仓集合的 Jaccard 距离。并列 tie-break 规则为因子值相同时按 `ts_code` 字典序升序优先入选；如需无偏 tie-break，调用方应在进入 B10 前对 `factor_value` 加微小扰动。
- 衰减曲线：默认计算 1/2/3/5/10/20 期 RankIC。
- 总结层：自动生成"优质因子特征达标表"，逐项列出通过/未通过；若关键指标不达标，报告结论为"研究中"。
- **bootstrap 噪声基线**（`bootstrap_n > 0` 显式开启）：对每个 trade_date 内随机打乱因子值 `n_boot` 次，给出 RankIC 的零假设双侧 p-value 与 95% 置信区间，写入 `result_json.bootstrap_baseline`；不改变 `result_value`。`target_kind=binary_success` 时跳过 bootstrap（成功率不适合按收益率口径 shuffle 比较）。
- **交易成本敏感性扫描**（`cost_grid_bps` 非空时启用）：以多空日序列扣除"换手率 × 单边成本 × 2"为净序列，对一组 bps 重新计算净累计收益、净 IR、净胜率，写入 `result_json.transaction_cost.sweep`。
- **行业 + 风格中性化**（`neutralize=True` 显式开启）：对每个 trade_date 独立做横截面 OLS 中性化，使用行业 dummy + 风格 z-score 回归 `factor_value`，残差进入主评估链路。**B10 不联网**：必须由调用方通过 `industry_panel` / `style_panel` 传入暴露面板，或在标准面板里自带同名风格列；缺失时直接报错。元信息写入 `result_json.neutralization`。
- **V7 研究诊断**（`research_diagnostics=True` 或面板内含 `factor_component_*` 列时自动启用）：写入 `result_json.research_diagnostics`，包含子因子 IC、子因子分层、反向因子、仓位状态分段、月度稳定性、跨收益口径对比 6 张表。所有研究表都按 `config["group_count"]` 出表，与主报告分层数一致。

## HTML 可视化报告
`write_report()` 会生成独立 HTML 文件，内嵌科研级 SVG 图表，无需外部 JS 或图片依赖：
- 页面顶部提供“分组选项”下拉按钮，可在五分组和十分组之间切换。
- 五分组与十分组结果在生成 HTML 时一次性计算并内嵌，页面切换不触发重计算。
- IC 时序与 RankIC 滚动均值。
- RankIC 分布直方图。
- 累计 IC / 累计 RankIC 曲线。
- 分层累计收益曲线。
- 分层平均收益单调性柱状图。
- 顶部组合换手率时序。
- RankIC 衰减曲线。
- 因子分布诊断图。
- 优质因子特征达标表和诊断摘要表。

## 调用方式
```python
from scripts.build import run, write_report, write_production

result = run(input_data, config={
    "group_mode": "quintile",
    "turnover_quantile": 0.8,
    "decay_horizons": [1, 2, 3, 5, 10, 20],
    "annualization_factor": 252,
    "data_version": "your-data-version",
})

write_production(input_data, "../生产产物/数据库.parquet", config={
    "data_version": "daily-factor-eval-v1",
})

report_path = write_report(input_data, "reports/factor_report.html", config={
    "target_id": "my_factor",
    "group_count": 5,
})
```

`input_data` 可以是 `pandas.DataFrame`、记录列表、包含 `data` 的字典，或 `.csv/.xlsx/.parquet` 文件路径。

## 路径规范

- 所有命令、输入输出示例和报告路径必须使用相对路径，不写入本地盘符、用户目录或本地解释器路径。
- 运行命令统一使用当前环境中的 `python`；如需切换解释器，应在外部终端环境中完成，不写进本 skill。
- 不提交 `__pycache__`、`.pyc` 或其他会记录绝对源码路径的缓存文件。
- `demo.mp4` 由人工录制后放入 `开发产物`，不要求通过代码生成；若使用脚本辅助生成，画面和脚本中也不得出现本地绝对路径。

## 代码结构
`scripts/` 按职责分层。生产入口 `run() / write_production() / write_report()` 都收口在 `build.py`，其余按"输入校验 → 指标 → 研究层 → 报告渲染 → 调度"分层组织。

| 文件 / 包 | 职责 |
|---|---|
| `build.py` | BUILD 标准入口 `run()`、`validate_input/validate_output`、`write_production` |
| `__init__.py` | scripts 包标记，使 `scripts` 可作为 Python 包被外部 `import scripts.build` |
| `data_io.py` | 输入读取、字段映射（含别名 / `config["columns"]`）、类型校验、主键去重 |
| `constants.py` | BUILD 编号、字段、股票池标签、配色常量 |
| `utils.py` | `safe_float / round_metric / json_safe` 等数值与序列化辅助 |
| `metrics.py` | 核心评估指标：横截面 IC/RankIC、ICIR、时间稳定性、分布、分层回测、单调性、换手率、衰减曲线、达标表与质量提示；同时编排 `compute_panel_base + apply_layer` 的"基底缓存 + group_count 重算"性能拆分 |
| `stats.py` | 统计严谨性：Newey-West HAC t 统计量、bootstrap 噪声基线、交易成本敏感性扫描 |
| `neutralize.py` | 横截面行业 + 风格中性化（OLS 残差）。**B10 不联网**：`industry_panel` / `style_panel` 必须由调用方通过 `config` 显式传入或预先合入面板，缺失时 `apply_neutralization` 直接抛 `ValueError` |
| `research_diagnostics.py` | V7 研究层（子因子 IC/分组、反向因子、仓位状态分段、月度稳定性、收益口径对比）。从 metrics 拆出来，避免主链路被研究分支耦合；所有研究表统一使用 `config["group_count"]`，分组语义与主报告对齐 |
| `visual/` 子包 | HTML 报告三层拆分：`svg_charts.py`（纯 SVG 工具）/ `sections.py`（report dict → 各章节 HTML 片段）/ `document.py`（HTML 文档组装、股票池/分组下拉切换、`make_group_reports` 复用 base） |
| `visual_report.py` | 对外稳定入口（`render_report_html / write_report / make_group_reports` 等），实际实现在 `visual/` 子包 |
| `daily_runner.py` | 命令行调度入口：读面板 → 一次 evaluate → 同时落生产 Parquet（按主键 upsert，原子写）+ 渲染 HTML 报告 |
| `demo.py` | 一键演示入口：合成 60 天 × 200 股因子面板（不联网），跑 `run + write_production + write_report`，产物落到 `开发产物/demo_output/`。详见根目录 `HOW_TO_DEMO.md` |
| `test.py` + `tests/` 子目录 | 测试套件：`tests/{fixtures,test_data_io,test_run_metrics,test_visual_report,test_research_diagnostics,test_write_production}.py`；顶层 `test.py` 是兼容入口，等价于 `python -m pytest scripts/tests` |

## 配置项
| 配置 | 默认值 | 说明 |
|---|---:|---|
| group_mode | quintile | 分组选项，支持 `quintile`/`5`/`五分组` 或 `decile`/`10`/`十分组` |
| group_count | 5 | 分层数量，保留给高级调用；若与 `group_mode` 同时传入必须一致 |
| turnover_quantile | 0.8 | 换手率顶部组合阈值，0.8 表示顶部 20% |
| decay_horizons | [1,2,3,5,10,20] | 衰减曲线评估周期 |
| factor_direction | positive | 因子方向，支持 positive / negative / auto |
| target_kind | return | 目标解释方式，支持 `return` 和 `binary_success` |
| annualization_factor | 252 | 多空 IR 年化倍数，日频通常为 252，周频可设 52，月频可设 12 |
| stock_pool | all_a | 股票池筛选，支持 `all_a`、`hs300`、`zz500`、`zz1000`、`zz2000` |
| drop_missing | true | 是否剔除含缺失值的行；非法类型和重复主键始终报错 |
| columns | {} | 自定义字段映射 |
| target_id | factor_evaluation_report | 输出目标 ID |
| data_version | factor-eval-v1.3 | 数据版本 |
| bootstrap_n | 0 | RankIC 日内 shuffle 噪声基线次数；0 表示关闭，研究复核建议 ≥ 200 |
| bootstrap_seed | 1729 | bootstrap 随机种子，保证噪声基线可复现 |
| cost_grid_bps | [] | 交易成本敏感性扫描，单位 bps；空列表表示不输出扫描，示例 `[1, 3, 5, 10]` |
| neutralize | false | 是否对 `factor_value` 做横截面行业 + 风格中性化（OLS 残差） |
| neutralize_industry | true | 是否使用行业暴露做中性化；为 false 时只做风格剥离 |
| neutralize_style | ["log_market_cap", "turnover"] | 中性化风格列；可设为 `[]` 关闭风格剥离 |
| industry_level | L1 | 中性化使用的行业层级，可选 `L1`/`L2`/`L3`，会被回填到 `result_json.neutralization.industry_level` |
| industry_panel | None | `[trade_date, ts_code, industry]` 暴露面板；`neutralize=True` + `neutralize_industry=True` 时**必须**显式传入（B10 不联网） |
| style_panel | None | `[trade_date, ts_code, *neutralize_style]` 暴露面板；`neutralize=True` + 风格列非空时**必须**显式传入或在标准面板里自带同名列 |
| research_diagnostics | false | 是否启用 V7 研究诊断；面板包含 `factor_component_*` 列时自动启用 |
| return_targets | RESEARCH_RETURN_TARGETS | 研究层 `return_target_comparison` 使用的收益口径列名集合 |
| enable_group_selector | true | HTML 报告是否生成五分组/十分组下拉切换 |
| enable_stock_pool_selector | true | HTML 报告是否生成股票池下拉切换 |

## 可被 Alpha 调用
- 是。
- 调用限制：输入必须包含稳定的 `trade_date`、`ts_code`、`factor_value`、`forward_return` 字段；收益方向默认因子值越高越好。若要评估衰减曲线，建议同时传入 `forward_return_1d/2d/3d/5d/10d/20d`。
- 依赖数据：调用方传入的标准结构化因子与收益报告；若改为 PandaAI data 或项目指定数据源，需先明确字段口径和权限。

## 是否需要生产结果
- 是否生成 `数据库.parquet`：是，作为混合型 BUILD 的生产产物。
- 更新频率：建议每日收盘后，或每次 Alpha 研发评估任务结束后。
- 字段结构：见 `生产产物/SKILL.md` 和 `references/api_guide.md`。

## 依赖
- pandas
- numpy
- pyarrow 或 fastparquet：仅在写入/读取 Parquet 时需要。
- **B10 不直接联网**：所有原始行情、龙虎榜、行业、风格因子等数据都由外部桥接层拉取，B10 仅消费已加工成 (trade_date, ts_code, factor_value, forward_return) 的标准面板。中性化所需的行业 / 风格暴露面板亦同——必须由调用方通过 `config` 传入或预先合入面板，B10 内部没有任何 `panda_data` 调用。
- 可视化报告使用内嵌 SVG，不依赖 matplotlib、seaborn 或外部前端库。

## 股票池评估模块

B10 支持在同一个评估面板中按股票池筛选结果。上游应先计算全量因子并传入股票池标签字段，B10 只做筛选与评估，不重新划分股票池。

可选股票池：

- `all_a`：全A股
- `hs300`：沪深300
- `zz500`：中证500
- `zz1000`：中证1000
- `zz2000`：中证2000/2000风格股票池

输入可包含 `is_pool_all_a`、`is_pool_hs300`、`is_pool_zz500`、`is_pool_zz1000`、`is_pool_zz2000`、`stock_pool_memberships` 和 `primary_stock_pool`。配置中设置 `stock_pool` 即可直接筛选：

```python
result = run(input_data, config={"stock_pool": "zz500", "group_mode": "quintile"})
```

HTML 报告会在顶部生成“股票池”下拉选项，并为可用股票池和五分组/十分组组合一次性生成内嵌结果；页面切换不触发后端重算。

B10 不直接依赖任何 Alpha 模块。若输入因子缺少股票池字段，调用方应在进入 B10 前通过独立桥接脚本或数据准备流程补齐 `is_pool_*` 标签。

## 运行测试
```bash
# 推荐：直接用兼容入口，自动遍历 tests/ 子目录里所有 test_* 函数
python scripts/test.py

# 等价路径（如果环境装了 pytest）：
python -m pytest scripts/tests -v
```

## 一键演示（不联网）
```bash
python scripts/demo.py                                       # 默认五分组、全A股
python scripts/demo.py --group-mode decile                   # 切十分组
python scripts/demo.py --bootstrap-n 200 --cost-grid-bps 1,3,5,10  # 噪声基线 + 成本扫描
```

会落到 `开发产物/demo_output/`：合成因子 CSV、HTML 报告、生产格式 Parquet。
完整演示话术见仓库 `build track/build-b10-factor-evaluation/HOW_TO_DEMO.md`。

测试拆分为 5 份子文件：
- `tests/test_data_io.py`：输入校验、字段映射、类型边界、主键去重。
- `tests/test_run_metrics.py`：`run()` 输出 schema、IC/分层、方向调整、binary_success、bootstrap、cost、`make_report` 与 `compute_panel_base + apply_layer` 拆分按位等价。
- `tests/test_visual_report.py`：HTML 渲染（含图表占位、股票池下拉）、性能拆分（`make_group_reports` 复用 base 的复用次数锁）。
- `tests/test_research_diagnostics.py`：V7 研究层输出与 supplied panel 中性化路径，含**红线复检**——`neutralize=True` 但未传 industry/style panel 必须 `ValueError`，证明 B10 不联网。
- `tests/test_write_production.py`：生产写入往返、`mode="append"` upsert、`daily_runner` 当前行选择。
