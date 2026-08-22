# 残差引导多路径因子选择算法

## 目录

- [1. 研究目标](#1-研究目标)
- [2. 数据表示与时间区域](#2-数据表示与时间区域)
- [3. 预处理](#3-预处理)
- [4. Ridge 残差候选生成](#4-ridge-残差候选生成)
- [5. 多路径 Beam Search](#5-多路径-beam-search)
- [6. LightGBM OOF 残差 Beam](#6-lightgbm-oof-残差-beam)
- [7. 穷举式联合 CV 因子池](#7-穷举式联合-cv-因子池)
- [8. 缓存、确定性与恢复](#8-缓存确定性与恢复)
- [9. 冻结与 OOS 评估](#9-冻结与-oos-评估)
- [10. 功能模块](#10-功能模块)
- [11. 最小命令](#11-最小命令)

## 1. 研究目标

给定候选因子全集 `F` 和未来收益标签 `y`，方法搜索一个较小的因子子集 `S`，其中 `S` 属于 `F`。搜索同时关注两类信息：

1. 当前模型尚未解释的横截面收益结构；
2. 新因子加入后，完整因子组合在因果时间折上的联合预测能力。

因此，候选生成由残差互补性驱动，路径保留与最终检查点由时序验证证据决定。每次增加因子后都重新联合拟合完整集合，因子系数和非线性交互可以随集合变化而更新。

## 2. 数据表示与时间区域

标签和原始因子均使用宽表 Parquet，索引为交易日，列为标的代码。运行时将宽表堆叠为 `(datetime, symbol)` MultiIndex 面板。

配置定义三个顺序且不重叠的时间区域：

- `Train`：单路径模型拟合和候选残差计算；
- `Valid`：单路径检查点选择，并与 Train 合并为 Beam 的开发期；
- `OOS`：仅在开发期结果冻结后用于显式评估。

Beam 与联合 CV 因子池在 `Train + Valid` 开发期内使用多个因果时间折。每个折包含：

- `fit_start`、`fit_end`：模型拟合区间；
- `score_start`、`score_end`：严格晚于拟合区间的评分区间。

`embargo_bars = h` 表示从 Train、Valid 以及每个 CV 拟合区间的尾部删除最后 `h` 个不同交易日。该值应依据前瞻标签的持有期或重叠期设置。

## 3. 预处理

### 3.1 横截面变换

当 `factor_transform: cross_sectional` 时，对每个交易日独立执行：

1. 将正负无穷转换为缺失值；
2. 依据 `winsor_lower` 和 `winsor_upper` 进行分位数缩尾；
3. 当 `cross_sectional_zscore: true` 时，执行当日去均值并除以总体标准差；
4. 当有效标的少于 `min_cross_section` 时，将该日视为无效；
5. 将处理后的缺失值填为 0。

### 3.2 滚动变换

当 `factor_transform: rolling_median_zscore` 时，对每个标的独立计算：

```text
z(i,t) = [x(i,t) - rolling_median(i,t)] / rolling_std(i,t)
```

其中窗口长度由 `rolling_window` 指定，最少样本数由 `rolling_min_periods` 指定，结果裁剪到 `[-rolling_clip, rolling_clip]`，缺失值填为 0。

### 3.3 标签变换

`label_transform` 可取：

- `raw`：保留原始收益标签；
- `cross_sectional_rank`：将每日标签转为百分位秩并减去 0.5。

`demean_label: true` 会进一步减去当日横截面均值。有效标签数少于 `min_cross_section` 的日期不参与训练或评分。

## 4. Ridge 残差候选生成

设当前因子集合为 `S`，对应设计矩阵为 `X_S`。Ridge 模型求解：

```text
min_(beta0,beta) sum_i w_i [y_i - beta0 - X_S,i beta]^2
                 + alpha * ||beta||_2^2
```

其中 `ridge_alpha = alpha`，截距 `beta0` 不受惩罚。当 `equal_date_weight: true` 时，同一交易日的每个样本权重为当日样本数的倒数，使每个交易日具有相同总权重。

当前训练残差为：

```text
r_S = y - y_hat_S
```

对剩余候选因子 `x_j`，在每个交易日 `t` 计算横截面相关系数：

```text
ic(j,t) = corr_cs(x_j,t, r_S,t)
signed_mean_ic(j) = mean_t ic(j,t)
residual_score(j) = abs(signed_mean_ic(j))
```

`score_method` 决定使用 Pearson 或其他已支持的相关方法。向量化快速路径用于 Pearson。负残差 IC 不会被丢弃：排序使用绝对值，`signed_mean_ic` 单独保留以记录方向。

单路径 `run` 每次加入残差分数最高的一个因子，在 Train 上重拟合，并以 Valid mean IC 选择最佳检查点。`min_residual_score`、`max_factors`、`min_delta`、`patience` 和 `min_factors_before_stopping` 共同控制停止。

## 5. 多路径 Beam Search

### 5.1 根节点

Ridge 在 `deterministic_roots: true` 时将全部单因子集合作为 super-root 候选，并计算根节点目标。LightGBM 则先按单因子与开发期标签的绝对逐日横截面相关性排序，保留前 `root_residual_shortlist` 个候选，再计算根节点 CV。两种模型随后都使用 `root_width`、`width` 和路径多样性规则形成第一层 Beam。

`deterministic_roots: false` 时，搜索从 `selection.initial_factor` 或指定随机种子的随机初始因子开始。`run-many-beam` 可在共享预处理特征上运行多个互不重复的随机起点。

### 5.2 路径扩展

在深度 `d`，对每个父路径 `S_p`：

1. 拟合当前联合模型并构造残差；
2. 计算所有未选候选的 `residual_score`；
3. 取前 `branch_width` 个候选；
4. 形成父路径与候选因子的并集；
5. 按 `search_objective` 对新集合计算路径目标。

`search_objective: cv` 对扩展集合立即执行联合时序 CV；Ridge `search_objective: residual` 使用开发期加权 Ridge `R^2`，不以 CV 决定路径保留。

相同因子集合按无序集合去重。每层最多保留 `width` 条路径，最大深度为 `final_depth`。

### 5.3 联合时序 CV

对每个候选因子集合和每个 `ridge_alpha`，算法在各因果折的 fit 区间拟合，在后续 score 区间计算每日横截面预测 IC。设共有 `K` 个有效折得分，则：

```text
cv_mean_ic = mean(q)
cv_std_ic  = std(q)
cv_min_ic  = min(q)
cv_se      = cv_std_ic / sqrt(K)

cv_score =
    cv_mean_ic
    - stability_penalty * cv_std_ic
    + min_year_weight * cv_min_ic
    - complexity_penalty * factor_count
```

多个 Ridge alpha 中选择 `cv_score` 最高者；并列时优先较小的 alpha。

### 5.4 搜索优先级与多样性

当 `search_objective: cv` 时，基础路径优先级为 `cv_score`，可选增强项为：

```text
priority =
    cv_score
    + trend_weight * mean(recent_cv_improvements)
    + continuation_weight * next_residual_probe
```

`trend_window` 控制近期增量窗口，`continuation_probe_width` 控制执行下一步互补性探测的候选数。Ridge `search_objective: residual` 直接以开发期加权 Ridge `R^2` 作为路径优先级，不应用趋势或延续探测增强项。

保留路径时计算因子集合的 Jaccard 相似度：

```text
J(A,B) = |A intersect B| / |A union B|
```

优先保留与已选路径相似度不超过 `diversity_max_jaccard` 的高分路径；若数量不足，再按优先级补足 Beam。

### 5.5 停止与检查点

`early_stopping_patience` 和 `early_stopping_min_delta` 依据每层最佳搜索目标控制提前停止。搜索结束后，每一深度取该层最佳前沿路径形成检查点序列。

`search_objective: cv` 时支持三类最终选择：

- 默认：选择 `cv_score` 峰值；
- `one_standard_error: true`：在峰值减去其标准误的范围内选择较浅检查点；
- `deep_selection_tolerance`：在峰值容差内选择因子数更多的检查点；设置后优先于 `one_standard_error`。

`search_objective: residual` 时，路径扩展以开发期加权 Ridge 残差 `R^2` 为目标，并在 `residual_selection_depth` 冻结指定深度；各深度仍计算联合 CV 以形成可比较的检查点证据。

## 6. LightGBM OOF 残差 Beam

当 `model.type: lgbm` 时，候选生成不能使用完整开发期样本内预测。对每个当前路径 `S`，算法按 `beam.cv_folds` 执行：

1. 在折的 fit 区间训练 LightGBM；
2. 在严格晚于 fit 的 score 区间预测；
3. 写入 `y - y_hat`，得到该区间残差；
4. 拼接所有 score 区间，形成 OOF 残差向量；
5. 使用 OOF 残差计算候选因子的逐日横截面残差 IC。

联合因子集合仍通过同一组时序折评分。可设置 `screen_fold_count` 和 `full_cv_candidates_per_parent`，先用部分近期折筛选候选，再对保留候选执行完整 CV。`cv_jobs * model_threads` 决定并行资源规模。

最终模型可使用 `validation_days` 从开发期尾部建立因果验证段，通过 `early_stopping_rounds` 确定迭代数，然后在完整开发期按该迭代数重拟合。

## 7. 穷举式联合 CV 因子池

`run-pool` 从空集合开始。每一步对每个尚未提出的候选分别构造增强集合，并执行完整联合时序 CV。得分最高的候选用于更新因子池。

当 `pool_capacity: null` 时，集合单调增长。当设置正整数容量后，若增强集合超过容量，则在完整开发期用 `pruning_alpha` 拟合 Ridge，并删除绝对系数最小的因子。每个候选最多被正式提出一次；容量裁剪后被删除的已提出因子不会重新进入候选队列。候选排名、删除因子、CV 分折指标和增量均写入历史文件。

`max_steps`、`min_delta` 和 `patience` 控制搜索长度与停止。

## 8. 缓存、确定性与恢复

预处理特征缓存使用 `(datetime, symbol)` MultiIndex 和按固定顺序排列的因子列。每个缓存必须具有同名 `.meta.json` manifest。加载时校验：

- 面板键和索引哈希；
- 有序因子名；
- 股票池；
- 时间切分；
- 预处理配置；
- 行数与日期范围。

`selection.random_seed`、LightGBM `random_state`、有序候选名称和确定性排序用于保证可复现性。Beam 可通过 `checkpoint_path` 持续写出前沿，并通过 `resume_history` 恢复最后一个已保留深度。

## 9. 冻结与 OOS 评估

搜索输出的 `summary.json.selected_factors` 是冻结因子集合。`evaluate-oos` 要求运行目录同时存在 `summary.json` 和 `config.json`，并逐项比较数据、切分、股票池、预处理、模型、选择、Beam 和因子池配置。

验证通过后，算法在完整 `Train + Valid` 上按冻结模型设置重拟合，并只对 OOS 生成：

- `oos_predictions.parquet`；
- `oos_evaluation.json`。

该步骤不构造持仓、不计算交易成本，也不执行收益回测。

## 10. 功能模块

```text
scripts/run_factor_selection.py
    因子物化、搜索、缓存校验与 OOS 评估入口

scripts/run_selection_backtest.py
    冻结 OOS 信号导出与回测 Skill 交接入口

scripts/residual_factor_selection/
    cli.py          子命令解析
    config.py       YAML 路径解析与配置约束
    data.py         宽表读取、股票池、切分、embargo 与时间折
    preprocess.py   因子和标签变换
    ridge.py        加权 Ridge 求解与预测
    metrics.py      每日 IC、ICIR 和误差指标
    selector.py     单路径残差前向选择与向量化候选评分
    beam.py         Ridge Beam、联合 CV、路径多样性与检查点
    lgbm_beam.py    LightGBM OOF 残差和两阶段候选评分
    pool.py         穷举式联合 CV 因子池
    cache.py        特征缓存 manifest 与一致性校验
    materialize.py  因子文件物化
    serialization.py JSON 安全序列化
    experiment.py   数据准备、运行编排、输出与 OOS
    backtest_adapter.py 信号校验、ticker 映射、handoff 生成与兼容执行
```

## 11. 最小命令

```bash
python examples/generate_residual_search_toy_data.py

python scripts/run_factor_selection.py \
  --config examples/residual_search/toy_config.yaml run-beam

python scripts/run_factor_selection.py \
  --config examples/residual_search/toy_config.yaml evaluate-oos \
  --run-dir <frozen-run-directory>
```
