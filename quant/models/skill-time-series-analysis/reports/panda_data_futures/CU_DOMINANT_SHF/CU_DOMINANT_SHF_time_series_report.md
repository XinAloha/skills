# CU_DOMINANT.SHF 自动时序检测报告

## 一句话结论

该序列的检测信号并不单一，适合先做状态识别和风险过滤，再决定具体投研方向。

## 时间序列性质

### 平稳性分析

ADF p-value=0.5097 未拒绝单位根，KPSS p-value=0.0225 拒绝平稳假设，整体更像趋势非平稳序列。

### 记忆性分析

Hurst=0.5496，接近随机游走区间，单独依赖记忆性证据需要谨慎。

### 趋势性分析

最新窗口被分类为 `weak trend or counter-trend`，趋势性不够明确，应谨慎使用单一趋势假设。

### 分布形态分析

KDE/QQ 显示主要尾部特征为 `fat_tail`，偏度特征为 `symmetric`，最大 QQ 偏离约为 0.1514。这说明分布形态会影响止损、仓位和风险预算设计。

## 量化投研建议

### 策略方向

- 适合进一步研究多状态过滤、趋势与反转切换、低置信度环境下的仓位控制等投研方向。
- 收益分布存在厚尾特征时，可补充波动率目标、尾部风险过滤和极端行情压力测试。

### 因子方向

- 状态识别类因子：Hurst 状态、波动分位、ADF/KPSS 组合标签和 regime filter。
- 风险类因子：尾部波动、QQ 偏离、极端收益频率和下行波动。

## 检测证据

### Stationarity / Hurst / ADF / KPSS

| window_size | hurst | adf_pvalue | kpss_pvalue | trend_type | min_lag | effective_max_lag | kpss_warning |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 60 | 0.7389 | 0.4414 | 0.0499 | strong trend, non-stationary (trend strategies) | 10 | 20 |  |
| 120 | 0.5923 | 0.1036 | 0.0476 | strong trend, non-stationary (trend strategies) | 20 | 40 |  |
| 180 | 0.5496 | 0.5097 | 0.0225 | weak trend or counter-trend | 30 | 60 |  |

## Log Diff 分析

除原始价格序列外，报告还分析 `log(price).diff(lag)` 后的时间序列；这里以 Log diff 1/5/10 为例观察不同持有尺度上的平稳性、记忆性和分布形态。

| lag | label | n_obs | hurst | adf_pvalue | kpss_pvalue | trend_type | tail_feature | skew_feature | kurtosis | skewness | qq_deviation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Log diff 1 | 241 | 0.5547 | 0.0000 | 0.1000 | trending but stationary (short-term trend possible) | fat_tail | symmetric | 1.7606 | -0.1673 | 0.1514 |
| 5 | Log diff 5 | 237 | 0.6781 | 0.0018 | 0.0862 | trending but stationary (short-term trend possible) | near_normal | symmetric | 0.5532 | -0.0892 | 0.0909 |
| 10 | Log diff 10 | 232 | 0.7163 | 0.0648 | 0.0395 | strong trend, non-stationary (trend strategies) | near_normal | symmetric | -0.1750 | -0.0933 | 0.0888 |

### Log Diff KDE / QQ

#### Log Diff KDE Diagnostics

| lag | label | n_obs | peak_height | peak_position | num_peaks | tail_feature | skew_feature | statistical_kurtosis | statistical_skewness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Log diff 1 | 241 | 0.4552 | 0.0551 | 1 | fat_tail | symmetric | 1.7606 | -0.1673 |
| 5 | Log diff 5 | 237 | 0.4325 | -0.1552 | 1 | near_normal | symmetric | 0.5532 | -0.0892 |
| 10 | Log diff 10 | 232 | 0.4396 | -0.0350 | 1 | near_normal | symmetric | -0.1750 | -0.0933 |

#### Log Diff QQ Diagnostics

| lag | label | n_obs | kurtosis | skewness | qq_deviation |
| --- | --- | --- | --- | --- | --- |
| 1 | Log diff 1 | 241 | 1.7606 | -0.1673 | 0.1514 |
| 5 | Log diff 5 | 237 | 0.5532 | -0.0892 | 0.0909 |
| 10 | Log diff 10 | 232 | -0.1750 | -0.0933 | 0.0888 |

### KDE / QQ

#### KDE Diagnostics

| index | peak_height | peak_position | num_peaks | tail_feature | skew_feature | statistical_kurtosis | statistical_skewness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.4552 | 0.0551 | 1 | fat_tail | symmetric | 1.7606 | -0.1673 |
| 5 | 0.4325 | -0.1552 | 1 | near_normal | symmetric | 0.5532 | -0.0892 |
| 20 | 0.4467 | -0.0551 | 1 | near_normal | symmetric | -0.0885 | -0.1466 |

#### QQ Diagnostics

| index | kurtosis | skewness | qq_deviation |
| --- | --- | --- | --- |
| 1 | 1.7606 | -0.1673 | 0.1514 |
| 5 | 0.5532 | -0.0892 | 0.0909 |
| 20 | -0.0885 | -0.1466 | 0.0966 |

## 图表

### KDE

![KDE](distribution_kde_dist.png)

### QQ

![QQ](distribution_qq_plot.png)

## 注意事项

- 这些检测结果用于确定投研方向，不能直接作为下单依据。
- 厚尾分布意味着极端波动更常见，后续研究需要单独评估尾部风险。
