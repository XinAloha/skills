"""Market microstructure confirmation signals for the panorama monitor.

Adds a 5th dimension to the existing 4-dimension analysis:
- advance/decline ratio (涨跌比)
- index volume trend (指数量能趋势)
- turnover trend (成交额趋势)
- limit-up/down statistics (涨跌停统计)

These are breadth/liquidity confirmation factors — they validate or weaken
capital-flow signals based on market participation and sentiment breadth.

Data sources:
    - nb_flow: northbound flow direction data (advancing/declining per market)
    - futures_data: CSI300 index volume from spot index daily data
    - margin_macro: aggregate margin data (total market turnover)
    - AKShare stock_zt_pool_em: limit-up/down stocks
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from ._types import SignalResult

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Detector 1: Advance/decline ratio
# ------------------------------------------------------------------

def detect_advance_decline_ratio(nb_flow: pd.DataFrame, config: dict) -> SignalResult:
    """Detect market breadth from advancing vs declining stocks.

    Uses advancing/declining counts from northbound flow data
    (positions [8] 上涨数, [9] 持平数, [10] 下跌数).

    Rules:
        - breadth (advancing / total) > bullish_threshold → bullish
        - breadth < bearish_threshold → bearish
        - Otherwise → neutral

    Args:
        nb_flow: DataFrame from stock_hsgt_fund_flow_summary_em.
        config: Full runtime config dict.

    Returns:
        SignalResult with key="advance_decline_ratio".
    """
    ms_cfg = config.get("microstructure", {})
    bullish_threshold = ms_cfg.get("advance_decline_bullish", 0.65)
    bearish_threshold = ms_cfg.get("advance_decline_bearish", 0.35)

    result = SignalResult(
        key="advance_decline_ratio",
        label="涨跌比",
        triggered=False,
        strength=0.0,
        direction="neutral",
        summary="",
        detail={"data_source": "akshare_eastmoney"},
    )

    if nb_flow is None or nb_flow.empty:
        result.summary = "缺少涨跌数据"
        result.detail = {"data_source": "akshare_eastmoney"}
        return result

    # Resolve advancing/declining columns
    adv_col = None
    dec_col = None
    flat_col = None
    for c in ["上涨数", "advancing", "up_count"]:
        if c in nb_flow.columns:
            adv_col = c
            break
    for c in ["下跌数", "declining", "down_count"]:
        if c in nb_flow.columns:
            dec_col = c
            break
    for c in ["持平数", "flat", "unchanged"]:
        if c in nb_flow.columns:
            flat_col = c
            break

    if adv_col is None or dec_col is None:
        result.summary = "缺少涨跌数据列"
        result.detail = {"data_source": "akshare_eastmoney"}
        return result

    adv = pd.to_numeric(nb_flow[adv_col], errors="coerce").sum()
    dec = pd.to_numeric(nb_flow[dec_col], errors="coerce").sum()
    flat = 0.0
    if flat_col:
        flat = pd.to_numeric(nb_flow[flat_col], errors="coerce").sum()

    total = adv + dec + flat
    if total == 0:
        result.summary = "涨跌数据全为零"
        result.detail = {"data_source": "akshare_eastmoney"}
        return result

    # Guard: if both advancing and declining are zero, market data is invalid
    # (e.g., non-trading day, data feed error). Return neutral, not bearish.
    if adv + dec == 0:
        result.summary = "涨跌家数均为零（数据异常或非交易日）"
        result.detail = {"data_source": "akshare_eastmoney", "advancing": 0, "declining": 0}
        return result

    breadth = adv / total
    adv_dec_ratio = adv / dec if dec > 0 else (float("inf") if adv > 0 else 0.0)

    result.detail = {
        "data_source": "akshare_eastmoney",
        "advancing": int(adv),
        "declining": int(dec),
        "flat": int(flat),
        "breadth": round(float(breadth), 4),
        "adv_dec_ratio": round(float(min(adv_dec_ratio, 999.0)), 2),
    }

    if breadth > bullish_threshold:
        result.triggered = True
        result.direction = "bullish"
        result.strength = round(min(1.0, (breadth - 0.5) / 0.45), 4)
        result.summary = f"上涨{int(adv)}家/下跌{int(dec)}家，涨跌比{adv_dec_ratio:.1f}，市场广度偏多"
    elif breadth < bearish_threshold:
        result.triggered = True
        result.direction = "bearish"
        result.strength = round(max(-1.0, (breadth - 0.5) / 0.45), 4)
        result.summary = f"上涨{int(adv)}家/下跌{int(dec)}家，涨跌比{adv_dec_ratio:.1f}，市场广度偏空"
    else:
        result.summary = f"上涨{int(adv)}家/下跌{int(dec)}家，涨跌均衡（广度{adv_dec_ratio:.1f}）"

    return result


# ------------------------------------------------------------------
# Detector 2: Index volume trend
# ------------------------------------------------------------------

def detect_index_volume_trend(futures_data: pd.DataFrame, config: dict) -> SignalResult:
    """Detect CSI300 index volume trend.

    Uses the index_volume column from futures_data (extracted from
    stock_zh_index_daily for CSI300).

    Rules:
        - volume > expansion_threshold * MA20 and price up → bullish
        - volume > expansion_threshold * MA20 and price down → bearish
        - volume < contraction_threshold * MA20 → neutral (low activity)
        - Otherwise → neutral

    Args:
        futures_data: DataFrame with index_volume and spot_close columns.
        config: Full runtime config dict.

    Returns:
        SignalResult with key="index_volume_trend".
    """
    ms_cfg = config.get("microstructure", {})
    expansion_threshold = ms_cfg.get("volume_expansion_threshold", 1.3)
    contraction_threshold = ms_cfg.get("volume_contraction_threshold", 0.7)
    ma_period = ms_cfg.get("volume_ma_period", 20)

    result = SignalResult(
        key="index_volume_trend",
        label="指数量能趋势",
        triggered=False,
        strength=0.0,
        direction="neutral",
        summary="",
        detail={"data_source": "akshare_sina"},
    )

    if futures_data is None or futures_data.empty:
        result.summary = "缺少指数数据"
        result.detail = {"data_source": "akshare_sina"}
        return result

    # Filter to CSI300 rows
    csi_mask = pd.Series(True, index=futures_data.index)
    if "index_name" in futures_data.columns:
        csi_mask = futures_data["index_name"] == "CSI300"

    csi_data = futures_data[csi_mask].copy()
    if csi_data.empty:
        result.summary = "缺少CSI300指数数据"
        result.detail = {"data_source": "akshare_sina"}
        return result

    if "index_volume" not in csi_data.columns:
        result.summary = "缺少指数成交量数据"
        result.detail = {"data_source": "akshare_sina"}
        return result

    volume = pd.to_numeric(csi_data["index_volume"], errors="coerce").dropna()
    if len(volume) < ma_period + 1:
        result.summary = f"成交量数据不足 (需{ma_period + 1}日，实际{len(volume)}日)"
        result.detail = {"data_source": "akshare_sina"}
        return result

    current_vol = volume.iloc[-1]
    ma20_vol = volume.iloc[-min(ma_period, len(volume)):].mean()
    expansion_ratio = current_vol / ma20_vol if ma20_vol > 0 else 1.0

    # Determine price direction
    price_up = False
    if "spot_close" in csi_data.columns:
        close = pd.to_numeric(csi_data["spot_close"], errors="coerce").dropna()
        if len(close) >= 5:
            price_up = close.iloc[-1] > close.iloc[-5]

    result.detail = {
        "data_source": "akshare_sina",
        "current_volume": int(current_vol),
        "ma20_volume": int(ma20_vol),
        "expansion_ratio": round(float(expansion_ratio), 3),
        "n_observations": len(volume),
    }

    if expansion_ratio > expansion_threshold:
        if price_up:
            result.triggered = True
            result.direction = "bullish"
            result.strength = round(min(1.0, (expansion_ratio - 1.0) / 0.7), 4)
            result.summary = f"指数量能{expansion_ratio:.1f}倍于MA20，放量上涨，趋势确认偏多"
        else:
            result.triggered = True
            result.direction = "bearish"
            result.strength = round(max(-1.0, -(expansion_ratio - 1.0) / 0.7), 4)
            result.summary = f"指数量能{expansion_ratio:.1f}倍于MA20，放量下跌，派发信号偏空"
    elif expansion_ratio < contraction_threshold:
        result.summary = f"指数量能{expansion_ratio:.1f}倍于MA20，缩量运行，市场参与度低"
    else:
        price_word = "↑" if price_up else "↓"
        result.summary = f"指数量能{expansion_ratio:.1f}倍于MA20（正常），方向{price_word}"

    return result


# ------------------------------------------------------------------
# Detector 3: Turnover trend
# ------------------------------------------------------------------

def detect_turnover_trend(
    margin_macro: pd.DataFrame,
    futures_data: pd.DataFrame,
    config: dict,
) -> SignalResult:
    """Detect total market turnover trend.

    Combines two data sources:
    1. margin_macro with total_turnover column (full market SH+SZ)
    2. futures_data with index_volume for CSI300 (fallback)

    Rules:
        - expansion > 1.3x MA20 and price rising → bullish (放量上涨)
        - expansion > 1.3x MA20 and price falling → bearish (放量下跌)
        - expansion < 0.7x → neutral (缩量)
        - Otherwise → neutral

    Args:
        margin_macro: DataFrame possibly with total_turnover column.
        futures_data: DataFrame with index_volume fallback.
        config: Full runtime config dict.

    Returns:
        SignalResult with key="turnover_trend".
    """
    ms_cfg = config.get("microstructure", {})
    expansion_threshold = ms_cfg.get("volume_expansion_threshold", 1.3)
    contraction_threshold = ms_cfg.get("volume_contraction_threshold", 0.7)
    ma_period = ms_cfg.get("volume_ma_period", 20)

    result = SignalResult(
        key="turnover_trend",
        label="成交额趋势",
        triggered=False,
        strength=0.0,
        direction="neutral",
        summary="",
        detail={"data_source": "unknown"},
    )

    # Try primary source: margin_macro total_turnover
    turnover_series = None
    source_label = ""

    if margin_macro is not None and not margin_macro.empty:
        for col in ["total_turnover", "总成交额", "market_turnover"]:
            if col in margin_macro.columns:
                raw = pd.to_numeric(margin_macro[col], errors="coerce").dropna()
                if len(raw) >= ma_period:
                    # Sum SH+SZ for each date
                    if "market" in margin_macro.columns:
                        sums = margin_macro.groupby("date")[col].apply(
                            lambda x: pd.to_numeric(x, errors="coerce").sum()
                        ).dropna()
                        if len(sums) >= ma_period:
                            turnover_series = sums
                            source_label = "全市场（沪+深）"
                            break
                    else:
                        turnover_series = raw
                        source_label = "融资宏观"
                        break

    # Fallback: CSI300 index volume
    if turnover_series is None and futures_data is not None and not futures_data.empty:
        csi_mask = pd.Series(True, index=futures_data.index)
        if "index_name" in futures_data.columns:
            csi_mask = futures_data["index_name"] == "CSI300"
        csi_data = futures_data[csi_mask]
        if not csi_data.empty and "index_volume" in csi_data.columns:
            raw = pd.to_numeric(csi_data["index_volume"], errors="coerce").dropna()
            if len(raw) >= ma_period:
                turnover_series = raw
                source_label = "CSI300指数成交量（替代）"

    if turnover_series is None or len(turnover_series) < ma_period:
        result.summary = "缺少全市场成交额数据"
        result.detail = {"data_source": "unknown"}
        return result

    current = turnover_series.iloc[-1]
    ma20 = turnover_series.iloc[-min(ma_period, len(turnover_series)):].mean()
    expansion_ratio = current / ma20 if ma20 > 0 else 1.0

    # Determine price direction from futures_data
    price_up = False
    if futures_data is not None and not futures_data.empty:
        csi_mask = pd.Series(True, index=futures_data.index)
        if "index_name" in futures_data.columns:
            csi_mask = futures_data["index_name"] == "CSI300"
        csi = futures_data[csi_mask]
        if not csi.empty and "spot_close" in csi.columns:
            close = pd.to_numeric(csi["spot_close"], errors="coerce").dropna()
            if len(close) >= 5:
                price_up = close.iloc[-1] > close.iloc[-5]

    result.detail = {
        "data_source": source_label,
        "current_turnover_億": round(float(current) / 1e8, 1) if current > 1e8 else round(float(current), 0),
        "ma20_turnover_億": round(float(ma20) / 1e8, 1) if ma20 > 1e8 else round(float(ma20), 0),
        "expansion_ratio": round(float(expansion_ratio), 3),
        "n_observations": len(turnover_series),
    }

    if expansion_ratio > expansion_threshold:
        if price_up:
            result.triggered = True
            result.direction = "bullish"
            result.strength = round(min(1.0, (expansion_ratio - 1.0) / 0.5), 4)
            result.summary = f"全市场成交额{expansion_ratio:.1f}倍于MA20，放量上涨，资金参与积极（{source_label}）"
        else:
            result.triggered = True
            result.direction = "bearish"
            result.strength = round(max(-1.0, -(expansion_ratio - 1.0) / 0.5), 4)
            result.summary = f"全市场成交额{expansion_ratio:.1f}倍于MA20，放量下跌，资金出逃压力（{source_label}）"
    elif expansion_ratio < contraction_threshold:
        result.summary = f"全市场成交额{expansion_ratio:.1f}倍于MA20，缩量运行，市场参与意愿低（{source_label}）"
    else:
        price_word = "↑" if price_up else "↓"
        result.summary = f"全市场成交额{expansion_ratio:.1f}倍于MA20（正常），方向{price_word}（{source_label}）"

    return result


# ------------------------------------------------------------------
# Detector 4: Limit-up/down stocks
# ------------------------------------------------------------------

def detect_limit_stocks(config: dict) -> SignalResult:
    """Detect limit-up/down stock counts as sentiment extremes.

    Uses ak.stock_zt_pool_em() and ak.stock_zt_pool_dtgc_em() if akshare is importable.
    Falls back to neutral if unavailable.

    Rules:
        - limit_up > 100 and limit_up / limit_down > 3 → bullish
        - limit_down > 100 and limit_down / limit_up > 3 → bearish
        - Otherwise → neutral

    Args:
        config: Full runtime config dict.

    Returns:
        SignalResult with key="limit_stocks".
    """
    ms_cfg = config.get("microstructure", {})
    up_threshold = ms_cfg.get("limit_up_count_threshold", 100)
    ratio_threshold = ms_cfg.get("limit_ratio_threshold", 3.0)

    result = SignalResult(
        key="limit_stocks",
        label="涨跌停统计",
        triggered=False,
        strength=0.0,
        direction="neutral",
        summary="",
        detail={"data_source": "akshare_realtime"},
    )

    try:
        import akshare as ak
    except ImportError:
        result.summary = "涨跌停数据不可用（akshare未安装）"
        result.detail = {"data_source": "akshare_realtime"}
        return result

    try:
        zt_df = ak.stock_zt_pool_em(date=config.get("_trade_date", None))
        if zt_df is None or zt_df.empty:
            result.summary = "涨跌停数据API返回为空"
            result.detail = {"data_source": "akshare_realtime"}
            return result

        limit_up = len(zt_df)
        # Try to get limit-down count
        try:
            dt_df = ak.stock_zt_pool_dtgc_em(date=config.get("_trade_date", None))
            limit_down = len(dt_df) if dt_df is not None else 0
        except Exception:
            limit_down = 0

        result.detail = {
            "data_source": "akshare_realtime",
            "limit_up_count": limit_up,
            "limit_down_count": limit_down,
            "up_down_ratio": round(limit_up / max(1, limit_down), 2),
        }

        if limit_up > up_threshold and limit_up / max(1, limit_down) > ratio_threshold:
            result.triggered = True
            result.direction = "bullish"
            result.strength = round(min(1.0, limit_up / 300), 4)
            result.summary = f"涨停{limit_up}家/跌停{limit_down}家，涨停家数远超跌停，市场情绪亢奋偏多"
        elif limit_down > up_threshold and limit_down / max(1, limit_up) > ratio_threshold:
            result.triggered = True
            result.direction = "bearish"
            result.strength = round(max(-1.0, -limit_down / 300), 4)
            result.summary = f"涨停{limit_up}家/跌停{limit_down}家，跌停家数远超涨停，恐慌情绪蔓延"
        else:
            result.summary = f"涨停{limit_up}家/跌停{limit_down}家，极端情绪不显著"

    except Exception as e:
        logger.warning("Limit stocks detector failed: %s", e)
        result.summary = "涨跌停数据API不可用"
        result.detail = {"data_source": "akshare_realtime"}

    return result


def detect_main_fund_flow(config: dict) -> SignalResult:
    """Detect domestic main fund flow direction and divergence with retail flow.

    Uses ak.stock_market_fund_flow() to get daily market-level fund flow
    by order size (超大单/大单/中单/小单). Main force = 超大单 + 大单 net inflow.

    Rules:
        - Main force inflow > threshold AND retail outflow → "聪明钱进场" (+0.7)
        - Main force inflow > threshold → "主力资金净流入" (+0.5)
        - Main force outflow > threshold AND retail inflow → "主力撤退" (-0.7)
        - Main force outflow > threshold → "主力资金净流出" (-0.5)
        - Otherwise → neutral
    """
    ms_cfg = config.get("microstructure", {})
    flow_threshold_亿 = ms_cfg.get("main_fund_flow_threshold_亿", 50.0)

    result = SignalResult(
        key="main_fund_flow",
        label="主力资金流向",
        triggered=False,
        strength=0.0,
        direction="neutral",
        summary="",
        detail={"data_source": "akshare_eastmoney"},
    )

    try:
        import akshare as ak
    except ImportError:
        result.summary = "主力资金数据不可用（akshare未安装）"
        result.detail = {"data_source": "akshare_eastmoney"}
        return result

    try:
        df = ak.stock_market_fund_flow()
        if df is None or df.empty:
            result.summary = "主力资金数据API返回为空"
            result.detail = {"data_source": "akshare_eastmoney"}
            return result

        # Get latest row
        latest = df.iloc[-1]

        # Resolve columns: API returns fixed order with Chinese names
        # Columns: 日期, 上证-收盘价, 上证-涨跌幅, 深证-收盘价, 深证-涨跌幅,
        #   主力净流入-净额, 主力净流入-净占比,
        #   超大单净流入-净额, 超大单净流入-净占比,
        #   大单净流入-净额, 大单净流入-净占比,
        #   中单净流入-净额, 中单净流入-净占比,
        #   小单净流入-净额, 小单净流入-净占比
        def _find_col(df_columns, keywords):
            for c in df_columns:
                cs = str(c)
                if all(kw in cs for kw in keywords):
                    return c
            return None

        super_large_col = _find_col(df.columns, ["超大单", "净额"])
        large_col = _find_col(df.columns, ["大单", "净额"])
        medium_col = _find_col(df.columns, ["中单", "净额"])
        small_col = _find_col(df.columns, ["小单", "净额"])

        # Fallback: try positional columns (API returns fixed order)
        # Columns order: 日期, 上证-收盘价, 上证-涨跌幅, 深证-收盘价, 深证-涨跌幅,
        #   主力净流入-净额, 主力净流入-净占比,
        #   超大单净流入-净额, 超大单净流入-净占比,
        #   大单净流入-净额, 大单净流入-净占比,
        #   中单净流入-净额, 中单净流入-净占比,
        #   小单净流入-净额, 小单净流入-净占比
        main_net = None
        super_large_net = None
        large_net = None
        medium_net = None
        small_net = None

        if super_large_col:
            super_large_net = pd.to_numeric(latest[super_large_col], errors="coerce") / 1e8
        if large_col:
            large_net = pd.to_numeric(latest[large_col], errors="coerce") / 1e8
        if medium_col:
            medium_net = pd.to_numeric(latest[medium_col], errors="coerce") / 1e8
        if small_col:
            small_net = pd.to_numeric(latest[small_col], errors="coerce") / 1e8

        # Try positional fallback for super large / large
        if super_large_net is None or pd.isna(super_large_net):
            if len(df.columns) > 7:
                super_large_net = pd.to_numeric(latest.iloc[7], errors="coerce") / 1e8
        if large_net is None or pd.isna(large_net):
            if len(df.columns) > 9:
                large_net = pd.to_numeric(latest.iloc[9], errors="coerce") / 1e8
        if medium_net is None or pd.isna(medium_net):
            if len(df.columns) > 11:
                medium_net = pd.to_numeric(latest.iloc[11], errors="coerce") / 1e8
        if small_net is None or pd.isna(small_net):
            if len(df.columns) > 13:
                small_net = pd.to_numeric(latest.iloc[13], errors="coerce") / 1e8

        # Calculate main force = 超大单 + 大单
        main_net = 0.0
        if super_large_net is not None and not pd.isna(super_large_net):
            main_net += super_large_net
        if large_net is not None and not pd.isna(large_net):
            main_net += large_net

        # Calculate retail = 中单 + 小单
        retail_net = 0.0
        if medium_net is not None and not pd.isna(medium_net):
            retail_net += medium_net
        if small_net is not None and not pd.isna(small_net):
            retail_net += small_net

        result.detail = {
            "data_source": "akshare_eastmoney",
            "main_force_net_亿": round(main_net, 2),
            "retail_net_亿": round(retail_net, 2),
            "super_large_net_亿": round(super_large_net, 2) if super_large_net is not None and not pd.isna(super_large_net) else None,
            "large_net_亿": round(large_net, 2) if large_net is not None and not pd.isna(large_net) else None,
            "medium_net_亿": round(medium_net, 2) if medium_net is not None and not pd.isna(medium_net) else None,
            "small_net_亿": round(small_net, 2) if small_net is not None and not pd.isna(small_net) else None,
        }

        # Determine signal
        if main_net > flow_threshold_亿 and retail_net < 0:
            result.triggered = True
            result.direction = "bullish"
            result.strength = round(min(1.0, main_net / 200), 4)
            result.summary = (
                f"主力净流入{main_net:.0f}亿，散户净流出{abs(retail_net):.0f}亿，"
                f"聪明钱逆势进场，主力与散户背离偏多"
            )
        elif main_net > flow_threshold_亿:
            result.triggered = True
            result.direction = "bullish"
            result.strength = round(min(1.0, main_net / 200), 4)
            result.summary = f"主力资金净流入{main_net:.0f}亿（超大单+大单），市场资金面偏多"
        elif main_net < -flow_threshold_亿 and retail_net > 0:
            result.triggered = True
            result.direction = "bearish"
            result.strength = round(max(-1.0, main_net / 200), 4)
            result.summary = (
                f"主力净流出{abs(main_net):.0f}亿，散户净流入{retail_net:.0f}亿，"
                f"主力撤退散户接盘，典型偏空分布"
            )
        elif main_net < -flow_threshold_亿:
            result.triggered = True
            result.direction = "bearish"
            result.strength = round(max(-1.0, main_net / 200), 4)
            result.summary = f"主力资金净流出{abs(main_net):.0f}亿（超大单+大单），市场资金面偏空"
        else:
            result.summary = (
                f"主力净流{main_net:+.0f}亿，散户净流{retail_net:+.0f}亿，"
                f"主力资金动向不显著（|主力|<{flow_threshold_亿:.0f}亿）"
            )

    except Exception as e:
        logger.warning("Main fund flow detector failed: %s", e)
        result.summary = "主力资金数据API不可用"
        result.detail = {"data_source": "akshare_eastmoney"}

    return result


def detect_lhb_activity(config: dict) -> SignalResult:
    """Detect limit-board (龙虎榜) activity as a sentiment indicator.

    Uses ak.stock_lhb_detail_em() to get daily limit-board stock details.
    Analyzes net buy/sell balance across all LHB stocks.

    Rules:
        - Net buy ratio > 0.6 AND buy/sell balance > threshold → bullish
        - Net sell ratio > 0.6 AND sell/buy balance > threshold → bearish
        - Otherwise → neutral
    """
    ms_cfg = config.get("microstructure", {})
    net_buy_ratio_threshold = ms_cfg.get("lhb_net_buy_ratio", 0.55)
    net_amount_threshold_亿 = ms_cfg.get("lhb_net_amount_threshold_亿", 5.0)

    result = SignalResult(
        key="lhb_activity",
        label="龙虎榜活跃度",
        triggered=False,
        strength=0.0,
        direction="neutral",
        summary="",
        detail={"data_source": "akshare_eastmoney"},
    )

    try:
        import akshare as ak
    except ImportError:
        result.summary = "龙虎榜数据不可用（akshare未安装）"
        result.detail = {"data_source": "akshare_eastmoney"}
        return result

    trade_date = config.get("_trade_date", None)
    if trade_date is None:
        result.summary = "无交易日期，跳过龙虎榜检测"
        result.detail = {"data_source": "akshare_eastmoney"}
        return result

    try:
        df = ak.stock_lhb_detail_em(start_date=trade_date, end_date=trade_date)
        if df is None or df.empty:
            result.summary = "龙虎榜数据API返回为空（当日无上榜股票）"
            result.detail = {"data_source": "akshare_eastmoney"}
            return result

        # Resolve key columns (API returns Chinese column names)
        net_amt_col = None
        buy_amt_col = None
        sell_amt_col = None
        for c in df.columns:
            cs = str(c)
            if "净买额" in cs or "NET_AMT" in cs.upper():
                net_amt_col = c
            if "买入金额" in cs or "BUY_AMT" in cs.upper():
                buy_amt_col = c
            if "卖出金额" in cs or "SELL_AMT" in cs.upper():
                sell_amt_col = c

        # Fallback: try positional columns
        if net_amt_col is None and len(df.columns) > 8:
            net_amt_col = df.columns[8]  # BILLBOARD_NET_AMT position
        if buy_amt_col is None and len(df.columns) > 9:
            buy_amt_col = df.columns[9]  # BILLBOARD_BUY_AMT position
        if sell_amt_col is None and len(df.columns) > 10:
            sell_amt_col = df.columns[10]  # BILLBOARD_SELL_AMT position

        total_net = 0.0
        total_buy = 0.0
        total_sell = 0.0
        buy_count = 0
        sell_count = 0
        stock_count = len(df)

        if net_amt_col is not None:
            net_vals = pd.to_numeric(df[net_amt_col], errors="coerce")
            total_net = net_vals.sum() / 1e8  # Convert to 亿
            buy_count = int((net_vals > 0).sum())
            sell_count = int((net_vals < 0).sum())

        if buy_amt_col is not None:
            total_buy = pd.to_numeric(df[buy_amt_col], errors="coerce").sum() / 1e8
        if sell_amt_col is not None:
            total_sell = pd.to_numeric(df[sell_amt_col], errors="coerce").sum() / 1e8

        result.detail = {
            "data_source": "akshare_eastmoney",
            "lhb_stock_count": stock_count,
            "net_buy_count": buy_count,
            "net_sell_count": sell_count,
            "total_net_amt_亿": round(total_net, 2),
            "total_buy_amt_亿": round(total_buy, 2),
            "total_sell_amt_亿": round(total_sell, 2),
        }

        # Determine signal
        if stock_count == 0:
            result.summary = "当日无龙虎榜上榜股票"
            return result

        net_buy_ratio = buy_count / max(1, stock_count)
        net_sell_ratio = sell_count / max(1, stock_count)

        if net_buy_ratio > net_buy_ratio_threshold and total_net > net_amount_threshold_亿:
            result.triggered = True
            result.direction = "bullish"
            result.strength = round(min(1.0, total_net / 50), 4)
            result.summary = (
                f"龙虎榜{stock_count}只股票，{buy_count}只净买入({net_buy_ratio:.0%})，"
                f"总净买入{total_net:.1f}亿，游资活跃偏多"
            )
        elif net_sell_ratio > net_buy_ratio_threshold and total_net < -net_amount_threshold_亿:
            result.triggered = True
            result.direction = "bearish"
            result.strength = round(max(-1.0, total_net / 50), 4)
            result.summary = (
                f"龙虎榜{stock_count}只股票，{sell_count}只净卖出({net_sell_ratio:.0%})，"
                f"总净卖出{abs(total_net):.1f}亿，游资撤离偏空"
            )
        else:
            result.summary = (
                f"龙虎榜{stock_count}只股票，买入{buy_count}只/卖出{sell_count}只，"
                f"净额{total_net:+.1f}亿，多空均衡"
            )

    except Exception as e:
        logger.warning("LHB activity detector failed: %s", e)
        result.summary = "龙虎榜数据API不可用"
        result.detail = {"data_source": "akshare_eastmoney"}

    return result


def detect_nh_nl_breadth(config: dict) -> SignalResult:
    """Detect market breadth from new-high / new-low stock counts.

    Uses ak.stock_a_high_low_statistics(symbol="all") to get daily NH-NL data.
    A classic technical breadth indicator: NH-NL diffusion index.

    Rules:
        - NH/(NH+NL) > 0.7 (20-day) → bullish breadth expansion
        - NL/(NH+NL) > 0.7 (20-day) → bearish breadth contraction
        - 60-day NH-NL ratio provides confirmation
        - Otherwise → neutral
    """
    ms_cfg = config.get("microstructure", {})
    nh_bullish_ratio = ms_cfg.get("nh_nl_bullish_ratio", 0.65)
    nl_bearish_ratio = ms_cfg.get("nh_nl_bearish_ratio", 0.65)

    result = SignalResult(
        key="nh_nl_breadth",
        label="新高新低",
        triggered=False,
        strength=0.0,
        direction="neutral",
        summary="",
        detail={"data_source": "akshare_eastmoney"},
    )

    try:
        import akshare as ak
    except ImportError:
        result.summary = "新高新低数据不可用（akshare未安装）"
        result.detail = {"data_source": "akshare_eastmoney"}
        return result

    try:
        df = ak.stock_a_high_low_statistics(symbol="all")
        if df is None or df.empty:
            result.summary = "新高新低数据API返回为空"
            result.detail = {"data_source": "akshare_eastmoney"}
            return result

        latest = df.iloc[-1]

        # Extract 20-day and 60-day NH/NL counts
        high20 = pd.to_numeric(latest.get("high20", 0), errors="coerce")
        low20 = pd.to_numeric(latest.get("low20", 0), errors="coerce")
        high60 = pd.to_numeric(latest.get("high60", 0), errors="coerce")
        low60 = pd.to_numeric(latest.get("low60", 0), errors="coerce")
        high120 = pd.to_numeric(latest.get("high120", 0), errors="coerce")
        low120 = pd.to_numeric(latest.get("low120", 0), errors="coerce")

        nh_nl_20_total = high20 + low20
        nh_nl_60_total = high60 + low60

        # Compute ratios
        nh20_ratio = high20 / nh_nl_20_total if nh_nl_20_total > 0 else 0.5
        nh60_ratio = high60 / nh_nl_60_total if nh_nl_60_total > 0 else 0.5

        result.detail = {
            "data_source": "akshare_eastmoney",
            "high20": int(high20) if not pd.isna(high20) else 0,
            "low20": int(low20) if not pd.isna(low20) else 0,
            "high60": int(high60) if not pd.isna(high60) else 0,
            "low60": int(low60) if not pd.isna(low60) else 0,
            "high120": int(high120) if not pd.isna(high120) else 0,
            "low120": int(low120) if not pd.isna(low120) else 0,
            "nh_ratio_20d": round(float(nh20_ratio), 3),
            "nh_ratio_60d": round(float(nh60_ratio), 3),
        }

        if nh_nl_20_total == 0:
            result.summary = "新高新低数据全为零（数据异常）"
            return result

        # Signal determination: 20-day is primary, 60-day confirms
        if nh20_ratio > nh_bullish_ratio:
            if nh60_ratio > 0.5:
                result.triggered = True
                result.direction = "bullish"
                result.strength = round(min(1.0, (nh20_ratio - 0.5) * 2.5), 4)
                result.summary = (
                    f"20日新高{int(high20)}只/新低{int(low20)}只(NH比{nh20_ratio:.0%})，"
                    f"60日NH比{nh60_ratio:.0%}确认，市场广度扩张偏多"
                )
            else:
                result.summary = (
                    f"20日新高{int(high20)}只/新低{int(low20)}只(NH比{nh20_ratio:.0%})，"
                    f"但60日NH比{nh60_ratio:.0%}未确认，广度信号存疑"
                )
        elif (1.0 - nh20_ratio) > nl_bearish_ratio:
            if nh60_ratio < 0.5:
                result.triggered = True
                result.direction = "bearish"
                result.strength = round(max(-1.0, -(0.5 - nh20_ratio) * 2.5), 4)
                result.summary = (
                    f"20日新低{int(low20)}只/新高{int(high20)}只(NL比{1-nh20_ratio:.0%})，"
                    f"60日NH比{nh60_ratio:.0%}确认，市场广度收缩偏空"
                )
            else:
                result.summary = (
                    f"20日新低{int(low20)}只/新高{int(high20)}只(NL比{1-nh20_ratio:.0%})，"
                    f"但60日NH比{nh60_ratio:.0%}未确认，广度信号存疑"
                )
        else:
            result.summary = (
                f"20日新高{int(high20)}只/新低{int(low20)}只，"
                f"60日新高{int(high60)}只/新低{int(low60)}只，市场广度中性"
            )

    except Exception as e:
        logger.warning("NH-NL breadth detector failed: %s", e)
        result.summary = "新高新低数据API不可用"
        result.detail = {"data_source": "akshare_eastmoney"}

    return result


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------

_DETECTOR_FUNC_MAP = {
    "advance_decline_ratio": detect_advance_decline_ratio,
    "index_volume_trend": detect_index_volume_trend,
    "turnover_trend": detect_turnover_trend,
    "limit_stocks": detect_limit_stocks,
    "main_fund_flow": detect_main_fund_flow,
    "lhb_activity": detect_lhb_activity,
    "nh_nl_breadth": detect_nh_nl_breadth,
}

MICROSTRUCTURE_REGISTRY = {
    "advance_decline_ratio": {
        "func": detect_advance_decline_ratio,
        "weight": 2,
        "label": "涨跌比",
        "half_life_days": 5,
    },
    "index_volume_trend": {
        "func": detect_index_volume_trend,
        "weight": 2,
        "label": "指数量能趋势",
        "half_life_days": 15,
    },
    "turnover_trend": {
        "func": detect_turnover_trend,
        "weight": 2,
        "label": "成交额趋势",
        "half_life_days": 10,
    },
    "limit_stocks": {
        "func": detect_limit_stocks,
        "weight": 1,
        "label": "涨跌停统计",
        "half_life_days": 3,
    },
    "main_fund_flow": {
        "func": detect_main_fund_flow,
        "weight": 2,
        "label": "主力资金流向",
        "half_life_days": 3,
    },
    "lhb_activity": {
        "func": detect_lhb_activity,
        "weight": 2,
        "label": "龙虎榜活跃度",
        "half_life_days": 3,
    },
    "nh_nl_breadth": {
        "func": detect_nh_nl_breadth,
        "weight": 2,
        "label": "新高新低",
        "half_life_days": 5,
    },
}


# ------------------------------------------------------------------
# Orchestration helpers
# ------------------------------------------------------------------

def run_all_detectors(
    nb_flow: pd.DataFrame | None,
    futures_data: pd.DataFrame | None,
    margin_macro: pd.DataFrame | None,
    config: dict,
    active_detectors: set | None = None,
) -> list[SignalResult]:
    """Run all microstructure detectors.

    Args:
        nb_flow: Northbound flow data (for advance/decline).
        futures_data: Index futures + spot data (for volume trend).
        margin_macro: Aggregate margin data (for turnover).
        config: Full runtime config dict.
        active_detectors: Optional set of detector keys to run. All if None.

    Returns:
        List of SignalResult, one per detector.
    """
    if active_detectors is None:
        active_detectors = set(MICROSTRUCTURE_REGISTRY.keys())

    results: list[SignalResult] = []
    for key in MICROSTRUCTURE_REGISTRY:
        if key not in active_detectors:
            continue
        entry = MICROSTRUCTURE_REGISTRY[key]
        try:
            func = entry["func"]
            # Each detector has a different signature
            if key == "advance_decline_ratio":
                res = func(nb_flow, config)
            elif key == "index_volume_trend":
                res = func(futures_data, config)
            elif key == "turnover_trend":
                res = func(margin_macro, futures_data, config)
            elif key == "limit_stocks":
                res = func(config)
            elif key == "main_fund_flow":
                res = func(config)
            elif key == "lhb_activity":
                res = func(config)
            elif key == "nh_nl_breadth":
                res = func(config)
            else:
                res = func(config)
        except Exception as e:
            logger.warning("Microstructure detector %s failed: %s", key, e)
            res = SignalResult(
                key=key,
                label=entry["label"],
                triggered=False,
                strength=0.0,
                direction="neutral",
                summary=f"检测器异常: {e}",
                detail={"data_source": "unknown"},
            )
        results.append(res)

    return results


def compute_composite_score(signals: list[SignalResult]) -> float:
    """Compute weighted composite score from microstructure signals.

    Weights from MICROSTRUCTURE_REGISTRY.

    Returns:
        Composite score in range [-1, 1].
    """
    if not signals:
        return 0.0

    total_weight = 0.0
    weighted_sum = 0.0
    for s in signals:
        entry = MICROSTRUCTURE_REGISTRY.get(s.key, {})
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
