---
name: build-b10-factor-evaluation-production
description: 当需要读取 IC测试与因子评估体系 的生产结果时，使用此 skill。该 skill 读取已生成的 Parquet 结果，不重复执行重计算流程。
tags: [quant, build, production, factor-evaluation]
---

# IC测试与因子评估体系生产结果

## 工具定位
- 工具类型：评估体系型 BUILD，生产结果读取。
- 服务对象：agent / Alpha / 人工复盘。
- 是否可被 Alpha 调用：是。

## 结果文件
- 文件路径：`数据库.parquet`
- 数据格式：Parquet
- 更新频率：建议每日收盘后，或每次 Alpha 研发评估任务结束后。
- 生成任务：由开发产物 `scripts/build.py` 中的 `write_production(input_data, output_path, config=None, mode="overwrite" | "append")` 生成。

所有路径均为相对路径说明，不绑定任何本地盘符、用户目录或本地 Python 环境。B10 生产读取端只读取本目录下的 `数据库.parquet`，不得通过绝对路径回连开发环境。

## 主键
- `trade_date`
- `build_id`
- `target_id`
- `result_type`

## 字段说明
| 字段 | 类型 | 说明 |
|---|---|---|
| trade_date | date/string | 评估报告截止日期 |
| build_id | string | BUILD 编号，固定为 B10 |
| build_name | string | BUILD 名称 |
| target_id | string | 评估对象，如因子名、策略名或报告 ID |
| result_type | string | 结果类型，默认 factor_evaluation_report |
| result_value | float | 核心结果值，默认 RankIC 均值 |
| result_json | string | 完整评估报告，JSON 字符串 |
| source_data_date | string | 输入数据截止日期 |
| data_version | string | 数据版本 |
| update_time | datetime/string | 结果生成时间 |

`result_json.summary` 中包含 `stock_pool`、`stock_pool_label`、`target_kind`、IC/RankIC、ICIR、累计多空收益、换手率、单调性和 `quality_check_passed`，用于说明该条评估结果对应的股票池筛选范围和是否达到优质因子特征。HTML 报告可同时内嵌多个股票池和分组模式的结果，但生产 Parquet 的单条摘要仍以调用时的 `config["stock_pool"]` 为准。

`result_json` 当前包含以下主要模块：

- `ic_analysis` / `raw_ic_analysis`：方向调整后与原始 IC/RankIC（含 Newey-West HAC t）。
- `ic_time_analysis`：累计 IC/RankIC、IC 自相关、RankIC 自相关。
- `ic_distribution`：IC/RankIC 偏度、峰度和极端占比。
- `factor_distribution`：因子横截面偏度、峰度、极端值占比。
- `factor_rank_autocorrelation`：因子 Rank 自相关 lag1/lag5。
- `layer_backtest`：分层收益、多空收益、多空 IR、单调性和多空胜率。
- `turnover_analysis`：顶部组合换手率。
- `decay_curve`：1/2/3/5/10/20 等持有期 RankIC。
- `quality_checklist` / `quality_warnings`：优质因子特征逐项达标表与质量提示。
- `bootstrap_baseline`：RankIC 噪声基线 p-value 与 95% 置信区间（仅当 `bootstrap_n > 0` 时输出）。
- `transaction_cost.sweep`：交易成本敏感性扫描结果（仅当 `cost_grid_bps` 非空时输出）。
- `neutralization`：中性化元信息（每天行业/风格列数、是否跳过、错误诊断）。**B10 不联网**——开启中性化时 `industry_panel` / `style_panel` 必须由桥接层在调用 B10 前传入。
- `research_diagnostics`：V7 研究层 6 张表（子因子 IC / 子因子分层 / 反向因子 / 仓位状态分段 / 月度稳定性 / 收益口径对比），仅在面板含 `factor_component_*` 列或显式 `research_diagnostics=True` 时输出。

当 `target_kind="return"` 时，`forward_return` 按收益率解释；当 `target_kind="binary_success"` 时，`forward_return` 按 0/1 成功标签解释。

## 读取规则
交易 agent 或 Alpha 读取 `数据库.parquet`，按日期、对象和结果类型查询。查询生产结果时不应重复触发 IC、分层回测、换手率和衰减曲线重计算。B10 生产结果只代表已生成的评估摘要，不直接调用任何 Alpha 模块。

### 标准查询示例
```python
import json
from pathlib import Path
import pandas as pd

# 1. 读取整库（同一文件内可包含多日、多 target_id 的累积评估摘要）
df = pd.read_parquet(Path("数据库.parquet"))

# 2. 取指定 target_id 在最新评估日期的那条
mask = (df["build_id"] == "B10") & (df["target_id"] == "my-factor-v1")
latest = df.loc[mask].sort_values("update_time").tail(1)

# 3. result_value 默认是 RankIC 均值，result_json 是完整报告
rank_ic = float(latest["result_value"].iloc[0])
report = json.loads(latest["result_json"].iloc[0])
quality_passed = report["summary"]["quality_check_passed"]
top_bottom = report["summary"]["long_short_cumulative_return"]
```

### 多日时间序列查询
```python
# 取近 30 天某因子的 RankIC 序列
recent = (
    df.loc[df["target_id"] == "my-factor-v1"]
      .sort_values("trade_date")
      .tail(30)[["trade_date", "result_value", "data_version"]]
)
```

## 写入语义
生产 Parquet 推荐使用 ``write_production(input_data, output_path, config, mode="append")`` 写入：
- ``mode="append"``（推荐日常调度）：按主键 ``(trade_date, build_id, target_id, result_type)`` upsert，同一主键以最新一次写入覆盖；不同主键并存，文件按日期累积。
- ``mode="overwrite"`` （默认，向后兼容）：直接覆盖，文件最终只剩这一次评估摘要。

写入流程为原子写：先 `*.tmp` 再 `replace`，避免半成品 Parquet。

## 禁止行为
- 不允许多人查询时重复触发重计算。
- 不允许手工修改 Parquet 结果。
- 生产结果异常时必须提示数据日期、对象、版本和异常原因。
- 不允许在生产文档、日志或读取脚本中写入本地绝对路径、本地解释器路径或用户目录。
- 不允许提交 `__pycache__`、`.pyc` 等可能记录绝对源码路径的缓存文件。
