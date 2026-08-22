# 因子组合权重方法

## 输入契约

所有输入因子必须满足：

- 同一 `horizon`
- 同一 `label_kind`
- 同一股票池和交易 mask
- 每日截面 z-score
- 已有单因子 `ScoreReport`
- 不使用 test 段信息筛选或调权

## 基础构造

```python
import numpy as np
import pandas as pd


def xs_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """逐日截面标准化。"""
    return df.sub(df.mean(axis=1), axis=0).div(df.std(axis=1).replace(0, np.nan), axis=0)


def combine_factors(factors: dict[str, pd.DataFrame],
                    weights: dict[str, float]) -> pd.DataFrame:
    """factors: factor_name -> [date × symbol] DataFrame。"""
    names = [name for name in weights if name in factors]
    total_w = sum(abs(weights[name]) for name in names)
    if total_w == 0:
        raise ValueError("All factor weights are zero")

    out = None
    for name in names:
        signal = xs_zscore(factors[name])
        contribution = signal * (weights[name] / total_w)
        out = contribution if out is None else out.add(contribution, fill_value=np.nan)
    return xs_zscore(out)
```

## 权重方案

### 1. Equal weight

适合样本短、因子数量少、质量差异不大时。它是所有复杂权重的基准线。

```python
weights = {name: 1.0 / len(selected) for name in selected}
```

### 2. Score-weighted

用 `factor-evaluate` 主分做权重，但要截断，避免单个因子支配组合。

```python
def score_weight(reports: dict, floor: float = 0.0,
                 cap: float = 0.35) -> dict[str, float]:
    raw = {k: max(floor, reports[k]["score"]) for k in reports}
    s = sum(raw.values())
    if s <= 0:
        return {k: 1.0 / len(raw) for k in raw}
    w = {k: v / s for k, v in raw.items()}
    w = {k: min(cap, v) for k, v in w.items()}
    s2 = sum(w.values())
    return {k: v / s2 for k, v in w.items()}
```

### 3. IR-weighted

适合强调 IC 稳定性，而不是短期收益最大化。

```python
def ir_weight(reports: dict, cap: float = 0.35) -> dict[str, float]:
    raw = {k: max(0.0, reports[k]["rank_ic_ir"]) for k in reports}
    s = sum(raw.values())
    if s <= 0:
        return {k: 1.0 / len(raw) for k in raw}
    w = {k: min(cap, v / s) for k, v in raw.items()}
    s2 = sum(w.values())
    return {k: v / s2 for k, v in w.items()}
```

### 4. Constrained optimizer

优化器只能在 train / val 上使用，且必须有约束：

- `sum(abs(w)) <= 1`
- 单因子权重上限，例如 `abs(w_i) <= 0.35`
- 高 turnover 因子加惩罚
- 高相关因子加惩罚
- 不允许因为 val 单期极端表现给出集中权重

目标函数建议：

```
maximize:
  expected_score(w)
  - lambda_corr * portfolio_correlation_penalty(w)
  - lambda_turn * turnover_penalty(w)
  - lambda_concentration * sum(w_i^2)
```

## 去冗余规则

先对因子相关矩阵聚类，再组合：

| 条件 | 处理 |
|---|---|
| rank corr > 0.8 | 同一簇，默认只保留 score 最高者 |
| rank corr 0.6~0.8 | 进入组合前考虑 factor-orthogonalize |
| top-bucket overlap > 70% | 视为交易层面重复 |
| corr < 0.4 且 score > 0 | 优先保留 |

## 稳定性检查

组合后必须做：

- 分年度权重敏感性
- 分年度 IC / Sharpe
- top-bucket overlap 与单因子对比
- turnover 是否高于所有单因子的合理区间
- 去掉任一单因子的 leave-one-out 影响
