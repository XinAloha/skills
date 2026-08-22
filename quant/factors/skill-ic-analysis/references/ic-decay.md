# IC Decay — 信息衰减曲线

不同 horizon 下的 IC，画一条衰减曲线。这是**决定 horizon 的核心依据**。

## 算法

```python
import numpy as np
import pandas as pd

def ic_decay(signal: pd.DataFrame, panel: pd.DataFrame,
             horizons: list = [1, 3, 5, 10, 20, 40, 60]) -> pd.DataFrame:
    """对每个 H 算 rank IC mean / IR / 正占比。"""
    open_p = panel.pivot(index="date", columns="symbol", values="open").sort_index()
    rows = []
    for h in horizons:
        # T+1 开盘到 T+1+h 开盘
        fwd = open_p.shift(-1).pct_change(h).shift(-h)
        fwd = fwd.sub(fwd.mean(axis=1), axis=0)  # market-neutral
        ic = _xs_corr(signal.rank(axis=1), fwd.rank(axis=1))
        rows.append({
            "horizon":  h,
            "ic_mean":  float(ic.mean()),
            "ic_ir":    float(ic.mean() / ic.std() * np.sqrt(252 / h)),
            "ic_pos":   float((ic > 0).mean()),
        })
    return pd.DataFrame(rows).set_index("horizon")
```

注：IC_IR 的年化因子用 `√(252/h)` 而不是 `√252` —— 因为 H 期 IC 之间不独立。

## 衰减形态分类

| 形态 | 因子类型 | 推荐 horizon |
|---|---|---|
| H=1 IC 最高，H=5 减半，H=20 ≈ 0 | **高频信号**（流动性、反转、价量背离） | H=1 或 3 |
| H=5 ~ H=20 平台，H=60 才衰 | **中频信号**（动量、低波） | H=10 或 20 |
| H=1 弱，H=20 才到峰值 | **低频信号**（基本面、估值） | H=20 或 60 |
| 全段都低（max IC < 0.02） | **因子无效** | 弃 |
| H=1 高、H=3 反向 | **短期反转嫁接，中期失效** | 只做 H=1 |
| H=20 比 H=10 还高且持续 | **超低频信号** | H=20 或 H=40 |

## 画图骨架

```python
import matplotlib.pyplot as plt

def plot_ic_decay(decay_df: pd.DataFrame, out: str = "ic_decay.png"):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    decay_df["ic_mean"].plot(ax=axes[0], marker="o", color="steelblue")
    axes[0].axhline(0, color="k", lw=0.5)
    axes[0].set_xlabel("Horizon (days)")
    axes[0].set_ylabel("rank IC mean")
    axes[0].set_title("IC decay")
    axes[0].grid(alpha=0.3)

    decay_df["ic_ir"].plot(ax=axes[1], marker="o", color="darkorange")
    axes[1].set_xlabel("Horizon (days)")
    axes[1].set_ylabel("rank IC_IR")
    axes[1].set_title("IC_IR decay")
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(out, dpi=120)
    plt.close()
```

## 用 decay 做 horizon 选择

通常**选 IC_IR 峰值附近**的 horizon，但要权衡换手成本：

- IC_IR(H=10) = 2.0、IC_IR(H=20) = 2.05 → 选 H=20，换手减半
- IC_IR(H=5) = 2.5、IC_IR(H=20) = 2.0 → 选 H=5（IC 提升 25% 值得高换手）

经验法则：**只有 IC_IR 提升 > 15%，才值得换更短的 horizon**（因为换手翻倍，手续费会吃掉很多收益）。
