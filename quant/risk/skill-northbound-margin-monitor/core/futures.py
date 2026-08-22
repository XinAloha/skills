"""Stock index futures signal detectors (3 signals, registry pattern).

Analyses CFFEX index futures (CSI 300/SSE 50/CSI 500) to extract
independent sentiment signals that complement northbound flow and
margin trading data.

Key metrics:
  - Basis (基差): futures_price - spot_index, as % of spot
  - Open interest trend: 5-day OI change rate and direction
  - Basis-OI convergence: whether basis direction is confirmed by OI

Data sources:
  - futures_data: Daily index futures data with columns:
    date, contract, close, spot_close, open_interest, volume, index_name
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from ._types import SignalResult, neutral_signal, apply_signal_decay

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------

FUTURES_REGISTRY = {
    "futures_basis": {
        "func": "detect_futures_basis",
        "weight": 3,
        "label": "期货基差",
        "half_life_days": 10,
    },
    "open_interest_trend": {
        "func": "detect_open_interest_trend",
        "weight": 2,
        "label": "持仓量趋势",
        "half_life_days": 15,
    },
    "basis_oi_convergence": {
        "func": "detect_basis_oi_convergence",
        "weight": 2,
        "label": "基差持仓共振",
        "half_life_days": 10,
    },
}


def _resolve_col(df: pd.DataFrame, *candidates: str) -> Optional[str]:
    """Return the first column name from *candidates* that exists in *df*."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _safe_float(series: pd.Series) -> pd.Series:
    """Convert series to float, coercing errors to NaN."""
    return pd.to_numeric(series, errors="coerce")


# ------------------------------------------------------------------
# Detector 1: Futures Basis (期货基差)
# ------------------------------------------------------------------

def detect_futures_basis(
    futures_data: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Analyse index futures basis (基差) direction and magnitude.

    Basis = (futures_close - spot_close) / spot_close * 100

    Positive basis (升水/contango) → bullish sentiment: futures traders
    willing to pay premium over spot.

    Negative basis (贴水/backwardation) → bearish sentiment: futures
    traders demand discount, often hedging pressure.

    Strength is determined by:
      - Basis magnitude vs historical distribution
      - Number of indices showing same-direction basis
      - Recent basis trend (expanding/contracting)
    """
    key = "futures_basis"
    label = "期货基差"

    if futures_data.empty:
        return neutral_signal(key, label, "无股指期货数据", detail={"data_source": "akshare_sina"})

    # Need date, close, spot_close columns
    date_col = _resolve_col(futures_data, "date", "日期")
    close_col = _resolve_col(futures_data, "close", "收盘价")
    spot_col = _resolve_col(futures_data, "spot_close", "spot", "现货收盘")
    idx_col = _resolve_col(futures_data, "index_name", "指数名称", "contract", "合约")

    if close_col is None or spot_col is None:
        return neutral_signal(key, label, "期货数据缺少价格字段", detail={"data_source": "akshare_sina"})

    df = futures_data.copy()
    df[close_col] = _safe_float(df[close_col])
    df[spot_col] = _safe_float(df[spot_col])

    # Get latest date per index
    if date_col and idx_col:
        df = df.sort_values(date_col)
        latest = df.groupby(idx_col).last().reset_index()
    else:
        latest = df.tail(3)

    if latest.empty or latest[close_col].isna().all():
        return neutral_signal(key, label, "期货价格数据为空", detail={"data_source": "akshare_sina"})

    # Calculate basis for each index
    latest["basis_pct"] = (
        (latest[close_col] - latest[spot_col]) / latest[spot_col] * 100
    )

    basis_values = latest["basis_pct"].dropna()
    if len(basis_values) < 1:
        return neutral_signal(key, label, "无法计算基差", detail={"data_source": "akshare_sina"})

    avg_basis = float(basis_values.mean())
    n_positive = int((basis_values > 0).sum())
    n_total = len(basis_values)

    # Determine direction
    if avg_basis > 0.3:
        direction = "bullish"
        triggered = True
    elif avg_basis < -0.3:
        direction = "bearish"
        triggered = True
    else:
        direction = "neutral"
        triggered = False

    # Strength: magnitude of basis relative to typical range
    abs_basis = abs(avg_basis)
    if abs_basis > 1.5:
        strength_raw = 1.0
    elif abs_basis > 0.8:
        strength_raw = 0.7
    elif abs_basis > 0.3:
        strength_raw = 0.4
    else:
        strength_raw = 0.2

    # Bonus for consensus across indices
    consensus = n_positive / n_total if n_total > 0 else 0.5
    consensus_factor = abs(consensus - 0.5) * 2  # 0 when even split, 1 when unanimous
    strength = strength_raw * (1.0 + consensus_factor * 0.5)
    strength = min(1.0, strength)

    if direction == "bearish":
        strength = -strength

    # Build summary
    basis_str = "、".join([
        f"{row.get(idx_col, '?')}:{row['basis_pct']:+.2f}%"
        for _, row in latest.iterrows()
    ][:3])

    if direction == "bullish":
        summary = f"期货升水（{avg_basis:+.2f}%），{n_positive}/{n_total}个指数升水，情绪偏多 [{basis_str}]"
    elif direction == "bearish":
        summary = f"期货贴水（{avg_basis:+.2f}%），{n_total - n_positive}/{n_total}个指数贴水，情绪偏空 [{basis_str}]"
    else:
        summary = f"期货基差接近平水（{avg_basis:+.2f}%），方向不明确 [{basis_str}]"

    consecutive = 1
    if date_col and len(df) >= 5:
        recent = df.sort_values(date_col).tail(5)
        if "basis_pct" not in recent.columns:
            recent["basis_pct"] = (
                (recent[close_col] - recent[spot_col]) / recent[spot_col] * 100
            )
        recent_basis = recent["basis_pct"].dropna()
        if len(recent_basis) >= 3:
            signs = np.sign(recent_basis.values[-3:])
            if direction == "bullish" and (signs > 0).all():
                consecutive = int((signs > 0).sum())
            elif direction == "bearish" and (signs < 0).all():
                consecutive = int((signs < 0).sum())

    return SignalResult(
        key=key, label=label, triggered=triggered,
        strength=round(strength, 4), direction=direction,
        summary=summary,
        detail={
            "data_source": "akshare_sina",
            "avg_basis_pct": round(avg_basis, 4),
            "n_positive": n_positive,
            "n_total": n_total,
            "consensus_factor": round(consensus_factor, 4),
            "consecutive_days": consecutive,
        },
    )


# ------------------------------------------------------------------
# Detector 2: Open Interest Trend (持仓量趋势)
# ------------------------------------------------------------------

def detect_open_interest_trend(
    futures_data: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Analyse open interest (OI) trend across index futures.

    Rising OI + rising price → trend confirmation, bullish
    Rising OI + falling price → trend confirmation, bearish
    Falling OI + trend → potential exhaustion/reversal
    Rising OI on its own → market participation increasing

    We look at 5-day OI change across all index futures.
    """
    key = "open_interest_trend"
    label = "持仓量趋势"

    if futures_data.empty:
        return neutral_signal(key, label, "无股指期货数据", detail={"data_source": "akshare_sina"})

    oi_col = _resolve_col(
        futures_data, "open_interest", "持仓量", "oi", "open_interest_qty"
    )
    date_col = _resolve_col(futures_data, "date", "日期")
    idx_col = _resolve_col(futures_data, "index_name", "指数名称", "contract", "合约")
    close_col = _resolve_col(futures_data, "close", "收盘价")

    if oi_col is None:
        return neutral_signal(key, label, "期货数据缺少持仓量字段", detail={"data_source": "akshare_sina"})

    df = futures_data.copy()
    df[oi_col] = _safe_float(df[oi_col])
    if close_col:
        df[close_col] = _safe_float(df[close_col])

    if date_col is None:
        return neutral_signal(key, label, "期货数据缺少日期字段", detail={"data_source": "akshare_sina"})

    df = df.sort_values(date_col)

    # Calculate 5-day OI change per index
    oi_changes = []
    if idx_col:
        for name, group in df.groupby(idx_col):
            if len(group) >= 5:
                oi_series = group[oi_col].dropna()
                if len(oi_series) >= 5:
                    oi_5d_ago = oi_series.iloc[-5]
                    oi_now = oi_series.iloc[-1]
                    if oi_5d_ago > 0:
                        change_pct = (oi_now - oi_5d_ago) / oi_5d_ago * 100
                        oi_changes.append(change_pct)
    else:
        if len(df) >= 5:
            oi_series = df[oi_col].dropna()
            if len(oi_series) >= 5:
                oi_5d_ago = oi_series.iloc[-5]
                oi_now = oi_series.iloc[-1]
                if oi_5d_ago > 0:
                    change_pct = (oi_now - oi_5d_ago) / oi_5d_ago * 100
                    oi_changes.append(change_pct)

    if not oi_changes:
        return neutral_signal(key, label, "持仓量数据不足（需至少5个交易日）", detail={"data_source": "akshare_sina"})

    avg_oi_change = float(np.mean(oi_changes))

    # Determine trend
    threshold = config.get("futures", {}).get("oi_change_threshold", 2.0)
    if avg_oi_change > threshold:
        direction = "bullish"
        triggered = True
    elif avg_oi_change < -threshold:
        direction = "bearish"
        triggered = True
    else:
        direction = "neutral"
        triggered = False

    # Strength
    abs_change = abs(avg_oi_change)
    if abs_change > 10:
        strength_raw = 1.0
    elif abs_change > 5:
        strength_raw = 0.7
    elif abs_change > 2:
        strength_raw = 0.4
    else:
        strength_raw = 0.2

    n_up = sum(1 for c in oi_changes if c > 0)
    agreement = max(n_up, len(oi_changes) - n_up) / len(oi_changes)
    strength = strength_raw * (0.6 + 0.4 * agreement)
    strength = min(1.0, strength)

    if direction == "bearish":
        strength = -strength

    n_idx = len(oi_changes)
    up_idx = sum(1 for c in oi_changes if c > 0)

    if direction == "bullish":
        summary = (
            f"持仓量上升（{avg_oi_change:+.1f}%），{up_idx}/{n_idx}个指数增仓，"
            f"市场参与度提升，偏多"
        )
    elif direction == "bearish":
        summary = (
            f"持仓量下降（{avg_oi_change:+.1f}%），{n_idx - up_idx}/{n_idx}个指数减仓，"
            f"资金撤离，偏空"
        )
    else:
        summary = f"持仓量变化不大（{avg_oi_change:+.1f}%），方向中性"

    return SignalResult(
        key=key, label=label, triggered=triggered,
        strength=round(strength, 4), direction=direction,
        summary=summary,
        detail={
            "data_source": "akshare_sina",
            "avg_oi_change_pct": round(avg_oi_change, 4),
            "oi_changes": [round(c, 4) for c in oi_changes],
            "n_indices": n_idx,
            "n_up": up_idx,
            "consecutive_days": 3 if triggered else 1,
        },
    )


# ------------------------------------------------------------------
# Detector 3: Basis-OI Convergence (基差持仓共振)
# ------------------------------------------------------------------

def detect_basis_oi_convergence(
    futures_data: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Detect convergence between basis direction and OI trend.

    Positive basis + rising OI → strong bullish (price premium confirmed by volume)
    Negative basis + rising OI → strong bearish (hedging pressure with volume)
    Positive basis + falling OI → weakening bullish
    Negative basis + falling OI → weakening bearish

    This detector internally calls the basis and OI detectors to get
    their directional signals, then checks for agreement.
    """
    key = "basis_oi_convergence"
    label = "基差持仓共振"

    if futures_data.empty:
        return neutral_signal(key, label, "无股指期货数据", detail={"data_source": "akshare_sina"})

    # Run individual detectors
    basis_result = detect_futures_basis(futures_data, config)
    oi_result = detect_open_interest_trend(futures_data, config)

    # Both must be triggered for convergence
    if not basis_result.triggered or not oi_result.triggered:
        return SignalResult(
            key=key, label=label, triggered=False,
            strength=0.0, direction="neutral",
            summary="基差与持仓未形成共振（单边信号不足）",
            detail={
                "data_source": "akshare_sina",
                "basis_triggered": basis_result.triggered,
                "oi_triggered": oi_result.triggered,
                "basis_direction": basis_result.direction,
                "oi_direction": oi_result.direction,
                "consecutive_days": 1,
            },
        )

    # Same direction → convergence confirmed
    if basis_result.direction == oi_result.direction:
        avg_strength = (basis_result.strength + oi_result.strength) / 2
        direction = basis_result.direction
        triggered = True

        # Amplify: agreement across independent signals
        strength = avg_strength * 1.3
        strength = max(-1.0, min(1.0, strength))

        if direction == "bullish":
            summary = (
                f"基差升水+持仓增加共振：期货升水有量能支撑，做多信号明确 "
                f"(基差{basis_result.strength:.2f}, 持仓{oi_result.strength:.2f})"
            )
        else:
            summary = (
                f"基差贴水+持仓增加共振：期货对冲压力有量能支撑，做空信号明确 "
                f"(基差{basis_result.strength:.2f}, 持仓{oi_result.strength:.2f})"
            )
    else:
        # Divergence → weaker signal
        direction = "neutral"
        triggered = False
        strength = 0.0
        summary = (
            f"基差与持仓方向背离（基差{basis_result.direction}，"
            f"持仓{oi_result.direction}），信号分歧，需谨慎"
        )

    return SignalResult(
        key=key, label=label, triggered=triggered,
        strength=round(strength, 4), direction=direction,
        summary=summary,
        detail={
            "data_source": "akshare_sina",
            "basis_triggered": basis_result.triggered,
            "oi_triggered": oi_result.triggered,
            "basis_direction": basis_result.direction,
            "oi_direction": oi_result.direction,
            "basis_strength": basis_result.strength,
            "oi_strength": oi_result.strength,
            "consecutive_days": basis_result.detail.get("consecutive_days", 1),
        },
    )


# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------

# Map detector names to actual functions (resolved at call time)
_DETECTOR_FUNC_MAP = {
    "futures_basis": detect_futures_basis,
    "open_interest_trend": detect_open_interest_trend,
    "basis_oi_convergence": detect_basis_oi_convergence,
}


def run_all_detectors(
    futures_data: pd.DataFrame,
    config: dict,
    active_detectors: set | None = None,
) -> list[SignalResult]:
    """Run all futures detectors and return their SignalResults.

    Args:
        futures_data: Index futures daily data.
        config: Full runtime config dict.
        active_detectors: If set, only run these detectors (by key).

    Returns:
        List of 3 SignalResult objects.
    """
    results: list[SignalResult] = []

    for key, entry in FUTURES_REGISTRY.items():
        if active_detectors is not None and key not in active_detectors:
            continue

        func = _DETECTOR_FUNC_MAP.get(key)
        if func is None:
            logger.warning("Futures detector '%s' not found in func map", key)
            continue

        try:
            result = func(futures_data, config)
        except Exception:
            logger.debug("Futures detector '%s' failed", key, exc_info=True)
            result = neutral_signal(key, entry["label"], f"{entry['label']}执行异常", detail={"data_source": "akshare_sina"})

        results.append(result)

    return results


def get_triggered_signals(results: list[SignalResult]) -> list[SignalResult]:
    """Return only triggered futures signals."""
    return [r for r in results if r.triggered]


def get_bullish_signals(results: list[SignalResult]) -> list[SignalResult]:
    """Return bullish futures signals."""
    return [r for r in results if r.direction == "bullish"]


def get_bearish_signals(results: list[SignalResult]) -> list[SignalResult]:
    """Return bearish futures signals."""
    return [r for r in results if r.direction == "bearish"]


def compute_composite_score(results: list[SignalResult]) -> float:
    """Compute weighted composite score for futures signals (-1.0 to 1.0).

    Weighted average of triggered signal strengths, with decay applied.
    """
    if not results:
        return 0.0

    total_weight = 0.0
    weighted_sum = 0.0

    for r in results:
        entry = FUTURES_REGISTRY.get(r.key, {})
        weight = entry.get("weight", 1.0)
        half_life = entry.get("half_life_days", 30)

        decayed_strength = apply_signal_decay(r, half_life_days=half_life)
        weighted_sum += decayed_strength * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return round(weighted_sum / total_weight, 4)
