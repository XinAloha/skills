# HORIZON / 标签错配

## 症状

```
ValueError: HORIZON=15 not in ALLOWED_HORIZONS=(1, 3, 5, 10, 20)
ValueError: LABEL_KIND='zlog' not in ALLOWED_LABEL_KINDS
RuntimeError: HORIZON mismatch: alpha=5, label=10
```

## 原因

| 错配类型 | 含义 |
|---|---|
| HORIZON 不在白名单 | 评估宪法只允许 5 个值，错配视为作弊 |
| LABEL_KIND 不在菜单 | 标签口味只允许 5 种 |
| `alpha.HORIZON ≠ make_labels` 用的 H | label 用 H=5、回测用 H=10 不可比 |

## HORIZON 白名单

`(1, 3, 5, 10, 20)` 交易日：

| H | 用途 |
|---|---|
| 1 | 高频反转 |
| 3 | 短周期 |
| 5 | 标准（默认）|
| 10 | 中周期 |
| 20 | 中长周期动量 |

**改成最近的合法值**。如果你的研究确实需要 H=15 / 30，**在 journal 留言**让人类评估升级宪法，不要自己绕过。

## LABEL_KIND 菜单（auto_research_alpha 项目）

| kind | 公式 | 用途 |
|---|---|---|
| `raw` | `open[T+1+H] / open[T+1] - 1` | 看绝对收益方向 |
| `market_neutral` | `raw - mean(raw, axis=1)` | **推荐**：扣除当日截面等权市场收益 |
| `vol_adjusted` | `raw / std_20(daily_return)` | 高波动股惩罚，更稳健 |
| `rank` | 截面分位 ∈ [0, 1] | 用 rank 作回归目标 |
| `zscore` | 截面 z-score | 与 rank 类似，保留尾部信息 |

## HORIZON 自洽检查

`alpha.HORIZON` 一旦设定，`prepare.make_labels(H)` 与 `prepare.backtest(H)` 必须用**同一个 H**。错配一律视为作弊。

```python
# 防御代码（写在 alpha.py 顶部）
assert HORIZON in (1, 3, 5, 10, 20), f"HORIZON {HORIZON} 越白名单"
assert LABEL_KIND in ("raw", "market_neutral", "vol_adjusted", "rank", "zscore")
```

## 反模式

- ❌ 想"试试 H=7"→ 改 prepare.ALLOWED_HORIZONS —— 改宪法是作弊
- ❌ 给 alpha 用 H=5、给 backtest 偷偷传 H=10 —— 数据不可比
- ❌ 自定义 LABEL_KIND，绕过白名单 —— 找人类升级宪法

## 正确升级路径（要新 horizon / label）

1. 在 `journal/runs.jsonl` 的 `note` 里留言："想试 H=15，理由是 IC decay 显示 H=10/20 之间还有一个峰"
2. 等**人类**评估并决定升级 `prepare.ALLOWED_HORIZONS`
3. 升级后才允许使用
