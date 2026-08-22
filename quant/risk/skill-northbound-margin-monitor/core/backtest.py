"""Historical score backtesting: IC analysis for the panorama composite score.

Computes rolling-window composite scores and evaluates their predictive power
against next-day market returns using Spearman Rank IC.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .northbound import (
    NORTHBOUND_REGISTRY,
    compute_composite_score as nb_composite_score,
    run_all_detectors as run_nb_detectors,
)
from .margin import (
    MARGIN_REGISTRY,
    compute_composite_score as margin_composite_score,
    run_all_detectors as run_margin_detectors,
)
from .futures import (
    FUTURES_REGISTRY,
    compute_composite_score as futures_composite_score,
    run_all_detectors as run_futures_detectors,
)
from .resonance import analyse_resonance, compute_resonance_score
from .scorer import compute_capital_flow_score

logger = logging.getLogger(__name__)


def _spearmanr(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman rank correlation coefficient (no scipy dependency)."""
    n = len(x)
    if n < 3:
        return 0.0
    # Check for zero variance
    if np.std(x) == 0 or np.std(y) == 0:
        return 0.0
    # Rank
    x_rank = np.argsort(np.argsort(x)).astype(float)
    y_rank = np.argsort(np.argsort(y)).astype(float)
    # Pearson correlation on ranks
    xm = x_rank - x_rank.mean()
    ym = y_rank - y_rank.mean()
    denom = np.sqrt((xm ** 2).sum() * (ym ** 2).sum())
    if denom == 0:
        return 0.0
    return float((xm * ym).sum() / denom)


@dataclass
class BacktestResult:
    """Result of a historical IC backtest run."""
    n_periods: int
    mean_ic: float
    ic_std: float
    icir: float                      # Information Coefficient IR = mean / std
    hit_rate: float                  # fraction of periods with correct direction
    ic_series: list[float] = field(default_factory=list)
    score_series: list[float] = field(default_factory=list)
    return_series: list[float] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    summary: str = ""


def run_ic_backtest(
    nb_summary: pd.DataFrame,
    margin_macro: pd.DataFrame,
    margin_detail: pd.DataFrame | None = None,
    stock_info: pd.DataFrame | None = None,
    futures_data: pd.DataFrame | None = None,
    config: dict | None = None,
    min_window: int = 60,
    return_col: str = "CSI300",
    step_days: int = 5,
) -> BacktestResult:
    """Compute rolling composite scores and evaluate IC vs next-period returns.

    For each date with at least *min_window* days of history, the pipeline
    is re-run using only data known as of that date. The composite score is
    then correlated with the next-period return of *return_col*.

    Args:
        nb_summary: Northbound daily summary (must have ``date`` column).
        margin_macro: Margin macro history (must have ``date`` column).
        margin_detail: Per-stock margin detail (optional — reduces accuracy).
        stock_info: Stock info for sector/name mapping (optional).
        futures_data: Index futures daily data (optional — excluded if absent).
        config: Runtime config dict.
        min_window: Minimum days of history required per period.
        return_col: Column in *nb_summary* used for return calculation
                    (default: CSI300).
        step_days: Step size between evaluation dates (1 = every day,
                   5 = weekly).

    Returns:
        BacktestResult with IC statistics and series.
    """
    cfg = config or {}
    stock_info = stock_info if stock_info is not None else pd.DataFrame()
    margin_detail = margin_detail if margin_detail is not None else pd.DataFrame()
    futures_data = futures_data if futures_data is not None else pd.DataFrame()

    # Prepare data
    nb = nb_summary.sort_values("date", ascending=True).copy()
    mg = margin_macro.sort_values("date", ascending=True).copy()
    fut = futures_data.sort_values("date", ascending=True).copy() if "date" in futures_data.columns else futures_data.copy()

    # Resolve return column
    ret_col = None
    for c in [return_col, "CSI300", "csi300", "沪深300"]:
        if c in nb.columns:
            ret_col = c
            break
    if ret_col is None:
        raise ValueError(f"No return column found in nb_summary (tried: {return_col})")

    returns = pd.to_numeric(nb[ret_col], errors="coerce").pct_change().shift(-1)
    dates = nb["date"].astype(str).tolist()

    n = len(nb)
    if n < min_window + 1:
        raise ValueError(f"Need at least {min_window + 1} rows, got {n}")

    scores: list[float] = []
    fwd_returns: list[float] = []
    eval_dates: list[str] = []

    # Rolling window evaluation
    for i in range(min_window, n - 1, step_days):
        eval_date = dates[i]
        nb_slice = nb.iloc[: i + 1].copy()
        mg_slice = mg[mg["date"].astype(str) <= eval_date].copy()

        if len(mg_slice) < 20:
            continue

        try:
            # Run detectors on sliced data
            nb_signals = run_nb_detectors(
                nb_slice, pd.DataFrame(), stock_info, cfg,
            )
            nb_comp = nb_composite_score(nb_signals)

            margin_signals = run_margin_detectors(
                margin_detail, mg_slice, stock_info, cfg,
            )
            mg_comp = margin_composite_score(margin_signals)

            # Futures (if available)
            futures_signals = []
            futures_comp = 0.0
            f_triggered = 0
            if not fut.empty and "date" in fut.columns:
                fut_slice = fut[fut["date"].astype(str) <= eval_date].copy()
                if len(fut_slice) >= 5:
                    futures_signals = run_futures_detectors(fut_slice, cfg)
                    futures_comp = futures_composite_score(futures_signals)
                    f_triggered = sum(1 for s in futures_signals if s.triggered)

            resonance_results = analyse_resonance(
                nb_comp, mg_comp,
                sum(1 for s in nb_signals if s.direction == "bullish"),
                sum(1 for s in nb_signals if s.direction == "bearish"),
                sum(1 for s in margin_signals if s.direction == "bullish"),
                sum(1 for s in margin_signals if s.direction == "bearish"),
                cfg,
            )
            res_score = compute_resonance_score(resonance_results, cfg)

            composite = compute_capital_flow_score(
                nb_comp, mg_comp, res_score,
                sum(1 for s in nb_signals if s.triggered),
                sum(1 for s in margin_signals if s.triggered),
                sum(1 for r in resonance_results if r.triggered),
                cfg,
                futures_composite=futures_comp,
                futures_triggered_count=f_triggered,
            )

            fwd_ret = returns.iloc[i]
            if pd.isna(fwd_ret):
                continue

            scores.append(composite.score)
            fwd_returns.append(float(fwd_ret))
            eval_dates.append(eval_date)

        except Exception:
            logger.debug("Backtest failed at %s", eval_date, exc_info=True)
            continue

    if len(scores) < 5:
        return BacktestResult(
            n_periods=len(scores),
            mean_ic=0.0, ic_std=0.0, icir=0.0, hit_rate=0.0,
            summary="数据不足（<5个评估周期）",
        )

    # Compute Spearman Rank IC
    score_arr = np.array(scores)
    ret_arr = np.array(fwd_returns)

    ic_values: list[float] = []
    hit_count = 0
    for j in range(len(score_arr)):
        # Rank IC at each point uses all data up to j (expanding window)
        if j >= 4:
            ic = _spearmanr(score_arr[: j + 1], ret_arr[: j + 1])
            if not np.isnan(ic):
                ic_values.append(float(ic))
        if j > 0:
            if (score_arr[j] - score_arr[j - 1]) * (ret_arr[j]) > 0:
                hit_count += 1

    if not ic_values:
        return BacktestResult(
            n_periods=len(scores),
            mean_ic=0.0, ic_std=0.0, icir=0.0, hit_rate=0.0,
            summary="无法计算IC",
        )

    mean_ic = float(np.mean(ic_values))
    ic_std = float(np.std(ic_values, ddof=1)) if len(ic_values) > 1 else 0.0
    icir = mean_ic / ic_std if ic_std > 0 else 0.0
    hit_rate = hit_count / max(len(scores) - 1, 1)

    # Build summary
    if mean_ic > 0.05 and icir > 0.5:
        quality = "优秀 — 评分具有显著预测能力"
    elif mean_ic > 0.02 and icir > 0.2:
        quality = "良好 — 评分具有一定预测能力"
    elif mean_ic > 0:
        quality = "一般 — 评分预测能力较弱"
    else:
        quality = "较差 — 评分方向性预测不佳"

    summary = (
        f"IC回测结果（{len(scores)}个周期，步长{step_days}日）：\n"
        f"Mean IC: {mean_ic:.4f}  |  IC Std: {ic_std:.4f}  |  ICIR: {icir:.4f}\n"
        f"Hit Rate: {hit_rate:.1%}  |  评级: {quality}"
    )

    logger.info("Backtest complete: %s", summary)

    return BacktestResult(
        n_periods=len(scores),
        mean_ic=mean_ic,
        ic_std=ic_std,
        icir=icir,
        hit_rate=round(hit_rate, 4),
        ic_series=ic_values,
        score_series=scores,
        return_series=fwd_returns,
        dates=eval_dates,
        summary=summary,
    )


def backtest_summary_table(result: BacktestResult) -> str:
    """Render a Markdown summary table for a BacktestResult."""
    return (
        f"| 指标 | 数值 |\n"
        f"|------|------|\n"
        f"| 评估周期数 | {result.n_periods} |\n"
        f"| Mean IC | {result.mean_ic:.4f} |\n"
        f"| IC Std | {result.ic_std:.4f} |\n"
        f"| ICIR | {result.icir:.4f} |\n"
        f"| Hit Rate | {result.hit_rate:.1%} |\n"
    )


# ------------------------------------------------------------------
# Rolling window stability analysis
# ------------------------------------------------------------------


@dataclass
class RollingICResult:
    """Rolling-window IC stability metrics."""
    window_size: int
    step_size: int
    n_windows: int
    ic_mean: float
    ic_std: float
    ic_min: float
    ic_max: float
    stability_ratio: float  # proportion of windows with IC > 0
    ic_series: list[float]
    window_end_dates: list[str]
    summary: str


def rolling_ic_analysis(
    scores: list[float],
    returns: list[float],
    dates: list[str],
    window_size: int = 60,
    step_size: int = 20,
) -> RollingICResult:
    """Compute rolling-window IC to assess signal stability over time.

    A consistently positive IC across windows indicates a robust signal.
    High variance in IC suggests the signal may be regime-dependent.

    Args:
        scores: Composite scores for each period.
        returns: Forward returns for each period.
        dates: Evaluation dates.
        window_size: Number of periods per rolling window.
        step_size: Step between windows.

    Returns:
        RollingICResult with stability metrics.
    """
    n = len(scores)
    if n < window_size:
        return RollingICResult(
            window_size=window_size, step_size=step_size,
            n_windows=0, ic_mean=0.0, ic_std=0.0, ic_min=0.0, ic_max=0.0,
            stability_ratio=0.0, ic_series=[], window_end_dates=[],
            summary=f"数据不足（需要至少{window_size}个周期，当前{n}个）",
        )

    window_ics: list[float] = []
    window_dates: list[str] = []

    score_arr = np.array(scores)
    ret_arr = np.array(returns)

    for start in range(0, n - window_size + 1, step_size):
        end = start + window_size
        ic = _spearmanr(score_arr[start:end], ret_arr[start:end])
        if not np.isnan(ic):
            window_ics.append(float(ic))
            window_dates.append(dates[end - 1] if end - 1 < len(dates) else "")

    if not window_ics:
        return RollingICResult(
            window_size=window_size, step_size=step_size,
            n_windows=0, ic_mean=0.0, ic_std=0.0, ic_min=0.0, ic_max=0.0,
            stability_ratio=0.0, ic_series=[], window_end_dates=[],
            summary="无法计算滚动IC",
        )

    ic_mean = float(np.mean(window_ics))
    ic_std = float(np.std(window_ics, ddof=1)) if len(window_ics) > 1 else 0.0
    ic_min = float(np.min(window_ics))
    ic_max = float(np.max(window_ics))
    stability_ratio = sum(1 for ic in window_ics if ic > 0) / len(window_ics)

    # Stability assessment
    if stability_ratio >= 0.8 and ic_std < 0.05:
        quality = "高度稳定"
    elif stability_ratio >= 0.6:
        quality = "基本稳定"
    elif stability_ratio >= 0.4:
        quality = "不稳定 — 信号方向性随时间变化"
    else:
        quality = "不可靠 — 信号方向性频繁反转"

    summary = (
        f"滚动IC分析（窗口{window_size}期，步长{step_size}期）：\n"
        f"窗口数: {len(window_ics)}  |  Mean IC: {ic_mean:.4f}  |  "
        f"IC Range: [{ic_min:.4f}, {ic_max:.4f}]\n"
        f"正向率: {stability_ratio:.1%}  |  稳定性: {quality}"
    )

    return RollingICResult(
        window_size=window_size,
        step_size=step_size,
        n_windows=len(window_ics),
        ic_mean=ic_mean,
        ic_std=ic_std,
        ic_min=ic_min,
        ic_max=ic_max,
        stability_ratio=round(stability_ratio, 4),
        ic_series=window_ics,
        window_end_dates=window_dates,
        summary=summary,
    )


# ------------------------------------------------------------------
# Per-detector IC analysis & weight optimization
# ------------------------------------------------------------------


@dataclass
class DetectorICResult:
    """IC analysis for a single detector."""
    key: str
    label: str
    dimension: str       # "northbound" | "margin" | "futures"
    current_weight: int
    mean_ic: float
    ic_ir: float
    hit_rate: float
    n_observations: int
    suggested_weight: int
    suggestion_reason: str


def analyse_detector_weights(
    nb_signals_list: list[list],
    margin_signals_list: list[list],
    futures_signals_list: list[list],
    returns: list[float],
    config: dict | None = None,
) -> list[DetectorICResult]:
    """Compute per-detector IC and suggest optimal weights.

    For each detector, compute the Spearman rank IC between its strength
    signal and forward returns, then suggest weight adjustments.

    Args:
        nb_signals_list: List of nb_signal lists, one per evaluation period.
        margin_signals_list: List of margin_signal lists, one per period.
        futures_signals_list: List of futures_signal lists, one per period.
        returns: Forward returns for each period.
        config: Config with current weights.

    Returns:
        List of DetectorICResult with per-detector metrics and suggestions.
    """
    cfg = config or {}

    # Collect detectors from registries
    detectors: list[dict] = []
    for key, meta in NORTHBOUND_REGISTRY.items():
        detectors.append({
            "key": key, "label": meta.get("label", key),
            "dimension": "northbound", "weight": meta.get("weight", 1),
            "registry": NORTHBOUND_REGISTRY,
        })
    for key, meta in MARGIN_REGISTRY.items():
        detectors.append({
            "key": key, "label": meta.get("label", key),
            "dimension": "margin", "weight": meta.get("weight", 1),
            "registry": MARGIN_REGISTRY,
        })
    for key, meta in FUTURES_REGISTRY.items():
        detectors.append({
            "key": key, "label": meta.get("label", key),
            "dimension": "futures", "weight": meta.get("weight", 1),
            "registry": FUTURES_REGISTRY,
        })

    results: list[DetectorICResult] = []

    for det in detectors:
        # Extract strength values for this detector across all periods
        strengths: list[float] = []
        valid_returns: list[float] = []

        signal_lists = {
            "northbound": nb_signals_list,
            "margin": margin_signals_list,
            "futures": futures_signals_list,
        }[det["dimension"]]

        for i, sigs in enumerate(signal_lists):
            if i >= len(returns):
                break
            for s in sigs:
                if getattr(s, "key", "") == det["key"]:
                    strengths.append(float(getattr(s, "strength", 0.0)))
                    valid_returns.append(float(returns[i]))
                    break

        if len(strengths) < 5:
            results.append(DetectorICResult(
                key=det["key"], label=det["label"],
                dimension=det["dimension"],
                current_weight=det["weight"],
                mean_ic=0.0, ic_ir=0.0, hit_rate=0.0,
                n_observations=len(strengths),
                suggested_weight=det["weight"],
                suggestion_reason="观察不足",
            ))
            continue

        # Compute IC
        strength_arr = np.array(strengths)
        ret_arr = np.array(valid_returns)
        ic = _spearmanr(strength_arr, ret_arr)

        # Compute IR via bootstrap sampling of IC
        ic_samples: list[float] = []
        n_bs = min(100, len(strengths))
        rng = np.random.RandomState(42)
        for _ in range(n_bs):
            idx = rng.choice(len(strengths), size=len(strengths) // 2, replace=False)
            sample_ic = _spearmanr(strength_arr[idx], ret_arr[idx])
            if not np.isnan(sample_ic):
                ic_samples.append(sample_ic)

        ic_ir = abs(ic) / (np.std(ic_samples, ddof=1) + 1e-8) if ic_samples else 0.0

        # Hit rate: direction match
        hits = 0
        for j in range(1, len(strengths)):
            s_dir = strengths[j] - strengths[j - 1]
            r_dir = valid_returns[j]
            if s_dir * r_dir > 0:
                hits += 1
        hit_rate = hits / max(len(strengths) - 1, 1)

        # Weight suggestion
        current_w = det["weight"]
        if abs(ic) > 0.05 and ic_ir > 0.5:
            suggested_w = min(current_w + 1, 4)
            reason = f"IC={ic:.3f}, ICIR={ic_ir:.2f} — 预测能力强，建议加权重"
        elif abs(ic) > 0.02 and ic_ir > 0.2:
            suggested_w = current_w
            reason = f"IC={ic:.3f}, ICIR={ic_ir:.2f} — 预测能力一般，维持权重"
        elif abs(ic) < 0.01 or ic_ir < 0.1:
            suggested_w = max(current_w - 1, 0)
            reason = f"IC={ic:.3f}, ICIR={ic_ir:.2f} — 预测能力弱，建议减权重"
        else:
            suggested_w = current_w
            reason = f"IC={ic:.3f}, ICIR={ic_ir:.2f} — 边界信号，暂维持权重"

        results.append(DetectorICResult(
            key=det["key"],
            label=det["label"],
            dimension=det["dimension"],
            current_weight=current_w,
            mean_ic=round(float(ic), 4),
            ic_ir=round(float(ic_ir), 2),
            hit_rate=round(float(hit_rate), 4),
            n_observations=len(strengths),
            suggested_weight=suggested_w,
            suggestion_reason=reason,
        ))

    # Sort by absolute IC descending
    results.sort(key=lambda r: abs(r.mean_ic), reverse=True)
    return results


# ------------------------------------------------------------------
# Score calibration: map score buckets to out-of-sample returns
# ------------------------------------------------------------------


@dataclass
class ScoreCalibration:
    """Maps composite score ranges to historical forward return distributions.

    This answers: "When the system said 40/D in the past, what actually
    happened to the market over the next N days?"
    """
    score_buckets: list[str]          # e.g. ["A+", "A", "B+", ...]
    bucket_ranges: list[str]          # e.g. ["85-100", "75-84", ...]
    mean_fwd_ret_1d: list[float]      # average 1-day forward return
    mean_fwd_ret_5d: list[float]      # average 5-day forward return
    mean_fwd_ret_20d: list[float]     # average 20-day forward return
    hit_rate_1d: list[float]          # fraction where return direction matches score direction
    hit_rate_5d: list[float]
    hit_rate_20d: list[float]
    n_observations: list[int]         # number of observations per bucket
    total_periods: int
    summary: str


# Bucket definitions (score range → grade → label)
SCORE_BUCKETS = [
    (85, 100, "A+", "强烈看多"),
    (75, 84, "A", "看多"),
    (65, 74, "B+", "偏多"),
    (55, 64, "B", "温和偏多"),
    (45, 54, "C", "中性"),
    (35, 44, "D", "中性偏空"),
    (25, 34, "E", "偏空"),
    (15, 24, "F", "看空"),
    (0, 14, "F-", "强烈看空"),
]


def calibrate_score_to_returns(
    scores: list[float],
    fwd_returns_1d: list[float],
    fwd_returns_5d: list[float] | None = None,
    fwd_returns_20d: list[float] | None = None,
) -> ScoreCalibration:
    """Compute historical forward return distributions per score bucket.

    Args:
        scores: Composite scores (0-100) for each period.
        fwd_returns_1d: 1-day forward returns (decimal, e.g. 0.005 = 0.5%).
        fwd_returns_5d: 5-day forward returns (optional).
        fwd_returns_20d: 20-day forward returns (optional).

    Returns:
        ScoreCalibration with per-bucket statistics.
    """
    n = len(scores)
    if n < 20:
        return ScoreCalibration(
            score_buckets=[], bucket_ranges=[], mean_fwd_ret_1d=[],
            mean_fwd_ret_5d=[], mean_fwd_ret_20d=[],
            hit_rate_1d=[], hit_rate_5d=[], hit_rate_20d=[],
            n_observations=[], total_periods=n,
            summary="数据不足（需要至少20个评估周期）",
        )

    fwd_5d = list(fwd_returns_5d) if fwd_returns_5d else [0.0] * n
    fwd_20d = list(fwd_returns_20d) if fwd_returns_20d else [0.0] * n

    bucket_labels: list[str] = []
    bucket_ranges: list[str] = []
    mean_1d: list[float] = []
    mean_5d: list[float] = []
    mean_20d: list[float] = []
    hr_1d: list[float] = []
    hr_5d: list[float] = []
    hr_20d: list[float] = []
    nobs: list[int] = []

    for lo, hi, grade, label in SCORE_BUCKETS:
        indices = [i for i, s in enumerate(scores) if lo <= s <= hi]
        if len(indices) < 3:
            continue

        rets_1d = [fwd_returns_1d[i] for i in indices if not np.isnan(fwd_returns_1d[i])]
        rets_5 = [fwd_5d[i] for i in indices if not np.isnan(fwd_5d[i])]
        rets_20 = [fwd_20d[i] for i in indices if not np.isnan(fwd_20d[i])]

        bucket_labels.append(f"{grade} ({label})")
        bucket_ranges.append(f"{lo}-{hi}")
        mean_1d.append(round(float(np.mean(rets_1d)) * 100, 2) if rets_1d else 0.0)
        mean_5d.append(round(float(np.mean(rets_5)) * 100, 2) if rets_5 else 0.0)
        mean_20d.append(round(float(np.mean(rets_20)) * 100, 2) if rets_20 else 0.0)

        # Hit rate: does the return direction match the score direction?
        # For scores > 50, expect positive return; for < 50, expect negative
        expected_dir = 1 if lo >= 50 else (-1 if hi <= 50 else 0)
        if expected_dir != 0 and rets_1d:
            hr_1d.append(round(sum(1 for r in rets_1d if r * expected_dir > 0) / len(rets_1d), 2))
        else:
            hr_1d.append(0.0)
        if expected_dir != 0 and rets_5:
            hr_5d.append(round(sum(1 for r in rets_5 if r * expected_dir > 0) / len(rets_5), 2))
        else:
            hr_5d.append(0.0)
        if expected_dir != 0 and rets_20:
            hr_20d.append(round(sum(1 for r in rets_20 if r * expected_dir > 0) / len(rets_20), 2))
        else:
            hr_20d.append(0.0)

        nobs.append(len(rets_1d))

    # Build summary
    if bucket_labels:
        # Find the bucket with the best 5d return
        best_idx = int(np.argmax(mean_5d)) if mean_5d else 0
        worst_idx = int(np.argmin(mean_5d)) if mean_5d else 0
        summary = (
            f"评分校准（{n}个周期）：\n"
            f"最佳分档: {bucket_labels[best_idx]} → 平均5日收益 {mean_5d[best_idx]:+.2f}%\n"
            f"最差分档: {bucket_labels[worst_idx]} → 平均5日收益 {mean_5d[worst_idx]:+.2f}%\n"
            f"覆盖分档: {len(bucket_labels)}/{len(SCORE_BUCKETS)}"
        )
    else:
        summary = "无足够数据填充评分分档"

    return ScoreCalibration(
        score_buckets=bucket_labels,
        bucket_ranges=bucket_ranges,
        mean_fwd_ret_1d=mean_1d,
        mean_fwd_ret_5d=mean_5d,
        mean_fwd_ret_20d=mean_20d,
        hit_rate_1d=hr_1d,
        hit_rate_5d=hr_5d,
        hit_rate_20d=hr_20d,
        n_observations=nobs,
        total_periods=n,
        summary=summary,
    )


def calibration_summary_table(cal: ScoreCalibration) -> str:
    """Render a Markdown table for score calibration results."""
    if not cal.score_buckets:
        return f"（{cal.summary}）"

    lines = [
        "| 评分等级 | 分数区间 | N | 1日收益均值 | 5日收益均值 | 20日收益均值 | 1日胜率 | 5日胜率 | 20日胜率 |",
        "|----------|----------|---|:----------:|:----------:|:-----------:|:------:|:------:|:------:|",
    ]
    for i in range(len(cal.score_buckets)):
        lines.append(
            f"| {cal.score_buckets[i]} | {cal.bucket_ranges[i]} | {cal.n_observations[i]} | "
            f"{cal.mean_fwd_ret_1d[i]:+.2f}% | {cal.mean_fwd_ret_5d[i]:+.2f}% | "
            f"{cal.mean_fwd_ret_20d[i]:+.2f}% | "
            f"{cal.hit_rate_1d[i]:.0%} | {cal.hit_rate_5d[i]:.0%} | {cal.hit_rate_20d[i]:.0%} |"
        )

    lines.append(f"\n> {cal.summary}")
    return "\n".join(lines)


def detector_weight_summary_table(results: list[DetectorICResult]) -> str:
    """Render a Markdown table summarizing per-detector IC results."""
    lines = [
        "| 检测器 | 维度 | 当前权重 | Mean IC | ICIR | Hit Rate | 建议权重 | 理由 |",
        "|--------|------|----------|---------|------|----------|----------|------|",
    ]
    for r in results:
        lines.append(
            f"| {r.label} | {r.dimension} | {r.current_weight} | "
            f"{r.mean_ic:+.4f} | {r.ic_ir:.2f} | {r.hit_rate:.1%} | "
            f"{r.suggested_weight} | {r.suggestion_reason} |"
        )
    return "\n".join(lines)
