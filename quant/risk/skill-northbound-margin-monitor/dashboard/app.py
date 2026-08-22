#!/usr/bin/env python
"""Panorama Monitor — Interactive Streamlit Dashboard.

Usage::

    streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

# Ensure project root is importable
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

st.set_page_config(
    page_title="资金面全景监控",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


@st.cache_data(ttl=300)
def list_report_dates(output_dir: str = "output") -> list[str]:
    """Scan output directory for date subdirectories with JSON reports."""
    root = Path(output_dir)
    if not root.exists():
        return []
    dates: list[str] = []
    for child in sorted(root.iterdir(), reverse=True):
        if child.is_dir() and list(child.glob("panorama_monitor_*.json")):
            dates.append(child.name)
    return dates


@st.cache_data(ttl=300)
def load_report(date_str: str, output_dir: str = "output") -> dict | None:
    """Load a JSON report for the given date (YYYY-MM-DD)."""
    root = Path(output_dir) / date_str
    json_files = list(root.glob("panorama_monitor_*.json"))
    if not json_files:
        return None
    try:
        return json.loads(json_files[0].read_text(encoding="utf-8"))
    except Exception:
        return None


def grade_color(grade: str) -> str:
    """Return HTML color for a letter grade."""
    if grade.startswith("A"):
        return "#00c853"
    if grade.startswith("B"):
        return "#64dd17"
    if grade.startswith("C"):
        return "#ffd600"
    if grade.startswith("D"):
        return "#ff9100"
    if grade.startswith("E"):
        return "#ff3d00"
    return "#d50000"


def stars_display(stars: int) -> str:
    """Return a star string for the given 0-5 rating."""
    return "★" * stars + "☆" * (5 - stars)


def signal_color(direction: str) -> str:
    """Return hex color for signal direction."""
    return {"bullish": "#00c853", "bearish": "#ff3d00"}.get(direction, "#9e9e9e")


# ------------------------------------------------------------------
# Main App
# ------------------------------------------------------------------


def main() -> None:
    st.title("📊 A股资金面全景监控")
    st.caption("北向资金 + 融资融券 + 股指期货 | 多维度交叉验证")

    # ── Sidebar ──
    st.sidebar.header("⏱ 选择交易日")
    dates = list_report_dates()
    if not dates:
        st.warning("未找到报告数据，请先运行 `python run.py` 生成报告。")
        st.stop()

    selected_date = st.sidebar.selectbox("交易日", dates, index=0)
    report = load_report(selected_date)

    if report is None:
        st.error(f"无法加载 {selected_date} 的报告数据。")
        st.stop()

    meta = report.get("meta", {})
    composite = report.get("composite", {})
    nb_data = report.get("northbound", {})
    mg_data = report.get("margin", {})
    fut_data = report.get("futures", {})
    pv_data = report.get("price_volume", {})
    micro_data = report.get("microstructure", {})
    res_data = report.get("resonance", {})
    llm_data = report.get("llm", {})
    industry = report.get("industry_ranking", [])
    risk_data = report.get("risk_level", {})
    prov = report.get("provenance", {})

    # ── Hero Section ──
    score = composite.get("score", 50)
    grade = composite.get("grade", "C")
    label = composite.get("label", "")

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### 数据时间")
    st.sidebar.text(meta.get("fetch_time", "-"))

    # ── Tab layout ──
    tab_labels = [
        "📋 概览", "🟢 北向", "💰 融资", "📈 期货",
        "📉 量价", "🔬 微观", "🔄 共振", "🤖 AI研判",
        "🏭 板块", "⚠️ 风险", "🔍 溯源",
    ]
    tabs = st.tabs(tab_labels)

    # ── Tab 0: Overview ──
    with tabs[0]:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("综合评分", f"{score:.0f}/100", help=composite.get("summary", ""))
        with col2:
            st.markdown(
                f"<h1 style='color:{grade_color(grade)};text-align:center;margin:0'>{grade}</h1>"
                f"<p style='text-align:center'>{label}</p>",
                unsafe_allow_html=True,
            )
        with col3:
            nb_trig = nb_data.get("triggered_count", 0)
            mg_trig = mg_data.get("triggered_count", 0)
            fut_trig = fut_data.get("triggered_count", 0)
            pv_trig = pv_data.get("triggered_count", 0)
            micro_trig = micro_data.get("triggered_count", 0)
            res_trig = res_data.get("triggered_count", 0)
            total_trig = nb_trig + mg_trig + fut_trig + pv_trig + micro_trig
            st.metric("触发信号", f"{total_trig}")
        with col4:
            if risk_data:
                s = risk_data.get("stars", 0)
                st.markdown(
                    f"<h2 style='text-align:center;color:#ff9100'>{stars_display(s)}</h2>"
                    f"<p style='text-align:center'>{risk_data.get('level', '-')}</p>",
                    unsafe_allow_html=True,
                )

        st.markdown("---")

        # Score breakdown
        st.subheader("分项得分")
        dims = [
            ("北向资金", composite.get("northbound_score", 0)),
            ("融资融券", composite.get("margin_score", 0)),
            ("股指期货", composite.get("futures_score", 0)),
            ("共振背离", composite.get("resonance_score", 0)),
        ]
        cols = st.columns(len(dims))
        for col, (name, val) in zip(cols, dims):
            col.metric(name, f"{val:+.3f}")

        st.markdown("---")
        st.subheader("综合研判")
        st.info(composite.get("summary", "-"))

    # ── Tab 1: Northbound ──
    with tabs[1]:
        st.subheader("北向资金信号")
        nb_signals = nb_data.get("signals", [])
        if nb_signals:
            _render_signal_table(nb_signals)
        else:
            st.info("无北向资金信号数据")

    # ── Tab 2: Margin ──
    with tabs[2]:
        st.subheader("融资融券信号")
        mg_signals = mg_data.get("signals", [])
        if mg_signals:
            _render_signal_table(mg_signals)
        else:
            st.info("无融资融券信号数据")

    # ── Tab 3: Futures ──
    with tabs[3]:
        st.subheader("股指期货信号")
        fut_signals = fut_data.get("signals", [])
        if fut_signals:
            _render_signal_table(fut_signals)
        else:
            st.info("无股指期货信号数据")

    # ── Tab 4: Price-Volume ──
    with tabs[4]:
        st.subheader("量价确认")
        pv_signals = pv_data.get("signals", [])
        if pv_signals:
            _render_signal_table(pv_signals)
        else:
            st.info("无量价确认信号数据")

    # ── Tab 5: Microstructure ──
    with tabs[5]:
        st.subheader("微观结构信号")
        micro_signals = micro_data.get("signals", [])
        if micro_signals:
            _render_signal_table(micro_signals)
        else:
            st.info("无微观结构信号数据")

    # ── Tab 6: Resonance ──
    with tabs[6]:
        st.subheader("共振/背离分析")
        patterns = res_data.get("patterns", [])
        if patterns:
            rows = []
            for p in patterns:
                rows.append({
                    "模式": p.get("label", "-"),
                    "触发": "✅" if p.get("triggered") else "—",
                    "方向": {"bullish": "🟢 看多", "bearish": "🔴 看空", "neutral": "⚪ 中性"}.get(p.get("direction", ""), "-"),
                    "强度": f"{p.get('strength', 0):+.2f}",
                    "解读": p.get("summary", p.get("description", "-")),
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("无共振分析数据")

    # ── Tab 7: AI Analysis ──
    with tabs[7]:
        st.subheader("AI 宏观研判")
        llm_source = llm_data.get("source", "none")
        llm_model = llm_data.get("model", "")
        llm_text = llm_data.get("analysis", "")

        if llm_text:
            if llm_source == "real":
                st.success(f"由 {llm_model} 实时生成")
            elif llm_source == "fallback":
                st.warning("LLM API 不可用，以下为规则引擎生成")
            elif llm_source == "error":
                st.error(f"LLM 分析异常: {llm_text}")
            if llm_source not in ("error",):
                st.markdown(llm_text)
        else:
            st.info("无 AI 分析数据")

    # ── Tab 8: Industry Rankings ──
    with tabs[8]:
        st.subheader("板块资金流向（行业融资暴露排名）")
        if industry:
            import pandas as pd
            df = pd.DataFrame(industry)
            if not df.empty:
                st.caption("Z-score > 0: 行业融资强度高于全市场平均")
                st.bar_chart(df.set_index("industry")["composite_z"], use_container_width=True)
                st.dataframe(
                    df.rename(columns={
                        "rank": "排名", "industry": "行业",
                        "stock_count": "股票数", "avg_balance_亿": "均融资余额(亿)",
                        "avg_buy_亿": "均融资买入(亿)", "composite_z": "综合Z",
                    }),
                    hide_index=True, use_container_width=True,
                )
        else:
            st.info("无行业排名数据")

    # ── Tab 9: Risk ──
    with tabs[9]:
        st.subheader("综合风险评估")
        if risk_data:
            s = risk_data.get("stars", 0)
            level = risk_data.get("level", "-")
            rs = risk_data.get("score", 0)

            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(
                    f"<h1 style='text-align:center;color:#ff9100'>{stars_display(s)}</h1>"
                    f"<h3 style='text-align:center'>{level} ({rs:.0f}/100)</h3>",
                    unsafe_allow_html=True,
                )
            with col2:
                factors = risk_data.get("factors", {})
                factor_df = {
                    "因子": ["看空信号比例", "看空信号强度", "共振背离风险", "融资买入热度"],
                    "权重": ["35%", "25%", "20%", "20%"],
                    "得分": [
                        f"{factors.get('bearish_ratio', 0)*100:.0f}%",
                        f"{factors.get('bearish_intensity', 0)*100:.0f}%",
                        f"{factors.get('resonance', 0)*100:.0f}%",
                        f"{factors.get('margin_danger', 0)*100:.0f}%",
                    ],
                }
                import pandas as pd
                st.dataframe(pd.DataFrame(factor_df), hide_index=True, use_container_width=True)

            details = risk_data.get("details", [])
            if details:
                st.markdown("#### 触发风险信号")
                for d in details:
                    st.markdown(f"- {d}")
        else:
            st.info("无风险评估数据")

    # ── Tab 10: Provenance ──
    with tabs[10]:
        st.subheader("数据溯源")
        if prov:
            source_labels = {
                "pandadata": "✅ Pandadata (实时)",
                "eastmoney": "✅ 东方财富 (实时)",
                "akshare_shenwan": "✅ AKShare (申万)",
                "csi300_index": "✅ CSI300指数",
                "nb_flow+futures+margin": "✅ 北向+期货+融资",
                "none": "⚠️ 无数据",
                "degraded": "⚠️ 降级模式",
            }
            rows = []
            for key, label in [
                ("northbound_summary", "北向资金汇总"),
                ("margin_detail", "融资融券明细"),
                ("margin_macro", "融资融券宏观"),
                ("futures", "股指期货"),
                ("stock_info", "股票信息"),
                ("shenwan", "申万行业分类"),
                ("price_volume", "量价确认"),
                ("microstructure", "微观结构"),
            ]:
                raw = prov.get(key, "none")
                display = source_labels.get(raw, raw)
                rows.append({"数据类别": label, "状态": display})
            import pandas as pd
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.info("无溯源数据")


def _render_signal_table(signals: list[dict]) -> None:
    """Render a consistent signal summary table."""
    rows = []
    for s in signals:
        rows.append({
            "指标": s.get("label", "-"),
            "触发": "✅ 触发" if s.get("triggered") else "—",
            "方向": {"bullish": "🟢 看多", "bearish": "🔴 看空", "neutral": "⚪ 中性"}.get(s.get("direction", ""), "-"),
            "强度": f"{s.get('strength', 0):+.2f}",
            "解读": s.get("summary", "-"),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
