# Top 篮 Jaccard — 信号惯性 vs 噪声

**两个相邻日的 Top 10% 股票池重合度** —— 衡量信号的"惯性 vs 噪声"。

## 算法

```python
import numpy as np
import pandas as pd

def top_basket_jaccard(signal: pd.DataFrame, top_pct: float = 0.10) -> pd.Series:
    """每日 Top X% 与前一日的 Jaccard 系数 ∈ [0, 1]。"""
    rank = signal.rank(axis=1, pct=True, ascending=False)
    top = rank <= top_pct
    jacs = []
    dates = []
    for i in range(1, len(top)):
        a = set(top.columns[top.iloc[i-1].values])
        b = set(top.columns[top.iloc[i].values])
        if not a and not b:
            continue
        jacs.append(len(a & b) / max(len(a | b), 1))
        dates.append(top.index[i])
    return pd.Series(jacs, index=dates)
```

## 解读表

| 平均 Jaccard | 含义 | 换手成本 | 适合 horizon |
|---|---|---|---|
| > 0.95 | 信号几乎不变（基本面慢变量） | 极低 | H=20+ |
| 0.80 ~ 0.95 | 中频信号 | 中 | H=5 ~ 20 |
| 0.50 ~ 0.80 | 高频信号 | 高 | H=1 ~ 5 |
| < 0.50 | 噪声主导 | 极高 | 多半实盘亏，重设计 |

## 与换手率的对应

```
理论换手 ≈ 2 × (1 - Jaccard) / horizon
H=5、Jaccard=0.85 → 单日换手 ~6%、年化 ~15
H=5、Jaccard=0.50 → 单日换手 ~20%、年化 ~50
```

实际回测换手会比这个略高（涨跌停剔除、新成分股替换等会带来额外换手）。

## 应用场景

### 场景 1：诊断高换手因子

回测换手率高得离谱（年化 100+）→ 算 Jaccard，看是不是 < 0.5 → 信号本身就是噪声主导，不是回测 bug。

### 场景 2：选 horizon

不同 horizon 的 Jaccard 不一样 —— 但单看 Jaccard 不够，要结合 IC decay。

### 场景 3：检测信号崩溃

```python
jacs = top_basket_jaccard(signal)
jacs.rolling(60).mean().plot()  # 60 日滚动 Jaccard
```

如果某段时间 Jaccard 突降 → 信号性质变了，可能是市场 regime 切换。

## 反模式

- ❌ Jaccard = 1.00（连续多日完全相同的 Top 篮）→ 信号没在更新（NaN 或 stale data）
- ❌ Jaccard 大小不算就直接看回测换手 → 看不出"是信号在动"还是"是市场流动性在变"
