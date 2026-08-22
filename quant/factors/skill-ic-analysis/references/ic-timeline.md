# IC 时序累计图 — 找崩溃点 / 平台期

**任何因子都要画 IC 时序累计图**，找失效段和平台期。

## 算法

```python
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def plot_ic_timeline(rank_ic: pd.Series, out: str = "ic_timeline.png",
                     rolling_window: int = 60):
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)

    # ① 日频 IC 柱状（红绿）
    colors = np.where(rank_ic > 0, "g", "r")
    axes[0].bar(rank_ic.index, rank_ic.values, width=1, color=colors, alpha=0.6)
    axes[0].axhline(0, color="k", lw=0.5)
    axes[0].set_title(f"Daily rank IC (mean={rank_ic.mean():.3f})")
    axes[0].grid(alpha=0.3)

    # ② 累计 IC
    rank_ic.cumsum().plot(ax=axes[1], color="navy", lw=1.5)
    axes[1].set_title("Cumulative rank IC")
    axes[1].grid(alpha=0.3)

    # ③ 滚动 IC（60 日均值）
    rolled = rank_ic.rolling(rolling_window).mean()
    rolled.plot(ax=axes[2], color="purple")
    axes[2].axhline(0, color="k", lw=0.5)
    axes[2].fill_between(rolled.index, rolled, 0,
                          where=rolled > 0, color="g", alpha=0.2)
    axes[2].fill_between(rolled.index, rolled, 0,
                          where=rolled < 0, color="r", alpha=0.2)
    axes[2].set_title(f"Rolling {rolling_window}-day IC mean")
    axes[2].grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(out, dpi=120)
    plt.close()
```

## 累计 IC 曲线形态判读

| 形态 | 解读 |
|---|---|
| **一路上扬** | 因子稳定有效，最理想 |
| **阶段平台 + 阶段斜坡** | 因子在某些行情有效（如反转因子在震荡市） |
| **中段大段下跌** | 因子在某段时间反向（典型 2022-2023 反转因子） |
| **单段斜坡占主导** | 因子靠某一段"行情风格"获利，可能不再持续（局部 alpha） |
| **阶梯式跳跃** | 信号集中在某些事件日（如季报、年报、大事件） |

## 滚动 IC 曲线判读

60 日滚动 IC 比累计 IC 更敏感，能看到**最近的因子状态**：

| 形态 | 解读 |
|---|---|
| 持续 > 0 | 因子健康 |
| 最近 6 个月持续 < 0 | 因子可能已失效，考虑下架 |
| 在 ±0 附近震荡 | 行情依赖型因子，信号弱 |

## 应用场景

### 场景 1：因子下架决策

如果累计 IC 曲线在最近半年掉头向下 → 强烈信号，考虑下架或暂停使用。

### 场景 2：发现局部 alpha

如果累计 IC 90% 的提升来自 2020 年那一波牛市 → 不要单独用这个因子，要和反向因子组合。

### 场景 3：识别 regime shift

如果时序图在某个时点（如 2022-04 注册制改革）前后 IC 性质完全不同 → 有 regime change，需要分段研究。

## 反模式

- ❌ 不画时序图，只看整体 IC mean → 看不到失效段
- ❌ 看了发现"前 5 年好、近 1 年差"还坚持用 → 该下架了
- ❌ 认为"累计上扬"等于"实盘必赚" → 别忘了未来不一定像过去
