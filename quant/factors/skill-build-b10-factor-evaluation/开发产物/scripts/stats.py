"""统计严谨性增强：Newey-West HAC t 统计量、bootstrap 噪声基线、交易成本敏感性指标。

为什么独立模块
- ``metrics.py`` 已经偏长；这些是横切于 IC 与分层回测的"诚实度"诊断，单独放好审计。
- 不依赖 statsmodels / scipy，避免给 B10 引入重依赖；HAC 自己写 Bartlett kernel，
  bootstrap 用 numpy 的 default_rng。
- 所有函数都接受**已经按时间序列就绪**的 1D ndarray / Series；不做日历对齐。

口径选择
- HAC 滞后阶 lag 默认按 Andrews 1991 的经验法 ``lag = max(1, int(4 * (n/100) ** (2/9)))``。
- bootstrap 噪声基线：把 factor_value 在每个 trade_date 内做随机 shuffle（保留每日横截面
  分布与样本量），与原始 forward_return 重新算 RankIC，重复 n_boot 次，
  得到"如果因子是噪声"的零分布。p_value 是 ``(|RankIC_real|<= |RankIC_boot|).mean()``。
- 交易成本：``cost_one_way`` 单边成本（默认 0 bps；用户传 5bps 表示万 5）；多空净化
  按当日 turnover × 成本 × 2（多腿 + 空腿换手）扣除，重新累乘求净 IR / 净累计。
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np
import pandas as pd


# ---------- Newey-West HAC（异方差与自相关稳健标准误） ----------

def andrews_lag(n: int) -> int:
    """Andrews 1991 经验滞后阶。常用近似，足够覆盖 IC 时间序列的弱自相关。"""
    if n < 4:
        return 0
    return max(1, int(4 * (n / 100.0) ** (2.0 / 9.0)))


def newey_west_se(values: np.ndarray, lag: int | None = None) -> tuple[float, float]:
    """对一维序列做 Newey-West HAC 长期方差估计，返回 ``(mean, hac_se)``。

    Args:
        values: 1D 序列（典型为日 IC 或日 RankIC）。
        lag: Bartlett kernel 滞后阶；None 时用 Andrews 经验法。

    Returns:
        ``(mean, hac_se)``：均值的 HAC 标准误。``hac_se = sqrt(omega / n)``，
        omega = γ_0 + 2 Σ_{k=1..L} (1 - k/(L+1)) γ_k。

    数值边界
    - 长度 < 2 或方差为 0：返回 ``(mean, nan)``，调用方按缺失处理。
    - omega 计算到负值（极少数高频反相关序列）：clip 到 0，避免开根号爆炸。
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = arr.size
    if n < 2:
        return (float(arr.mean()) if n else 0.0, float("nan"))

    mean = arr.mean()
    centered = arr - mean
    if not np.any(centered):
        return (float(mean), float("nan"))

    if lag is None:
        lag = andrews_lag(n)
    lag = max(0, min(lag, n - 1))

    gamma_0 = float((centered ** 2).sum() / n)
    omega = gamma_0
    for k in range(1, lag + 1):
        weight = 1.0 - k / (lag + 1)
        gamma_k = float((centered[k:] * centered[:-k]).sum() / n)
        omega += 2.0 * weight * gamma_k

    omega = max(omega, 0.0)
    hac_se = float(np.sqrt(omega / n))
    return float(mean), hac_se


def newey_west_t_stat(values: np.ndarray | pd.Series, lag: int | None = None) -> dict[str, float]:
    """返回 ``{"mean", "se_iid", "se_hac", "t_iid", "t_hac", "lag"}``。

    - ``se_iid`` = std(ddof=1) / sqrt(n)，与现有 ``ic_summary.t_stat`` 同口径。
    - ``se_hac`` = Newey-West HAC，把 IC 序列的自相关吸收掉。
    - ``t_iid`` = mean / se_iid；``t_hac`` = mean / se_hac。
    """
    arr = np.asarray(values, dtype=float) if not isinstance(values, pd.Series) else values.to_numpy(dtype=float)
    arr = arr[np.isfinite(arr)]
    n = int(arr.size)
    if n < 2:
        return {
            "mean": float(arr.mean()) if n else 0.0,
            "se_iid": float("nan"),
            "se_hac": float("nan"),
            "t_iid": float("nan"),
            "t_hac": float("nan"),
            "lag": int(lag or 0),
            "n": n,
        }

    mean = float(arr.mean())
    std = float(arr.std(ddof=1))
    se_iid = std / np.sqrt(n) if std else float("nan")
    _, se_hac = newey_west_se(arr, lag=lag)
    return {
        "mean": mean,
        "se_iid": se_iid,
        "se_hac": se_hac,
        "t_iid": (mean / se_iid) if se_iid and np.isfinite(se_iid) else float("nan"),
        "t_hac": (mean / se_hac) if se_hac and np.isfinite(se_hac) else float("nan"),
        "lag": int(lag) if lag is not None else int(andrews_lag(n)),
        "n": n,
    }


# ---------- Bootstrap 噪声基线 ----------

def _spearman_per_day(panel: pd.DataFrame, factor_col: str, target_col: str = "forward_return") -> np.ndarray:
    """日内 Spearman RankIC 序列，返回 numpy array。

    薄封装 ``metrics.daily_spearman_series`` 以保留旧 import 路径；新代码请直接用
    ``metrics.daily_spearman_series`` 拿 pandas Series。曾经这里有一份独立实现，
    现已合并到 ``metrics._pairwise_corr_per_day`` 单一来源。
    """
    try:
        from .metrics import daily_spearman_series
    except ImportError:
        from metrics import daily_spearman_series  # type: ignore[no-redef]
    series = daily_spearman_series(panel, factor_col, target_col)
    return series.to_numpy(dtype=float)


def bootstrap_rank_ic_baseline(
    panel: pd.DataFrame,
    n_boot: int = 200,
    seed: int = 1729,
    factor_col: str = "factor_value",
    target_col: str = "forward_return",
) -> dict[str, Any]:
    """通过日内 shuffle 生成 RankIC 噪声分布，返回 p-value 和置信区间。

    Args:
        panel: 已 validate 的标准面板，含 ``trade_date``、``factor_col``、``target_col``。
        n_boot: 重采样次数；200 已经足够稳定，1000+ 给更紧的尾部。
        seed: 复现性种子；测试与生产环境保持一致输出。

    Returns:
        ``{"observed", "p_two_sided", "ci95_low", "ci95_high", "boot_mean", "n_boot", "n_days"}``。
        ``p_two_sided`` 是 ``(|RankIC_boot| >= |RankIC_observed|).mean()``：
        越小代表"看到这种 IC 的概率在零假设下越低"。
    """
    if panel.empty or n_boot <= 0:
        return {
            "observed": 0.0,
            "p_two_sided": float("nan"),
            "ci95_low": float("nan"),
            "ci95_high": float("nan"),
            "boot_mean": float("nan"),
            "n_boot": int(n_boot),
            "n_days": 0,
        }

    observed_series = _spearman_per_day(panel, factor_col, target_col)
    observed = float(observed_series.mean()) if observed_series.size else 0.0

    rng = np.random.default_rng(seed)
    boot_means = np.zeros(n_boot, dtype=float)
    # 预先分组，避免每次 bootstrap 重新 groupby
    groups = list(panel.groupby("trade_date", sort=False))
    for b in range(n_boot):
        rows = []
        for _, day in groups:
            n = len(day)
            if n < 2:
                continue
            shuffled = day[factor_col].to_numpy(dtype=float).copy()
            rng.shuffle(shuffled)
            tmp = day.copy()
            tmp["__shuf__"] = shuffled
            ic = tmp[["__shuf__", target_col]].rank(method="average").corr().iloc[0, 1]
            if np.isfinite(ic):
                rows.append(ic)
        boot_means[b] = float(np.mean(rows)) if rows else 0.0

    p = float((np.abs(boot_means) >= abs(observed)).mean())
    ci_low, ci_high = np.quantile(boot_means, [0.025, 0.975]).tolist()
    return {
        "observed": observed,
        "p_two_sided": p,
        "ci95_low": float(ci_low),
        "ci95_high": float(ci_high),
        "boot_mean": float(boot_means.mean()),
        "n_boot": int(n_boot),
        "n_days": int(observed_series.size),
    }


# ---------- 交易成本敏感性 ----------

def transaction_cost_adjusted_ls(
    long_short_returns: pd.Series,
    daily_turnover: pd.Series,
    cost_one_way_bps: float = 0.0,
    annualization_factor: float = 252.0,
) -> dict[str, float]:
    """把多空日收益按每日换手扣减后的净指标。

    净日收益 = 总收益 - 换手率 × cost × 2（多腿 + 空腿同换手率）。
    cost 以 ``bps``（万分之一）为单位输入：``cost_one_way_bps=5`` 表示单边万 5。

    Returns:
        ``{"cost_bps", "average_turnover", "net_long_short_cumulative_return",
            "net_long_short_ir", "net_long_short_win_rate"}``。
    """
    if long_short_returns is None or len(long_short_returns) == 0:
        return {
            "cost_bps": float(cost_one_way_bps),
            "average_turnover": 0.0,
            "net_long_short_cumulative_return": 0.0,
            "net_long_short_ir": 0.0,
            "net_long_short_win_rate": 0.0,
        }

    ls = pd.to_numeric(long_short_returns, errors="coerce").fillna(0.0)
    to = pd.to_numeric(daily_turnover, errors="coerce").reindex(ls.index).fillna(0.0)
    cost = float(cost_one_way_bps) / 10000.0
    deducted = ls - to * cost * 2.0
    cum = (1 + deducted).cumprod()
    cum_value = float(cum.iloc[-1] - 1) if len(cum) else 0.0
    std = float(deducted.std(ddof=1)) if len(deducted) > 1 else 0.0
    ir = (
        float(deducted.mean() / std * np.sqrt(annualization_factor))
        if std and np.isfinite(std)
        else 0.0
    )
    win = float((deducted > 0).mean()) if len(deducted) else 0.0
    return {
        "cost_bps": float(cost_one_way_bps),
        "average_turnover": float(to.mean()),
        "net_long_short_cumulative_return": cum_value,
        "net_long_short_ir": ir,
        "net_long_short_win_rate": win,
    }


def cost_sweep(
    long_short_returns: pd.Series,
    daily_turnover: pd.Series,
    cost_grid_bps: Sequence[float] = (0, 1, 3, 5, 10, 20),
    annualization_factor: float = 252.0,
) -> list[dict[str, float]]:
    """对一组单边成本（bps）扫描，返回每个成本点的净指标。"""
    return [
        transaction_cost_adjusted_ls(
            long_short_returns,
            daily_turnover,
            cost_one_way_bps=float(cost),
            annualization_factor=annualization_factor,
        )
        for cost in cost_grid_bps
    ]
