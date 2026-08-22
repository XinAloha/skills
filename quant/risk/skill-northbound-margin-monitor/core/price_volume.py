"""Price-volume confirmation factors for the panorama monitor.

Adds a 4th dimension (index momentum + volatility regime) to the
existing 3-dimension analysis (northbound + margin + futures).

These are confirmation factors — they validate or weaken the primary
capital-flow signals based on index price action and volatility regime.

Data source: CSI300 daily data from northbound summary (csi300 column).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from ._types import SignalResult

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Detector 1: Index momentum
# ------------------------------------------------------------------

def detect_index_momentum(data: pd.DataFrame, config: dict) -> SignalResult:
    """Detect CSI300 index momentum signal.

    Computes 20-day return and MA20 deviation to classify trend direction.

    Rules:
        - 20-day return > bullish_threshold + price > MA20 → bullish
        - 20-day return < bearish_threshold + price < MA20 → bearish
        - Otherwise → neutral

    Args:
        data: DataFrame with csi300 column (or CSI300).
        config: Full runtime config dict.

    Returns:
        SignalResult with key="index_momentum".
    """
    pv_cfg = config.get("price_volume", {})
    lookback = pv_cfg.get("momentum_lookback", 20)
    bullish_threshold = pv_cfg.get("momentum_bullish_threshold", 5.0)
    bearish_threshold = pv_cfg.get("momentum_bearish_threshold", -5.0)

    result = SignalResult(
        key="index_momentum",
        label="指数动量",
        triggered=False,
        strength=0.0,
        direction="neutral",
        summary="",
        detail={"data_source": "akshare_eastmoney"},
    )

    # Resolve CSI300 column
    csi_col = None
    for c in ["csi300", "CSI300", "close"]:
        if c in data.columns:
            csi_col = c
            break
    if csi_col is None:
        result.summary = "缺少CSI300数据"
        result.detail = {"data_source": "akshare_eastmoney"}
        return result

    series = pd.to_numeric(data[csi_col], errors="coerce").dropna()
    if len(series) < lookback:
        result.summary = f"数据不足 (需{lookback}日，实际{len(series)}日)"
        result.detail = {"data_source": "akshare_eastmoney"}
        return result

    current = series.iloc[-1]
    prev = series.iloc[-lookback] if len(series) >= lookback else series.iloc[0]
    ma20 = series.iloc[-min(lookback, len(series)):].mean()

    ret_20d = (current / prev - 1.0) * 100
    ma_deviation = (current / ma20 - 1.0) * 100

    result.detail = {
        "data_source": "akshare_eastmoney",
        "csi300_current": round(float(current), 1),
        "ret_20d_pct": round(float(ret_20d), 2),
        "ma20": round(float(ma20), 1),
        "ma_deviation_pct": round(float(ma_deviation), 2),
        "lookback": lookback,
    }

    if ret_20d > bullish_threshold and current > ma20:
        result.triggered = True
        result.direction = "bullish"
        strength_raw = min(1.0, ret_20d / 15.0)  # ~15% return → strength=1.0
        result.strength = round(strength_raw, 4)
        result.summary = f"20日涨幅{ret_20d:.1f}%，价格高于MA20({ma20:.0f})，趋势偏多"
    elif ret_20d < bearish_threshold and current < ma20:
        result.triggered = True
        result.direction = "bearish"
        strength_raw = max(-1.0, ret_20d / 15.0)
        result.strength = round(strength_raw, 4)
        result.summary = f"20日跌幅{abs(ret_20d):.1f}%，价格低于MA20({ma20:.0f})，趋势偏空"
    else:
        direction_word = "上涨" if ret_20d > 0 else "下跌"
        result.summary = f"20日{direction_word}{abs(ret_20d):.1f}%，趋势方向不明确"

    return result


# ------------------------------------------------------------------
# Detector 2: Volatility regime
# ------------------------------------------------------------------

def detect_volatility_regime(data: pd.DataFrame, config: dict) -> SignalResult:
    """Detect volatility regime based on 20-day annualized historical volatility.

    Rules:
        - Volatility > high_threshold → bearish (high-vol = risk-off)
        - Volatility < low_threshold → bullish (low-vol = stable)
        - Otherwise → neutral

    Args:
        data: DataFrame with csi300 column (or CSI300).
        config: Full runtime config dict.

    Returns:
        SignalResult with key="volatility_regime".
    """
    pv_cfg = config.get("price_volume", {})
    lookback = pv_cfg.get("volatility_lookback", 20)
    high_threshold = pv_cfg.get("volatility_high_threshold", 30.0)
    low_threshold = pv_cfg.get("volatility_low_threshold", 15.0)

    result = SignalResult(
        key="volatility_regime",
        label="波动率区间",
        triggered=False,
        strength=0.0,
        direction="neutral",
        summary="",
        detail={"data_source": "akshare_eastmoney"},
    )

    # Resolve CSI300 column
    csi_col = None
    for c in ["csi300", "CSI300", "close"]:
        if c in data.columns:
            csi_col = c
            break
    if csi_col is None:
        result.summary = "缺少CSI300数据"
        result.detail = {"data_source": "akshare_eastmoney"}
        return result

    series = pd.to_numeric(data[csi_col], errors="coerce").dropna()
    if len(series) < lookback + 1:
        result.summary = f"数据不足 (需{lookback + 1}日，实际{len(series)}日)"
        result.detail = {"data_source": "akshare_eastmoney"}
        return result

    # Compute daily log returns
    daily_returns = np.log(series / series.shift(1)).dropna().tail(lookback)
    if len(daily_returns) < 5:
        result.summary = f"有效收益率数据不足 ({len(daily_returns)}日)"
        result.detail = {"data_source": "akshare_eastmoney"}
        return result

    annualized_vol = float(np.std(daily_returns, ddof=1) * np.sqrt(252) * 100)

    result.detail = {
        "data_source": "akshare_eastmoney",
        "annualized_vol_pct": round(annualized_vol, 2),
        "lookback": lookback,
        "n_observations": len(daily_returns),
    }

    if annualized_vol > high_threshold:
        result.triggered = True
        result.direction = "bearish"
        result.strength = round(min(1.0, (annualized_vol - high_threshold) / 20.0), 4)
        result.summary = f"年化波动率{annualized_vol:.1f}%（高波），风险偏好下降"
    elif annualized_vol < low_threshold:
        result.triggered = True
        result.direction = "bullish"
        result.strength = round(min(1.0, (low_threshold - annualized_vol) / 15.0), 4)
        result.summary = f"年化波动率{annualized_vol:.1f}%（低波），市场稳定偏多"
    else:
        result.summary = f"年化波动率{annualized_vol:.1f}%，处于正常区间"

    return result


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------

_DETECTOR_FUNC_MAP = {
    "index_momentum": detect_index_momentum,
    "volatility_regime": detect_volatility_regime,
}

PRICE_VOLUME_REGISTRY = {
    "index_momentum": {
        "func": detect_index_momentum,
        "weight": 2,
        "label": "指数动量",
        "half_life_days": 15,
    },
    "volatility_regime": {
        "func": detect_volatility_regime,
        "weight": 1,
        "label": "波动率区间",
        "half_life_days": 10,
    },
}


# ------------------------------------------------------------------
# Orchestration helpers
# ------------------------------------------------------------------

def run_all_detectors(
    data: pd.DataFrame,
    config: dict,
    active_detectors: set | None = None,
) -> list[SignalResult]:
    """Run all price-volume detectors.

    Args:
        data: CSI300 daily data (from northbound summary).
        config: Full runtime config dict.
        active_detectors: Optional set of detector keys to run. All if None.

    Returns:
        List of SignalResult, one per detector.
    """
    if active_detectors is None:
        active_detectors = set(PRICE_VOLUME_REGISTRY.keys())

    results: list[SignalResult] = []
    for key in PRICE_VOLUME_REGISTRY:
        if key not in active_detectors:
            continue
        entry = PRICE_VOLUME_REGISTRY[key]
        try:
            result = entry["func"](data, config)
        except Exception as e:
            logger.warning("Price-volume detector %s failed: %s", key, e)
            result = SignalResult(
                key=key,
                label=entry["label"],
                triggered=False,
                strength=0.0,
                direction="neutral",
                summary=f"检测器异常: {e}",
                detail={"data_source": "akshare_eastmoney"},
            )
        results.append(result)

    return results


def compute_composite_score(signals: list[SignalResult]) -> float:
    """Compute weighted composite score from price-volume signals.

    Weights from PRICE_VOLUME_REGISTRY.

    Returns:
        Composite score in range [-1, 1].
    """
    if not signals:
        return 0.0

    total_weight = 0.0
    weighted_sum = 0.0
    for s in signals:
        entry = PRICE_VOLUME_REGISTRY.get(s.key, {})
        w = entry.get("weight", 1)
        weighted_sum += s.strength * w
        total_weight += w

    if total_weight == 0:
        return 0.0

    return round(weighted_sum / total_weight, 4)


def get_triggered_signals(signals: list[SignalResult]) -> list[SignalResult]:
    """Return triggered signals."""
    return [s for s in signals if s.triggered]


def get_bullish_signals(signals: list[SignalResult]) -> list[SignalResult]:
    """Return bullish signals."""
    return [s for s in signals if s.direction == "bullish"]


def get_bearish_signals(signals: list[SignalResult]) -> list[SignalResult]:
    """Return bearish signals."""
    return [s for s in signals if s.direction == "bearish"]
