# 残差引导因子选择

这是一个可由 Codex 文字调用的量化因子搜索 Skill。方法从因子库中逐步寻找对当前模型残差具有互补解释力的候选，并通过严格的时序交叉验证、多路径保留和冻结式 OOS 评估，形成可审计的紧凑因子集合。

## 项目信息

- **项目状态**：QuantSkills Community Project，未经 QuantSkills 官方审核、认证或背书。
- **维护方**：`X-Tech-group`。
- **仓库元数据**：组织、仓库、项目类型、集合、许可证和维护信息统一声明在 [`skill.yml`](skill.yml) 中。

## 方法概览

```text
宽表标签 + 因子库
        |
        v
股票池确定 -> 因子预处理 -> Train / Valid / OOS 隔离
        |
        v
当前因子集联合建模
        |
        +-- Ridge 单路径: Train 样本内残差
        |
        +-- Ridge Beam: Train+Valid 开发期样本内残差
        |
        +-- LightGBM Beam: expanding-fold OOF 残差
        |
        v
逐日横截面计算候选因子与残差的相关性
        |
        v
按 |mean daily residual IC| 排序并扩展搜索路径
        |
        v
        +-- search_objective=cv: 时间序列 CV 联合评分与 Beam 剪枝
        |
        +-- search_objective=residual: 开发期加权 Ridge R^2 与 Beam 剪枝
        |
        v
选择并冻结开发期检查点
        |
        v
显式 evaluate-oos -> 冻结的 OOS prediction 与标签层指标
        |
        +-- 导出交接清单 -> Codex 调用 $factor-backtest
```

设当前因子集合为 `S`，标签为 `y`，当前模型预测为 `y_hat_S`，残差为：

```text
r_S = y - y_hat_S
```

对每个尚未选择的候选因子 `x_j`，先在每个交易日计算横截面相关系数，再对有效日期取均值：

```text
signed_mean_ic_j = mean_t corr_cs(x_j,t, r_S,t)
candidate_score_j = abs(signed_mean_ic_j)
```

绝对值评分允许正相关和负相关的互补因子进入候选集合；符号仍写入结果文件。候选加入后，模型会使用完整的新因子集合重新拟合，而不是把单因子模型简单叠加。

## 残差与模型

Ridge 单路径 `run` 和 `run-many` 使用 Train 上当前联合模型的样本内残差；Ridge Beam 使用 Train+Valid 开发期上当前联合模型的样本内残差。模型包含不受惩罚的截距，可通过 `equal_date_weight` 让每个交易日具有相同总权重。Ridge 路径支持单路径、批量随机起点、确定性 super-root Beam 和随机起点 Beam。

LightGBM 模式仅用于 Beam 搜索。每个时序折在较早区间拟合，并在后续评分区间产生预测；候选排序使用这些预测拼接得到的 OOF 残差。最终拟合可以从开发期末尾划出验证尾段进行 early stopping，再按确定的迭代轮数在完整开发期重拟合。

## 多路径搜索

Beam Search 不只保留当前最优的一条路径。每一层从保留路径的残差候选榜中取前 `branch_width` 个扩展，并保留最多 `width` 条路径。`search_objective: cv` 对扩展集合计算联合时序 CV；Ridge `search_objective: residual` 使用开发期加权 Ridge `R^2` 保留路径，在 `residual_selection_depth` 冻结，并为各深度检查点补充 CV 证据。路径间使用 Jaccard 相似度约束，以避免搜索资源集中在高度重复的因子组合上。

默认 CV 评分为：

```text
cv_score =
    mean(fold_ic)
    - stability_penalty * std(fold_ic)
    + min_year_weight * min(fold_ic)
    - complexity_penalty * factor_count
```

`trend_weight` 可将最近若干层的 CV 增量加入路径优先级，`continuation_weight` 可加入下一步残差互补性探测。CV 目标下，最终检查点可以选择峰值 CV、one-standard-error 规则下的较浅路径，或在 `deep_selection_tolerance` 容差内选择更深路径；设置 `deep_selection_tolerance` 时，该规则优先于 `one_standard_error`。

`run-pool` 提供穷举式联合 CV 因子池搜索：每一步对所有剩余候选分别执行联合 CV，选择得分最高的更新；设置 `pool_capacity` 后，扩展超过容量时删除完整样本 Ridge 绝对系数最小的因子。

## 数据与时间隔离

标签文件和原始因子文件采用宽表 Parquet：

- 行索引：交易日；
- 列：标的代码；
- 每个因子一个文件；
- 标签通常为对齐到当前交易日的未来收益。

`Train < Valid < OOS` 必须按时间顺序且互不重叠。运行时可以预处理并缓存完整面板，但搜索目标、候选排序和检查点选择只访问 Train 与 Valid 组成的开发期；OOS 数值仅由冻结后的 `evaluate-oos` 用于预测和指标计算。每个 CV 拟合段和 Train/Valid 尾部都会按 `embargo_bars` 删除相应数量的交易日，用于隔离前瞻标签的时间重叠。

支持两类因子预处理：

- `cross_sectional`：逐日缩尾、可选横截面 z-score，非有限值和处理后缺失值填为 0；
- `rolling_median_zscore`：逐标的滚动中位数与滚动标准差归一化，并执行幅度裁剪和缺失值填 0。

标签可保持原值或转换为逐日横截面秩，并可逐日去均值。股票池可显式指定，也可依据 Train 标签覆盖率固定。

## 运行方式

安装依赖并生成确定性的烟雾测试数据：

```bash
python -m pip install -r requirements.txt
python examples/generate_residual_search_toy_data.py
```

执行单路径、Beam 和联合 CV 因子池搜索：

```bash
python scripts/run_factor_selection.py \
  --config examples/residual_search/toy_config.yaml run

python scripts/run_factor_selection.py \
  --config examples/residual_search/toy_config.yaml run-beam

python scripts/run_factor_selection.py \
  --config examples/residual_search/toy_config.yaml run-pool
```

冻结开发期结果后再执行 OOS：

```bash
python scripts/run_factor_selection.py \
  --config examples/residual_search/toy_config.yaml evaluate-oos \
  --run-dir <frozen-run-directory>
```

需要收益层验证时，先为 Codex 内部的 `$factor-backtest` 导出冻结 OOS 信号和交接清单：

```bash
python scripts/run_selection_backtest.py \
  --run-dir <frozen-run-directory> \
  --export-only
```

命令输出结构化 JSON，其中包含 `input_file`、`factor_column=prediction`、`timespan`、`signal_manifest` 和 `signal_direction`。Codex 将这些字段连同真实市场数据目录和组合参数交给 `$factor-backtest`，由后者校验数据、执行回测并检查产物。导出模式不会定位外部脚本，也不会启动子进程；直接 CLI 执行仅作为显式兼容方式保留。

当两个 Skill 均已安装并注册时，Codex 可以根据“回测收益、净值、回撤、持仓、换手或对冲表现”等自然语言识别并依次调用两个 Skill，使用者不需要显式书写 Skill 名称。

其他命令：

| 命令 | 功能 |
|---|---|
| `materialize` | 从行情和因子公式物化宽表因子文件 |
| `validate-cache` | 校验预处理特征缓存及其 manifest |
| `run-many` | 共享特征缓存运行多个 Ridge 单路径 |
| `run-many-beam` | 共享特征缓存运行多个随机起点 Beam |
| `evaluate-oos` | 对冻结结果重拟合并生成 OOS 预测 |

完整参数见 [使用与配置](references/usage.md)，算法细节见 [算法说明](references/algorithm.md)，Codex Skill 交接契约见 [回测集成](references/backtest_integration.md)。

## 输出

每个搜索目录包含：

- `summary.json`：冻结因子、开发期指标和模型元数据；
- `iteration_history.csv`：逐检查点指标与选择记录；
- `beam_history.csv`：仅 Beam 搜索生成，记录路径、父路径、分折得分和保留状态；
- `residual_top10.csv`：逐路径残差候选排名；
- `config.json`：解析为绝对路径后的完整配置。

批量运行还会生成 `batch_summary.csv`、`batch_metrics.json`、`factor_frequency.csv` 和 `path_similarity.csv`。显式 OOS 评估生成 `oos_predictions.parquet` 与 `oos_evaluation.json`。回测交接生成 `backtest_input/prediction.parquet`、信号 manifest 和标准输出中的 handoff JSON；回测结果由 `$factor-backtest` 写入其指定输出目录。

## 代码结构

```text
scripts/
├── run_factor_selection.py
├── run_selection_backtest.py
└── residual_factor_selection/
    ├── cli.py           命令行入口
    ├── config.py        配置解析与时间约束
    ├── data.py          宽表读取、股票池、切分与 embargo
    ├── preprocess.py    因子与标签预处理
    ├── ridge.py         加权 Ridge
    ├── metrics.py       每日 IC、ICIR 和误差指标
    ├── selector.py      单路径残差前向选择
    ├── beam.py          Ridge 多路径搜索与联合时序 CV
    ├── lgbm_beam.py     LightGBM OOF 残差 Beam
    ├── pool.py          穷举式联合 CV 因子池
    ├── cache.py         特征缓存 manifest 与一致性校验
    ├── materialize.py   因子物化
    ├── serialization.py JSON 安全序列化
    ├── experiment.py    实验编排、缓存、输出与 OOS
    └── backtest_adapter.py  冻结信号转换、Skill 交接与兼容执行
```

本 Skill 负责冻结因子集合、模型预测、标签层指标以及面向 `$factor-backtest` 的确定性信号交接。组合构建、换手、交易成本、执行价格和收益计算由 `$factor-backtest` 负责，具体边界见 [下游评估](references/downstream_evaluation.md)。

## 研究边界

- **数据来源**：仓库不附带真实市场、因子或标签数据；示例脚本只生成确定性的合成数据。真实数据由使用者提供，并由使用者负责数据许可、访问授权和合规使用。
- **核心假设**：输入因子在对应观察时点真实可得，未来收益标签与观察日正确对齐，Train、Valid、OOS 和 `embargo_bars` 能够隔离前瞻信息，股票池与交易日历定义在研究区间内保持可审计。
- **结果依赖**：筛选结果和回测结果取决于数据质量、因子覆盖、标签口径、股票池、预处理、模型与搜索参数，以及下游交易成本、执行价格和组合约束。
- **方法边界**：本 Skill 输出因子集合、标签层指标和冻结 OOS 信号；组合收益、风险、持仓和换手由 `$factor-backtest` 独立计算与验证。
- **用途**：输出仅用于量化研究、教育和方法论评估，不构成投资建议、调仓建议、生产部署许可或收益承诺。
