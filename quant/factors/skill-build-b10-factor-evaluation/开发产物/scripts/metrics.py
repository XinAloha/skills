from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

try:
    from .constants import STOCK_POOL_ALIASES, STOCK_POOL_LABELS, VALID_FACTOR_DIRECTIONS, VALID_TARGET_KINDS
    from .neutralize import apply_neutralization
    from .stats import (
        bootstrap_rank_ic_baseline,
        cost_sweep,
        newey_west_t_stat,
    )
    from .utils import round_metric, safe_float
except ImportError:
    from constants import STOCK_POOL_ALIASES, STOCK_POOL_LABELS, VALID_FACTOR_DIRECTIONS, VALID_TARGET_KINDS
    from neutralize import apply_neutralization
    from stats import (
        bootstrap_rank_ic_baseline,
        cost_sweep,
        newey_west_t_stat,
    )
    from utils import round_metric, safe_float

# 注：研究诊断 (RESEARCH_RETURN_TARGETS / make_research_diagnostics 等) 已下沉到
# research_diagnostics.py。但是该模块依赖 metrics 的 daily_ic / ic_summary /
# layer_backtest，会形成循环 import。为兼容旧 ``from metrics import
# make_research_diagnostics`` 的调用方，重新导出在文件末尾完成（彼时 metrics
# 自己的函数都已定义，循环 import 才不会爆）。


GROUP_MODE_TO_COUNT = {
    "5": 5,
    "quintile": 5,
    "five": 5,
    "五分组": 5,
    "五组": 5,
    "10": 10,
    "decile": 10,
    "ten": 10,
    "十分组": 10,
    "十组": 10,
}


def resolve_group_count(config: dict) -> tuple[int, str]:
    group_mode = config.get("group_mode")
    if group_mode is None:
        group_count = int(config.get("group_count", 5))
        return group_count, "custom" if group_count not in {5, 10} else ("quintile" if group_count == 5 else "decile")

    mode_key = str(group_mode).strip().lower()
    if mode_key not in GROUP_MODE_TO_COUNT:
        raise ValueError("group_mode 必须是 quintile/5/五分组 或 decile/10/十分组")

    resolved_count = GROUP_MODE_TO_COUNT[mode_key]
    if "group_count" in config and int(config["group_count"]) != resolved_count:
        raise ValueError("group_mode 与 group_count 冲突，请只保留一个分组选项或保持二者一致")
    return resolved_count, "quintile" if resolved_count == 5 else "decile"


def validate_config(config: dict) -> dict[str, Any]:
    group_count, group_mode = resolve_group_count(config)
    if group_count < 2:
        raise ValueError("group_count 必须大于等于 2")

    turnover_quantile = float(config.get("turnover_quantile", 0.8))
    if not 0 < turnover_quantile < 1:
        raise ValueError("turnover_quantile 必须在 0 和 1 之间")

    horizons = [int(x) for x in config.get("decay_horizons", [1, 2, 3, 5, 10, 20])]
    if not horizons or any(x < 1 for x in horizons):
        raise ValueError("decay_horizons 必须是正整数列表")

    factor_direction = str(config.get("factor_direction", "positive")).lower()
    if factor_direction not in VALID_FACTOR_DIRECTIONS:
        raise ValueError(f"factor_direction 必须是 {sorted(VALID_FACTOR_DIRECTIONS)} 之一")

    target_kind = str(config.get("target_kind", "return")).lower()
    if target_kind not in VALID_TARGET_KINDS:
        raise ValueError(f"target_kind 必须是 {sorted(VALID_TARGET_KINDS)} 之一")

    annualization_factor = float(config.get("annualization_factor", 252))
    if annualization_factor <= 0:
        raise ValueError("annualization_factor 必须大于 0")

    # P3: bootstrap 噪声基线（默认关闭以兼容旧调用；调用方 opt-in 设 >=200 即可）
    bootstrap_n = int(config.get("bootstrap_n", 0))
    if bootstrap_n < 0:
        raise ValueError("bootstrap_n 必须 >= 0；0 表示关闭 bootstrap 基线")
    bootstrap_seed = int(config.get("bootstrap_seed", 1729))

    # P3: 交易成本扫描；列表内必须为非负数；空列表表示不出 cost_sweep
    cost_grid_raw = config.get("cost_grid_bps", [])
    if cost_grid_raw is None:
        cost_grid = []
    else:
        cost_grid = [float(x) for x in cost_grid_raw]
        if any(c < 0 for c in cost_grid):
            raise ValueError("cost_grid_bps 中不允许出现负成本")

    # P3: 中性化
    neutralize_flag = bool(config.get("neutralize", False))
    industry_level = str(config.get("industry_level", "L1")).upper()
    if industry_level not in {"L1", "L2", "L3"}:
        raise ValueError("industry_level 必须是 L1/L2/L3 之一")

    stock_pool = resolve_stock_pool(config.get("stock_pool", "all_a"))

    return {
        **config,
        "group_count": group_count,
        "group_mode": group_mode,
        "turnover_quantile": turnover_quantile,
        "decay_horizons": sorted(set(horizons)),
        "factor_direction": factor_direction,
        "target_kind": target_kind,
        "annualization_factor": annualization_factor,
        "bootstrap_n": bootstrap_n,
        "bootstrap_seed": bootstrap_seed,
        "cost_grid_bps": cost_grid,
        "neutralize": neutralize_flag,
        "industry_level": industry_level,
        "stock_pool": stock_pool,
        "stock_pool_label": STOCK_POOL_LABELS[stock_pool],
    }


def resolve_stock_pool(value: Any) -> str:
    text = str(value or "all_a").strip()
    if text in STOCK_POOL_LABELS:
        return text
    key = text.lower()
    if key in STOCK_POOL_ALIASES:
        return STOCK_POOL_ALIASES[key]
    if text in STOCK_POOL_ALIASES:
        return STOCK_POOL_ALIASES[text]
    raise ValueError(f"stock_pool 必须是 {list(STOCK_POOL_LABELS.values())} 或 {list(STOCK_POOL_LABELS)} 之一")


def filter_stock_pool(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    pool = str(config.get("stock_pool", "all_a"))
    if pool == "all_a":
        if "is_pool_all_a" in panel.columns:
            out = panel.loc[panel["is_pool_all_a"].astype(bool)].copy()
            if out.empty:
                raise ValueError("全A股在当前输入区间内没有可评估样本")
        else:
            out = panel.copy()
        out.attrs.update(panel.attrs)
        out.attrs["raw_row_count"] = int(panel.attrs.get("raw_row_count", len(panel)))
        out.attrs["stock_pool"] = pool
        out.attrs["stock_pool_label"] = STOCK_POOL_LABELS[pool]
        out.attrs["stock_pool_filtered_row_count"] = int(len(panel) - len(out))
        return out

    label = STOCK_POOL_LABELS[pool]
    flag_col = f"is_pool_{pool}"
    if flag_col in panel.columns:
        mask = panel[flag_col].astype(bool)
    elif "stock_pool_memberships" in panel.columns:
        memberships = panel["stock_pool_memberships"].fillna("").astype(str)
        mask = memberships.str.contains(label, regex=False) | memberships.str.contains(pool, regex=False)
    elif "primary_stock_pool" in panel.columns:
        mask = panel["primary_stock_pool"].fillna("").astype(str).isin({label, pool})
    else:
        raise ValueError("input_data 未包含股票池标签字段，无法按指定股票池筛选")

    out = panel.loc[mask].copy()
    if out.empty:
        raise ValueError(f"股票池 {label} 在当前输入区间内没有可评估样本")
    out.attrs.update(panel.attrs)
    out.attrs["raw_row_count"] = int(panel.attrs.get("raw_row_count", len(panel)))
    out.attrs["stock_pool"] = pool
    out.attrs["stock_pool_label"] = label
    out.attrs["stock_pool_filtered_row_count"] = int(len(panel) - len(out))
    return out


def series_corr(x: pd.Series, y: pd.Series, method: str = "pearson") -> float:
    valid = pd.DataFrame({"x": x, "y": y}).replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) < 2 or valid["x"].nunique() < 2 or valid["y"].nunique() < 2:
        return np.nan
    if method == "spearman":
        valid = valid.rank(method="average")
    return float(valid["x"].corr(valid["y"], method="pearson"))


def series_skew(s: pd.Series) -> float:
    clean = pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    return round_metric(clean.skew()) if len(clean) >= 3 else 0.0


def series_kurtosis(s: pd.Series) -> float:
    clean = pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    return round_metric(clean.kurt()) if len(clean) >= 4 else 0.0


def lag_autocorr(values: pd.Series, lag: int) -> float:
    clean = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(clean) <= lag:
        return 0.0
    return round_metric(clean.autocorr(lag=lag))


def _pairwise_corr_per_day(panel: pd.DataFrame, factor_col: str, target_col: str, method: str) -> pd.Series:
    """对每个 trade_date 求 ``factor_col`` 与 ``target_col`` 的横截面相关系数。

    Args:
        method: ``"pearson"`` 或 ``"spearman"``；spearman 内部用 rank 后的 pearson 等价。

    向量化实现：先全表 dropna / replace inf → 按日 rank（spearman 用）→ 用 groupby 聚合
    出每日 ``n / Σx / Σy / Σx² / Σy² / Σxy``，闭式公式得相关系数。比逐日 Python 循环快
    5-20 倍（依赖样本规模）。

    返回值是 ``pd.Series``，``index = trade_date``，仅保留 ``n>=2`` 且分子分母非零的日。
    """
    valid = panel[["trade_date", factor_col, target_col]].replace([np.inf, -np.inf], np.nan).dropna().copy()
    if valid.empty:
        return pd.Series(dtype="float64")

    if method == "spearman":
        valid["_x"] = valid.groupby("trade_date")[factor_col].rank(method="average")
        valid["_y"] = valid.groupby("trade_date")[target_col].rank(method="average")
    else:
        valid["_x"] = pd.to_numeric(valid[factor_col], errors="coerce")
        valid["_y"] = pd.to_numeric(valid[target_col], errors="coerce")

    valid["_x_sq"] = valid["_x"].pow(2)
    valid["_y_sq"] = valid["_y"].pow(2)
    valid["_xy"] = valid["_x"] * valid["_y"]
    grouped = valid.groupby("trade_date").agg(
        n=("_x", "size"),
        sx=("_x", "sum"),
        sy=("_y", "sum"),
        sx2=("_x_sq", "sum"),
        sy2=("_y_sq", "sum"),
        sxy=("_xy", "sum"),
    )
    numerator = grouped["n"] * grouped["sxy"] - grouped["sx"] * grouped["sy"]
    denominator = np.sqrt(
        (grouped["n"] * grouped["sx2"] - grouped["sx"].pow(2))
        * (grouped["n"] * grouped["sy2"] - grouped["sy"].pow(2))
    )
    corr = numerator / denominator.replace(0, np.nan)
    corr = corr.loc[grouped["n"] >= 2]
    return corr.replace([np.inf, -np.inf], np.nan).dropna()


def daily_ic(panel: pd.DataFrame, factor_col: str = "factor_value") -> pd.DataFrame:
    """每日横截面 IC / RankIC / 样本数。

    向量化版本：原先按日 Python 循环 + ``series_corr`` 调用，在千日级面板上慢 5-20×。
    现在 IC 与 RankIC 各调用一次 ``_pairwise_corr_per_day``，结果按 trade_date 合并。

    与历史实现保持兼容：
    - ``sample_count`` 取整日全部行数（包含含 NaN 行），与原 ``len(day)`` 一致。
    - 最终对 IC 和 RankIC 同时 NaN 的行丢弃，与原 ``dropna(how="all")`` 一致。
    """
    if panel.empty:
        return pd.DataFrame(columns=["trade_date", "ic", "rank_ic", "sample_count"])

    ic = _pairwise_corr_per_day(panel, factor_col, "forward_return", "pearson").rename("ic")
    rank_ic = _pairwise_corr_per_day(panel, factor_col, "forward_return", "spearman").rename("rank_ic")
    sample_count = panel.groupby("trade_date").size().rename("sample_count").astype(int)

    # 用 sample_count 做 base，保留所有 trade_date；ic/rank_ic 缺日补 NaN
    out = pd.concat([sample_count, ic, rank_ic], axis=1).reset_index()
    out = out.dropna(subset=["ic", "rank_ic"], how="all").reset_index(drop=True)
    out["sample_count"] = out["sample_count"].fillna(0).astype(int)
    return out[["trade_date", "ic", "rank_ic", "sample_count"]]


def daily_spearman_series(panel: pd.DataFrame, factor_col: str, target_col: str) -> pd.Series:
    """日内 Spearman RankIC 序列（兼容旧 import 路径）。

    历史上 metrics 里有自己的实现、stats.py 又写了一份 ``_spearman_per_day``——
    收口为统一调用 ``_pairwise_corr_per_day``。
    """
    return _pairwise_corr_per_day(panel, factor_col, target_col, "spearman")


def ic_summary(daily: pd.DataFrame) -> dict[str, Any]:
    def summarize(s: pd.Series) -> dict[str, float]:
        std = s.std(ddof=1)
        # Newey-West HAC：吸收 IC 时间序列里的弱自相关，给出更诚实的 t 统计量。
        hac = newey_west_t_stat(s)
        return {
            "mean": round_metric(s.mean()),
            "std": round_metric(std),
            "ir": round_metric(s.mean() / std) if len(s) > 1 and std else 0.0,
            "positive_ratio": round_metric((s > 0).mean()) if len(s) else 0.0,
            "t_stat": round_metric(s.mean() / (std / np.sqrt(len(s)))) if len(s) > 1 and std else 0.0,
            "t_stat_hac": round_metric(hac["t_hac"]),
            "hac_se": round_metric(hac["se_hac"]),
            "hac_lag": int(hac["lag"]),
        }

    ic = daily["ic"].dropna()
    rank_ic = daily["rank_ic"].dropna()
    return {
        "ic": summarize(ic),
        "rank_ic": summarize(rank_ic),
        "daily": daily.round(6).to_dict("records"),
    }


def ic_time_analysis(daily: pd.DataFrame) -> dict[str, Any]:
    out = daily.sort_values("trade_date").copy()
    out["cum_ic"] = out["ic"].fillna(0).cumsum()
    out["cum_rank_ic"] = out["rank_ic"].fillna(0).cumsum()
    ic = out["ic"].dropna()
    rank_ic = out["rank_ic"].dropna()
    return {
        "ic_autocorr_lag1": lag_autocorr(ic, 1),
        "ic_autocorr_lag5": lag_autocorr(ic, 5),
        "rank_ic_autocorr_lag1": lag_autocorr(rank_ic, 1),
        "rank_ic_autocorr_lag5": lag_autocorr(rank_ic, 5),
        "cum_ic_final": round_metric(out["cum_ic"].iloc[-1]) if len(out) else 0.0,
        "cum_rank_ic_final": round_metric(out["cum_rank_ic"].iloc[-1]) if len(out) else 0.0,
        "daily": out.round(6).to_dict("records"),
    }


def ic_distribution_analysis(daily: pd.DataFrame) -> dict[str, Any]:
    ic = daily["ic"].dropna()
    rank_ic = daily["rank_ic"].dropna()
    return {
        "ic_skew": series_skew(ic),
        "ic_kurtosis": series_kurtosis(ic),
        "rank_ic_skew": series_skew(rank_ic),
        "rank_ic_kurtosis": series_kurtosis(rank_ic),
        "ic_extreme_ratio": round_metric((ic.abs() > 0.15).mean()) if len(ic) else 0.0,
        "rank_ic_extreme_ratio": round_metric((rank_ic.abs() > 0.15).mean()) if len(rank_ic) else 0.0,
    }


def factor_distribution_analysis(panel: pd.DataFrame, factor_col: str = "factor_value") -> dict[str, Any]:
    daily_rows = []
    for trade_date, day in panel.groupby("trade_date"):
        values = pd.to_numeric(day[factor_col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if values.empty:
            continue
        std = values.std(ddof=1)
        mean = values.mean()
        extreme_ratio = (values.sub(mean).abs() > 3 * std).mean() if std and np.isfinite(std) else 0.0
        daily_rows.append(
            {
                "trade_date": trade_date,
                "mean": round_metric(mean),
                "std": round_metric(std),
                "skew": series_skew(values),
                "kurtosis": series_kurtosis(values),
                "extreme_ratio": round_metric(extreme_ratio),
                "sample_count": int(len(values)),
            }
        )
    daily = pd.DataFrame(daily_rows)
    if daily.empty:
        return {
            "avg_skew": 0.0,
            "avg_kurtosis": 0.0,
            "avg_extreme_ratio": 0.0,
            "daily": [],
        }
    return {
        "avg_skew": round_metric(daily["skew"].mean()),
        "avg_kurtosis": round_metric(daily["kurtosis"].mean()),
        "avg_extreme_ratio": round_metric(daily["extreme_ratio"].mean()),
        "daily": daily.round(6).to_dict("records"),
    }


def factor_rank_autocorrelation(panel: pd.DataFrame, factor_col: str = "factor_value", lags: list[int] | None = None) -> dict[str, Any]:
    lags = lags or [1, 5]
    if panel.empty:
        return {"summary": {f"lag{lag}": 0.0 for lag in lags}, "daily": []}

    ranks = panel[["trade_date", "ts_code", factor_col]].copy()
    ranks["rank_pct"] = ranks.groupby("trade_date")[factor_col].rank(pct=True, method="average")
    wide = (
        ranks.pivot_table(index="trade_date", columns="ts_code", values="rank_pct", aggfunc="mean")
        .sort_index()
    )
    if wide.empty:
        return {"summary": {f"lag{lag}": 0.0 for lag in lags}, "daily": []}

    rows = []
    for lag in lags:
        if lag >= len(wide):
            continue
        current = wide.iloc[lag:]
        previous = wide.shift(lag).iloc[lag:]
        corr = current.corrwith(previous, axis=1)
        overlap_count = current.notna().where(previous.notna()).sum(axis=1)
        for trade_date, rank_autocorr in corr.items():
            rows.append(
                {
                    "trade_date": trade_date,
                    "lag": int(lag),
                    "rank_autocorr": round_metric(rank_autocorr),
                    "overlap_count": int(overlap_count.loc[trade_date]),
                }
            )
    daily = pd.DataFrame(rows, columns=["trade_date", "lag", "rank_autocorr", "overlap_count"])
    daily = daily.dropna(subset=["rank_autocorr"])
    summary = {}
    for lag in lags:
        values = daily.loc[daily["lag"].eq(lag), "rank_autocorr"] if not daily.empty else pd.Series(dtype=float)
        summary[f"lag{lag}"] = round_metric(values.mean()) if len(values) else 0.0
    return {"summary": summary, "daily": daily.round(6).to_dict("records")}


def assign_quantiles(panel: pd.DataFrame, group_count: int, factor_col: str = "factor_value") -> pd.DataFrame:
    def assign(values: pd.Series) -> pd.Series:
        q = min(group_count, values.nunique(), len(values))
        if q < 2:
            return pd.Series(["G1"] * len(values), index=values.index)
        labels = [f"G{i}" for i in range(1, q + 1)]
        return pd.qcut(values.rank(method="first"), q, labels=labels).astype(str)

    out = panel.copy()
    out["group"] = out.groupby("trade_date")[factor_col].transform(assign)
    return out


def layer_backtest(
    panel: pd.DataFrame,
    group_count: int,
    factor_col: str = "factor_value",
    annualization_factor: float = 252,
    target_kind: str = "return",
    resolved_direction: str = "positive",
) -> dict[str, Any]:
    grouped = assign_quantiles(panel, group_count, factor_col)
    daily_group = (
        grouped.groupby(["trade_date", "group"], observed=False)["forward_return"]
        .mean()
        .unstack()
        .sort_index()
    )
    mean_return = daily_group.mean()
    ordered_groups = sorted(daily_group.columns, key=lambda x: int(x[1:]))
    low, high = ordered_groups[0], ordered_groups[-1]
    long_short = daily_group[high].fillna(0) - daily_group[low].fillna(0)
    if target_kind == "binary_success":
        total = daily_group.expanding(min_periods=1).mean().iloc[-1]
        long_short_value = long_short.mean()
    else:
        total = (1 + daily_group.fillna(0)).prod() - 1
        long_short_curve = (1 + long_short).cumprod()
        long_short_value = long_short_curve.iloc[-1] - 1 if len(long_short_curve) else 0.0

    monotonic_steps = np.diff([mean_return[g] for g in ordered_groups])
    monotonic_score = float((monotonic_steps >= 0).mean()) if len(monotonic_steps) else 0.0
    spearman = series_corr(
        pd.Series(range(1, len(ordered_groups) + 1)),
        pd.Series([mean_return[g] for g in ordered_groups]),
        "spearman",
    )

    # `resolved_direction` 描述外层 make_report 已经按 factor_direction 调整后的方向；
    # 调整后我们始终期望"高分组优于低分组"，因此 monotonicity 的语义方向映射回原始因子。
    direction_label = "decreasing" if str(resolved_direction).lower() == "negative" else "increasing"

    return {
        "group_count": int(len(ordered_groups)),
        "daily_group_return": daily_group.round(6).reset_index().to_dict("records"),
        "group_mean_return": {g: round_metric(mean_return[g]) for g in ordered_groups},
        "group_cumulative_return": {g: round_metric(total[g]) for g in ordered_groups},
        "long_short_cumulative_return": round_metric(long_short_value),
        "long_short_ir": round_metric(long_short.mean() / long_short.std(ddof=1) * np.sqrt(annualization_factor))
        if len(long_short) > 1 and long_short.std(ddof=1)
        else 0.0,
        "long_short_win_rate": round_metric((long_short > 0).mean()) if len(long_short) else 0.0,
        # P3: 把多空日序列暴露出来，apply_layer 里给 transaction_cost_adjusted_ls 用；
        # 名称和单位与 daily_group_return 一致，索引为 trade_date。
        "_long_short_series": long_short,
        "monotonicity": {
            "direction": direction_label,
            "score": round_metric(monotonic_score),
            "adjacent_positive_ratio": round_metric(monotonic_score),
            "spearman": round_metric(spearman),
            "passed": bool(monotonic_score >= 0.75 and safe_float(spearman) > 0),
        },
    }


def turnover(panel: pd.DataFrame, quantile: float, factor_col: str = "factor_value") -> dict[str, Any]:
    holdings = []
    for trade_date, day in panel.groupby("trade_date"):
        top_n = max(1, int(np.ceil(len(day) * (1 - quantile))))
        # tie-break 规则（确定性可复现）：因子值并列时按 ts_code 字典序升序优先入选。
        # 这意味着代码较小的股票在并列时占优；下游若需要无偏 tie-break，应在进入 B10 前
        # 对 factor_value 加微小扰动（例如 factor_value + epsilon * hash(ts_code)）。
        ranked = day.sort_values([factor_col, "ts_code"], ascending=[False, True])
        holdings.append((trade_date, set(ranked.head(top_n)["ts_code"])))

    rows = []
    previous = None
    for trade_date, current in holdings:
        if previous is None:
            value = 0.0
        else:
            union = previous | current
            value = 1 - len(previous & current) / len(union) if union else 0.0
        rows.append({"trade_date": trade_date, "turnover": round_metric(value), "holding_count": len(current)})
        previous = current

    values = [row["turnover"] for row in rows[1:]]
    return {
        "top_quantile": round_metric(1 - quantile),
        "average_turnover": round_metric(np.mean(values)) if values else 0.0,
        "daily": rows,
    }


def decay_curve(
    panel: pd.DataFrame,
    horizons: list[int],
    factor_col: str = "factor_value",
    target_kind: str = "return",
) -> list[dict[str, Any]]:
    rows = []
    base = panel.sort_values(["ts_code", "trade_date"]).copy()
    grouped_return = base.groupby("ts_code", sort=False)["forward_return"]
    for horizon in horizons:
        horizon_col = f"forward_return_{int(horizon)}d"
        if horizon_col in base.columns:
            future_return = pd.to_numeric(base[horizon_col], errors="coerce")
        elif horizon == 1:
            future_return = base["forward_return"]
        elif target_kind == "binary_success":
            shifted_targets = [grouped_return.shift(-offset) for offset in range(horizon)]
            future_return = pd.concat(shifted_targets, axis=1).mean(axis=1, skipna=False)
        else:
            compounded = pd.Series(1.0, index=base.index)
            for offset in range(horizon):
                compounded = compounded * (1 + grouped_return.shift(-offset))
            future_return = compounded - 1

        shifted = base[["trade_date", factor_col]].copy()
        shifted["future_return"] = future_return
        s = daily_spearman_series(shifted, factor_col, "future_return")
        rows.append({"horizon": int(horizon), "rank_ic": round_metric(s.mean()) if len(s) else 0.0, "sample_days": int(len(s))})
    return rows


def direction_multiplier(raw_rank_ic: float, factor_direction: str) -> tuple[int, str]:
    if factor_direction == "negative":
        return -1, "negative"
    if factor_direction == "auto" and raw_rank_ic < 0:
        return -1, "negative"
    return 1, "positive"


def quality_warnings(
    panel: pd.DataFrame,
    daily: pd.DataFrame,
    layer_report: dict[str, Any],
    config: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    dropped = int(panel.attrs.get("dropped_missing_row_count", 0))
    pool_dropped = int(panel.attrs.get("stock_pool_filtered_row_count", 0))
    requested_group_count = int(config["group_count"])
    actual_group_count = int(layer_report["group_count"])
    if dropped:
        warnings.append(f"输入中有 {dropped} 行缺失值已在评估前剔除。")
    if pool_dropped:
        warnings.append(f"股票池筛选剔除了 {pool_dropped} 行非目标票池样本。")
    if actual_group_count < requested_group_count:
        warnings.append(f"横截面可用标的不足，配置为 {requested_group_count} 组，实际分为 {actual_group_count} 组。")
    if panel["trade_date"].nunique() < 20:
        warnings.append("有效交易日少于 20 天，ICIR 和换手率稳定性可能不足。")
    if panel["ts_code"].nunique() < int(layer_report["group_count"]) * 2:
        warnings.append("横截面标的数偏少，分层回测和单调性检验可能不稳定。")
    if daily.empty:
        warnings.append("没有可计算 IC 的有效交易日，请检查每日横截面样本数或因子是否为常数。")
    if config.get("target_kind") == "binary_success" and not panel["forward_return"].between(0, 1).all():
        warnings.append("target_kind=binary_success 时 forward_return 应为 0/1 成功标签，请检查输入。")
    if not layer_report["monotonicity"]["passed"]:
        metric_name = "成功率" if config.get("target_kind") == "binary_success" else "收益"
        warnings.append(f"分层{metric_name}未通过默认单调性检验，需要结合业务方向和样本期进一步确认。")
    return warnings


def quality_checklist(
    summary: dict[str, Any],
    ic_report: dict[str, Any],
    time_report: dict[str, Any],
    distribution_report: dict[str, Any],
    factor_distribution_report: dict[str, Any],
    layer_report: dict[str, Any],
    decay_report: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rank_ic = safe_float(summary.get("rank_ic"))
    rank_icir = safe_float(summary.get("rank_icir"))
    ic = safe_float(summary.get("ic"))
    icir = safe_float(summary.get("icir"))
    decay_values = [abs(safe_float(row.get("rank_ic"))) for row in decay_report]
    first_decay = decay_values[0] if decay_values else 0.0
    later_decay = decay_values[3] if len(decay_values) > 3 else (decay_values[-1] if decay_values else 0.0)
    items = [
        {
            "dimension": "基础层",
            "metric": "RankIC 均值",
            "value": round_metric(rank_ic),
            "threshold": "|RankIC| >= 0.02",
            "passed": bool(abs(rank_ic) >= 0.02),
            "note": "验证横截面排序预测能力。",
        },
        {
            "dimension": "基础层",
            "metric": "RankICIR",
            "value": round_metric(rank_icir),
            "threshold": "|RankICIR| >= 0.5",
            "passed": bool(abs(rank_icir) >= 0.5),
            "note": "验证 IC 稳定性。",
        },
        {
            "dimension": "基础层",
            "metric": "IC 均值",
            "value": round_metric(ic),
            "threshold": "|IC| >= 0.02",
            "passed": bool(abs(ic) >= 0.02),
            "note": "验证线性预测能力。",
        },
        {
            "dimension": "基础层",
            "metric": "ICIR",
            "value": round_metric(icir),
            "threshold": "|ICIR| >= 0.5",
            "passed": bool(abs(icir) >= 0.5),
            "note": "验证线性 IC 稳定性。",
        },
        {
            "dimension": "时间层",
            "metric": "累计 RankIC",
            "value": round_metric(time_report.get("cum_rank_ic_final")),
            "threshold": "方向累计值持续同向",
            "passed": bool(rank_ic * safe_float(time_report.get("cum_rank_ic_final")) > 0),
            "note": "长期有效性摘要。",
        },
        {
            "dimension": "时间层",
            "metric": "RankIC 自相关 lag1",
            "value": round_metric(time_report.get("rank_ic_autocorr_lag1")),
            "threshold": "-0.2 到 0.8",
            "passed": bool(-0.2 <= safe_float(time_report.get("rank_ic_autocorr_lag1")) <= 0.8),
            "note": "过高可能过慢，过低可能不稳定。",
        },
        {
            "dimension": "时间层",
            "metric": "衰减合理性",
            "value": round_metric(later_decay),
            "threshold": "中期 RankIC 不快速归零",
            "passed": bool(first_decay == 0 or later_decay >= first_decay * 0.25),
            "note": "观察预测周期是否过短。",
        },
        {
            "dimension": "分布层",
            "metric": "RankIC 偏度",
            "value": round_metric(distribution_report.get("rank_ic_skew")),
            "threshold": "|skew| <= 1",
            "passed": bool(abs(safe_float(distribution_report.get("rank_ic_skew"))) <= 1),
            "note": "IC 分布不应过度偏斜。",
        },
        {
            "dimension": "分布层",
            "metric": "RankIC 峰度",
            "value": round_metric(distribution_report.get("rank_ic_kurtosis")),
            "threshold": "kurtosis <= 5",
            "passed": bool(safe_float(distribution_report.get("rank_ic_kurtosis")) <= 5),
            "note": "尾部风险不应过强。",
        },
        {
            "dimension": "分布层",
            "metric": "因子极端值占比",
            "value": round_metric(factor_distribution_report.get("avg_extreme_ratio")),
            "threshold": "<= 1%",
            "passed": bool(safe_float(factor_distribution_report.get("avg_extreme_ratio")) <= 0.01),
            "note": "横截面异常值风险。",
        },
        {
            "dimension": "分层层",
            "metric": "分层单调性",
            "value": round_metric(layer_report["monotonicity"]["spearman"]),
            "threshold": "Spearman > 0 且相邻改善 >= 75%",
            "passed": bool(layer_report["monotonicity"]["passed"]),
            "note": "验证因子区分度。",
        },
        {
            "dimension": "分层层",
            "metric": "多空胜率",
            "value": round_metric(layer_report.get("long_short_win_rate")),
            "threshold": ">= 50%",
            "passed": bool(safe_float(layer_report.get("long_short_win_rate")) >= 0.5),
            "note": "高分组相对低分组的日胜率。",
        },
    ]
    return items


def compute_panel_base(panel: pd.DataFrame, config: dict) -> dict[str, Any]:
    """Pool-filtered、group_count 无关的预计算缓存。

    把 daily_ic / ic_time_analysis / factor_rank_autocorrelation / turnover /
    decay_curve 等"只取决于股票池筛选后面板与方向调整因子值"的指标算一次，
    供同一面板下不同 group_count 的 apply_layer 共享。

    注意：research_report 与 group_count 部分绑定（reverse_factor_analysis 直接
    用 config["group_count"]，state/monthly/return_target 走 min(5, group_count)），
    因此故意留在 apply_layer 里按 group_count 重算，保证语义一致。

    P3 扩展：
    - ``neutralize=True`` 时调用 ``apply_neutralization`` 在 stock pool 筛选后、方向
      调整前替换 factor_value（行业 + 风格 OLS 残差），其余指标基于残差因子计算。
      调用方未传入 ``industry_panel`` / ``style_panel`` 时（B10 不联网）会
      直接 ``ValueError``——这是配置错误，应该让用户看到，不再静默兜底。
      ``RuntimeError``（OLS 数值异常等）仍捕获后写到 ``neutralize_meta``。
    - ``bootstrap_n>0`` 且 ``target_kind=return`` 时附带 RankIC 的噪声基线 p-value 和
      95% 置信区间；binary_success 跳过（成功率不适合按收益率口径 shuffle 比较）。
    """
    panel = filter_stock_pool(panel, config)

    neutralize_meta: list[dict[str, Any]] = []
    if bool(config.get("neutralize", False)):
        try:
            neutralized = apply_neutralization(panel, config)
            panel = neutralized
            neutralize_meta = list(neutralized.attrs.get("neutralize_meta", []))
        except RuntimeError as exc:
            # OLS 数值异常等运行时错误：保留原 panel，写一条错误进 base，
            # 由 apply_layer 推到 quality_warnings 里。配置错误（缺暴露面板）走 ValueError，
            # 不在这里捕获——让用户立刻看到，避免静默退化。
            neutralize_meta = [{"error": str(exc), "skipped": True}]

    raw_daily = daily_ic(panel, "factor_value")
    raw_ic_report = ic_summary(raw_daily)
    multiplier, resolved_direction = direction_multiplier(raw_ic_report["rank_ic"]["mean"], config["factor_direction"])

    eval_panel = panel.copy()
    eval_panel["effective_factor_value"] = eval_panel["factor_value"] * multiplier
    daily = daily_ic(eval_panel, "effective_factor_value")
    ic_report = ic_summary(daily)
    time_report = ic_time_analysis(daily)
    distribution_report = ic_distribution_analysis(daily)
    factor_distribution_report = factor_distribution_analysis(eval_panel, "effective_factor_value")
    rank_autocorr_report = factor_rank_autocorrelation(eval_panel, "effective_factor_value", [1, 5])
    turnover_report = turnover(eval_panel, float(config["turnover_quantile"]), "effective_factor_value")
    decay_report = decay_curve(
        eval_panel,
        list(config["decay_horizons"]),
        "effective_factor_value",
        str(config["target_kind"]),
    )

    bootstrap_report: dict[str, Any] = {}
    if int(config.get("bootstrap_n", 0)) > 0 and str(config.get("target_kind", "return")) == "return":
        bootstrap_report = bootstrap_rank_ic_baseline(
            eval_panel,
            n_boot=int(config["bootstrap_n"]),
            seed=int(config.get("bootstrap_seed", 1729)),
            factor_col="effective_factor_value",
            target_col="forward_return",
        )

    return {
        "panel": panel,
        "eval_panel": eval_panel,
        "raw_ic_report": raw_ic_report,
        "multiplier": multiplier,
        "resolved_direction": resolved_direction,
        "daily": daily,
        "ic_report": ic_report,
        "time_report": time_report,
        "distribution_report": distribution_report,
        "factor_distribution_report": factor_distribution_report,
        "rank_autocorr_report": rank_autocorr_report,
        "turnover_report": turnover_report,
        "decay_report": decay_report,
        "bootstrap_report": bootstrap_report,
        "neutralize_meta": neutralize_meta,
    }


def apply_layer(base: dict[str, Any], config: dict) -> dict[str, Any]:
    """基于 compute_panel_base 缓存装配最终报告。

    只对依赖 group_count 的部分（layer_backtest / research_diagnostics /
    quality_checklist / quality_warnings 中的 group_count 检查）重算。
    """
    panel = base["panel"]
    eval_panel = base["eval_panel"]
    raw_ic_report = base["raw_ic_report"]
    resolved_direction = base["resolved_direction"]
    daily = base["daily"]
    ic_report = base["ic_report"]
    time_report = base["time_report"]
    distribution_report = base["distribution_report"]
    factor_distribution_report = base["factor_distribution_report"]
    rank_autocorr_report = base["rank_autocorr_report"]
    turnover_report = base["turnover_report"]
    decay_report = base["decay_report"]
    bootstrap_report = base.get("bootstrap_report") or {}
    neutralize_meta = base.get("neutralize_meta") or []

    layer_report = layer_backtest(
        eval_panel,
        int(config["group_count"]),
        "effective_factor_value",
        float(config["annualization_factor"]),
        str(config["target_kind"]),
        resolved_direction=resolved_direction,
    )

    # P3 交易成本：把 long_short 日序列按每日换手扣除单边成本 × 2 后重新算 IR / 累计。
    long_short_series = layer_report.pop("_long_short_series", None)
    turnover_daily = pd.DataFrame(turnover_report.get("daily", []))
    if long_short_series is not None and not turnover_daily.empty:
        turnover_daily = turnover_daily.set_index("trade_date")["turnover"]
        ls = long_short_series.copy()
        # long_short 索引是 trade_date，turnover 索引也是 trade_date，按对应日对齐
        ls.index = ls.index.astype(str) if hasattr(ls.index, "astype") else ls.index
        cost_grid = list(config.get("cost_grid_bps") or [])
        cost_aware = {
            "cost_grid_bps": cost_grid,
            "sweep": cost_sweep(
                ls,
                turnover_daily,
                cost_grid_bps=cost_grid,
                annualization_factor=float(config["annualization_factor"]),
            )
            if cost_grid
            else [],
        }
    else:
        cost_aware = {"cost_grid_bps": [], "sweep": []}

    research_report = make_research_diagnostics(eval_panel, config)
    warning_list = quality_warnings(eval_panel, daily, layer_report, config)
    warning_list.extend(research_report.get("return_target_comparison", {}).get("warnings", []))
    # 把中性化阶段的错误也作为质量提示推上去，不静默吃掉
    for meta in neutralize_meta:
        if meta.get("error"):
            warning_list.append(f"中性化失败已回退到原因子：{meta['error']}")
            break
    if config["target_kind"] == "binary_success":
        methodology = "target_kind=binary_success 时，forward_return 被解释为 0/1 次日封板成功标签；分组均值表示成功率；多空值表示高分组与低分组的成功率差；RankIC 为因子与成功标签的横截面秩相关；衰减曲线使用未来 n 个信号样本成功标签均值。"
    else:
        methodology = "按交易日横截面计算 Pearson IC 与 Spearman RankIC；forward_return 为可交易收益时建议使用 t+1 close 到 t+2 close；factor_direction 决定评估时是否反向排序因子；分层收益以调整方向后的因子高组为好组；多空 IR 使用 annualization_factor 年化；换手率使用顶部组合 Jaccard 距离；衰减曲线用调整方向后的因子与未来第 n 期收益的 RankIC。"
    if bool(config.get("neutralize", False)):
        methodology += " 已对 factor_value 做横截面行业 + 风格中性化（OLS 残差），IC 与分层均基于残差因子。"

    summary_preview = {
        "ic": ic_report["ic"]["mean"],
        "icir": ic_report["ic"]["ir"],
        "rank_ic": ic_report["rank_ic"]["mean"],
        "rank_icir": ic_report["rank_ic"]["ir"],
    }
    checklist = quality_checklist(
        summary_preview,
        ic_report,
        time_report,
        distribution_report,
        factor_distribution_report,
        layer_report,
        decay_report,
    )
    checklist_passed = all(item["passed"] for item in checklist)

    summary = {
        "sample_count": int(len(panel)),
        "raw_sample_count": int(panel.attrs.get("raw_row_count", len(panel))),
        "dropped_missing_row_count": int(panel.attrs.get("dropped_missing_row_count", 0)),
        "date_count": int(panel["trade_date"].nunique()),
        "asset_count": int(panel["ts_code"].nunique()),
        "start_date": str(panel["trade_date"].min()),
        "end_date": str(panel["trade_date"].max()),
        "factor_direction": str(config["factor_direction"]),
        "resolved_factor_direction": resolved_direction,
        "target_kind": str(config["target_kind"]),
        "group_mode": str(config["group_mode"]),
        "group_count": int(layer_report["group_count"]),
        "configured_group_count": int(config["group_count"]),
        "annualization_factor": config["annualization_factor"],
        "stock_pool": str(config.get("stock_pool", "all_a")),
        "stock_pool_label": str(config.get("stock_pool_label", STOCK_POOL_LABELS["all_a"])),
        "ic": ic_report["ic"]["mean"],
        "icir": ic_report["ic"]["ir"],
        "rank_ic": ic_report["rank_ic"]["mean"],
        "rank_icir": ic_report["rank_ic"]["ir"],
        "raw_ic": raw_ic_report["ic"]["mean"],
        "raw_rank_ic": raw_ic_report["rank_ic"]["mean"],
        "long_short_cumulative_return": layer_report["long_short_cumulative_return"],
        "long_short_ir": layer_report["long_short_ir"],
        "average_turnover": turnover_report["average_turnover"],
        "monotonicity_passed": layer_report["monotonicity"]["passed"],
        "rank_ic_autocorr_lag1": time_report["rank_ic_autocorr_lag1"],
        "rank_ic_autocorr_lag5": time_report["rank_ic_autocorr_lag5"],
        "factor_rank_autocorr_lag1": rank_autocorr_report["summary"]["lag1"],
        "factor_rank_autocorr_lag5": rank_autocorr_report["summary"]["lag5"],
        "ic_skew": distribution_report["ic_skew"],
        "ic_kurtosis": distribution_report["ic_kurtosis"],
        "rank_ic_skew": distribution_report["rank_ic_skew"],
        "rank_ic_kurtosis": distribution_report["rank_ic_kurtosis"],
        "factor_avg_skew": factor_distribution_report["avg_skew"],
        "factor_avg_kurtosis": factor_distribution_report["avg_kurtosis"],
        "factor_avg_extreme_ratio": factor_distribution_report["avg_extreme_ratio"],
        "quality_check_passed": checklist_passed,
        "research_diagnostics_enabled": bool(research_report),
        # P3：HAC t 与 bootstrap p-value 暴露在 summary，便于 result_value 之外快速对比
        "rank_ic_t_hac": ic_report["rank_ic"].get("t_stat_hac"),
        "ic_t_hac": ic_report["ic"].get("t_stat_hac"),
        "rank_ic_bootstrap_p": bootstrap_report.get("p_two_sided"),
        "rank_ic_bootstrap_ci_low": bootstrap_report.get("ci95_low"),
        "rank_ic_bootstrap_ci_high": bootstrap_report.get("ci95_high"),
        "neutralized": bool(config.get("neutralize", False)) and not any(m.get("error") for m in neutralize_meta),
    }

    return {
        "summary": summary,
        "ic_analysis": ic_report,
        "raw_ic_analysis": raw_ic_report,
        "ic_time_analysis": time_report,
        "ic_distribution": distribution_report,
        "factor_distribution": factor_distribution_report,
        "factor_rank_autocorrelation": rank_autocorr_report,
        "layer_backtest": layer_report,
        "turnover_analysis": turnover_report,
        "decay_curve": decay_report,
        "research_diagnostics": research_report,
        "quality_checklist": checklist,
        "quality_warnings": warning_list,
        "methodology": methodology,
        # P3 新增模块：默认空 dict / 空 list 不影响下游
        "bootstrap_baseline": bootstrap_report,
        "transaction_cost": cost_aware,
        "neutralization": {
            "enabled": bool(config.get("neutralize", False)),
            "industry_level": str(config.get("industry_level", "L1")),
            "style_factors": list(config.get("neutralize_style") or []),
            "daily_meta": neutralize_meta,
        },
    }


def make_report(panel: pd.DataFrame, config: dict) -> dict[str, Any]:
    """对外稳定入口：完整跑一次因子评估报告。

    内部拆为 compute_panel_base + apply_layer，便于多 group_count 复用。
    单独调用时仍是一次性完整路径，行为与拆分前完全一致（由 test 中
    test_make_report_equivalent_to_split_path 覆盖）。
    """
    base = compute_panel_base(panel, config)
    return apply_layer(base, config)


# 兼容旧 import：``from metrics import make_research_diagnostics`` 等。
# 在文件末尾才 import，避免与 research_diagnostics 形成顶部循环 import。
try:
    from .research_diagnostics import (  # noqa: E402
        RESEARCH_RETURN_TARGETS,
        component_bin_analysis,
        component_ic_analysis,
        make_research_diagnostics,
        monthly_stability,
        research_component_columns,
        return_target_comparison,
        reverse_factor_analysis,
        state_segment_analysis,
    )
except ImportError:
    from research_diagnostics import (  # type: ignore[no-redef]  # noqa: E402
        RESEARCH_RETURN_TARGETS,
        component_bin_analysis,
        component_ic_analysis,
        make_research_diagnostics,
        monthly_stability,
        research_component_columns,
        return_target_comparison,
        reverse_factor_analysis,
        state_segment_analysis,
    )
