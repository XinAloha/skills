# Layer 1：量化盘点

复盘的第一层 —— 把"已经做了什么"量化出来。

## 数据源

扫描以下来源（按项目可能的命名）：

| 数据 | 典型位置 | 格式 |
|---|---|---|
| 实验日志 | `journal/runs.jsonl` / `experiments.jsonl` | JSONL，一行一次实验 |
| 因子库索引 | `factor_library/INDEX.md` / `models/registry.json` | Markdown / JSON |
| 因子卡 | `factor_library/<id>/card.json` | JSON，含 score、metrics |
| best 标记 | `journal/best.json` / 当前 alpha.py | JSON / Python |

## 必算指标

```
总实验数        : N
ACCEPTED 数     : N_acc  (接受率 = N_acc / N)
REJECTED 数     : N_rej
CRASHED 数      : N_crash  (其中黑名单 / 数值校验 / 相关性 各占多少)

分数轨迹（best 演进）：
  Iter 01  baseline             : +0.05
  Iter 04  +amihud              : +0.18  (+0.13)
  Iter 09  IC_IR weighted       : +0.31  (+0.13)
  ...

提分动力学：
  前 20 轮平均提分 +0.025/轮
  20-50 轮平均提分 +0.008/轮
  50+ 轮平均提分 +0.002/轮  ← 边际收益递减
```

## 通用计算骨架

```python
import json, pandas as pd
from pathlib import Path

def load_runs(journal_path: str = "journal/runs.jsonl") -> pd.DataFrame:
    rows = [json.loads(line) for line in Path(journal_path).read_text(encoding="utf-8").splitlines()]
    return pd.DataFrame(rows)

def quantitative_stats(runs: pd.DataFrame) -> dict:
    n_total = len(runs)
    n_acc = (runs["status"] == "ACCEPTED").sum()
    n_rej = (runs["status"] == "REJECTED").sum()
    n_crash = (runs["status"] == "CRASH").sum()

    # best 演进
    best_so_far = runs["score"].cummax()
    breakthroughs = runs[runs["score"] == best_so_far].copy()
    breakthroughs["delta"] = breakthroughs["score"].diff().fillna(breakthroughs["score"].iloc[0])

    # 提分动力学（按 iter 段）
    accepted = runs[runs["status"] == "ACCEPTED"].sort_values("iter")
    accepted_delta = accepted["score"].diff().dropna()
    early = accepted_delta.iloc[:20].mean() if len(accepted_delta) >= 20 else None
    middle = accepted_delta.iloc[20:50].mean() if len(accepted_delta) >= 50 else None
    late = accepted_delta.iloc[50:].mean() if len(accepted_delta) > 50 else None

    return {
        "n_total":  n_total,
        "n_acc":    n_acc, "accept_rate": n_acc / n_total,
        "n_rej":    n_rej,
        "n_crash":  n_crash, "crash_rate": n_crash / n_total,
        "breakthroughs":  breakthroughs[["iter", "name", "score", "delta"]].to_dict("records"),
        "delta_per_iter": {"early_20": early, "mid_30": middle, "late": late},
    }
```

## 预警阈值

| 指标 | 健康 | 预警 | 含义 |
|---|---|---|---|
| 接受率 | 25% ~ 50% | < 15% 或 > 60% | < 15% 假设质量低；> 60% 在挑软柿子 |
| CRASH 率 | < 5% | > 10% | 多半是禁词或 API 误用 |
| 提分动力学 | 持续 > +0.005/轮 | 平台期 | 该 phase transition 了 |
| 平台期持续 | < 10 轮 | > 30 轮 | 强信号：换标签 / 换模型 / 进 Phase 2 |

## 提分动力学曲线

画累计 best score 曲线 + 接受事件标记：

```python
import matplotlib.pyplot as plt

def plot_score_trajectory(runs: pd.DataFrame, out: str = "score_trajectory.png"):
    fig, ax = plt.subplots(figsize=(12, 5))

    runs["score"].plot(ax=ax, color="lightgray", alpha=0.5, label="raw score")
    runs["score"].cummax().plot(ax=ax, color="navy", lw=2, label="best so far")

    accepted = runs[runs["status"] == "ACCEPTED"]
    ax.scatter(accepted.index, accepted["score"], color="g", s=30, label="ACCEPTED")

    crashed = runs[runs["status"] == "CRASH"]
    ax.scatter(crashed.index, crashed["score"].fillna(-2), color="r", s=20, marker="x", label="CRASH")

    ax.set_xlabel("Iteration")
    ax.set_ylabel("score")
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out, dpi=120)
    plt.close()
```

## 反模式

- ❌ 只看"现在的 best"，不看演进过程 —— 看不出动力学
- ❌ 不算 CRASH 率 —— 漏掉了"哪些方向已经被禁区屏蔽"
- ❌ 把 ACCEPTED 当"成功"，REJECTED 当"失败" —— REJECTED 也有研究价值（说明那个方向不 work）
