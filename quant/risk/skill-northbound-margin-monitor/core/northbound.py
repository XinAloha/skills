"""North-bound capital flow signal detectors (7 signals, registry pattern).

Each detector analyses north-bound (沪深港通) data and returns a SignalResult
with direction ("bullish"/"bearish"/"neutral"), strength (-1.0 to 1.0), and
a human-readable summary.

Data sources:
  - nb_summary: AKShare ``stock_hsgt_hist_em`` — daily northbound summary history
  - nb_flow:    AKShare ``stock_hsgt_fund_flow_summary_em`` — SH/SZ flow direction
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from ._types import SignalResult, neutral_signal, apply_signal_decay

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Data source labels
# ------------------------------------------------------------------

_SOURCE_MAP = {
    "direct": "direct_nb",
    "market_value": "market_value_diff",
    "csi300": "csi300_proxy",
}


# ------------------------------------------------------------------
# Shared helper: resolve net flow column with fallback chain
# ------------------------------------------------------------------

def _resolve_net_column(
    nb_summary: pd.DataFrame,
    recent_check_days: int = 10,
) -> tuple[Optional[str], pd.DataFrame, Optional[str]]:
    """Resolve a usable net flow column from *nb_summary*.

    Fallback chain (each step validates recent data quality before accepting):

      1. Direct net columns (net_buy_amount, net_buy, etc.)
         — accepted only if ≥3 of the last *recent_check_days* rows are non-NaN.
      2. Market value diff
         — accepted only if ≥3 of the last *recent_check_days* mv values are > 0.
      3. CSI300 index diff (last resort proxy)
         — accepted only if ≥3 of the last *recent_check_days* csi300 values are > 0.

    Without these quality checks, a column that exists but has all-NaN recent
    data produces bogus signals (all-zero net flow → fake "accelerating outflow").

    Returns:
        (column_name, df, source_type) — column_name may be ``None`` if
        unresolvable; *df* may be a modified copy of *nb_summary* (sorted +
        extra column); *source_type* is one of ``"direct"``, ``"market_value"``,
        ``"csi300"``, or ``None``.
    """
    MIN_RECENT_VALID = 3  # at least this many recent data points needed

    # 1. Direct net flow columns — check recent data quality
    for candidate in ["net_buy_amount", "net_buy", "net_flow", "资金净流入", "净买入"]:
        if candidate in nb_summary.columns:
            recent = pd.to_numeric(
                nb_summary[candidate].tail(recent_check_days), errors="coerce"
            )
            if recent.notna().sum() >= MIN_RECENT_VALID:
                return candidate, nb_summary, "direct"
            logger.debug(
                "Column '%s' exists but only %d/%d recent values are non-NaN — skipping",
                candidate, recent.notna().sum(), len(recent),
            )

    # 2. Market value diff
    mv_col = None
    for candidate in ["market_value", "持股市值"]:
        if candidate in nb_summary.columns:
            mv_col = candidate
            break
    if mv_col is not None:
        df = nb_summary.sort_values("date", ascending=True).copy()
        df["_net"] = df[mv_col].diff()
        recent_mv = pd.to_numeric(df[mv_col].tail(recent_check_days), errors="coerce")
        if (recent_mv > 0).sum() >= MIN_RECENT_VALID:
            return "_net", df, "market_value"
        logger.debug(
            "market_value diff: only %d/%d recent values > 0 — skipping",
            (recent_mv > 0).sum(), len(recent_mv),
        )

    # 3. CSI300 diff (last resort proxy)
    csi_col = None
    for candidate in ["csi300", "CSI300", "沪深300"]:
        if candidate in nb_summary.columns:
            csi_col = candidate
            break
    if csi_col is not None:
        df = nb_summary.sort_values("date", ascending=True).copy()
        df["_net"] = df[csi_col].diff()
        recent_csi = pd.to_numeric(df[csi_col].tail(recent_check_days), errors="coerce")
        if (recent_csi > 0).sum() >= MIN_RECENT_VALID:
            return "_net", df, "csi300"
        logger.debug(
            "CSI300 diff: only %d/%d recent values > 0 — skipping",
            (recent_csi > 0).sum(), len(recent_csi),
        )

    return None, nb_summary, None


# ------------------------------------------------------------------
# Detector 1: Flow Trend (净流向趋势)
# ------------------------------------------------------------------

def detect_flow_trend(
    nb_summary: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Detect consecutive-day net capital flow trend.

    Analyses whether north-bound capital shows persistent net inflow or
    outflow over consecutive trading days.

    Strength: normalized by consecutive_days_threshold, capped at ±1.0.
    """
    key = "flow_trend"
    label = "净流向趋势"
    threshold = config.get("northbound", {}).get("consecutive_days_threshold", 3)

    if nb_summary.empty:
        return neutral_signal(key, label, "无北向资金数据", detail={"data_source": "none"})

    net_col, nb_summary, source_type = _resolve_net_column(nb_summary)
    if net_col is None:
        return neutral_signal(key, label, "无法计算净流向", detail={"data_source": "none"})

    # Sort by date and check consecutive direction
    df = nb_summary.sort_values("date", ascending=True).copy()
    net_vals = pd.to_numeric(df[net_col], errors="coerce")

    # Count consecutive days at the end with same direction
    recent = net_vals.dropna()
    ds_label = _SOURCE_MAP.get(source_type, "unknown")
    if len(recent) < 2:
        return neutral_signal(key, label, "数据不足", detail={"data_source": ds_label})

    last_direction = 1 if recent.iloc[-1] > 0 else (-1 if recent.iloc[-1] < 0 else 0)
    if last_direction == 0:
        return neutral_signal(key, label, "当日净流向为零", detail={"data_source": ds_label})

    consecutive = 1
    for i in range(len(recent) - 2, -1, -1):
        val = recent.iloc[i]
        direction = 1 if val > 0 else (-1 if val < 0 else 0)
        if direction == last_direction:
            consecutive += 1
        else:
            break

    triggered = consecutive >= threshold
    strength = min(consecutive / max(threshold, 1), 1.0) * last_direction
    direction = "bullish" if last_direction > 0 else "bearish"
    desc = "净流入" if last_direction > 0 else "净流出"

    detail = {
        "data_source": ds_label,
        "consecutive_days": consecutive,
        "threshold": threshold,
        "direction_desc": desc,
        "recent_values": recent.tail(consecutive).tolist(),
    }

    if triggered:
        summary = f"连续{consecutive}日{desc}（阈值{threshold}日），趋势{'强化' if consecutive > threshold else '确立'}"
    else:
        summary = f"{desc}{consecutive}日，未达阈值{threshold}日"

    return SignalResult(
        key=key, label=label, triggered=triggered,
        strength=round(strength, 4), direction=direction,
        summary=summary, detail=detail,
    )


# ------------------------------------------------------------------
# Detector 2: Single-Day Anomaly (单日异常)
# ------------------------------------------------------------------

def detect_single_day_anomaly(
    nb_summary: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Detect abnormal single-day net capital flow via Z-score.

    Computes Z-score of today's net flow vs trailing 60-day distribution.
    |Z| > threshold → signal triggered.
    """
    key = "single_day_anomaly"
    label = "单日异常"
    z_threshold = config.get("northbound", {}).get("anomaly_zscore_threshold", 2.0)

    if nb_summary.empty:
        return neutral_signal(key, label, "无北向资金数据", detail={"data_source": "none"})

    net_col, nb_summary, source_type = _resolve_net_column(nb_summary)
    if net_col is None:
        return neutral_signal(key, label, "无法计算净流向", detail={"data_source": "none"})

    df = nb_summary.sort_values("date", ascending=True)
    net_vals = pd.to_numeric(df[net_col], errors="coerce").dropna()

    ds_label = _SOURCE_MAP.get(source_type, "unknown")
    if len(net_vals) < 21:
        return neutral_signal(key, label, f"数据不足（仅{len(net_vals)}日）", detail={"data_source": ds_label})

    today = net_vals.iloc[-1]
    history = net_vals.iloc[-61:-1]  # up to 60 days before today
    if len(history) < 20:
        history = net_vals.iloc[:-1]

    mu = history.mean()
    sigma = history.std()
    if sigma == 0 or pd.isna(sigma):
        return neutral_signal(key, label, "波动率为零，无法计算Z-score", detail={"data_source": ds_label})

    z_score = (today - mu) / sigma
    triggered = abs(z_score) >= z_threshold
    direction = "bullish" if z_score > 0 else "bearish"
    strength = np.clip(z_score / (z_threshold * 2), -1.0, 1.0)

    desc = "大幅净流入" if z_score > 0 else "大幅净流出"
    detail = {
        "data_source": ds_label,
        "today_net": float(today),
        "mean_60d": float(mu),
        "std_60d": float(sigma),
        "z_score": round(float(z_score), 2),
        "z_threshold": z_threshold,
    }

    if triggered:
        summary = f"单日{desc}（Z={z_score:.1f}，|Z|≥{z_threshold}），{'远超' if abs(z_score) >= z_threshold * 1.5 else '超过'}历史均值"
    else:
        summary = f"单日净流向正常（Z={z_score:.1f}，|Z|<{z_threshold}）"

    return SignalResult(
        key=key, label=label, triggered=triggered,
        strength=round(strength, 4), direction=direction,
        summary=summary, detail=detail,
    )


# ------------------------------------------------------------------
# Detector 3: Sector Preference (板块偏好)
# ------------------------------------------------------------------

def detect_sector_preference(
    nb_summary: pd.DataFrame,
    stock_info: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Analyse north-bound sector/industry preference.

    Computes sector distribution from stock_info and estimates flow
    preference based on market value changes aggregated by industry.
    """
    key = "sector_preference"
    label = "板块偏好"

    if nb_summary.empty:
        return neutral_signal(key, label, "无北向资金数据", detail={"data_source": "none"})

    if stock_info.empty or "industry" not in stock_info.columns:
        return neutral_signal(key, label, "无行业分类数据，无法计算板块偏好", detail={"data_source": "none"})

    # Check for overall direction — try market_value first, then net_buy, then proxy
    df = nb_summary.sort_values("date", ascending=True)
    mv_col = None
    for candidate in ["market_value", "持股市值"]:
        if candidate in df.columns:
            mv_col = candidate
            break

    proxy_note = ""
    sector_source = "none"
    if mv_col is not None:
        recent_mv = pd.to_numeric(df[mv_col].tail(10), errors="coerce")
        mv_usable = (recent_mv > 0).sum() >= 3
        if mv_usable:
            recent = recent_mv.dropna()
            sector_source = "market_value_diff"
            if len(recent) >= 6:
                recent_change = recent.iloc[-1] - recent.iloc[-6]
            else:
                recent_change = 0
        else:
            # market_value is all 0 — fall back to net column resolution
            mv_col = None

    if mv_col is None:
        net_col, df_resolved, net_source = _resolve_net_column(df)
        if net_col is None:
            return neutral_signal(key, label, "无法计算板块偏好", detail={"data_source": "none"})
        sector_source = _SOURCE_MAP.get(net_source, "unknown")
        if net_source == "csi300":
            proxy_note = "（注：北向净买入数据不可用，方向基于沪深300替代指标）"
        recent_change = pd.to_numeric(df_resolved[net_col].tail(5), errors="coerce").sum()

    # Count industries (proxy for sector concentration)
    industry_counts = stock_info["industry"].value_counts()
    top_industries = industry_counts.head(5).index.tolist()

    direction = "bullish" if recent_change > 0 else "bearish"
    change_abs = abs(recent_change)

    # Normalise change magnitude for threshold comparison
    if mv_col is not None and recent_mv is not None:
        recent_mv_vals = pd.to_numeric(recent_mv, errors="coerce").dropna()
        if len(recent_mv_vals) > 0 and recent_mv_vals.iloc[-1] > 0:
            change_pct = change_abs / recent_mv_vals.iloc[-1]
        else:
            change_pct = 0.0
    else:
        # No market_value — estimate from net flow data itself.
        # The net_col/dataset_resolved variables are set in the mv_col-is-None
        # branch above; use the full net_buy series as denominator.
        flow_col = net_col if net_col is not None else "net_buy_amount"
        df_flow = df_resolved if df_resolved is not None else df
        flow_vals = pd.to_numeric(df_flow[flow_col], errors="coerce").dropna()
        avg_daily = flow_vals.abs().mean() if len(flow_vals) > 0 else 0
        change_pct = change_abs / max(1.0, avg_daily) if avg_daily > 0 else 0.0

    detail = {
        "data_source": sector_source,
        "overall_direction": "净流入" if recent_change > 0 else "净流出",
        "change_abs": round(float(change_abs), 2),
        "change_pct": round(float(change_pct * 100), 2),
        "top_industries_by_count": top_industries,
        "note": "板块偏好基于行业分布+汇总流向推算，非直接持仓数据",
    }
    if proxy_note:
        detail["proxy_note"] = proxy_note

    # Only trigger on meaningful change (>0.5% relative or CSI300 proxy with caution)
    min_threshold = 0.003 if proxy_note else 0.005  # 0.3% proxy / 0.5% direct
    triggered = change_pct > min_threshold
    strength = 0.5 if triggered else 0.0
    if proxy_note and triggered:
        strength = 0.3  # reduced confidence when using CSI300 proxy
    if direction == "bearish":
        strength = -strength

    summary = (
        f"北向资金整体{'流入' if recent_change > 0 else '流出'}，"
        f"重点关注行业：{'、'.join(top_industries[:3])}"
        + (f" {proxy_note}" if proxy_note else "")
    )

    return SignalResult(
        key=key, label=label, triggered=triggered,
        strength=round(strength, 4), direction=direction,
        summary=summary, detail=detail,
    )


# ------------------------------------------------------------------
# Detector 4: Heavy Holdings Change (重仓股变动)
# ------------------------------------------------------------------

def detect_holdings_change(
    nb_summary: pd.DataFrame,
    stock_info: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Analyse top holdings market value and recent changes.

    Identifies the largest north-bound holdings and their trend direction.
    Since per-stock holdings data is limited, this works from market-value
    changes in the summary data.
    """
    key = "holdings_change"
    label = "重仓股变动"
    top_n = config.get("northbound", {}).get("top_n_holdings", 20)

    if nb_summary.empty:
        return neutral_signal(key, label, "无北向资金数据", detail={"data_source": "none"})

    df = nb_summary.sort_values("date", ascending=True)

    mv_col = None
    for candidate in ["market_value", "持股市值"]:
        if candidate in df.columns:
            mv_col = candidate
            break

    if mv_col is None:
        return neutral_signal(key, label, "无持仓市值数据", detail={"data_source": "none"})

    recent = pd.to_numeric(df[mv_col], errors="coerce").dropna()
    if len(recent) < 6:
        return neutral_signal(key, label, "市值数据不足", detail={"data_source": "market_value_diff"})

    current_mv = recent.iloc[-1]
    short_change = recent.iloc[-1] - recent.iloc[-6]
    if len(recent) >= 21:
        med_change = recent.iloc[-1] - recent.iloc[-21]
    else:
        med_change = short_change

    change_pct_5d = short_change / recent.iloc[-6] * 100 if recent.iloc[-6] != 0 else 0

    direction = "bullish" if short_change > 0 else "bearish"
    threshold = config.get("northbound", {}).get("holdings_change_threshold", 0.5)
    triggered = abs(change_pct_5d) > threshold

    detail = {
        "data_source": "market_value_diff",
        "current_market_value_亿元": round(float(current_mv) / 1e8, 2) if current_mv > 1e6 else round(float(current_mv), 2),
        "change_5d": round(float(short_change), 2),
        "change_20d": round(float(med_change), 2) if len(recent) >= 21 else None,
        "change_pct_5d": round(float(change_pct_5d), 2),
        "threshold": threshold,
        "top_n": top_n,
        "note": "基于汇总市值变化，非个股持仓明细",
    }

    if triggered:
        if direction == "bullish":
            summary = f"北向持仓市值{current_mv/1e8:.0f}亿，5日增加{change_pct_5d:.1f}%，外资持续加仓"
        else:
            summary = f"北向持仓市值{current_mv/1e8:.0f}亿，5日减少{abs(change_pct_5d):.1f}%，外资减仓"
        strength = np.clip(change_pct_5d / 2.0, -1.0, 1.0)
    else:
        summary = f"北向持仓市值{current_mv/1e8:.0f}亿，5日变动{change_pct_5d:+.1f}%，变化不大"
        strength = 0.0

    return SignalResult(
        key=key, label=label, triggered=triggered,
        strength=round(strength, 4), direction=direction,
        summary=summary, detail=detail,
    )


# ------------------------------------------------------------------
# Detector 5: Cumulative Trend (累计趋势)
# ------------------------------------------------------------------

def detect_cumulative_trend(
    nb_summary: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Analyse cumulative net buy trend: 20MA vs 60MA crossover.

    Accelerating when 20MA > 60MA and rising; decelerating when
    20MA < 60MA and falling. This is the northbound equivalent of
    a MACD signal on cumulative flows.
    """
    key = "cumulative_trend"
    label = "累计趋势"
    ma_short = config.get("northbound", {}).get("ma_short_window", 20)
    ma_long = config.get("northbound", {}).get("ma_long_window", 60)

    if nb_summary.empty:
        return neutral_signal(key, label, "无北向资金数据", detail={"data_source": "none"})

    net_col, nb_summary, net_source = _resolve_net_column(nb_summary)
    if net_col is None:
        return neutral_signal(key, label, "无法计算累计趋势", detail={"data_source": "none"})

    df = nb_summary.sort_values("date", ascending=True)
    net_vals = pd.to_numeric(df[net_col], errors="coerce").fillna(0.0)
    cum_net = net_vals.cumsum()

    if len(cum_net) < ma_long:
        return neutral_signal(key, label, f"数据不足（需≥{ma_long}日，当前{len(cum_net)}日）",
                              detail={"data_source": _SOURCE_MAP.get(net_source, "unknown")})

    ma20 = cum_net.rolling(ma_short).mean()
    ma60 = cum_net.rolling(ma_long).mean()

    current_ma20 = ma20.iloc[-1]
    current_ma60 = ma60.iloc[-1]
    prev_ma20 = ma20.iloc[-2] if len(ma20) >= 2 else current_ma20
    prev_ma60 = ma60.iloc[-2] if len(ma60) >= 2 else current_ma60

    gap = current_ma20 - current_ma60
    gap_prev = prev_ma20 - prev_ma60

    # Determine regime
    above = current_ma20 > current_ma60
    accelerating = gap > gap_prev  # gap widening = accelerating

    if above and accelerating:
        triggered = True
        direction = "bullish"
        regime = "加速流入"
        strength = np.clip(abs(gap) / (abs(current_ma60) + 1) * 10, 0.1, 1.0)
    elif above and not accelerating:
        triggered = True
        direction = "bullish"
        regime = "流入减速"
        strength = 0.3
    elif not above and not accelerating:
        triggered = True
        direction = "bearish"
        regime = "加速流出"
        strength = np.clip(abs(gap) / (abs(current_ma60) + 1) * 10, 0.1, 1.0)
        strength = -strength
    else:  # below but recovering
        triggered = False
        direction = "bearish"
        regime = "流出减缓"
        strength = -0.2

    detail = {
        "ma20": round(float(current_ma20), 2),
        "ma60": round(float(current_ma60), 2),
        "gap": round(float(gap), 2),
        "regime": regime,
        "ma_short_window": ma_short,
        "ma_long_window": ma_long,
        "data_source": _SOURCE_MAP.get(net_source, "unknown"),
    }

    # Format summary based on data source
    if net_source == "csi300":
        summary = (
            f"沪深300累计变动MA{ma_short}({current_ma20:.0f}点)"
            f"{'＞' if above else '＜'}MA{ma_long}({current_ma60:.0f}点)，{regime}"
            f"（北向净买入数据不可用，使用沪深300替代）"
        )
    else:
        summary = (
            f"累计净买入MA{ma_short}({current_ma20/1e8:.1f}亿)"
            f"{'＞' if above else '＜'}MA{ma_long}({current_ma60/1e8:.1f}亿)，{regime}"
        )

    return SignalResult(
        key=key, label=label, triggered=triggered,
        strength=round(strength, 4), direction=direction,
        summary=summary, detail=detail,
    )


# ------------------------------------------------------------------
# Detector 6: Market Flow Direction (市场流向)
# ------------------------------------------------------------------

def detect_market_flow_direction(
    nb_flow: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Check whether SH and SZ north-bound flows align or diverge.

    AKShare ``stock_hsgt_fund_flow_summary_em`` columns (2026):
      [0] 交易日, [1] 类型(沪港通/深港通), [2] 板块(沪股通/深股通/港股通),
      [3] 资金方向(北向/南向), [4] 交易状态,
      [5] 成交净买额, [6] 资金净流入, [7] 当日资金余额,
      [8] 上涨数, [9] 持平数, [10] 下跌数,
      [11] 相关指数, [12] 指数涨跌幅

    We filter to 北向 rows (沪股通/深股通) and check index performance.
    """
    key = "market_flow_direction"
    label = "市场流向"

    if nb_flow.empty:
        return neutral_signal(key, label, "无市场流向数据", detail={"data_source": "none"})

    # Detect columns by name (with fallback to positional)
    sector_col = None
    direction_col = None
    index_col = None
    index_chg_col = None

    for i, col in enumerate(nb_flow.columns):
        col_str = str(col)
        if "板块" in col_str:
            sector_col = col
        elif "方向" in col_str:
            direction_col = col
        elif "指数" in col_str and "涨跌" not in col_str:
            index_col = col
        elif "涨跌幅" in col_str:
            index_chg_col = col

    # Fallback to positional if column name detection fails
    if sector_col is None and len(nb_flow.columns) > 2:
        sector_col = nb_flow.columns[2]
    if direction_col is None and len(nb_flow.columns) > 3:
        direction_col = nb_flow.columns[3]
    if index_col is None and len(nb_flow.columns) > 11:
        index_col = nb_flow.columns[11]
    if index_chg_col is None and len(nb_flow.columns) > 12:
        index_chg_col = nb_flow.columns[12]

    # Filter to northbound rows only (沪股通/深股通, not 港股通)
    north_rows = nb_flow.copy()
    if sector_col is not None:
        north_rows = north_rows[
            north_rows[sector_col].astype(str).str.contains("股通")
            & ~north_rows[sector_col].astype(str).str.contains("港股通")
        ]

    if north_rows.empty:
        north_rows = nb_flow  # fallback: use all rows

    # Determine SH/SZ direction from available data
    sh_row = north_rows[north_rows[sector_col].astype(str).str.contains("沪")] if sector_col else pd.DataFrame()
    sz_row = north_rows[north_rows[sector_col].astype(str).str.contains("深")] if sector_col else pd.DataFrame()

    sh_perf = None
    sz_perf = None

    if index_chg_col is not None:
        if not sh_row.empty:
            sh_chg = pd.to_numeric(sh_row[index_chg_col], errors="coerce")
            sh_perf = sh_chg.iloc[0] if len(sh_chg) > 0 else None
        if not sz_row.empty:
            sz_chg = pd.to_numeric(sz_row[index_chg_col], errors="coerce")
            sz_perf = sz_chg.iloc[0] if len(sz_chg) > 0 else None

    # Determine direction from flow or index performance
    sh_dir = 0
    sz_dir = 0

    if direction_col is not None:
        if not sh_row.empty:
            sh_val = str(sh_row[direction_col].iloc[0]) if len(sh_row) > 0 else ""
            sh_dir = 1 if "北" in sh_val or "入" in sh_val else (-1 if "南" in sh_val or "出" in sh_val else 0)
        if not sz_row.empty:
            sz_val = str(sz_row[direction_col].iloc[0]) if len(sz_row) > 0 else ""
            sz_dir = 1 if "北" in sz_val or "入" in sz_val else (-1 if "南" in sz_val or "出" in sz_val else 0)

    # If direction not determined, use index performance as proxy
    if sh_dir == 0 and sh_perf is not None and not pd.isna(sh_perf):
        sh_dir = 1 if sh_perf > 0 else (-1 if sh_perf < 0 else 0)
    if sz_dir == 0 and sz_perf is not None and not pd.isna(sz_perf):
        sz_dir = 1 if sz_perf > 0 else (-1 if sz_perf < 0 else 0)

    aligned = sh_dir == sz_dir and sh_dir != 0
    both_in = sh_dir == 1 and sz_dir == 1
    both_out = sh_dir == -1 and sz_dir == -1

    detail = {
        "data_source": "akshare_eastmoney",
        "sh_direction": "流入" if sh_dir == 1 else ("流出" if sh_dir == -1 else "持平"),
        "sz_direction": "流入" if sz_dir == 1 else ("流出" if sz_dir == -1 else "持平"),
        "aligned": aligned,
    }

    if both_in:
        triggered = True
        direction = "bullish"
        strength = 0.8
        summary = "沪股通+深股通双双净流入，市场一致看多"
    elif both_out:
        triggered = True
        direction = "bearish"
        strength = -0.8
        summary = "沪股通+深股通双双净流出，市场一致看空"
    elif aligned:
        triggered = True
        direction = "bullish" if sh_dir == 1 else "bearish"
        strength = 0.4 if sh_dir == 1 else -0.4
        summary = f"沪深股通同向{'流入' if sh_dir == 1 else '流出'}，方向一致"
    else:
        triggered = False
        direction = "neutral"
        strength = 0.0
        summary = f"沪股通{'流入' if sh_dir == 1 else '流出'}，深股通{'流入' if sz_dir == 1 else '流出'}，市场分歧"

    return SignalResult(
        key=key, label=label, triggered=triggered,
        strength=round(strength, 4), direction=direction,
        summary=summary, detail=detail,
    )


# ------------------------------------------------------------------
# Detector 7: Flow Direction Trend (流向趋势 — 基于累积方向历史)
# ------------------------------------------------------------------


def detect_flow_direction_trend(
    nb_flow_history: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Detect consecutive-day flow direction trend from accumulated nb_flow history.

    Uses the daily direction signal (+1 inflow, -1 outflow) aggregated
    across SH+SZ markets. This provides an independent directional signal
    based on actual northbound flow direction data, replacing the broken
    ``net_buy_amount`` column.

    Args:
        nb_flow_history: Accumulated history from ``FlowAccumulator.get_direction_series()``.
            Expected columns: date, direction_sum, direction_days,
            adv_sum, dec_sum, flat_sum, index_chg_avg.
        config: Full runtime config dict.

    Returns:
        SignalResult with key="flow_direction_trend".
    """
    key = "flow_direction_trend"
    label = "流向趋势"
    threshold = config.get("northbound", {}).get("consecutive_days_threshold", 3)

    if nb_flow_history is None or nb_flow_history.empty:
        return neutral_signal(key, label, "无流向历史数据（需累积≥2日）", detail={"data_source": "none"})

    if "direction_sum" not in nb_flow_history.columns:
        return neutral_signal(key, label, "流向数据格式异常", detail={"data_source": "none"})

    df = nb_flow_history.sort_values("date", ascending=True)
    directions = df["direction_sum"].dropna()

    if len(directions) < 2:
        return neutral_signal(key, label, "流向历史不足（需累积≥2日）", detail={"data_source": "nb_flow_accumulated"})

    # Determine last day's net direction
    last_val = directions.iloc[-1]
    if last_val > 0:
        last_dir = 1
    elif last_val < 0:
        last_dir = -1
    else:
        return neutral_signal(key, label, "当日沪深两市流向均衡（净方向=0）", detail={"data_source": "nb_flow_accumulated"})

    # Count consecutive days with same direction
    consecutive = 1
    for i in range(len(directions) - 2, -1, -1):
        val = directions.iloc[i]
        if (val > 0 and last_dir > 0) or (val < 0 and last_dir < 0):
            consecutive += 1
        else:
            break

    triggered = consecutive >= threshold
    base_strength = min(consecutive / max(threshold, 1), 1.0)

    # Consensus strength: how many markets agreed on average
    consensus_factor = 1.0
    consensus_label = "strong"
    if "direction_days" in df.columns:
        recent_consensus = df["direction_days"].tail(consecutive)
        avg_consensus = recent_consensus.mean() if len(recent_consensus) > 0 else 0
        if avg_consensus >= 2.0:
            consensus_factor = 1.0
            consensus_label = "strong"
        elif avg_consensus >= 1.0:
            consensus_factor = 0.7
            consensus_label = "moderate"
        else:
            consensus_factor = 0.5
            consensus_label = "weak"

    strength = base_strength * consensus_factor * last_dir
    direction = "bullish" if last_dir > 0 else "bearish"

    desc = "净流入" if last_dir > 0 else "净流出"

    detail = {
        "consecutive_days": consecutive,
        "threshold": threshold,
        "direction_desc": desc,
        "consensus": consensus_label,
        "direction_sum_last": float(last_val),
        "data_source": "nb_flow_accumulated",
    }

    if triggered:
        summary = (
            f"北向连续{consecutive}日{desc}"
            f"（两市共识={consensus_label}，阈值{threshold}日）"
        )
    else:
        summary = (
            f"北向{desc}{consecutive}日，未达阈值{threshold}日"
            f"（共识={consensus_label}）"
        )

    return SignalResult(
        key=key, label=label, triggered=triggered,
        strength=round(strength, 4), direction=direction,
        summary=summary, detail=detail,
    )


# ------------------------------------------------------------------
# Merged flow trend detector (replaces flow_trend + flow_direction_trend)
# ------------------------------------------------------------------

def _detect_flow_trend_merged(
    nb_summary: pd.DataFrame,
    config: dict,
    nb_flow_history: Optional[pd.DataFrame] = None,
    *,
    _key: str = "flow_trend",
    _label: str = "净流向趋势",
) -> SignalResult:
    """Detect consecutive-day flow direction trend with smart data priority.

    Priority chain:
      1. **nb_flow_history** (FlowAccumulator, ≥10 dates) → ``direction_sum``
         with consensus_factor weighting.
      2. **nb_summary** via ``_resolve_net_column()`` fallback
         (net_buy_amount → market_value diff → CSI300 proxy).
      3. Neutral if nothing works.

    Both ``"flow_trend"`` and ``"flow_direction_trend"`` registry keys
    route through this function; the difference is whether
    *nb_flow_history* is supplied by the pipeline.
    """
    key = _key
    label = _label
    threshold = config.get("northbound", {}).get("consecutive_days_threshold", 3)

    # ── Priority 1: FlowAccumulator direction_sum ──
    if nb_flow_history is not None and not nb_flow_history.empty:
        df_fh = nb_flow_history.sort_values("date", ascending=True)
        if "direction_sum" in df_fh.columns and len(df_fh) >= 10:
            directions = df_fh["direction_sum"].dropna()
            if len(directions) >= 2:
                last_val = directions.iloc[-1]
                if last_val > 0:
                    last_dir = 1
                elif last_val < 0:
                    last_dir = -1
                else:
                    return neutral_signal(
                        key, label, "当日沪深两市流向均衡（净方向=0）",
                        detail={"data_source": "nb_flow_accumulated"},
                    )

                # Count consecutive same-direction days
                consecutive = 1
                for i in range(len(directions) - 2, -1, -1):
                    v = directions.iloc[i]
                    if (v > 0 and last_dir > 0) or (v < 0 and last_dir < 0):
                        consecutive += 1
                    else:
                        break

                triggered = consecutive >= threshold
                base_strength = min(consecutive / max(threshold, 1), 1.0)

                # Consensus factor from flow accumulator
                consensus_factor = 1.0
                consensus_label = "strong"
                if "direction_days" in df_fh.columns:
                    recent_consensus = df_fh["direction_days"].tail(consecutive)
                    avg_consensus = recent_consensus.mean() if len(recent_consensus) > 0 else 0
                    if avg_consensus >= 2.0:
                        consensus_factor = 1.0
                        consensus_label = "strong"
                    elif avg_consensus >= 1.0:
                        consensus_factor = 0.7
                        consensus_label = "moderate"
                    else:
                        consensus_factor = 0.5
                        consensus_label = "weak"

                strength = base_strength * consensus_factor * last_dir
                direction = "bullish" if last_dir > 0 else "bearish"
                desc = "净流入" if last_dir > 0 else "净流出"

                detail = {
                    "data_source": "nb_flow_accumulated",
                    "consecutive_days": consecutive,
                    "threshold": threshold,
                    "direction_desc": desc,
                    "consensus": consensus_label,
                    "direction_sum_last": float(last_val),
                    "priority": "flow_history",
                }

                if triggered:
                    summary = (
                        f"北向连续{consecutive}日{desc}"
                        f"（两市共识={consensus_label}，阈值{threshold}日）"
                    )
                else:
                    summary = (
                        f"北向{desc}{consecutive}日，未达阈值{threshold}日"
                        f"（共识={consensus_label}）"
                    )

                return SignalResult(
                    key=key, label=label, triggered=triggered,
                    strength=round(strength, 4), direction=direction,
                    summary=summary, detail=detail,
                )

    # ── Priority 2: _resolve_net_column fallback chain ──
    if nb_summary is not None and not nb_summary.empty:
        net_col, df_resolved, source_type = _resolve_net_column(nb_summary)
        if net_col is not None:
            df = df_resolved.sort_values("date", ascending=True)
            net_vals = pd.to_numeric(df[net_col], errors="coerce")
            recent = net_vals.dropna()
            ds_label = _SOURCE_MAP.get(source_type, "unknown")
            if len(recent) < 2:
                return neutral_signal(key, label, "数据不足", detail={"data_source": ds_label})

            last_dir = 1 if recent.iloc[-1] > 0 else (-1 if recent.iloc[-1] < 0 else 0)
            if last_dir == 0:
                return neutral_signal(key, label, "当日净流向为零", detail={"data_source": ds_label})

            consecutive = 1
            for i in range(len(recent) - 2, -1, -1):
                d = 1 if recent.iloc[i] > 0 else (-1 if recent.iloc[i] < 0 else 0)
                if d == last_dir:
                    consecutive += 1
                else:
                    break

            triggered = consecutive >= threshold
            strength = min(consecutive / max(threshold, 1), 1.0) * last_dir
            direction = "bullish" if last_dir > 0 else "bearish"
            desc = "净流入" if last_dir > 0 else "净流出"

            detail = {
                "data_source": ds_label,
                "consecutive_days": consecutive,
                "threshold": threshold,
                "direction_desc": desc,
                "recent_values": recent.tail(consecutive).tolist(),
                "priority": "net_column",
            }

            if triggered:
                summary = f"连续{consecutive}日{desc}（阈值{threshold}日），趋势{'强化' if consecutive > threshold else '确立'}"
            else:
                summary = f"{desc}{consecutive}日，未达阈值{threshold}日"

            return SignalResult(
                key=key, label=label, triggered=triggered,
                strength=round(strength, 4), direction=direction,
                summary=summary, detail=detail,
            )
        else:
            return neutral_signal(key, label, "无法计算净流向", detail={"data_source": "none"})

    # ── Priority 3: No data ──
    return neutral_signal(key, label, "无北向资金数据", detail={"data_source": "none"})


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------

NORTHBOUND_REGISTRY = {
    "flow_trend": {
        "func": _detect_flow_trend_merged,
        "weight": 3,
        "label": "净流向趋势",
        "description": "连续N日净流入/流出方向检测（智能优先级：流向历史>净买入>市值差>CSI300代理）",
        "half_life_days": 20,
    },
    "single_day_anomaly": {
        "func": detect_single_day_anomaly,
        "weight": 2,
        "label": "单日异常",
        "description": "单日净买入Z-score vs 60天分布",
        "half_life_days": 5,
    },
    "sector_preference": {
        "func": detect_sector_preference,
        "weight": 2,
        "label": "板块偏好",
        "description": "行业持仓市值/变动聚合分析",
        "half_life_days": 15,
    },
    "holdings_change": {
        "func": detect_holdings_change,
        "weight": 1,
        "label": "重仓股变动",
        "description": "持仓市值5/20日变动趋势",
        "half_life_days": 10,
    },
    "cumulative_trend": {
        "func": detect_cumulative_trend,
        "weight": 3,
        "label": "累计趋势",
        "description": "累计净买入20MA vs 60MA加速/减速",
        "half_life_days": 30,
    },
    "market_flow_direction": {
        "func": detect_market_flow_direction,
        "weight": 2,
        "label": "市场流向",
        "description": "沪股通+深股通方向一致/分歧",
        "half_life_days": 5,
    },
    "flow_direction_trend": {
        "func": _detect_flow_trend_merged,
        "weight": 3,
        "label": "流向趋势",
        "description": "基于北向方向累积历史的连续趋势（与flow_trend合并，优先使用累积数据）",
        "half_life_days": 20,
    },
}


def run_all_detectors(
    nb_summary: pd.DataFrame,
    nb_flow: pd.DataFrame,
    stock_info: pd.DataFrame,
    config: dict,
    active_detectors: Optional[set[str]] = None,
    nb_flow_history: Optional[pd.DataFrame] = None,
) -> list[SignalResult]:
    """Run all active northbound detectors.

    Args:
        nb_summary: Daily northbound summary (from ``stock_hsgt_hist_em``).
        nb_flow: Market flow direction (from ``stock_hsgt_fund_flow_summary_em``).
        stock_info: Stock detail info with industry column.
        config: Full runtime config dict.
        active_detectors: Set of detector keys to run. None = run all.
        nb_flow_history: Accumulated flow direction history (optional).
            Pass to enable the ``flow_direction_trend`` detector.

    Returns:
        List of SignalResult, one per active detector.
    """
    if active_detectors is None:
        active_detectors = set(NORTHBOUND_REGISTRY.keys())

    results: list[SignalResult] = []
    for key in active_detectors:
        entry = NORTHBOUND_REGISTRY.get(key)
        if entry is None:
            continue
        try:
            func = entry["func"]
            if key == "flow_direction_trend":
                result = func(nb_summary, config, nb_flow_history, _key=key, _label=entry["label"])
            elif key == "flow_trend":
                result = func(nb_summary, config, _key=key, _label=entry["label"])
            elif key == "market_flow_direction":
                result = func(nb_flow, config)
            elif key == "sector_preference":
                result = func(nb_summary, stock_info, config)
            elif key == "holdings_change":
                result = func(nb_summary, stock_info, config)
            else:
                result = func(nb_summary, config)
            results.append(result)
        except Exception:
            logger.exception("Northbound detector %s failed", key)
            results.append(neutral_signal(key, entry["label"], "检测器异常", detail={"data_source": "unknown"}))
    return results


def get_triggered_signals(results: list[SignalResult]) -> list[SignalResult]:
    """Return only triggered signals (strength significantly non-zero)."""
    return [r for r in results if r.triggered]


def get_bullish_signals(results: list[SignalResult]) -> list[SignalResult]:
    """Return signals with bullish direction."""
    return [r for r in results if r.direction == "bullish"]


def get_bearish_signals(results: list[SignalResult]) -> list[SignalResult]:
    """Return signals with bearish direction."""
    return [r for r in results if r.direction == "bearish"]


def compute_composite_score(results: list[SignalResult]) -> float:
    """Compute weighted composite sentiment score from all results.

    Applies signal decay: persistent signals lose strength over time
    (exponential decay with per-detector half-life).

    Returns:
        Float in range -1.0 (max bearish) to 1.0 (max bullish).
        0.0 = neutral.
    """
    total_weight = 0.0
    weighted_sum = 0.0
    for r in results:
        entry = NORTHBOUND_REGISTRY.get(r.key)
        if entry is None:
            continue
        w = entry["weight"]
        half_life = entry.get("half_life_days", 30)
        s = apply_signal_decay(r, half_life)
        if np.isnan(s) or np.isinf(s):
            s = 0.0
        weighted_sum += s * w
        total_weight += w
    if total_weight == 0:
        return 0.0
    return round(weighted_sum / total_weight, 4)
