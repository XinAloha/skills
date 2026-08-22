# 双 IC 对照（IC analysis 基础）

> 详见 factor-evaluate skill 的 `references/dual-ic.md`，这里给 IC analysis 视角下的"诊断输入"。

## 通用计算

```python
import numpy as np
import pandas as pd

def both_ic(signal: pd.DataFrame, fwd_ret: pd.DataFrame) -> dict:
    aligned = signal.reindex_like(fwd_ret)
    rank_ic = _xs_corr(aligned.rank(axis=1), fwd_ret.rank(axis=1))
    pearson_ic = _xs_corr(aligned, fwd_ret)
    return {
        "rank_ic_mean":      rank_ic.mean(),
        "rank_ic_ir":        rank_ic.mean() / rank_ic.std() * np.sqrt(252),
        "pearson_ic_mean":   pearson_ic.mean(),
        "pearson_ic_ir":     pearson_ic.mean() / pearson_ic.std() * np.sqrt(252),
        "rank_ic_series":    rank_ic,
        "pearson_ic_series": pearson_ic,
    }

def _xs_corr(x: pd.DataFrame, y: pd.DataFrame) -> pd.Series:
    """逐日截面 Pearson。"""
    x = x.sub(x.mean(axis=1), axis=0)
    y = y.sub(y.mean(axis=1), axis=0)
    num = (x * y).sum(axis=1)
    den = np.sqrt((x ** 2).sum(axis=1) * (y ** 2).sum(axis=1))
    return num / den.replace(0, np.nan)
```

## 对照诊断表

| 模式 | 解读 | 行动 |
|---|---|---|
| rank IC 高、Pearson IC 低 | **排序对，量级失真**（少数极端值主导） | winsorize 更严，或最终用 rank 信号 |
| Pearson IC 高、rank IC 低 | **被极端值主导**，整体相关性弱 | 检查异常股、加 MAD 过滤 |
| 两者都高且接近 | **分布良好** | 健康，进入下一步分析 |
| 两者都低（< 0.02） | **无效** | 删除或重设计 |

## 量级参考（A 股截面）

| 指标 | 弱 | 中 | 强 | 极强（怀疑 bug） |
|---|---|---|---|---|
| rank IC mean | < 0.02 | 0.02 ~ 0.04 | 0.04 ~ 0.08 | > 0.10 |
| rank IC_IR | < 1.0 | 1.0 ~ 2.5 | 2.5 ~ 5.0 | > 6.0 |
| Pearson IC | 通常 ≈ rank IC × 0.7 ~ 0.9 | | | |

## IC > 0 占比（额外的稳定性指标）

```python
ic_positive_ratio = (rank_ic > 0).mean()
```

| 占比 | 解读 |
|---|---|
| > 65% | 信号稳定有效 |
| 55% ~ 65% | 一般 |
| 50% ~ 55% | 信号弱（接近抛硬币） |
| < 50% | 多半反向，考虑取负 |
