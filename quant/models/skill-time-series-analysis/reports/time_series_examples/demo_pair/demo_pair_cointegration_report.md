# Demo Pair 协整检测报告

## 一句话结论

Engle-Granger 检测显示残差 ADF p-value=0.0000，两条序列在当前样本中存在协整证据。

## Pair / 双序列协整检测结果

### Engle-Granger 回归

- alpha: `3.0714`
- beta: `1.5993`
- is_cointegrated: `True`

### 残差平稳性

残差 ADF p-value=0.0000，用于判断两条序列线性组合后的残差是否平稳。

| Metric | Value |
|---|---:|
| `alpha` | 3.0714 |
| `beta` | 1.5993 |
| `adf_statistic` | -8.7408 |
| `adf_pvalue` | 0.0000 |
| `adf_lags` | 2 |
| `adf_critical_values` | {'1%': -3.467845319799907, '5%': -2.878011745497439, '10%': -2.575551186759871} |
| `is_cointegrated` | True |
| `n_obs` | 180 |
| `r_squared` | 0.9999 |

### Residual Summary

| Metric | Value |
|---|---:|
| `residual_mean` | 0.0000 |
| `residual_std` | 0.1728 |
| `residual_min` | -0.4070 |
| `residual_max` | 0.6018 |

## 量化投研建议

- 适合进一步研究配对价差、残差 z-score、协整关系稳定性、滚动 beta 和残差风险过滤等投研方向。
- 协整检测只是研究入口，不是买卖建议，也不是执行依据。

## 注意事项

- Engle-Granger 对样本区间、回归方向和结构变化敏感。
- 后续研究应检查滚动窗口下 alpha、beta 和残差 ADF 是否稳定。
