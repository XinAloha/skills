"""Composite scoring engine for the northbound + margin panorama.

Combines northbound signals, margin signals, and resonance patterns
into a single 0–100 capital flow composite score with risk penalty.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CompositeScore:
    """Overall capital flow assessment."""
    score: float              # 0–100 composite score
    grade: str                # A+ to F
    label: str                # Chinese label (极度乐观 ~ 极度悲观)
    northbound_score: float   # -1 to 1
    margin_score: float       # -1 to 1
    futures_score: float      # -1 to 1
    resonance_score: float    # -1 to 1
    risk_penalty: float       # 0–1, higher = more risk
    summary: str
    nb_data_quality: float = 1.0       # 0-1, quality of NB data
    nb_quality_note: str = ""          # Explanation if quality degraded


# ------------------------------------------------------------------
# Composite scoring
# ------------------------------------------------------------------

def compute_capital_flow_score(
    nb_composite: float,
    margin_composite: float,
    resonance_score: float,
    nb_triggered_count: int,
    margin_triggered_count: int,
    resonance_triggered_count: int,
    config: dict,
    futures_composite: float = 0.0,
    futures_triggered_count: int = 0,
    pv_composite: float = 0.0,
    pv_triggered_count: int = 0,
    micro_composite: float = 0.0,
    micro_triggered_count: int = 0,
    max_possible: int = 21,
    nb_data_quality: float = 1.0,
) -> CompositeScore:
    """Compute the 0–100 capital flow composite score.

    Formula:
        base = nb_weight * nb_composite + margin_weight * margin_composite
               + futures_weight * futures_composite + pv_weight * pv_composite
               + micro_weight * micro_composite
        with_resonance = base * (1 + resonance_modifier)
        score_0_100 = (with_resonance + 1) * 50  (map -1..1 → 0..100)
        risk_penalty applied if triggered signals cross danger thresholds

    Args:
        nb_composite: Northbound composite score (-1 to 1).
        margin_composite: Margin composite score (-1 to 1).
        resonance_score: Resonance/divergence score (-1 to 1).
        nb_triggered_count: Number of triggered northbound signals.
        margin_triggered_count: Number of triggered margin signals.
        resonance_triggered_count: Number of triggered resonance patterns.
        config: Full runtime config dict.
        futures_composite: Futures composite score (-1 to 1). Default 0.0.
        futures_triggered_count: Number of triggered futures signals. Default 0.
        pv_composite: Price-volume composite score (-1 to 1). Default 0.0.
        pv_triggered_count: Number of triggered price-volume signals. Default 0.
        micro_composite: Microstructure composite score (-1 to 1). Default 0.0.
        micro_triggered_count: Number of triggered microstructure signals. Default 0.
        max_possible: Total possible triggered signals across all dimensions.
            Computed at call site from signal list lengths. Default 21
            (6 nb + 6 margin + 3 futures + 2 pv + 4 micro).
        nb_data_quality: Northbound data quality score 0.0-1.0 (1.0 = all real,
            0.0 = all proxy). When < 0.5, NB weight is auto-reduced and
            redistributed to other dimensions. Default 1.0.

    Returns:
        CompositeScore with 0–100 score and grade.
    """
    scoring_cfg = config.get("scoring", {})
    nb_weight = scoring_cfg.get("northbound_weight", 0.35)
    margin_weight = scoring_cfg.get("margin_weight", 0.35)
    futures_weight = scoring_cfg.get("futures_weight", 0.17)
    pv_weight = scoring_cfg.get("price_volume_weight", 0.08)
    micro_weight = scoring_cfg.get("microstructure_weight", 0.05)
    risk_threshold = scoring_cfg.get("risk_overheat_threshold", 0.7)

    # ── Adaptive weighting: reduce NB weight when data quality is degraded ──
    quality_threshold = scoring_cfg.get("nb_quality_threshold", 0.5)
    quality_decay = scoring_cfg.get("nb_quality_decay", 0.6)
    nb_quality_note = ""

    if nb_data_quality < quality_threshold:
        # NB data is mostly proxy — reduce its weight
        decay_factor = 1.0 - quality_decay * (1.0 - nb_data_quality / quality_threshold)
        decay_factor = max(0.2, decay_factor)  # Floor: NB weight won't drop below 20% of original
        reduced_nb = nb_weight * (1.0 - decay_factor)
        # Redistribute to other dimensions proportionally
        other_total = margin_weight + futures_weight + pv_weight + micro_weight
        if other_total > 0:
            margin_weight += reduced_nb * (margin_weight / other_total)
            futures_weight += reduced_nb * (futures_weight / other_total)
            pv_weight += reduced_nb * (pv_weight / other_total)
            micro_weight += reduced_nb * (micro_weight / other_total)
        nb_weight *= decay_factor
        nb_quality_note = f" (北向数据质量{nb_data_quality:.0%}，权重自动下调)"

    # Base weighted score (5 dimensions)
    base = (
        nb_weight * nb_composite
        + margin_weight * margin_composite
        + futures_weight * futures_composite
        + pv_weight * pv_composite
        + micro_weight * micro_composite
    )

    # Resonance amplifier (configurable)
    resonance_mod = 0.0
    if resonance_triggered_count > 0:
        strong_threshold = scoring_cfg.get("resonance_strong_threshold", 0.3)
        if resonance_score > strong_threshold:
            resonance_mod = scoring_cfg.get("resonance_boost_strong", 0.15)
        elif resonance_score > 0:
            resonance_mod = scoring_cfg.get("resonance_boost_weak", 0.08)
        elif resonance_score < -strong_threshold:
            resonance_mod = scoring_cfg.get("resonance_dampen_strong", -0.10)
        elif resonance_score < 0:
            resonance_mod = scoring_cfg.get("resonance_dampen_weak", -0.05)

    with_resonance = base * (1.0 + resonance_mod)

    # Clamp to -1..1
    with_resonance = max(-1.0, min(1.0, with_resonance))

    # Map to 0–100
    score_0_100 = round((with_resonance + 1.0) * 50.0, 1)

    # Risk penalty: if many triggered signals all pointing same way,
    # it could indicate overheating or panic.
    # Uses ratio-based thresholds so penalty scales automatically with
    # the number of detectors in the system.
    risk_penalty = 0.0
    total_triggered = (nb_triggered_count + margin_triggered_count
                       + futures_triggered_count + pv_triggered_count
                       + micro_triggered_count)
    # max_possible is passed in from the call site (computed from signal list lengths)
    triggered_ratio = total_triggered / max(1, max_possible)
    high_trig_ratio = scoring_cfg.get("risk_penalty_high_triggered_ratio", 0.38)
    high_amount = scoring_cfg.get("risk_penalty_high_amount", 0.2)
    high_base = scoring_cfg.get("risk_penalty_high_base_threshold", 0.6)
    med_trig_ratio = scoring_cfg.get("risk_penalty_medium_triggered_ratio", 0.28)
    med_amount = scoring_cfg.get("risk_penalty_medium_amount", 0.1)
    med_base = scoring_cfg.get("risk_penalty_medium_base_threshold", 0.5)

    if triggered_ratio >= high_trig_ratio and abs(base) > high_base:
        risk_penalty = high_amount
    elif triggered_ratio >= med_trig_ratio and abs(base) > med_base:
        risk_penalty = med_amount

    if risk_penalty > 0:
        if base > 0:
            score_0_100 = max(0, score_0_100 - risk_penalty * 50)
        else:
            score_0_100 = min(100, score_0_100 + risk_penalty * 50)

    # Assign grade
    grade, label = _assign_grade(score_0_100)

    # Build summary with actionable suggestions (v2.3)
    suggestions = _generate_suggestions(
        score_0_100, grade, nb_composite, margin_composite,
        futures_composite, micro_composite,
    )

    if score_0_100 >= 70:
        summary = f"资金面{label}（{score_0_100:.0f}分），北向+融资双多，做多信号强烈"
    elif score_0_100 >= 55:
        summary = f"资金面{label}（{score_0_100:.0f}分），整体偏多，关注共振信号"
    elif score_0_100 >= 45:
        summary = f"资金面{label}（{score_0_100:.0f}分），多空均衡，等待方向确认"
    elif score_0_100 >= 30:
        summary = f"资金面{label}（{score_0_100:.0f}分），整体偏空，注意风险控制"
    else:
        summary = f"资金面{label}（{score_0_100:.0f}分），北向+融资双空，避险信号强烈"

    # Append suggestions to summary
    if suggestions:
        summary += "\n" + suggestions

    return CompositeScore(
        score=score_0_100,
        grade=grade,
        label=label,
        northbound_score=round(nb_composite, 4),
        margin_score=round(margin_composite, 4),
        futures_score=round(futures_composite, 4),
        resonance_score=round(resonance_score, 4),
        risk_penalty=round(risk_penalty, 4),
        summary=summary,
        nb_data_quality=round(nb_data_quality, 4),
        nb_quality_note=nb_quality_note,
    )


def _assign_grade(score: float) -> tuple[str, str]:
    """Map 0–100 score to grade and Chinese label."""
    if score >= 85:
        return "A+", "极度乐观"
    elif score >= 75:
        return "A", "乐观"
    elif score >= 65:
        return "B+", "偏乐观"
    elif score >= 55:
        return "B", "中性偏多"
    elif score >= 45:
        return "C", "中性"
    elif score >= 35:
        return "D", "中性偏空"
    elif score >= 25:
        return "E", "偏悲观"
    elif score >= 15:
        return "F", "悲观"
    else:
        return "F-", "极度悲观"


def _generate_suggestions(
    score: float,
    grade: str,
    nb_composite: float,
    margin_composite: float,
    futures_composite: float,
    micro_composite: float,
) -> str:
    """Generate actionable observation points based on the composite score.

    These are NOT investment recommendations — they are systematic
    observations about what the score configuration implies for
    portfolio monitoring. All suggestions use cautious language
    ("可关注", "可考虑", "建议观察") and never prescribe specific trades.
    """
    points: list[str] = []

    # ── Score-driven observations ──
    if grade in ("A+", "A"):
        points.append(
            "• 资金面信号偏强，可关注指数ETF或蓝筹股的跟踪机会；"
            "建议结合基本面确认趋势持续性"
        )
    elif grade == "B+":
        points.append(
            "• 资金面温和偏多但未形成强烈共振，可维持现有仓位观察；"
            "等待北向+融资方向一致后再评估加仓"
        )
    elif grade in ("B", "C"):
        points.append(
            "• 多空交织，方向不明确——建议控制仓位、减少频繁操作；"
            "可关注结构性机会（行业中性排名靠前的板块）"
        )
    elif grade in ("D", "E"):
        points.append(
            "• 资金面偏空，建议降低风险暴露、检查持仓集中度；"
            "可关注对冲工具（如股指期货空头、反向ETF）的机会"
        )
    elif grade in ("F", "F-"):
        points.append(
            "• 资金面极度偏空，系统性风险上升——建议大幅降低仓位或空仓观望；"
            "关注融资去杠杆进程是否加速"
        )

    # ── Dimension-specific observations ──
    if nb_composite < -0.3:
        points.append(
            "• 北向信号偏空（使用CSI300代理，注意信号质量有限），"
            "外资流向趋势偏谨慎"
        )
    if margin_composite > 0.4:
        points.append(
            "• 融资信号过热——杠杆率处于历史高位，需警惕去杠杆引发的"
            "负反馈风险"
        )
    if margin_composite < -0.3:
        points.append(
            "• 融资信号偏冷——杠杆资金持续收缩，市场风险偏好低迷"
        )
    if futures_composite < -0.2:
        points.append(
            "• 期货基差偏空——期指贴水扩大，对冲成本和套保需求上升"
        )
    if micro_composite > 0.4:
        points.append(
            "• 微观结构信号转暖——龙虎榜活跃/涨跌比扩大/主力资金流入，"
            "短期情绪边际改善"
        )
    if micro_composite < -0.3:
        points.append(
            "• 微观结构信号偏冷——市场广度收窄/主力资金流出/新高新低比恶化"
        )

    return "\n".join(points) if points else ""


# ------------------------------------------------------------------
# Risk level assessment
# ------------------------------------------------------------------


@dataclass
class RiskLevel:
    """Comprehensive risk assessment (0-5 star scale)."""
    score: float              # 0-100 risk score
    stars: int                # 0-5 star rating (0=low risk, 5=high risk)
    level: str                # Chinese label (低风险/中风险/高风险)
    factor_bearish_ratio: float      # bearish signal ratio contribution
    factor_bearish_intensity: float  # bearish intensity contribution
    factor_resonance: float          # resonance risk contribution
    factor_margin_danger: float      # margin buy danger contribution
    details: list[str]        # specific risk signals found


def compute_risk_level(
    nb_signals: list,
    margin_signals: list,
    futures_signals: list,
    resonance_results: list,
    pv_signals: list | None = None,
    micro_signals: list | None = None,
    margin_macro: pd.DataFrame | None = None,
    config: dict | None = None,
) -> RiskLevel:
    """Compute a 0-5 star comprehensive risk score from all signals.

    Four factors weighted:
      - bearish signal ratio:   35% — how many triggered signals are bearish
      - bearish intensity:      25% — how strong are the bearish signals
      - resonance risk:         20% — bearish resonance/divergence patterns
      - margin buy danger:      20% — margin buy ratio overheating

    Args:
        nb_signals: Northbound signal results.
        margin_signals: Margin signal results.
        futures_signals: Futures signal results.
        resonance_results: Resonance pattern results.
        pv_signals: Price-volume signal results (optional).
        micro_signals: Microstructure signal results (optional).
        margin_macro: Aggregated margin macro data (optional).
        config: Runtime config dict.

    Returns:
        RiskLevel with 0-100 score, 0-5 stars, label, and factor breakdown.
    """
    config = config or {}
    margin_cfg = config.get("margin", {})
    buy_ratio_dangerous = margin_cfg.get("buy_ratio_dangerous", 0.15)
    buy_ratio_hot = margin_cfg.get("buy_ratio_hot", 0.10)

    # Collect all signals
    all_signals = list(nb_signals) + list(margin_signals) + list(futures_signals)
    if pv_signals:
        all_signals.extend(pv_signals)
    if micro_signals:
        all_signals.extend(micro_signals)

    total_triggered = sum(1 for s in all_signals if getattr(s, "triggered", False))
    bearish_triggered = sum(
        1 for s in all_signals
        if getattr(s, "triggered", False) and getattr(s, "direction", "") == "bearish"
    )

    # Factor 1: bearish signal ratio (0-1)
    factor_ratio = bearish_triggered / max(1, total_triggered) if total_triggered > 0 else 0.0

    # Factor 2: bearish intensity (0-1, average |strength| / 3.0, capped at 1.0)
    bearish_strengths = [
        abs(getattr(s, "strength", 0.0))
        for s in all_signals
        if getattr(s, "triggered", False) and getattr(s, "direction", "") == "bearish"
    ]
    factor_intensity = min(1.0, sum(bearish_strengths) / 3.0) if bearish_strengths else 0.0

    # Factor 3: resonance risk (0-1)
    total_resonance = len(resonance_results)
    bearish_resonance = sum(
        1 for r in resonance_results
        if getattr(r, "triggered", False) and getattr(r, "direction", "") == "bearish"
    )
    factor_resonance = bearish_resonance / max(1, total_resonance) if total_resonance > 0 else 0.0

    # Factor 4: margin buy danger (0-1)
    # margin_macro has SH+SZ per date — group by date and sum to get national totals
    factor_margin = 0.0
    if margin_macro is not None and not margin_macro.empty:
        buy_col = None
        bal_col = None
        for col in ["buy_on_margin_value", "融资买入额"]:
            if col in margin_macro.columns:
                buy_col = col
                break
        if "margin_balance" in margin_macro.columns:
            bal_col = "margin_balance"
        elif "融资余额" in margin_macro.columns:
            bal_col = "融资余额"

        if buy_col is not None and bal_col is not None:
            df = margin_macro.copy()
            df["_buy"] = pd.to_numeric(df[buy_col], errors="coerce")
            df["_bal"] = pd.to_numeric(df[bal_col], errors="coerce")
            if "date" in df.columns:
                daily = df.groupby("date", as_index=False).agg(
                    _buy_sum=("_buy", "sum"),
                    _bal_sum=("_bal", "sum"),
                )
                if len(daily) > 0:
                    buy_val = daily["_buy_sum"].iloc[-1]
                    bal_val = daily["_bal_sum"].iloc[-1]
                    buy_ratio = buy_val / max(1, bal_val) if bal_val > 0 else 0
                    if buy_ratio >= buy_ratio_dangerous:
                        factor_margin = 1.0
                    elif buy_ratio >= buy_ratio_hot:
                        factor_margin = 0.5

    # Weighted score (0-100)
    weights = {"ratio": 0.35, "intensity": 0.25, "resonance": 0.20, "margin": 0.20}
    risk_score = round(
        (weights["ratio"] * factor_ratio
         + weights["intensity"] * factor_intensity
         + weights["resonance"] * factor_resonance
         + weights["margin"] * factor_margin) * 100.0,
        1,
    )

    # Stars: 0-5
    stars = round(risk_score / 20.0)
    stars = max(0, min(5, stars))

    if stars <= 1:
        level = "低风险"
    elif stars <= 3:
        level = "中风险"
    else:
        level = "高风险"

    # Collect specific risk signals for display
    details: list[str] = []
    for s in all_signals:
        if getattr(s, "triggered", False) and getattr(s, "direction", "") == "bearish":
            label = getattr(s, "label", "")
            summary = getattr(s, "summary", "")
            if label and summary:
                details.append(f"[{label}] {summary}")

    return RiskLevel(
        score=risk_score,
        stars=stars,
        level=level,
        factor_bearish_ratio=round(factor_ratio, 4),
        factor_bearish_intensity=round(factor_intensity, 4),
        factor_resonance=round(factor_resonance, 4),
        factor_margin_danger=round(factor_margin, 4),
        details=details,
    )


# ------------------------------------------------------------------
# Stock ranking helpers
# ------------------------------------------------------------------

def rank_stocks_by_margin_balance(
    margin_detail: pd.DataFrame,
    stock_info: pd.DataFrame,
    top_n: int = 20,
) -> pd.DataFrame:
    """Rank stocks by margin balance, joining with stock info for names.

    Args:
        margin_detail: Per-stock margin data.
        stock_info: Stock detail info with symbol, name, industry.
        top_n: Number of top stocks to return.

    Returns:
        DataFrame with columns: symbol, name, industry, margin_balance, rank.
    """
    if margin_detail.empty:
        return pd.DataFrame()

    # Resolve columns
    sym_col = None
    bal_col = None
    for c in ["symbol", "股票代码"]:
        if c in margin_detail.columns:
            sym_col = c
            break
    for c in ["margin_balance", "融资余额"]:
        if c in margin_detail.columns:
            bal_col = c
            break

    if sym_col is None or bal_col is None:
        logger.warning("Cannot rank by margin balance: missing columns")
        return pd.DataFrame()

    df = margin_detail.copy()
    df[bal_col] = pd.to_numeric(df[bal_col], errors="coerce")

    # Get latest per symbol
    if "date" in df.columns:
        df = df.sort_values("date")
        df = df.groupby(sym_col).last().reset_index()

    top = df.nlargest(top_n, bal_col)

    result = top[[sym_col, bal_col]].copy()
    result["rank"] = range(1, len(result) + 1)

    # Join with stock_info for names
    if not stock_info.empty:
        info_sym_col = None
        name_col = None
        for c in ["symbol", "股票代码"]:
            if c in stock_info.columns:
                info_sym_col = c
                break
        for c in ["name", "股票名称"]:
            if c in stock_info.columns:
                name_col = c
                break
        if info_sym_col is not None and name_col is not None:
            info_map = stock_info.set_index(info_sym_col)[name_col].to_dict()
            result["name"] = result[sym_col].map(info_map).fillna("")
        else:
            result["name"] = ""
    else:
        result["name"] = ""

    # Add industry if available (prefer Shenwan)
    if not stock_info.empty:
        ind_col_name = "sw_industry" if "sw_industry" in stock_info.columns else "industry"
        if ind_col_name in stock_info.columns:
            ind_col = "symbol" if "symbol" in stock_info.columns else "股票代码"
            if ind_col in stock_info.columns:
                ind_map = stock_info.set_index(ind_col)[ind_col_name].to_dict()
                result["industry"] = result[sym_col].map(ind_map).fillna("")
            else:
                result["industry"] = ""
        else:
            result["industry"] = ""
    else:
        result["industry"] = ""

    # Rename balance column
    result = result.rename(columns={bal_col: "margin_balance", sym_col: "symbol"})
    result = result[["rank", "symbol", "name", "industry", "margin_balance"]]

    return result


def rank_stocks_by_margin_buy(
    margin_detail: pd.DataFrame,
    stock_info: pd.DataFrame,
    top_n: int = 20,
) -> pd.DataFrame:
    """Rank stocks by margin buy amount (当日融资买入额).

    Args:
        margin_detail: Per-stock margin data.
        stock_info: Stock detail info.
        top_n: Number of top stocks to return.

    Returns:
        DataFrame with columns: symbol, name, industry, buy_amount, rank.
    """
    if margin_detail.empty:
        return pd.DataFrame()

    sym_col = None
    buy_col = None
    for c in ["symbol", "股票代码"]:
        if c in margin_detail.columns:
            sym_col = c
            break
    for c in ["buy_on_margin_value", "融资买入额"]:
        if c in margin_detail.columns:
            buy_col = c
            break

    if sym_col is None or buy_col is None:
        logger.warning("Cannot rank by margin buy: missing columns")
        return pd.DataFrame()

    df = margin_detail.copy()
    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce")

    if "date" in df.columns:
        df = df.sort_values("date")
        df = df.groupby(sym_col).last().reset_index()

    top = df.nlargest(top_n, buy_col)
    result = top[[sym_col, buy_col]].copy()
    result["rank"] = range(1, len(result) + 1)

    # Join with stock_info
    if not stock_info.empty:
        info_sym = "symbol" if "symbol" in stock_info.columns else "股票代码"
        info_name = "name" if "name" in stock_info.columns else "股票名称"
        if info_sym in stock_info.columns and info_name in stock_info.columns:
            name_map = stock_info.set_index(info_sym)[info_name].to_dict()
            result["name"] = result[sym_col].map(name_map).fillna("")
        else:
            result["name"] = ""
        if "industry" in stock_info.columns or "sw_industry" in stock_info.columns:
            ind_col_name = "sw_industry" if "sw_industry" in stock_info.columns else "industry"
            ind_map = stock_info.set_index(info_sym)[ind_col_name].to_dict() if info_sym in stock_info.columns else {}
            result["industry"] = result[sym_col].map(ind_map).fillna("")
        else:
            result["industry"] = ""
    else:
        result["name"] = ""
        result["industry"] = ""

    result = result.rename(columns={buy_col: "margin_buy", sym_col: "symbol"})
    result = result[["rank", "symbol", "name", "industry", "margin_buy"]]

    return result


# ------------------------------------------------------------------
# Industry-neutral sector analysis
# ------------------------------------------------------------------


def compute_industry_neutral_ranking(
    margin_detail: pd.DataFrame,
    stock_info: pd.DataFrame,
    top_n: int = 10,
) -> pd.DataFrame:
    """Rank industries by margin exposure, neutralized for industry size.

    Computes per-industry z-scores for margin balance and margin buy,
    then aggregates into an industry-level composite that adjusts for
    the number of stocks in each industry (size-neutral).

    Args:
        margin_detail: Per-stock margin data with margin_balance / buy_on_margin_value.
        stock_info: Stock info with symbol, industry columns.
        top_n: Number of top industries to return.

    Returns:
        DataFrame with columns: industry, stock_count, avg_balance_亿,
        avg_buy_亿, z_balance, z_buy, composite_z, rank.
    """
    if margin_detail.empty or stock_info.empty:
        return pd.DataFrame()

    # Column resolution
    sym_col = None
    bal_col = None
    buy_col = None
    for c in ["symbol", "股票代码"]:
        if c in stock_info.columns and c in margin_detail.columns:
            sym_col = c
            break
    for c in ["margin_balance", "融资余额"]:
        if c in margin_detail.columns:
            bal_col = c
            break
    for c in ["buy_on_margin_value", "融资买入额"]:
        if c in margin_detail.columns:
            buy_col = c
            break

    if sym_col is None or bal_col is None:
        return pd.DataFrame()

    # Get latest per-stock data
    df = margin_detail.copy()
    for col in [bal_col, buy_col] if buy_col else [bal_col]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "date" in df.columns:
        df = df.sort_values("date")
        df = df.groupby(sym_col).last().reset_index()

    # Merge with industry info — prefer Shenwan classification when available
    industry_col_name = "industry"
    if "sw_industry" in stock_info.columns:
        industry_col_name = "sw_industry"
        logger.info("Using Shenwan industry classification for neutral ranking")

    info_cols = [sym_col, industry_col_name]
    # Ensure both columns exist
    info_cols = [c for c in info_cols if c in stock_info.columns]
    if len(info_cols) < 2:
        return pd.DataFrame()

    info_key = "symbol" if "symbol" in stock_info.columns else sym_col
    df = df.merge(
        stock_info[info_cols].rename(columns={info_key: sym_col, industry_col_name: "industry"}),
        on=sym_col, how="left",
    )
    if "industry" not in df.columns:
        return pd.DataFrame()

    df = df.dropna(subset=["industry"])
    df = df[df["industry"] != "未知"]

    # Per-industry aggregates
    industry_stats = df.groupby("industry").agg(
        stock_count=(sym_col, "count"),
        avg_balance_亿=(bal_col, lambda x: x.mean() / 1e8),
        total_balance_亿=(bal_col, lambda x: x.sum() / 1e8),
    ).reset_index()

    if buy_col and buy_col in df.columns:
        buy_stats = df.groupby("industry")[buy_col].agg(
            avg_buy_亿=lambda x: x.mean() / 1e8,
            total_buy_亿=lambda x: x.sum() / 1e8,
        ).reset_index()
        industry_stats = industry_stats.merge(buy_stats, on="industry", how="left")
    else:
        industry_stats["avg_buy_亿"] = 0.0
        industry_stats["total_buy_亿"] = 0.0

    # Z-score normalization (industry-neutral: adjust for size bias)
    for metric in ["avg_balance_亿", "avg_buy_亿"]:
        col = f"z_{metric.replace('avg_', '').replace('_亿', '')}"
        vals = industry_stats[metric].values
        if len(vals) >= 3 and np.std(vals) > 0:
            industry_stats[col] = (vals - np.mean(vals)) / np.std(vals)
        else:
            industry_stats[col] = 0.0

    # Composite z-score (equal weight balance + buy)
    z_balance = industry_stats["z_balance"].fillna(0)
    z_buy = industry_stats["z_buy"].fillna(0)
    industry_stats["composite_z"] = (z_balance + z_buy) / 2.0

    # Rank by composite z
    industry_stats = industry_stats.sort_values("composite_z", ascending=False)
    industry_stats["rank"] = range(1, len(industry_stats) + 1)

    columns = [
        "rank", "industry", "stock_count",
        "avg_balance_亿", "avg_buy_亿",
        "z_balance", "z_buy", "composite_z",
    ]
    return industry_stats.head(top_n)[columns].reset_index(drop=True)
