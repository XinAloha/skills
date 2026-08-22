# 相关性门控 —— 防因子换皮重复

A 股量价因子族很容易"换皮重复"（5 日反转 vs 1 日反转、波动率 vs 振幅 vs MAX）。高相关性的因子加进 ridge / IC_IR 加权时只带共线性，不带新信息。

## 触发条件

`add_factor` 和 `modify_factor` 时，runner 在跑 `alpha.run` 之前**先单独算所有因子两两的截面 spearman 相关性**。对新因子检查：

| \|ρ\|（与任一旧因子） | 行为 |
|---|---|
| ≥ **0.85** | **直接 PermissionError**，CRASH 后自动 revert，写 `journal/last_failed/correlation_{iter}.txt` |
| 0.60 ~ 0.85 | 警告打印，但允许继续；跑完按主分决定 ACCEPT/REJECT |
| < 0.60 | 静默通过 |

## 计算方式

```python
def factor_correlation(f1: pd.DataFrame, f2: pd.DataFrame) -> float:
    """两份截面因子的整体 spearman ρ。"""
    x = f1.rank(axis=1).values.flatten()
    y = f2.rank(axis=1).values.flatten()
    mask = ~(np.isnan(x) | np.isnan(y))
    if mask.sum() < 100:
        return np.nan
    return float(np.corrcoef(x[mask], y[mask])[0, 1])
```

注：取**截面 rank 后整体 Pearson**（等价于 Spearman），不是逐日 IC 间相关。

## 命中 ≥ 0.85 怎么办

**不要加 `# noqa` 绕过**。三个改设计方向：

1. **换计算方式**：如 `vol_20` 已存在，新因子从"绝对波动"改成"相对波动 vol_20 / mean_vol_120"
2. **换输入**：反转用 `close` 已有，新因子改用 `vwap`
3. **换横截面定义**：全市场已有，新因子改成"行业内 z-score"

## 何时绕过

如果你确信高相关因子有**独立价值**（如做风险因子做对冲），改 `op_type` = `combine_method`，在组合层面专门处理（GLS 残差化 / 因子正交化），而不是当 alpha 因子加。

## 阈值的来源

- 0.85 是"严格门槛"：高于此几乎一定是同质化
- 0.60 是"软警告"：可能合理（如不同窗口的同一概念），但要在 ITER_NOTE 里说清楚
- 这两个阈值在不同市场可能要调（美股波动小，可能要降到 0.80 / 0.50）

> 参考实现：`auto_research_alpha/program.md §12` + runner 的 `_check_correlation()`。
