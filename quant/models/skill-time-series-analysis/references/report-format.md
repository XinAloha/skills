# Report Format

Use `generate_time_series_report(...)` for this structure:

```markdown
# <title>

## 一句话结论

<plain-language conclusion>

## 时间序列性质

### 平稳性分析

### 记忆性分析

### 趋势性分析

### 分布形态分析

## 量化投研建议

### 策略方向

### 因子方向

## 检测证据

### Stationarity / Hurst / ADF / KPSS

## Log Diff 分析

<Log diff 1/5/10 stationarity, memory, and distribution summary table>

### Log Diff KDE / QQ

#### Log Diff KDE Diagnostics

<KDE peak, tail, and skew table for Log diff 1/5/10>

#### Log Diff QQ Diagnostics

<QQ kurtosis, skewness, and deviation table for Log diff 1/5/10>

### KDE / QQ

## 图表

## 注意事项
```

Use `generate_spread_report(...)` for spread or price-difference reports:

```markdown
# <title>

## 一句话结论

## Spread / 价差检测结果

### 半衰期

### Hurst / ADF / KPSS

## 量化投研建议

## 检测证据

### KDE / QQ

## 图表

## 注意事项
```

Use `generate_pair_cointegration_report(...)` for two related series:

```markdown
# <title>

## 一句话结论

## Pair / 双序列协整检测结果

### Engle-Granger 回归

### 残差平稳性

### Residual Summary

## 量化投研建议

## 注意事项
```

Keep conclusions before evidence. Strategy and factor sections must describe
research directions only, never direct order instructions.
