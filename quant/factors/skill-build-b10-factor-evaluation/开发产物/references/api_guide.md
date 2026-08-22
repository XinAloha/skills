# IC测试与因子评估体系 API Guide

## 数据来源
本 BUILD 使用调用方传入的标准 Python 结构化数据作为正式输入。上游可以来自 PandaAI data、Alpha 因子脚本或项目指定数据源，但传入本工具前必须统一为稳定字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| trade_date | date/string | 信号日期 |
| ts_code | string | 标的代码 |
| factor_value | float | 因子值 |
| forward_return | float | 与信号日期匹配的评估目标；`target_kind=return` 时为收益率，`target_kind=binary_success` 时为 0/1 标签 |

默认支持别名：`date`、`asset`、`factor`、`return`。也可以通过 `config["columns"]` 配置自定义字段映射。

### PandaAI data 接入方式

B10 不直接调用 PandaAI data，**所有原始行情、龙虎榜、指数权重等接口都由外部桥接层负责**，B10 仅消费"已加工成 (trade_date, ts_code, factor_value, forward_return) 的标准面板"。这也是项目红线"B10 不依赖任何具体 Alpha"的体现。

外部桥接层的标准职责：
1. 从上游数据源（Alpha 生产库、行情接口等）拿到因子值与行情。
2. 按 t+1 close → t+2 close 计算 `forward_return` 与 `forward_return_{1,2,3,5,10,20}d`。
3. 通过行情或指数成分标注 `is_pool_*`、`stock_pool_memberships`、`primary_stock_pool`。
4. 拼成标准面板后传给 B10 `run() / write_production() / write_report()`。

如果你要为新的因子源写桥接，**不要**在 B10 内部新增数据拉取代码——在 B10 外部准备好标准面板后传入。

`target_kind` 决定 `forward_return` 的解释方式：

- `target_kind="return"`：`forward_return` 是收益率，HTML 报告显示“平均收益 / 累计收益”。若信号在收盘后生成，推荐上游传入可交易收益，例如 `close[t+2] / close[t+1] - 1`。
- `target_kind="binary_success"`：`forward_return` 是 0/1 成功标签，HTML 报告显示“成功率”，用于打板接力研究分支。

可选多周期收益列用于真实 RankIC 衰减：

| 字段 | 类型 | 说明 |
|---|---|---|
| forward_return_1d | float | 1 日持有期收益 |
| forward_return_2d | float | 2 日持有期收益 |
| forward_return_3d | float | 3 日持有期收益 |
| forward_return_5d | float | 5 日持有期收益 |
| forward_return_10d | float | 10 日持有期收益 |
| forward_return_20d | float | 20 日持有期收益 |

B10 在计算 `decay_horizons` 时优先读取对应 `forward_return_{n}d` 列，缺失时才按 `forward_return` 做兼容计算。

## 标准入口
```python
from scripts.build import run, render_report_html, validate_input, validate_output, write_report, write_production

result = run(input_data, config=None)
html = render_report_html(input_data, config=None)
report_path = write_report(input_data, "reports/factor_report.html", config=None)
```

## 模块职责
开发实现按"输入校验 → 指标 → 研究层 → 报告 → 调度"分层。对外稳定入口仍在 `scripts/build.py`，新代码可以直接 import 子模块。

| 文件 / 包 | 说明 |
|---|---|
| `build.py` | BUILD 标准入口、输出 schema、生产写入 |
| `__init__.py` | `scripts` 包标记，使其可作为 Python 包被外部 `import scripts.build` |
| `data_io.py` | 输入数据读取、字段映射和校验 |
| `constants.py` | 常量定义（BUILD ID、字段、股票池标签、配色） |
| `utils.py` | `safe_float / round_metric / json_safe` 等数值与序列化辅助 |
| `metrics.py` | 因子评估核心计算 + `compute_panel_base/apply_layer` 性能拆分 |
| `stats.py` | Newey-West HAC、bootstrap 噪声基线、交易成本敏感性扫描 |
| `neutralize.py` | 横截面行业 + 风格中性化（OLS 残差，**B10 不联网**，必须由调用方传入暴露面板） |
| `research_diagnostics.py` | V7 研究层（子因子 / 反向因子 / 状态分段 / 月度稳定性 / 收益口径对比） |
| `visual/` 子包 | HTML 报告三层：`svg_charts.py` / `sections.py` / `document.py` |
| `visual_report.py` | 兼容入口，re-export `visual/` 子包 + 历史 monkeypatch 入口 |
| `daily_runner.py` | 命令行调度入口（一次 evaluate → 同时落生产 Parquet + HTML） |

`run()` 返回一行表格型结果，字段固定为：

| 字段 | 类型 | 说明 |
|---|---|---|
| trade_date | string | 报告截止日期 |
| build_id | string | 固定为 B10 |
| build_name | string | 固定为 IC测试与因子评估体系 |
| target_id | string | 默认 factor_evaluation_report |
| result_type | string | 默认 factor_evaluation_report |
| result_value | float | 默认 RankIC 均值 |
| result_json | string | 合法 JSON 字符串 |
| source_data_date | string | 输入数据截止日期 |
| data_version | string | 数据版本 |
| update_time | string | 生成时间 |

## HTML 评估报告
```python
report_path = write_report(
    input_data,
    "reports/factor_report.html",
    config={"target_id": "my_factor", "group_mode": "decile"},
)
```

`write_report()` 输出一个独立 HTML 文件，内嵌 SVG 图表和指标表，不依赖 matplotlib、seaborn 或外部 JS。报告包含：

页面顶部提供“分组选项”下拉按钮，可在五分组和十分组之间切换。两套分组结果在 HTML 生成时一次性计算并内嵌，页面切换不触发后端重计算。

| 图表 | 说明 |
|---|---|
| IC Time Series | 每日 IC 与 RankIC 滚动均值 |
| RankIC Distribution | RankIC 分布直方图 |
| Cumulative IC | 累计 IC 与累计 RankIC |
| Quantile Cumulative Return | 分层累计收益曲线 |
| Mean Return by Quantile | 分层平均收益单调性柱状图 |
| Turnover Analysis | 顶部组合换手率时序 |
| RankIC Decay Curve | 不同持有周期 RankIC 衰减 |
| Factor Distribution Diagnostics | 因子横截面偏度和极端值占比诊断 |

报告还包含“优质因子特征达标表”，覆盖基础层、时间层、分布层和分层层：

- 基础层：IC/RankIC 均值、标准差、ICIR、t-stat、正占比。
- 时间层：累计 IC/RankIC、IC 自相关、因子 Rank 自相关、多周期衰减。
- 分布层：IC/RankIC 偏度峰度、因子值偏度峰度、极端值占比。
- 分层层：五分组/十分组收益、单调性 Spearman、相邻组改善比例、多空收益、IR 和胜率。

当 `group_mode="decile"` 但某些样本横截面不足以切出 10 组时，报告会在 `summary.configured_group_count` 保留配置组数，并在 `summary.group_count` 与质量提示中说明实际分组数。

## 配置
| 配置 | 默认值 | 说明 |
|---|---:|---|
| group_mode | quintile | 分组选项，支持 `quintile`/`5`/`五分组` 或 `decile`/`10`/`十分组` |
| group_count | 5 | 分层回测组数，保留给高级调用；若与 `group_mode` 同时传入必须一致 |
| turnover_quantile | 0.8 | 顶部组合阈值，0.8 表示顶部 20% |
| decay_horizons | [1,2,3,5,10,20] | 衰减曲线周期 |
| factor_direction | positive | 因子方向，支持 `positive`、`negative`、`auto`；核心分层和换手按调整方向后的因子排序 |
| target_kind | return | 目标解释方式，支持 `return` 和 `binary_success` |
| annualization_factor | 252 | 多空 IR 年化倍数，日频通常为 252，周频可设 52，月频可设 12 |
| stock_pool | all_a | 股票池筛选，支持 `all_a`、`hs300`、`zz500`、`zz1000`、`zz2000` 及中文标签 |
| drop_missing | true | 是否剔除含缺失值行；非法类型、非有限数字和重复主键始终报错 |
| columns | {} | 字段映射，支持 `{标准字段: 原始字段}` 或 `{原始字段: 标准字段}` |
| target_id | factor_evaluation_report | 输出目标 ID |
| result_type | factor_evaluation_report | 输出类型 |
| data_version | factor-eval-v1.3 | 数据版本 |
| update_time | 当前时间 | 生成时间 |
| bootstrap_n | 0 | RankIC 日内 shuffle 噪声基线次数；0 表示关闭，建议研究复核时设为 200 或更高 |
| bootstrap_seed | 1729 | bootstrap 随机种子，保证噪声基线可复现 |
| cost_grid_bps | [] | 交易成本敏感性扫描，单位 bps；空列表表示不输出扫描，示例 `[1, 3, 5, 10]` |
| neutralize | false | 是否对 `factor_value` 做横截面行业 + 风格中性化 |
| neutralize_industry | true | 是否使用行业暴露做中性化；为 false 时只做风格剥离 |
| neutralize_style | ["log_market_cap", "turnover"] | 中性化风格暴露列；可设为 `[]` 关闭风格剥离 |
| industry_level | L1 | 中性化使用的行业层级，可选 `L1`/`L2`/`L3`，会回填到 `result_json.neutralization.industry_level` |
| industry_panel | None | `[trade_date, ts_code, industry]`；`neutralize=True` + `neutralize_industry=True` 时**必须**显式传入。**B10 不联网**，缺失会直接 `ValueError` |
| style_panel | None | `[trade_date, ts_code, *neutralize_style]`；`neutralize=True` + 风格列非空时**必须**显式传入或在标准面板里自带同名列 |
| research_diagnostics | false | 是否启用 V7 研究诊断；面板包含 `factor_component_*` 列时自动启用 |
| return_targets | RESEARCH_RETURN_TARGETS | 研究层 `return_target_comparison` 使用的收益口径列 |
| enable_group_selector | true | HTML 报告是否生成五分组/十分组下拉切换 |
| enable_stock_pool_selector | true | HTML 报告是否生成股票池下拉切换 |

### 高级诊断说明

`bootstrap_n > 0` 时，B10 会在每个交易日内随机打乱因子值，生成 RankIC 的零假设分布，并在 `result_json.bootstrap_baseline` 输出双侧 p-value、95% 区间和样本天数。该过程只用于研究复核，不改变 `result_value`。`target_kind=binary_success` 时跳过 bootstrap（成功率口径不适合 shuffle 比较）。

`cost_grid_bps` 只在显式传入时输出 `result_json.transaction_cost.sweep`。多空净收益口径为：日多空收益 - 顶部组合换手率 × 单边成本 × 2。

`neutralize=True` 时，B10 对每个 `trade_date` 独立做横截面 OLS 中性化，使用行业 dummy 和风格因子 z-score 回归 `factor_value`，再用残差进入 IC、分层、换手、衰减等主评估链路。**B10 不联网**：`industry_panel` / `style_panel` 必须由调用方通过 `config` 显式传入，或在标准面板里自带同名风格列；缺失时 `apply_neutralization` 直接抛 `ValueError`，不会回退到任何在线数据接口。如果上游缺数据，请在外部桥接层拉好行业/风格再传入。

## 股票池筛选

如果上游因子面板包含股票池标签，B10 可以通过 `config["stock_pool"]` 按股票池评估。支持值为 `all_a`、`hs300`、`zz500`、`zz1000`、`zz2000`，也支持中文标签“全A股”“沪深300”“中证500”“中证1000”“中证2000”。

可选输入字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| is_pool_all_a | bool | 是否属于全A股股票池 |
| is_pool_hs300 | bool | 是否属于沪深300 |
| is_pool_zz500 | bool | 是否属于中证500 |
| is_pool_zz1000 | bool | 是否属于中证1000 |
| is_pool_zz2000 | bool | 是否属于中证2000/2000风格股票池 |
| stock_pool_memberships | string | 股票池标签集合，使用 `|` 分隔 |
| primary_stock_pool | string | 主股票池标签 |

示例：

```python
report_path = write_report(
    input_data,
    "reports/factor_report.html",
    config={"stock_pool": "hs300", "group_mode": "decile"},
)
```

当 `enable_group_selector=True` 时，HTML 会生成股票池下拉选项，展示输入数据中实际存在的股票池。若请求非全A股股票池但输入缺少标签字段，B10 会抛出配置/输入错误，避免误把全样本当成目标股票池。

股票池标签由上游或独立桥接脚本在进入 B10 前准备；B10 只校验和使用输入中的 `is_pool_*`、`stock_pool_memberships`、`primary_stock_pool` 字段，不直接调用任何 Alpha 模块取数。

## 生产写入
```python
write_production(
    input_data,
    "../生产产物/数据库.parquet",
    config={"data_version": "daily-factor-eval-v1"},
    mode="append",   # 推荐日常调度；默认 "overwrite" 保持向后兼容
)
```

写入前会执行 `validate_output()`，检查字段完整、主键不重复、关键字段非空、`result_json` 可解析。写入 Parquet 需要安装 `pyarrow` 或 `fastparquet`。

`mode="append"` 时，B10 读取已有 Parquet → 按主键 `(trade_date, build_id, target_id, result_type)` upsert（同主键覆盖、不同主键累积）→ 通过临时文件 `*.tmp` 原子重命名落地，避免写入过程被打断时留下半成品。

## 命令行调度

```bash
python scripts/daily_runner.py \
    --input 输入面板.parquet \
    --target-id my-factor-v1 \
    --stock-pool zz500 \
    --group-mode quintile \
    --data-version daily-eval-v1 \
    --output ../生产产物/数据库.parquet \
    --mode append \
    --report-dir reports/daily \
    --log-file logs/b10-daily.log
```

`daily_runner.py` 把 `run() + write_production(mode="append") + write_report()` 串起来，落 HTML 到 `reports/daily/{target_id}_{end_date}.html`，结构化日志写到 `--log-file`（默认 stderr）。

## 异常行为
- 空输入：抛出 `ValueError("input_data 不能为空")`。
- 缺字段：抛出 `ValueError("input_data 缺少必要字段: ...")`。
- 非法数值类型：抛出包含字段名和异常行数的 `ValueError`。
- 重复主键：同一 `trade_date + ts_code` 重复时抛出 `ValueError`。
- 非法配置：抛出包含配置名的 `ValueError`。
- Parquet 引擎缺失：`write_production()` 抛出 `RuntimeError("写入 Parquet 需要安装 pyarrow 或 fastparquet")`。
