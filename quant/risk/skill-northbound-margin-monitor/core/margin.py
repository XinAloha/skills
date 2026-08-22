"""Margin trading signal detectors (6 signals, registry pattern).

Each detector analyses margin + short selling data and returns a
SignalResult with direction, strength, and a human-readable summary.

Data sources:
  - margin_detail: Per-stock margin data (Pandadata ``get_margin`` or AKShare fallback)
  - margin_macro:  Aggregate SH+SZ margin history (AKShare ``macro_china_market_margin_sh/sz``)
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from ._types import SignalResult, neutral_signal, apply_signal_decay

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Helper: resolve columns from Chinese or English names
# ------------------------------------------------------------------

def _resolve_col(df: pd.DataFrame, *candidates: str) -> Optional[str]:
    """Return the first column name from *candidates* that exists in *df*."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _df_source(df: pd.DataFrame) -> str:
    """Map DataFrame attrs source tag to standard data_source label."""
    if df is None or df.empty:
        return "none"
    raw = df.attrs.get("source", "") if hasattr(df, "attrs") else ""
    label_map = {
        "pandadata": "pandadata",
        "eastmoney": "akshare_eastmoney",
    }
    return label_map.get(raw, "unknown")


# ------------------------------------------------------------------
# Detector 1: Margin Balance Trend (融资余额趋势)
# ------------------------------------------------------------------

def detect_margin_balance_trend(
    margin_macro: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Analyse margin balance trend: current vs 5/20-day moving average.

    Rising margin balance → leveraged buying, bullish sentiment.
    Falling margin balance → de-leveraging, cautious/bearish.
    Extreme rise → potential overheating risk.
    """
    key = "margin_balance_trend"
    label = "融资余额趋势"
    short_window = config.get("margin", {}).get("trend_short_window", 5)
    long_window = config.get("margin", {}).get("trend_long_window", 20)

    if margin_macro.empty:
        return neutral_signal(key, label, "无融资宏观数据", detail={"data_source": _df_source(margin_macro)})

    # Resolve balance column
    bal_col = _resolve_col(
        margin_macro, "margin_balance", "融资余额", "margin_balance_total"
    )
    if bal_col is None:
        # Try to compute from detail if available
        return neutral_signal(key, label, "无融资余额字段", detail={"data_source": _df_source(margin_macro)})

    # Aggregate SH+SZ by date
    date_col = _resolve_col(margin_macro, "date", "日期")
    if date_col is None:
        # Assume rows are in date order
        bal = pd.to_numeric(margin_macro[bal_col], errors="coerce").dropna()
        if bal.empty:
            return neutral_signal(key, label, "融资余额数据为空", detail={"data_source": _df_source(margin_macro)})
        # Use the latest values
        if "market" in margin_macro.columns:
            grouped = margin_macro.groupby("market")[bal_col].last()
            current = grouped.sum()
        else:
            current = bal.iloc[-1]
    else:
        grouped = margin_macro.groupby(date_col)[bal_col].sum().sort_index()
        if len(grouped) < long_window:
            return neutral_signal(key, label, f"数据不足（需≥{long_window}日，当前{len(grouped)}日）", detail={"data_source": _df_source(margin_macro)})
        current = grouped.iloc[-1]
        ma5 = grouped.rolling(short_window).mean().iloc[-1]
        ma20 = grouped.rolling(long_window).mean().iloc[-1]

        if pd.isna(ma5) or pd.isna(ma20):
            return neutral_signal(key, label, "均线计算失败", detail={"data_source": _df_source(margin_macro)})

        prev = grouped.iloc[-2] if len(grouped) >= 2 else current
        change_1d = (current - prev) / prev * 100 if prev != 0 else 0
        change_vs_ma20 = (current - ma20) / ma20 * 100

        # Heat assessment
        if change_vs_ma20 > 10:
            heat = "过热"
            triggered = True
            direction = "bearish"  # overheating = risk
            strength = -0.7
        elif change_vs_ma20 > 5:
            heat = "偏热"
            triggered = True
            direction = "bullish"
            strength = 0.5
        elif change_vs_ma20 > 0:
            heat = "温和上升"
            triggered = True
            direction = "bullish"
            strength = 0.3
        elif change_vs_ma20 > -5:
            heat = "温和下降"
            triggered = False
            direction = "bearish"
            strength = -0.2
        else:
            heat = "快速去杠杆"
            triggered = True
            direction = "bearish"
            strength = -0.6

        detail = {
            "data_source": _df_source(margin_macro),
            "current_balance_亿": round(float(current) / 1e8, 2),
            "ma5_亿": round(float(ma5) / 1e8, 2),
            "ma20_亿": round(float(ma20) / 1e8, 2),
            "change_1d_pct": round(float(change_1d), 2),
            "change_vs_ma20_pct": round(float(change_vs_ma20), 2),
            "heat_level": heat,
        }

        summary = f"融资余额{current/1e8:.0f}亿（MA20:{ma20/1e8:.0f}亿，{change_vs_ma20:+.1f}%），{heat}"

        return SignalResult(
            key=key, label=label, triggered=triggered,
            strength=round(strength, 4), direction=direction,
            summary=summary, detail=detail,
        )

    # Fallback: no date column, just report current state
    return neutral_signal(key, label, "无法按日期聚合融资余额", detail={"data_source": _df_source(margin_macro)})


# ------------------------------------------------------------------
# Detector 2: Margin Buy Ratio (融资买入比)
# ------------------------------------------------------------------

def detect_margin_buy_ratio(
    margin_detail: pd.DataFrame,
    margin_macro: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Analyse margin buy amount as percentage of total market turnover.

    > 10%: hot (杠杆活跃)
    > 15%: dangerous (过度杠杆，回调风险)
    < 5%:  cold (杠杆低迷)
    """
    key = "margin_buy_ratio"
    label = "融资买入比"
    hot_threshold = config.get("margin", {}).get("buy_ratio_hot", 0.10)
    danger_threshold = config.get("margin", {}).get("buy_ratio_dangerous", 0.15)

    # Try to get total margin buy from macro (latest date only)
    buy_col = _resolve_col(
        margin_macro, "buy_on_margin_value", "融资买入额", "margin_buy"
    )
    if buy_col is None:
        # Fallback: sum from detail (latest date)
        if not margin_detail.empty:
            detail_buy_col = _resolve_col(
                margin_detail, "buy_on_margin_value", "融资买入额"
            )
            if detail_buy_col is not None:
                # Filter to latest date if available
                det_date_col = _resolve_col(margin_detail, "date", "日期")
                if det_date_col is not None and not margin_detail.empty:
                    latest = margin_detail[det_date_col].max()
                    latest_detail = margin_detail[margin_detail[det_date_col] == latest]
                    total_buy = pd.to_numeric(latest_detail[detail_buy_col], errors="coerce").sum()
                else:
                    total_buy = pd.to_numeric(margin_detail[detail_buy_col], errors="coerce").sum()
                buy_source_df = margin_detail
            else:
                return neutral_signal(key, label, "无融资买入额数据", detail={"data_source": _df_source(margin_detail)})
        else:
            return neutral_signal(key, label, "无融资买入额数据", detail={"data_source": _df_source(margin_detail)})
    else:
        # Use latest date only to avoid summing all history
        buy_source_df = margin_macro
        date_col = _resolve_col(margin_macro, "date", "日期")
        if date_col is not None:
            latest = margin_macro[date_col].max()
            latest_macro = margin_macro[margin_macro[date_col] == latest]
            total_buy = pd.to_numeric(latest_macro[buy_col], errors="coerce").sum()
        else:
            total_buy = pd.to_numeric(margin_macro[buy_col], errors="coerce").sum()

    # Try to get total market turnover (may not be available)
    turnover_col = _resolve_col(margin_macro, "total_turnover", "总成交额", "market_turnover")
    if turnover_col is not None:
        total_turnover = pd.to_numeric(margin_macro[turnover_col], errors="coerce").sum()
    else:
        # Estimate: A-share daily turnover is typically 5000-15000 亿
        # Without exact data, we can't compute the ratio precisely
        # Use the buy amount itself to gauge activity
        buy_amount_亿 = float(total_buy) / 1e8

        # Configurable heuristic buckets: (threshold_亿, ratio)
        # Defaults based on typical A-share daily turnover of 5000-15000亿
        buckets = config.get("margin", {}).get("buy_ratio_estimate_buckets", [
            [1500, 0.18],
            [1000, 0.12],
            [500, 0.08],
            [200, 0.05],
        ])
        ratio_estimate = 0.02  # default fallback
        for threshold_亿, ratio in buckets:
            if buy_amount_亿 > threshold_亿:
                ratio_estimate = ratio
                break

        detail = {
            "data_source": _df_source(buy_source_df),
            "margin_buy_亿": round(buy_amount_亿, 2),
            "estimated_ratio": round(ratio_estimate, 4),
            "note": "总成交额不可用，买入比为基于融资买入额的估算值",
        }

        if ratio_estimate >= danger_threshold:
            triggered = True
            direction = "bearish"
            strength = -0.8
            summary = f"融资买入{buy_amount_亿:.0f}亿，估算买入比{ratio_estimate:.0%}（≥{danger_threshold:.0%}），过度杠杆危险"
        elif ratio_estimate >= hot_threshold:
            triggered = True
            direction = "bullish"
            strength = 0.4
            summary = f"融资买入{buy_amount_亿:.0f}亿，估算买入比{ratio_estimate:.0%}（≥{hot_threshold:.0%}），杠杆活跃"
        else:
            triggered = False
            direction = "neutral"
            strength = -0.1
            summary = f"融资买入{buy_amount_亿:.0f}亿，估算买入比{ratio_estimate:.0%}（<{hot_threshold:.0%}），杠杆平淡"

        return SignalResult(
            key=key, label=label, triggered=triggered,
            strength=round(strength, 4), direction=direction,
            summary=summary, detail=detail,
        )

    # If we have turnover data
    if total_turnover > 0:
        buy_ratio = float(total_buy) / float(total_turnover)
    else:
        return neutral_signal(key, label, "总成交额为零", detail={"data_source": _df_source(buy_source_df)})

    detail = {
        "data_source": _df_source(buy_source_df),
        "margin_buy_亿": round(float(total_buy) / 1e8, 2),
        "total_turnover_亿": round(float(total_turnover) / 1e8, 2),
        "buy_ratio": round(buy_ratio, 4),
    }

    if buy_ratio >= danger_threshold:
        triggered = True
        direction = "bearish"
        strength = -0.8
        summary = f"融资买入比{buy_ratio:.1%}（≥{danger_threshold:.0%}），过度杠杆，回调风险高"
    elif buy_ratio >= hot_threshold:
        triggered = True
        direction = "bullish"
        strength = 0.4
        summary = f"融资买入比{buy_ratio:.1%}（≥{hot_threshold:.0%}），杠杆活跃，做多情绪强"
    elif buy_ratio >= 0.05:
        triggered = False
        direction = "neutral"
        strength = 0.1
        summary = f"融资买入比{buy_ratio:.1%}，杠杆水平正常"
    else:
        triggered = False
        direction = "neutral"
        strength = -0.1
        summary = f"融资买入比{buy_ratio:.1%}，杠杆低迷"

    return SignalResult(
        key=key, label=label, triggered=triggered,
        strength=round(strength, 4), direction=direction,
        summary=summary, detail=detail,
    )


# ------------------------------------------------------------------
# Detector 3: Short Selling Trend (融券趋势)
# ------------------------------------------------------------------

def detect_short_trend(
    margin_macro: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Analyse short selling balance change rate over N days.

    Rising short balance → bearish sentiment (看空情绪上升).
    Falling short balance → short covering, potentially bullish.
    """
    key = "short_trend"
    label = "融券趋势"
    change_days = config.get("margin", {}).get("short_change_days", 5)

    if margin_macro.empty:
        return neutral_signal(key, label, "无融券宏观数据", detail={"data_source": _df_source(margin_macro)})

    short_col = _resolve_col(
        margin_macro, "short_balance", "融券余额", "short_balance_total"
    )
    if short_col is None:
        return neutral_signal(key, label, "无融券余额字段", detail={"data_source": _df_source(margin_macro)})

    date_col = _resolve_col(margin_macro, "date", "日期")
    if date_col is not None:
        grouped = margin_macro.groupby(date_col)[short_col].sum().sort_index()
    else:
        bal = pd.to_numeric(margin_macro[short_col], errors="coerce").dropna()
        grouped = bal

    if len(grouped) < change_days + 1:
        return neutral_signal(key, label, f"数据不足（需≥{change_days + 1}日，当前{len(grouped)}日）", detail={"data_source": _df_source(margin_macro)})

    current = grouped.iloc[-1]
    prev = grouped.iloc[-(change_days + 1)]
    if prev == 0:
        return neutral_signal(key, label, "前期融券余额为零", detail={"data_source": _df_source(margin_macro)})

    change_rate = (current - prev) / prev * 100

    detail = {
        "data_source": _df_source(margin_macro),
        "current_short_balance_亿": round(float(current) / 1e8, 2),
        "prev_short_balance_亿": round(float(prev) / 1e8, 2) if prev else 0,
        "change_days": change_days,
        "change_rate_pct": round(float(change_rate), 2),
    }

    if change_rate > 20:
        triggered = True
        direction = "bearish"
        strength = -0.7
        summary = f"融券余额{change_days}日大增{change_rate:.1f}%，看空情绪急剧上升"
    elif change_rate > 10:
        triggered = True
        direction = "bearish"
        strength = -0.4
        summary = f"融券余额{change_days}日增加{change_rate:.1f}%，看空情绪上升"
    elif change_rate > 0:
        triggered = False
        direction = "bearish"
        strength = -0.1
        summary = f"融券余额{change_days}日微增{change_rate:.1f}%"
    elif change_rate > -10:
        triggered = False
        direction = "bullish"
        strength = 0.1
        summary = f"融券余额{change_days}日下降{abs(change_rate):.1f}%，空头回补"
    elif change_rate > -20:
        triggered = True
        direction = "bullish"
        strength = 0.4
        summary = f"融券余额{change_days}日大降{abs(change_rate):.1f}%，空头大幅回补"
    else:
        triggered = True
        direction = "bullish"
        strength = 0.6
        summary = f"融券余额{change_days}日急降{abs(change_rate):.1f}%，空头恐慌回补"

    return SignalResult(
        key=key, label=label, triggered=triggered,
        strength=round(strength, 4), direction=direction,
        summary=summary, detail=detail,
    )


# ------------------------------------------------------------------
# Detector 4: Margin Heavy Stocks (融资重仓股)
# ------------------------------------------------------------------

def detect_margin_heavy_stocks(
    margin_detail: pd.DataFrame,
    stock_info: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Identify top margin-heavy stocks by balance, buy amount, and buy ratio.

    High concentration in a few stocks → systematic risk signal.
    """
    key = "margin_heavy_stocks"
    label = "融资重仓股"
    top_n = config.get("margin", {}).get("top_n_margin_stocks", 20)

    if margin_detail.empty:
        return neutral_signal(key, label, "无融资明细数据", detail={"data_source": _df_source(margin_detail)})

    bal_col = _resolve_col(
        margin_detail, "margin_balance", "融资余额"
    )
    buy_col = _resolve_col(
        margin_detail, "buy_on_margin_value", "融资买入额"
    )

    if bal_col is None and buy_col is None:
        return neutral_signal(key, label, "无融资余额/买入额字段", detail={"data_source": _df_source(margin_detail)})

    # Get symbol column
    sym_col = _resolve_col(margin_detail, "symbol", "股票代码")
    name_col = _resolve_col(margin_detail, "name", "股票名称")

    # Get top N by balance
    triggered = True  # Always report this, it's informational
    direction = "neutral"
    strength = 0.0

    detail: dict = {"data_source": _df_source(margin_detail), "top_n": top_n}

    # Filter to latest date per symbol to avoid multi-day inflation
    margin_latest = margin_detail.copy()
    if "date" in margin_latest.columns:
        margin_latest = margin_latest.sort_values("date")
        margin_latest = margin_latest.groupby(sym_col if sym_col else margin_latest.index).last().reset_index()

    if bal_col is not None:
        top_bal = margin_latest.nlargest(top_n, bal_col)
        if sym_col is not None:
            top_symbols_bal = top_bal[sym_col].tolist()
        else:
            top_symbols_bal = top_bal.index.tolist()[:top_n]
        detail["top_by_balance"] = top_symbols_bal[:10]

        total_bal = pd.to_numeric(margin_latest[bal_col], errors="coerce").sum()
        top_bal_sum = pd.to_numeric(top_bal[bal_col], errors="coerce").sum()
        concentration = top_bal_sum / total_bal * 100 if total_bal > 0 else 0
        detail["balance_concentration_pct"] = round(float(concentration), 1)

        if concentration > 40:
            direction = "bearish"
            strength = -0.4
            summary = f"融资余额TOP{top_n}集中度{concentration:.0f}%，高度集中，系统性风险"
        elif concentration > 25:
            summary = f"融资余额TOP{top_n}集中度{concentration:.0f}%，适度集中"
        else:
            summary = f"融资余额TOP{top_n}集中度{concentration:.0f}%，分布分散"
    else:
        summary = "融资重仓股数据基于买入额排名"

    if buy_col is not None:
        top_buy = margin_latest.nlargest(top_n, buy_col)
        if sym_col is not None:
            top_symbols_buy = top_buy[sym_col].tolist()
        else:
            top_symbols_buy = top_buy.index.tolist()[:top_n]
        detail["top_by_buy"] = top_symbols_buy[:10]

    return SignalResult(
        key=key, label=label, triggered=triggered,
        strength=round(strength, 4), direction=direction,
        summary=summary, detail=detail,
    )


# ------------------------------------------------------------------
# Detector 5: Margin/Short Ratio (融资融券比)
# ------------------------------------------------------------------

def detect_margin_short_ratio(
    margin_macro: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Analyse total margin balance / total short balance ratio.

    High ratio → strong bullish bias (融资主导).
    Low/falling ratio → rising bearish sentiment (融券增加).
    Trend direction matters more than absolute level.
    """
    key = "margin_short_ratio"
    label = "融资融券比"

    if margin_macro.empty:
        return neutral_signal(key, label, "无融资融券宏观数据", detail={"data_source": _df_source(margin_macro)})

    bal_col = _resolve_col(margin_macro, "margin_balance", "融资余额")
    short_col = _resolve_col(margin_macro, "short_balance", "融券余额")

    if bal_col is None or short_col is None:
        return neutral_signal(key, label, "缺少融资余额或融券余额字段", detail={"data_source": _df_source(margin_macro)})

    date_col = _resolve_col(margin_macro, "date", "日期")
    if date_col is not None:
        grouped_bal = margin_macro.groupby(date_col)[bal_col].sum().sort_index()
        grouped_short = margin_macro.groupby(date_col)[short_col].sum().sort_index()
    else:
        grouped_bal = pd.to_numeric(margin_macro[bal_col], errors="coerce")
        grouped_short = pd.to_numeric(margin_macro[short_col], errors="coerce")

    if grouped_short.empty or (grouped_short == 0).any():
        return neutral_signal(key, label, "融券余额为零，无法计算比率", detail={"data_source": _df_source(margin_macro)})

    ratio = grouped_bal / grouped_short

    if len(ratio) < 6:
        return neutral_signal(key, label, f"数据不足（仅{len(ratio)}日）", detail={"data_source": _df_source(margin_macro)})

    current = ratio.iloc[-1]
    prev_5d = ratio.iloc[-6] if len(ratio) >= 6 else ratio.iloc[0]
    prev_20d = ratio.iloc[-21] if len(ratio) >= 21 else ratio.iloc[0]

    change_5d = (current - prev_5d) / prev_5d * 100 if prev_5d != 0 else 0
    change_20d = (current - prev_20d) / prev_20d * 100 if prev_20d != 0 else 0

    detail = {
        "data_source": _df_source(margin_macro),
        "current_ratio": round(float(current), 2),
        "change_5d_pct": round(float(change_5d), 2),
        "change_20d_pct": round(float(change_20d), 2),
    }

    # Interpret ratio trend
    if change_5d > 15 and change_20d > 20:
        triggered = True
        direction = "bullish"  # Strong margin preference
        strength = 0.6
        summary = f"融资/融券比{current:.1f}，5日{change_5d:+.1f}%，20日{change_20d:+.1f}%，多头主导强化"
    elif change_5d > 5:
        triggered = True
        direction = "bullish"
        strength = 0.3
        summary = f"融资/融券比{current:.1f}，5日{change_5d:+.1f}%，偏多倾向上升"
    elif change_5d < -15 and change_20d < -20:
        triggered = True
        direction = "bearish"
        strength = -0.6
        summary = f"融资/融券比{current:.1f}，5日{change_5d:+.1f}%，20日{change_20d:+.1f}%，空头力量上升"
    elif change_5d < -5:
        triggered = True
        direction = "bearish"
        strength = -0.3
        summary = f"融资/融券比{current:.1f}，5日{change_5d:+.1f}%，偏空倾向上升"
    else:
        triggered = False
        direction = "neutral"
        strength = 0.0
        summary = f"融资/融券比{current:.1f}，5日变化{change_5d:+.1f}%，多空均衡"

    return SignalResult(
        key=key, label=label, triggered=triggered,
        strength=round(strength, 4), direction=direction,
        summary=summary, detail=detail,
    )


# ------------------------------------------------------------------
# Detector 6: Margin Type Distribution (融资类型分布)
# ------------------------------------------------------------------

def detect_margin_type_distribution(
    margin_detail: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Analyse margin type distribution (cash vs stock collateral).

    High proportion of stock-collateral margin → higher systemic risk
    (stock price decline → collateral value drop → forced liquidation).
    Cash-collateral margin is more stable.
    """
    key = "margin_type_distribution"
    label = "融资类型分布"

    if margin_detail.empty:
        return neutral_signal(key, label, "无融资明细数据", detail={"data_source": _df_source(margin_detail)})

    type_col = _resolve_col(margin_detail, "margin_type", "融资类型")
    if type_col is None:
        return neutral_signal(key, label, "无融资类型字段", detail={"data_source": _df_source(margin_detail)})

    type_counts = margin_detail[type_col].value_counts()
    total = len(margin_detail)

    detail = {"data_source": _df_source(margin_detail), "total_stocks": total}
    for t, count in type_counts.items():
        detail[f"type_{t}_count"] = count
        detail[f"type_{t}_pct"] = round(count / total * 100, 1)

    # Check if there's meaningful distribution
    if len(type_counts) <= 1:
        return neutral_signal(key, label, f"融资类型单一（{type_counts.index[0] if len(type_counts) > 0 else '未知'}）", detail={"data_source": _df_source(margin_detail)})

    triggered = True
    # If stock-collateral type is dominant, flag as slightly bearish
    dominant_type = type_counts.index[0]
    dominant_pct = type_counts.iloc[0] / total * 100

    # Map type values to Chinese with risk interpretation
    _type_labels = {
        "cash": "现金担保融资",
        "stock": "股票担保融资",
        "现金": "现金担保融资",
        "股票": "股票担保融资",
        "融资融券": "两融综合",
    }
    _type_risk = {
        "cash": "质押稳定，风险可控",
        "stock": "受股价波动影响，需关注质押物贬值风险",
        "现金": "质押稳定，风险可控",
        "股票": "受股价波动影响，需关注质押物贬值风险",
    }

    if dominant_pct > 80:
        direction = "neutral"
        strength = -0.1
        dom_label = _type_labels.get(str(dominant_type), str(dominant_type))
        dom_risk = _type_risk.get(str(dominant_type), "")
        summary = f"融资类型以{dom_label}为主（{dominant_pct:.0f}%），高度集中" + (f"——{dom_risk}" if dom_risk else "")
    else:
        direction = "neutral"
        strength = 0.0
        parts = []
        for t, c in type_counts.head(3).items():
            label = _type_labels.get(str(t), str(t))
            risk = _type_risk.get(str(t), "")
            parts.append(f"{label}({c/total*100:.0f}%)——{risk}" if risk else f"{label}({c/total*100:.0f}%)")
        summary = f"融资类型分布：{'；'.join(parts)}。结构均衡，融资类型分布健康。"

    return SignalResult(
        key=key, label=label, triggered=triggered,
        strength=round(strength, 4), direction=direction,
        summary=summary, detail=detail,
    )


# ------------------------------------------------------------------
# Detector 7: Extreme Regime (极端杠杆区间)
# ------------------------------------------------------------------

def detect_margin_extreme_regime(
    margin_macro: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Detect extreme margin balance regimes via historical percentile analysis.

    Uses rolling percentile of margin balance to detect:
      - > P95 + high buy ratio → "杠杆极端过热" (strong bearish, -0.9)
      - > P95, buy ratio normal → "杠杆高位运行" (moderate bearish, -0.5)
      - < P5 → "杠杆极端冰点" (bullish, +0.6)
      - Normal range → not triggered

    Args:
        margin_macro: Aggregate SH+SZ margin history with margin_balance column.
        config: Full runtime config dict.

    Returns:
        SignalResult with key="margin_extreme_regime".
    """
    key = "margin_extreme_regime"
    label = "杠杆极端区间"
    cfg = config.get("margin", {})
    extreme_pct = cfg.get("extreme_percentile", 95)
    ice_pct = cfg.get("ice_point_percentile", 5)
    min_history = cfg.get("extreme_regime_min_history", 60)

    if margin_macro.empty:
        return neutral_signal(key, label, "无融资宏观数据", detail={"data_source": _df_source(margin_macro)})

    bal_col = _resolve_col(
        margin_macro, "margin_balance", "融资余额", "margin_balance_total"
    )
    if bal_col is None:
        return neutral_signal(key, label, "无融资余额字段", detail={"data_source": _df_source(margin_macro)})

    date_col = _resolve_col(margin_macro, "date", "日期")
    if date_col is not None:
        grouped = margin_macro.groupby(date_col)[bal_col].sum().sort_index()
    else:
        grouped = pd.to_numeric(margin_macro[bal_col], errors="coerce").dropna()

    if len(grouped) < min_history:
        return neutral_signal(
            key, label,
            f"历史数据不足（需≥{min_history}日，当前{len(grouped)}日）",
            detail={"data_source": _df_source(margin_macro)},
        )

    current = grouped.iloc[-1]
    hist = grouped.iloc[:-1]  # exclude current day for percentile calc
    p95 = float(np.percentile(hist, extreme_pct))
    p5 = float(np.percentile(hist, ice_pct))

    detail = {
        "data_source": _df_source(margin_macro),
        "current_balance_亿": round(float(current) / 1e8, 2),
        "p95_亿": round(p95 / 1e8, 2),
        "p5_亿": round(p5 / 1e8, 2),
        "percentile_rank": round(float((hist < current).mean()) * 100, 1),
        "min_history": min_history,
    }

    if current > p95:
        # Try to extract buy ratio for combined signal
        buy_ratio = _extract_margin_buy_ratio(margin_macro, config)
        danger_threshold = cfg.get("buy_ratio_dangerous", 0.15)

        if buy_ratio is not None and buy_ratio >= danger_threshold:
            triggered = True
            direction = "bearish"
            strength = -0.9
            summary = (
                f"融资余额{current / 1e8:.0f}亿超过P{extreme_pct}（{p95 / 1e8:.0f}亿），"
                f"买入比{buy_ratio:.0%}（≥{danger_threshold:.0%}），"
                f"杠杆极端过热，系统性风险极高"
            )
        else:
            triggered = True
            direction = "bearish"
            strength = -0.5
            summary = (
                f"融资余额{current / 1e8:.0f}亿超过P{extreme_pct}（{p95 / 1e8:.0f}亿），"
                f"杠杆高位运行，回调风险上升"
            )
        detail["buy_ratio"] = round(buy_ratio, 4) if buy_ratio is not None else None
    elif current < p5:
        triggered = True
        direction = "bullish"
        strength = 0.6
        summary = (
            f"融资余额{current / 1e8:.0f}亿低于P{ice_pct}（{p5 / 1e8:.0f}亿），"
            f"杠杆极端冰点，市场情绪见底信号"
        )
    else:
        triggered = False
        direction = "neutral"
        strength = 0.0
        pct_rank = round(float((hist < current).mean()) * 100, 1)
        summary = (
            f"融资余额{current / 1e8:.0f}亿处于P{pct_rank}分位，杠杆水平正常"
        )

    return SignalResult(
        key=key, label=label, triggered=triggered,
        strength=round(strength, 4), direction=direction,
        summary=summary, detail=detail,
    )


def _extract_margin_buy_ratio(
    margin_macro: pd.DataFrame,
    config: dict,
) -> Optional[float]:
    """Extract current margin buy ratio from macro data.

    Tries actual buy/turnover ratio first, then falls back to
    the heuristic estimate used by ``detect_margin_buy_ratio``.

    Returns:
        Buy ratio as float (0.0–1.0), or None if data unavailable.
    """
    buy_col = _resolve_col(margin_macro, "buy_on_margin_value", "融资买入额", "margin_buy")
    if buy_col is None:
        return None

    date_col = _resolve_col(margin_macro, "date", "日期")
    if date_col is not None:
        latest = margin_macro[date_col].max()
        latest_macro = margin_macro[margin_macro[date_col] == latest]
    else:
        latest_macro = margin_macro

    total_buy = pd.to_numeric(latest_macro[buy_col], errors="coerce").sum()

    turnover_col = _resolve_col(margin_macro, "total_turnover", "总成交额", "market_turnover")
    if turnover_col is not None:
        total_turnover = pd.to_numeric(latest_macro[turnover_col], errors="coerce").sum()
        if total_turnover > 0:
            return float(total_buy) / float(total_turnover)

    # Estimate from buy amount heuristic
    buy_amount_亿 = float(total_buy) / 1e8
    buckets = config.get("margin", {}).get("buy_ratio_estimate_buckets", [
        [1500, 0.18], [1000, 0.12], [500, 0.08], [200, 0.05],
    ])
    for threshold_亿, ratio in buckets:
        if buy_amount_亿 > threshold_亿:
            return ratio
    return 0.02


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------

MARGIN_REGISTRY = {
    "margin_balance_trend": {
        "func": detect_margin_balance_trend,
        "weight": 3,
        "label": "融资余额趋势",
        "description": "融资余额 vs 5/20日均线，热度评级",
        "half_life_days": 25,
    },
    "margin_buy_ratio": {
        "func": detect_margin_buy_ratio,
        "weight": 3,
        "label": "融资买入比",
        "description": "融资买入/总成交，>10%热 >15%危险",
        "half_life_days": 8,
    },
    "short_trend": {
        "func": detect_short_trend,
        "weight": 2,
        "label": "融券趋势",
        "description": "5日融券余额变化率，看空情绪",
        "half_life_days": 10,
    },
    "margin_heavy_stocks": {
        "func": detect_margin_heavy_stocks,
        "weight": 1,
        "label": "融资重仓股",
        "description": "TOP20融资余额/买入额排名，集中度分析",
        "half_life_days": 15,
    },
    "margin_short_ratio": {
        "func": detect_margin_short_ratio,
        "weight": 2,
        "label": "融资融券比",
        "description": "融资/融券总余额比率，多空倾向",
        "half_life_days": 20,
    },
    "margin_type_distribution": {
        "func": detect_margin_type_distribution,
        "weight": 1,
        "label": "融资类型分布",
        "description": "现金vs股票融资占比分析",
        "half_life_days": 20,
    },
    "margin_extreme_regime": {
        "func": detect_margin_extreme_regime,
        "weight": 3,
        "label": "杠杆极端区间",
        "description": "历史分位数检测：>P95过热 / <P5冰点",
        "half_life_days": 30,
    },
}


def run_all_detectors(
    margin_detail: pd.DataFrame,
    margin_macro: pd.DataFrame,
    stock_info: pd.DataFrame,
    config: dict,
    active_detectors: Optional[set[str]] = None,
) -> list[SignalResult]:
    """Run all active margin detectors.

    Args:
        margin_detail: Per-stock margin data.
        margin_macro: Aggregate SH+SZ margin history.
        stock_info: Stock detail info for name/industry mapping.
        config: Full runtime config dict.
        active_detectors: Set of detector keys to run. None = run all.

    Returns:
        List of SignalResult, one per active detector.
    """
    if active_detectors is None:
        active_detectors = set(MARGIN_REGISTRY.keys())

    results: list[SignalResult] = []
    for key in active_detectors:
        entry = MARGIN_REGISTRY.get(key)
        if entry is None:
            continue
        try:
            func = entry["func"]
            if key == "margin_heavy_stocks":
                result = func(margin_detail, stock_info, config)
            elif key == "margin_type_distribution":
                result = func(margin_detail, config)
            elif key == "margin_buy_ratio":
                result = func(margin_detail, margin_macro, config)
            else:
                result = func(margin_macro, config)
            results.append(result)
        except Exception:
            logger.exception("Margin detector %s failed", key)
            results.append(neutral_signal(key, entry["label"], "检测器异常", detail={"data_source": "unknown"}))
    return results


def get_triggered_signals(results: list[SignalResult]) -> list[SignalResult]:
    """Return only triggered signals."""
    return [r for r in results if r.triggered]


def get_bullish_signals(results: list[SignalResult]) -> list[SignalResult]:
    """Return signals with bullish direction."""
    return [r for r in results if r.direction == "bullish"]


def get_bearish_signals(results: list[SignalResult]) -> list[SignalResult]:
    """Return signals with bearish direction."""
    return [r for r in results if r.direction == "bearish"]


def compute_composite_score(results: list[SignalResult]) -> float:
    """Compute weighted composite sentiment score from all results.

    Applies signal decay: persistent signals lose strength over time.

    Returns:
        Float in range -1.0 (max bearish) to 1.0 (max bullish).
    """
    total_weight = 0.0
    weighted_sum = 0.0
    for r in results:
        entry = MARGIN_REGISTRY.get(r.key)
        if entry is None:
            continue
        w = entry["weight"]
        half_life = entry.get("half_life_days", 30)
        s = apply_signal_decay(r, half_life)
        weighted_sum += s * w
        total_weight += w
    if total_weight == 0:
        return 0.0
    return round(weighted_sum / total_weight, 4)
