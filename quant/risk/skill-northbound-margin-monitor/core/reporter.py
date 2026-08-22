"""Report generator: Markdown daily report + JSON structured output.

Produces a 7-section Markdown report and a companion JSON file with
full signal breakdown for auditability and downstream consumption.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from ._types import SignalResult
from .resonance import ResonanceResult
from .scorer import CompositeScore, RiskLevel

logger = logging.getLogger(__name__)


def _safe_fmt(val, fmt: str = ".2f") -> str:
    """Safely format a numeric value, returning '-' on NaN/None."""
    if val is None:
        return "-"
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return "-"
        return f"{f:{fmt}}"
    except (ValueError, TypeError):
        return str(val)


def _provenance_label(source: str) -> str:
    """Map df.attrs source tag to Chinese provenance label."""
    labels = {
        "pandadata": "Pandadata (实时)",
        "eastmoney": "东方财富 (实时)",
        "degraded": "降级模式 (部分数据不可用)",
        "unknown": "未知来源",
        "none": "无数据",
    }
    return labels.get(source, source)


_SOURCE_ICONS = {
    "direct_nb": "📡北向直",
    "market_value_diff": "📊市值差",
    "csi300_proxy": "📈CSI300",
    "nb_flow_accumulated": "📋流累积",
    "pandadata": "🏢Panda",
    "akshare_eastmoney": "🌐东方财富",
    "akshare_sina": "🌐新浪",
    "akshare_realtime": "🌐AK实时",
    "none": "—",
    "unknown": "❓",
}


def _source_icon(source_label: str) -> str:
    """Return a compact source icon/label for table display."""
    if not source_label:
        return "❓"
    return _SOURCE_ICONS.get(source_label, source_label[:10])


# ------------------------------------------------------------------
# Markdown report
# ------------------------------------------------------------------

def _find_previous_report(current_date: str, output_dir: str | Path = "output") -> dict | None:
    """Find the most recent previous trading day's JSON report.

    Scans output directory for date subdirectories before *current_date*,
    sorted descending, and returns the first valid JSON report found.

    Args:
        current_date: Trading day in YYYYMMDD format.
        output_dir: Root output directory to scan.

    Returns:
        Parsed JSON dict of the previous report, or None if none found.
    """
    out_root = Path(output_dir)
    if not out_root.exists():
        return None

    current_dt = datetime.strptime(current_date, "%Y%m%d")

    # Collect all date dirs that contain a JSON report
    candidates: list[tuple[datetime, Path]] = []
    for child in out_root.iterdir():
        if not child.is_dir():
            continue
        try:
            child_dt = datetime.strptime(child.name, "%Y-%m-%d")
        except ValueError:
            continue
        if child_dt >= current_dt:
            continue
        json_files = list(child.glob("panorama_monitor_*.json"))
        if json_files:
            candidates.append((child_dt, json_files[0]))

    if not candidates:
        return None

    # Get most recent previous date
    candidates.sort(key=lambda x: x[0], reverse=True)
    _, json_path = candidates[0]

    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Could not read previous report: %s", json_path)
        return None


def _generate_historical_comparison(
    current_composite,
    nb_signals: list,
    margin_signals: list,
    futures_signals: list,
    resonance_results: list,
    previous_report: dict | None,
) -> str:
    """Generate a Markdown historical comparison table.

    Args:
        current_composite: CompositeScore from the current run.
        nb_signals: Current northbound signal results.
        margin_signals: Current margin signal results.
        futures_signals: Current futures signal results.
        resonance_results: Current resonance pattern results.
        previous_report: Parsed JSON dict from the previous report.

    Returns:
        Markdown string for the historical comparison section.
    """
    if previous_report is None:
        return ""

    lines: list[str] = []
    add = lines.append

    prev_meta = previous_report.get("meta", {})
    prev_composite = previous_report.get("composite", {})
    prev_nb = previous_report.get("northbound", {})
    prev_mg = previous_report.get("margin", {})
    prev_fut = previous_report.get("futures", {})
    prev_res = previous_report.get("resonance", {})

    prev_date = prev_meta.get("trade_date", "未知")
    try:
        prev_date_display = datetime.strptime(prev_date, "%Y%m%d").strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        prev_date_display = str(prev_date)

    add(f"*对比基准: {prev_date_display}*")
    add("")

    def _delta_str(cur: float, prev_val: float, fmt_spec: str = ".2f") -> str:
        """Format delta with ▲/▼ indicator."""
        delta = cur - prev_val
        arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "─")
        return f"{delta:{fmt_spec}} {arrow}"

    add("| 指标 | 上一交易日 | 本日 | 变化 |")
    add("|------|-----------|------|------|")

    # Composite score
    prev_score = prev_composite.get("score", 50.0)
    prev_grade = prev_composite.get("grade", "C")
    cur_score = current_composite.score
    cur_grade = current_composite.grade
    add(f"| 综合得分 | {prev_score:.0f} ({prev_grade}) | {cur_score:.0f} ({cur_grade}) | {_delta_str(cur_score, prev_score, '.0f')} |")

    # Northbound score
    prev_nb_score = prev_composite.get("northbound_score", 0.0)
    cur_nb_score = current_composite.northbound_score
    add(f"| 北向得分 | {prev_nb_score:+.3f} | {cur_nb_score:+.3f} | {_delta_str(cur_nb_score, prev_nb_score, '+.3f')} |")

    # Margin score
    prev_mg_score = prev_composite.get("margin_score", 0.0)
    cur_mg_score = current_composite.margin_score
    add(f"| 融资得分 | {prev_mg_score:+.3f} | {cur_mg_score:+.3f} | {_delta_str(cur_mg_score, prev_mg_score, '+.3f')} |")

    # Futures score
    prev_fut_score = prev_composite.get("futures_score")
    if prev_fut_score is not None:
        cur_fut_score = current_composite.futures_score
        add(f"| 期货得分 | {prev_fut_score:+.3f} | {cur_fut_score:+.3f} | {_delta_str(cur_fut_score, prev_fut_score, '+.3f')} |")

    # Resonance score
    prev_res_score = prev_composite.get("resonance_score", 0.0)
    cur_res_score = current_composite.resonance_score
    add(f"| 共振得分 | {prev_res_score:+.3f} | {cur_res_score:+.3f} | {_delta_str(cur_res_score, prev_res_score, '+.3f')} |")

    # Triggered signals comparison
    cur_nb_trig = sum(1 for s in nb_signals if s.triggered)
    cur_mg_trig = sum(1 for s in margin_signals if s.triggered)
    cur_fut_trig = sum(1 for s in futures_signals if s.triggered)
    cur_res_trig = sum(1 for r in resonance_results if r.triggered)

    prev_nb_trig = prev_nb.get("triggered_count", 0)
    prev_mg_trig = prev_mg.get("triggered_count", 0)
    prev_fut_trig = prev_fut.get("triggered_count", 0)
    prev_res_trig = prev_res.get("triggered_count", 0)

    def _count_delta(cur_cnt: int, prev_cnt: int) -> str:
        delta = cur_cnt - prev_cnt
        if delta > 0:
            return f"+{delta} ▲"
        elif delta < 0:
            return f"{delta} ▼"
        return "0 ─"

    nb_total = len(nb_signals)
    mg_total = len(margin_signals)
    fut_total = len(futures_signals)
    res_total = len(resonance_results)
    add(f"| 北向触发数 | {prev_nb_trig}/{nb_total} | {cur_nb_trig}/{nb_total} | {_count_delta(cur_nb_trig, prev_nb_trig)} |")
    add(f"| 融资触发数 | {prev_mg_trig}/{mg_total} | {cur_mg_trig}/{mg_total} | {_count_delta(cur_mg_trig, prev_mg_trig)} |")
    add(f"| 期货触发数 | {prev_fut_trig}/{fut_total} | {cur_fut_trig}/{fut_total} | {_count_delta(cur_fut_trig, prev_fut_trig)} |")
    add(f"| 共振触发数 | {prev_res_trig}/{res_total} | {cur_res_trig}/{res_total} | {_count_delta(cur_res_trig, prev_res_trig)} |")

    add("")
    add("*注: 历史对比基于前一交易日的 JSON 报告数据*")
    add("")

    return "\n".join(lines)


def generate_markdown_report(
    trade_date: str,
    nb_signals: list[SignalResult],
    margin_signals: list[SignalResult],
    resonance_results: list[ResonanceResult],
    composite: CompositeScore,
    nb_summary: pd.DataFrame,
    margin_detail: pd.DataFrame,
    margin_macro: pd.DataFrame,
    top_margin_balance: pd.DataFrame,
    top_margin_buy: pd.DataFrame,
    stock_info: pd.DataFrame,
    fetch_time: str,
    config: dict,
    llm_analysis: str = "",
    llm_source: str = "none",
    llm_model: str = "",
    futures_signals: list[SignalResult] | None = None,
    futures_data: pd.DataFrame | None = None,
    industry_ranking: pd.DataFrame | None = None,
    previous_report: dict | None = None,
    pv_signals: list[SignalResult] | None = None,
    micro_signals: list[SignalResult] | None = None,
    risk_level: RiskLevel | None = None,
) -> str:
    """Generate the full Markdown daily report.

    Args:
        trade_date: Trading day in YYYYMMDD format.
        nb_signals: All northbound signal results.
        margin_signals: All margin signal results.
        resonance_results: All resonance/divergence results.
        composite: Composite scoring result.
        nb_summary: Northbound daily summary DataFrame.
        margin_detail: Per-stock margin DataFrame.
        margin_macro: Aggregate margin history DataFrame.
        top_margin_balance: Top stocks by margin balance.
        top_margin_buy: Top stocks by margin buy amount.
        stock_info: Stock detail info DataFrame.
        fetch_time: ISO timestamp of data fetch.
        config: Full runtime config dict.
        futures_signals: Futures signal results (optional).
        futures_data: Index futures daily data (optional).

    Returns:
        Markdown report string.
    """
    if futures_signals is None:
        futures_signals = []
    if futures_data is None:
        futures_data = pd.DataFrame()
    if pv_signals is None:
        pv_signals = []
    pv_composite_val = pv_composite_score_val = 0.0
    if pv_signals:
        total_w = 0.0
        weighted_s = 0.0
        for s in pv_signals:
            w = 1 if s.key != "index_momentum" else 2
            weighted_s += s.strength * w
            total_w += w
        if total_w > 0:
            pv_composite_val = round(weighted_s / total_w, 4)

    if micro_signals is None:
        micro_signals = []
    micro_composite_val = 0.0
    if micro_signals:
        total_w = 0.0
        weighted_s = 0.0
        for s in micro_signals:
            w = s.weight if hasattr(s, 'weight') else 1
            weighted_s += s.strength * w
            total_w += w
        if total_w > 0:
            micro_composite_val = round(weighted_s / total_w, 4)

    dt = datetime.strptime(trade_date, "%Y%m%d")
    date_display = dt.strftime("%Y-%m-%d")

    lines: list[str] = []
    add = lines.append  # shorthand (avoid _ to prevent rebind in loops)

    # ── Header ──
    add(f"# 北向资金 + 融资融券全景监控 — {date_display}")
    add("")
    add(f"**生成时间**: {fetch_time} | **综合评分**: {composite.score:.0f}/100 ({composite.grade} — {composite.label})")
    add("")
    add("---")
    add("")

    # ── 1. Northbound overview ──
    add("## 一、北向资金概览")
    add("")

    nb_triggered = [s for s in nb_signals if s.triggered]
    nb_bullish = [s for s in nb_signals if s.direction == "bullish"]
    nb_bearish = [s for s in nb_signals if s.direction == "bearish"]

    add("| 指标 | 信号 | 方向 | 强度 | 来源 | 解读 |")
    add("|------|------|------|------|------|------|")
    for s in nb_signals:
        direction_icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(s.direction, "⚪")
        triggered_mark = "**触发**" if s.triggered else "未触发"
        src = _source_icon(s.detail.get("data_source", ""))
        add(f"| {s.label} | {triggered_mark} | {direction_icon} | {s.strength:+.2f} | {src} | {s.summary} |")
    add("")
    add(f"**北向综合评分**: {composite.northbound_score:+.3f} | "
      f"触发信号: {len(nb_triggered)}/{len(nb_signals)} | "
      f"看多: {len(nb_bullish)} | 看空: {len(nb_bearish)}")
    add("")

    # Northbound data summary
    if not nb_summary.empty:
        add("### 北向资金数据摘要")
        add("")
        mv_col = None
        for c in ["market_value", "持股市值"]:
            if c in nb_summary.columns:
                mv_col = c
                break
        net_col = None
        for c in ["net_buy_amount", "净买入", "资金净流入"]:
            if c in nb_summary.columns:
                net_col = c
                break

        mv_data_usable = False
        if mv_col is not None:
            recent_mv = pd.to_numeric(nb_summary[mv_col].tail(10), errors="coerce")
            mv_data_usable = (recent_mv > 0).sum() >= 3
        if mv_data_usable and mv_col is not None:
            recent = pd.to_numeric(nb_summary[mv_col], errors="coerce").dropna()
            if len(recent) >= 2:
                latest_mv = recent.iloc[-1]
                prev_mv = recent.iloc[-6] if len(recent) >= 6 else recent.iloc[0]
                chg = (latest_mv - prev_mv) / prev_mv * 100 if prev_mv != 0 else 0
                add(f"- 最新持仓市值: {latest_mv/1e8:.0f} 亿元")
                add(f"- 5日市值变动: {chg:+.2f}%")
        else:
            add("- 持仓市值: 近期数据不可用")

        net_data_usable = False
        if net_col is not None:
            recent_net = pd.to_numeric(nb_summary[net_col].tail(10), errors="coerce")
            net_data_usable = recent_net.notna().sum() >= 3
        if net_data_usable and net_col is not None:
            recent_net = pd.to_numeric(nb_summary[net_col], errors="coerce").tail(5)
            net_5d = recent_net.sum()
            add(f"- 近5日净买入合计: {net_5d/1e8:+.1f} 亿元")
        elif not mv_data_usable:
            add("- 净买入数据: 近期不可用（使用替代指标估算）")
        add("")

    add("---")
    add("")

    # ── 2. Margin overview ──
    add("## 二、融资融券概览")
    add("")

    mg_triggered = [s for s in margin_signals if s.triggered]
    mg_bullish = [s for s in margin_signals if s.direction == "bullish"]
    mg_bearish = [s for s in margin_signals if s.direction == "bearish"]

    add("| 指标 | 信号 | 方向 | 强度 | 来源 | 解读 |")
    add("|------|------|------|------|------|------|")
    for s in margin_signals:
        direction_icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(s.direction, "⚪")
        triggered_mark = "**触发**" if s.triggered else "未触发"
        src = _source_icon(s.detail.get("data_source", ""))
        add(f"| {s.label} | {triggered_mark} | {direction_icon} | {s.strength:+.2f} | {src} | {s.summary} |")
    add("")
    add(f"**融资综合评分**: {composite.margin_score:+.3f} | "
      f"触发信号: {len(mg_triggered)}/{len(margin_signals)} | "
      f"看多: {len(mg_bullish)} | 看空: {len(mg_bearish)}")
    add("")

    # Margin macro summary
    if not margin_macro.empty:
        add("### 融资融券宏观数据")
        add("")
        # Show latest date's aggregate values, not all-history sum
        date_col = "date" if "date" in margin_macro.columns else "日期"
        if date_col in margin_macro.columns:
            latest_date = margin_macro[date_col].max()
            latest_data = margin_macro[margin_macro[date_col] == latest_date]
        else:
            latest_data = margin_macro

        for label, col_candidates in [
            ("融资余额", ["margin_balance", "融资余额"]),
            ("融券余额", ["short_balance", "融券余额"]),
            ("融资买入额", ["buy_on_margin_value", "融资买入额"]),
        ]:
            col = None
            for c in col_candidates:
                if c in latest_data.columns:
                    col = c
                    break
            if col is not None:
                total = pd.to_numeric(latest_data[col], errors="coerce").sum()
                if total > 0:
                    add(f"- {label}: {total/1e8:.0f} 亿元")
        add("")

    # Top margin stocks
    if not top_margin_balance.empty:
        add("### 融资余额 TOP10")
        add("")
        add("| 排名 | 代码 | 名称 | 行业 | 融资余额(亿) |")
        add("|------|------|------|------|-------------|")
        for _, row in top_margin_balance.head(10).iterrows():
            bal = float(row.get("margin_balance", 0)) / 1e8
            add(f"| {int(row['rank'])} | {row['symbol']} | {row.get('name', '-')} | {row.get('industry', '-')} | {bal:.1f} |")
        add("")

    if not top_margin_buy.empty:
        add("### 融资买入 TOP10")
        add("")
        add("| 排名 | 代码 | 名称 | 行业 | 融资买入(亿) |")
        add("|------|------|------|------|-------------|")
        for _, row in top_margin_buy.head(10).iterrows():
            buy = float(row.get("margin_buy", 0)) / 1e8
            add(f"| {int(row['rank'])} | {row['symbol']} | {row.get('name', '-')} | {row.get('industry', '-')} | {buy:.1f} |")
        add("")

    # ── 2.5. Futures overview ──
    if futures_signals:
        add("---")
        add("")
        add("## 三、股指期货信号")
        add("")

        f_triggered = [s for s in futures_signals if s.triggered]
        f_bullish = [s for s in futures_signals if s.direction == "bullish"]
        f_bearish = [s for s in futures_signals if s.direction == "bearish"]

        add("| 指标 | 信号 | 方向 | 强度 | 来源 | 解读 |")
        add("|------|------|------|------|------|------|")
        for s in futures_signals:
            direction_icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(s.direction, "⚪")
            triggered_mark = "**触发**" if s.triggered else "未触发"
            src = _source_icon(s.detail.get("data_source", ""))
            add(f"| {s.label} | {triggered_mark} | {direction_icon} | {s.strength:+.2f} | {src} | {s.summary} |")
        add("")
        add(f"**期货综合评分**: {composite.futures_score:+.3f} | "
            f"触发信号: {len(f_triggered)}/3 | "
            f"看多: {len(f_bullish)} | 看空: {len(f_bearish)}")
        add("")

        # Futures data summary
        if not futures_data.empty:
            add("### 期货数据摘要")
            add("")
            idx_col = None
            for c in ["index_name", "指数名称", "contract", "合约"]:
                if c in futures_data.columns:
                    idx_col = c
                    break
            date_col = None
            for c in ["date", "日期"]:
                if c in futures_data.columns:
                    date_col = c
                    break
            if idx_col is not None:
                for name, group in futures_data.groupby(idx_col):
                    if len(group) > 0:
                        last = group.sort_values(date_col).iloc[-1] if date_col else group.iloc[-1]
                        close = float(last.get("close", 0))
                        oi = float(last.get("open_interest", 0))
                        add(f"- {name}: 收盘 {close:.1f} | 持仓 {oi/10000:.0f}万手")
                add("")

    add("---")
    add("")

    # ── 3. Resonance analysis ──
    add("## 四、共振/背离分析")
    add("")

    triggered_resonance = [r for r in resonance_results if r.triggered]
    if triggered_resonance:
        for r in resonance_results:
            if r.triggered:
                icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(r.direction, "⚪")
                add(f"### {icon} {r.label}")
                add("")
                add(f"**强度**: {r.strength:+.3f}")
                add("")
                add(f"{r.description}")
                add("")
    else:
        add("*无共振/背离信号触发*")
        add("")
        add(f"共振评分: {composite.resonance_score:+.3f}")
        add("")

    add("---")
    add("")

    # ── 4.5. Price-volume confirmation ──
    if pv_signals:
        add("## 五、量价确认")
        add("")

        pv_triggered_list = [s for s in pv_signals if s.triggered]
        pv_bullish_list = [s for s in pv_signals if s.direction == "bullish"]
        pv_bearish_list = [s for s in pv_signals if s.direction == "bearish"]

        add("| 指标 | 信号 | 方向 | 强度 | 来源 | 解读 |")
        add("|------|------|------|------|------|------|")
        for s in pv_signals:
            direction_icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(s.direction, "⚪")
            triggered_mark = "**触发**" if s.triggered else "未触发"
            src = _source_icon(s.detail.get("data_source", ""))
            add(f"| {s.label} | {triggered_mark} | {direction_icon} | {s.strength:+.2f} | {src} | {s.summary} |")
        add("")
        add(f"**量价综合评分**: {pv_composite_val:+.3f} | "
            f"触发信号: {len(pv_triggered_list)}/2 | "
            f"看多: {len(pv_bullish_list)} | 看空: {len(pv_bearish_list)}")
        add("")

    # ── 4.6. Microstructure signals ──
    if micro_signals:
        add("## 六、微观结构信号")
        add("")

        micro_triggered_list = [s for s in micro_signals if s.triggered]
        micro_bullish_list = [s for s in micro_signals if s.direction == "bullish"]
        micro_bearish_list = [s for s in micro_signals if s.direction == "bearish"]

        add("| 指标 | 信号 | 方向 | 强度 | 来源 | 解读 |")
        add("|------|------|------|------|------|------|")
        for s in micro_signals:
            direction_icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(s.direction, "⚪")
            triggered_mark = "**触发**" if s.triggered else "未触发"
            src = _source_icon(s.detail.get("data_source", ""))
            add(f"| {s.label} | {triggered_mark} | {direction_icon} | {s.strength:+.2f} | {src} | {s.summary} |")
        add("")
        add(f"**微观结构综合评分**: {micro_composite_val:+.3f} | "
            f"触发信号: {len(micro_triggered_list)}/{len(micro_signals)} | "
            f"看多: {len(micro_bullish_list)} | 看空: {len(micro_bearish_list)}")
        add("")

    add("---")
    add("")

    # ── 5. Sentiment summary ──
    add("## 七、综合情绪评估")
    add("")
    add(f"**综合评分**: {composite.score:.0f}/100 ({composite.grade})")
    add("")
    add(f"**评估**: {composite.label} — {composite.summary}")
    add("")
    add(f"**风险惩罚**: {composite.risk_penalty:.0%}")
    add("")

    add("### 分项得分")
    add("")
    add(f"| 维度 | 得分 | 说明 |")
    add(f"|------|------|------|")
    nb_note = f"{len(nb_triggered)}/{len(nb_signals)} 信号触发"
    if composite.nb_quality_note:
        nb_note += f" ⚠️{composite.nb_quality_note}"
    add(f"| 北向资金 | {composite.northbound_score:+.3f} | {nb_note} |")
    add(f"| 融资融券 | {composite.margin_score:+.3f} | {len(mg_triggered)}/{len(margin_signals)} 信号触发 |")
    if futures_signals:
        f_triggered_count = sum(1 for s in futures_signals if s.triggered)
        add(f"| 股指期货 | {composite.futures_score:+.3f} | {f_triggered_count}/3 信号触发 |")
    if pv_signals:
        pv_trig_count = sum(1 for s in pv_signals if s.triggered)
        add(f"| 量价确认 | {pv_composite_val:+.3f} | {pv_trig_count}/2 信号触发 |")
    if micro_signals:
        micro_trig_count = sum(1 for s in micro_signals if s.triggered)
        add(f"| 微观结构 | {micro_composite_val:+.3f} | {micro_trig_count}/4 信号触发 |")
    add(f"| 共振背离 | {composite.resonance_score:+.3f} | {len(triggered_resonance)}/4 模式触发 |")
    add(f"| **综合** | **{composite.score:.0f}/100** | **{composite.grade}** |")
    add("")

    add("---")
    add("")

    # ── 5.5. Historical comparison ──
    add("## 八、历史对比")
    add("")
    if previous_report is not None:
        comparison = _generate_historical_comparison(
            composite, nb_signals, margin_signals,
            futures_signals, resonance_results, previous_report,
        )
        if comparison:
            add(comparison)
    else:
        add("*无历史数据可比（未找到前一交易日的报告）*")
    add("")
    add("---")
    add("")

    # ── 7. LLM Macro Analysis ──
    if llm_analysis and llm_source not in ("none",):
        add("## 九、AI 宏观研判")
        add("")
        if llm_source == "real":
            add(f"*由 {llm_model or config.get('llm', {}).get('model', 'LLM')} 基于以上全部信号综合分析生成*")
        elif llm_source == "fallback":
            add("*⚠️ LLM API 不可用，以下为规则引擎生成的基础分析*")
        else:
            add(f"*⚠️ LLM 分析异常（{llm_source}）*")
        add("")
        add(llm_analysis)
        add("")

    add("---")
    add("")

    # ── 8. Sector flow (industry-neutral) ──
    add("## 十、板块资金流向")
    add("")

    if industry_ranking is not None and not industry_ranking.empty:
        classification_note = " (申万一级行业分类)" if (
            not stock_info.empty and "sw_industry" in stock_info.columns
        ) else ""
        add(f"**行业融资暴露排名** (市值中性化 Z-score，消除行业规模偏差){classification_note}:")
        add("")
        add("| 排名 | 行业 | 股票数 | 平均融资余额(亿) | 平均融资买入(亿) | Z-余额 | Z-买入 | 综合Z |")
        add("|------|------|--------|-----------------|-----------------|--------|--------|-------|")
        for _, row in industry_ranking.iterrows():
            add(
                f"| {int(row['rank'])} | {row['industry']} | {int(row['stock_count'])} | "
                f"{_safe_fmt(row['avg_balance_亿'], '.1f')} | {_safe_fmt(row['avg_buy_亿'], '.1f')} | "
                f"{_safe_fmt(row['z_balance'], '.2f')} | {_safe_fmt(row['z_buy'], '.2f')} | "
                f"{_safe_fmt(row['composite_z'], '.2f')} |"
            )
        add("")
        add("*Z-score > 0: 行业融资强度高于全市场平均；Z-score < 0: 低于平均。综合Z = (Z-余额 + Z-买入) / 2*")
    elif not stock_info.empty and "industry" in stock_info.columns:
        industry_counts = stock_info["industry"].value_counts()
        add(f"**A股行业分布** (共{len(industry_counts)}个行业):")
        add("")
        add("| 行业 | 上市公司数 |")
        add("|------|-----------|")
        for ind, count in industry_counts.head(10).items():
            add(f"| {ind} | {count} |")
        add("")
        add("*注: 个股融资明细数据不可用，显示基础行业分布。*")
    else:
        add("*行业分类数据不可用*")
    add("")

    add("---")
    add("")

    # ── 11. Comprehensive risk assessment ──
    add("## 十一、综合风险评估")
    add("")

    if risk_level is not None:
        # Star display
        stars_display = "★" * risk_level.stars + "☆" * (5 - risk_level.stars)
        add(f"**风险等级**: {stars_display} ({risk_level.stars}/5 — {risk_level.level})")
        add("")
        add(f"**风险得分**: {risk_level.score:.0f}/100")
        add("")

        # Factor breakdown
        add("### 风险因子分解")
        add("")
        add("| 因子 | 权重 | 得分 | 说明 |")
        add("|------|------|------|------|")
        add(f"| 看空信号比例 | 35% | {risk_level.factor_bearish_ratio:.0%} | 触发信号中看空信号占比 |")
        add(f"| 看空信号强度 | 25% | {risk_level.factor_bearish_intensity:.0%} | 看空信号强度归一化 |")
        add(f"| 共振背离风险 | 20% | {risk_level.factor_resonance:.0%} | 看空共振/背离模式触发比 |")
        add(f"| 融资买入热度 | 20% | {risk_level.factor_margin_danger:.0%} | 融资买入占比过热程度 |")
        add("")

        # Specific risk signals
        if risk_level.details:
            add("### 触发风险信号")
            add("")
            for detail in risk_level.details:
                add(f"- {detail}")
            add("")
        else:
            add("*当前无具体风险信号触发*")
            add("")
    else:
        # Fallback: simple risk compilation
        risks: list[str] = []
        for s in nb_signals:
            if s.triggered and s.direction == "bearish" and abs(s.strength) > 0.5:
                risks.append(f"- [北向] {s.summary}")
        for s in margin_signals:
            if s.triggered and s.direction == "bearish" and abs(s.strength) > 0.5:
                risks.append(f"- [融资] {s.summary}")
        for r in resonance_results:
            if r.triggered and r.direction == "bearish":
                risks.append(f"- [共振] {r.summary}")

        if risks:
            add(f"**共{len(risks)}项风险提示:**")
            add("")
            for risk in risks:
                add(risk)
                add("")
        else:
            add("*当前无重大风险提示*")
            add("")

    add("---")
    add("")

    # ── 10. Data provenance ──
    add("## 十二、数据溯源")
    add("")
    add("| 数据类别 | 数据源 | 状态 |")
    add("|----------|--------|------|")

    nb_source = nb_summary.attrs.get("source", "unknown") if not nb_summary.empty else "none"
    mg_detail_source = margin_detail.attrs.get("source", "unknown") if not margin_detail.empty else "none"
    mg_macro_source = margin_macro.attrs.get("source", "unknown") if not margin_macro.empty else "none"
    info_source = stock_info.attrs.get("source", "unknown") if not stock_info.empty else "none"

    add(f"| 北向资金汇总 | {_provenance_label(nb_source)} | {'✅' if nb_source != 'degraded' else '⚠️'} |")
    add(f"| 融资融券明细 | {_provenance_label(mg_detail_source)} | {'✅' if mg_detail_source != 'degraded' else '⚠️'} |")
    add(f"| 融资融券宏观 | {_provenance_label(mg_macro_source)} | {'✅' if mg_macro_source != 'degraded' else '⚠️'} |")
    add(f"| 股票信息 | {_provenance_label(info_source)} | {'✅' if info_source != 'degraded' else '⚠️'} |")
    sw_available = not stock_info.empty and "sw_industry" in stock_info.columns
    add(f"| 申万行业分类 | {'AKShare (申万)' if sw_available else '不可用'} | {'✅' if sw_available else '⚠️'} |")
    fut_source = futures_data.attrs.get("source", "none") if not futures_data.empty else "none"
    add(f"| 股指期货 | {_provenance_label(fut_source)} | {'✅' if fut_source not in ('degraded', 'none') else '⚠️'} |")
    pv_available = len(pv_signals) > 0
    add(f"| 量价确认 | {'CSI300指数 (北向数据)' if pv_available else '不可用'} | {'✅' if pv_available else '⚠️'} |")
    micro_available = len(micro_signals) > 0
    add(f"| 微观结构 | {'北向+期货+融资数据' if micro_available else '不可用'} | {'✅' if micro_available else '⚠️'} |")
    add("")

    add("---")
    add(f"*报告由 skill-northbound-margin-monitor 自动生成 | {fetch_time}*")

    return "\n".join(lines)


# ------------------------------------------------------------------
# JSON output
# ------------------------------------------------------------------

def _to_native(val):
    """Convert numpy types to native Python for JSON serialization."""
    import numpy as np
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        if np.isnan(val) or np.isinf(val):
            return None
        return float(val)
    if isinstance(val, (np.bool_,)):
        return bool(val)
    if isinstance(val, np.ndarray):
        return [_to_native(v) for v in val.tolist()]
    if isinstance(val, dict):
        return {k: _to_native(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_to_native(v) for v in val]
    return val


def _industry_ranking_to_list(df: pd.DataFrame | None) -> list[dict]:
    """Convert industry ranking DataFrame to list of dicts for JSON."""
    if df is None or df.empty:
        return []
    result = []
    for _, row in df.iterrows():
        result.append({
            "rank": int(row["rank"]),
            "industry": str(row["industry"]),
            "stock_count": int(row["stock_count"]),
            "avg_balance_亿": round(float(row["avg_balance_亿"]), 2),
            "avg_buy_亿": round(float(row["avg_buy_亿"]), 2),
            "z_balance": round(float(row["z_balance"]), 4),
            "z_buy": round(float(row["z_buy"]), 4),
            "composite_z": round(float(row["composite_z"]), 4),
        })
    return result


def generate_json_output(
    trade_date: str,
    nb_signals: list[SignalResult],
    margin_signals: list[SignalResult],
    resonance_results: list[ResonanceResult],
    composite: CompositeScore,
    top_margin_balance: pd.DataFrame,
    top_margin_buy: pd.DataFrame,
    fetch_time: str,
    nb_summary: pd.DataFrame,
    margin_detail: pd.DataFrame,
    margin_macro: pd.DataFrame,
    stock_info: pd.DataFrame,
    config: dict,
    llm_analysis: str = "",
    llm_source: str = "none",
    llm_model: str = "",
    futures_signals: list[SignalResult] | None = None,
    futures_data: pd.DataFrame | None = None,
    industry_ranking: pd.DataFrame | None = None,
    previous_report: dict | None = None,
    pv_signals: list[SignalResult] | None = None,
    micro_signals: list[SignalResult] | None = None,
    risk_level: RiskLevel | None = None,
) -> dict:
    """Generate structured JSON output for downstream consumption.

    Returns:
        dict ready for json.dump().
    """
    if futures_signals is None:
        futures_signals = []
    if futures_data is None:
        futures_data = pd.DataFrame()
    if pv_signals is None:
        pv_signals = []
    if micro_signals is None:
        micro_signals = []
    def signal_to_dict(s):
        return {
            "key": s.key,
            "label": s.label,
            "triggered": s.triggered,
            "strength": s.strength,
            "direction": s.direction,
            "summary": s.summary,
            "detail": s.detail,
        }

    def resonance_to_dict(r):
        return {
            "pattern": r.pattern,
            "label": r.label,
            "triggered": r.triggered,
            "strength": r.strength,
            "direction": r.direction,
            "summary": r.summary,
            "description": r.description,
        }

    # Serialize top-N DataFrames
    top_bal = []
    if not top_margin_balance.empty:
        for _, row in top_margin_balance.head(10).iterrows():
            top_bal.append({
                "rank": int(row["rank"]),
                "symbol": str(row["symbol"]),
                "name": str(row.get("name", "")),
                "industry": str(row.get("industry", "")),
                "margin_balance": float(row.get("margin_balance", 0)),
            })

    top_buy = []
    if not top_margin_buy.empty:
        for _, row in top_margin_buy.head(10).iterrows():
            top_buy.append({
                "rank": int(row["rank"]),
                "symbol": str(row["symbol"]),
                "name": str(row.get("name", "")),
                "industry": str(row.get("industry", "")),
                "margin_buy": float(row.get("margin_buy", 0)),
            })

    # Risk level
    risk_data = None
    if risk_level is not None:
        risk_data = {
            "score": risk_level.score,
            "stars": risk_level.stars,
            "level": risk_level.level,
            "factors": {
                "bearish_ratio": risk_level.factor_bearish_ratio,
                "bearish_intensity": risk_level.factor_bearish_intensity,
                "resonance": risk_level.factor_resonance,
                "margin_danger": risk_level.factor_margin_danger,
            },
            "details": risk_level.details,
        }

    # Provenance
    sw_available = not stock_info.empty and "sw_industry" in stock_info.columns
    pv_available = len(pv_signals) > 0
    provenance = {
        "northbound_summary": nb_summary.attrs.get("source", "none") if not nb_summary.empty else "none",
        "margin_detail": margin_detail.attrs.get("source", "none") if not margin_detail.empty else "none",
        "margin_macro": margin_macro.attrs.get("source", "none") if not margin_macro.empty else "none",
        "futures": futures_data.attrs.get("source", "none") if not futures_data.empty else "none",
        "stock_info": stock_info.attrs.get("source", "none") if not stock_info.empty else "none",
        "shenwan": "akshare_shenwan" if sw_available else "none",
        "price_volume": "csi300_index" if pv_available else "none",
        "microstructure": "nb_flow+futures+margin" if len(micro_signals) > 0 else "none",
    }

    result = {
        "meta": {
            "trade_date": trade_date,
            "fetch_time": fetch_time,
            "generator": "skill-northbound-margin-monitor",
            "version": "1.0.0",
        },
        "composite": {
            "score": composite.score,
            "grade": composite.grade,
            "label": composite.label,
            "northbound_score": composite.northbound_score,
            "margin_score": composite.margin_score,
            "futures_score": composite.futures_score,
            "resonance_score": composite.resonance_score,
            "risk_penalty": composite.risk_penalty,
            "nb_data_quality": composite.nb_data_quality,
            "nb_quality_note": composite.nb_quality_note,
            "summary": composite.summary,
        },
        "northbound": {
            "signals": [signal_to_dict(s) for s in nb_signals],
            "triggered_count": sum(1 for s in nb_signals if s.triggered),
            "bullish_count": sum(1 for s in nb_signals if s.direction == "bullish"),
            "bearish_count": sum(1 for s in nb_signals if s.direction == "bearish"),
        },
        "margin": {
            "signals": [signal_to_dict(s) for s in margin_signals],
            "triggered_count": sum(1 for s in margin_signals if s.triggered),
            "bullish_count": sum(1 for s in margin_signals if s.direction == "bullish"),
            "bearish_count": sum(1 for s in margin_signals if s.direction == "bearish"),
            "top_by_balance": top_bal,
            "top_by_buy": top_buy,
        },
        "futures": {
            "signals": [signal_to_dict(s) for s in futures_signals],
            "triggered_count": sum(1 for s in futures_signals if s.triggered),
            "bullish_count": sum(1 for s in futures_signals if s.direction == "bullish"),
            "bearish_count": sum(1 for s in futures_signals if s.direction == "bearish"),
        },
        "price_volume": {
            "signals": [signal_to_dict(s) for s in pv_signals],
            "triggered_count": sum(1 for s in pv_signals if s.triggered),
            "bullish_count": sum(1 for s in pv_signals if s.direction == "bullish"),
            "bearish_count": sum(1 for s in pv_signals if s.direction == "bearish"),
        },
        "microstructure": {
            "signals": [signal_to_dict(s) for s in micro_signals],
            "triggered_count": sum(1 for s in micro_signals if s.triggered),
            "bullish_count": sum(1 for s in micro_signals if s.direction == "bullish"),
            "bearish_count": sum(1 for s in micro_signals if s.direction == "bearish"),
        },
        "industry_ranking": _industry_ranking_to_list(industry_ranking),
        "resonance": {
            "patterns": [resonance_to_dict(r) for r in resonance_results],
            "triggered_count": sum(1 for r in resonance_results if r.triggered),
        },
        "llm": {
            "source": llm_source,
            "analysis": llm_analysis,
            "model": llm_model or config.get("llm", {}).get("model", "unknown"),
        },
        "risk_level": risk_data,
        "provenance": provenance,
    }

    # Historical comparison
    if previous_report is not None:
        prev_composite = previous_report.get("composite", {})
        prev_nb = previous_report.get("northbound", {})
        prev_mg = previous_report.get("margin", {})
        prev_fut = previous_report.get("futures", {})
        prev_res = previous_report.get("resonance", {})
        prev_meta = previous_report.get("meta", {})

        result["historical_comparison"] = {
            "previous_date": prev_meta.get("trade_date", "unknown"),
            "score_delta": {
                "previous": prev_composite.get("score", 50.0),
                "current": composite.score,
                "change": composite.score - prev_composite.get("score", 50.0),
            },
            "northbound_score_delta": {
                "previous": prev_composite.get("northbound_score", 0.0),
                "current": composite.northbound_score,
                "change": composite.northbound_score - prev_composite.get("northbound_score", 0.0),
            },
            "margin_score_delta": {
                "previous": prev_composite.get("margin_score", 0.0),
                "current": composite.margin_score,
                "change": composite.margin_score - prev_composite.get("margin_score", 0.0),
            },
            "futures_score_delta": {
                "previous": prev_composite.get("futures_score", 0.0),
                "current": composite.futures_score,
                "change": composite.futures_score - prev_composite.get("futures_score", 0.0),
            },
            "resonance_score_delta": {
                "previous": prev_composite.get("resonance_score", 0.0),
                "current": composite.resonance_score,
                "change": composite.resonance_score - prev_composite.get("resonance_score", 0.0),
            },
            "triggered_counts": {
                "northbound": {"previous": prev_nb.get("triggered_count", 0),
                               "current": sum(1 for s in nb_signals if s.triggered)},
                "margin": {"previous": prev_mg.get("triggered_count", 0),
                           "current": sum(1 for s in margin_signals if s.triggered)},
                "futures": {"previous": prev_fut.get("triggered_count", 0),
                            "current": sum(1 for s in futures_signals if s.triggered)},
                "resonance": {"previous": prev_res.get("triggered_count", 0),
                              "current": sum(1 for r in resonance_results if r.triggered)},
            },
        }
    else:
        result["historical_comparison"] = None

    return _to_native(result)


# ------------------------------------------------------------------
# Write output files
# ------------------------------------------------------------------

def write_report(
    trade_date: str,
    markdown: str,
    json_data: dict,
    output_dir: Optional[str | Path] = None,
    config: Optional[dict] = None,
) -> tuple[Path, Path]:
    """Write Markdown and JSON report files to the output directory.

    Output path: ``<output_dir>/YYYY-MM-DD/panorama_monitor_YYYYMMDD.{md,json}``

    Args:
        trade_date: Trading day in YYYYMMDD format.
        markdown: Markdown report string.
        json_data: JSON-serialisable dict.
        output_dir: Override output directory. Defaults to config.output.dir.
        config: Full runtime config dict.

    Returns:
        (md_path, json_path) as Path objects.
    """
    cfg = config or {}
    out_dir = Path(output_dir or cfg.get("output", {}).get("dir", "output"))

    dt = datetime.strptime(trade_date, "%Y%m%d")
    date_dir = out_dir / dt.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)

    base_name = f"panorama_monitor_{trade_date}"

    md_path = date_dir / f"{base_name}.md"
    md_path.write_text(markdown, encoding="utf-8")
    logger.info("Markdown report written: %s", md_path)

    json_path = date_dir / f"{base_name}.json"
    json_path.write_text(
        json.dumps(json_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("JSON report written: %s", json_path)

    return md_path, json_path
