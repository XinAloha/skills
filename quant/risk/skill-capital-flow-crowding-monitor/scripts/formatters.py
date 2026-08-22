"""formatters.py — CapitalFlowReport 渲染 JSON / 中文文本 / Markdown"""
from __future__ import annotations
import json

_CN = {"margin": "融资融券", "northbound": "北向持股", "block": "大宗交易"}


def to_json(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)


def _strength_tag(s):
    if s is None:
        return "—"
    if s > 0.05:
        return f"+{s:.2f}(净流入)"
    if s < -0.05:
        return f"{s:.2f}(净流出)"
    return f"{s:.2f}(中性)"


def _crowd_tag(c):
    pct = c.get("crowding_pct")
    if pct is None:
        return c.get("level", "—")
    flag = "🔴" if c.get("alert") else ""
    return f"{flag}{pct:.0f}% 分位 · {c.get('level')}"


def to_text(report: dict) -> str:
    L = []
    L.append("=" * 64)
    L.append("A股 跨市场资金面 / 拥挤度监测（两融 + 北向 + 大宗）")
    p = report["params"]
    L.append(f"生成时间: {report['generated_at']}   标的数: {report['universe_size']}   后端: {report['backend']}")
    L.append(f"观察窗口: {p['window_days']}天   拥挤回溯: {p['crowding_lookback']}天   维度: {p['dimensions']}")
    L.append("=" * 64)
    if not report["items"]:
        L.append("（无标的数据）")
    for it in report["items"]:
        crowd = it["crowding"]
        flag = "🔴" if crowd.get("alert") else ("🟢" if it["consensus"].get("is_consensus") else "  ")
        L.append("")
        L.append(f"{flag} {it['symbol']}   综合资金强度 {_strength_tag(it['composite_strength'])}   "
                 f"拥挤度 {_crowd_tag(crowd)}")
        # 三源明细
        for src in ("margin", "northbound", "block"):
            f = it["flows"].get(src)
            if not f:
                continue
            L.append(f"    [{_CN[src]}] 强度 {_strength_tag(f.get('strength'))}  —  {f.get('detail','')}")
        # 共识/背离
        cons = it["consensus"]
        L.append(f"    共识度: {cons.get('consensus_score')}（有效源 {cons.get('active_sources')}）· {cons.get('direction')}")
        for d in cons.get("divergence", []):
            L.append(f"      ↔ 背离: {d}")
        # 拥挤说明
        if crowd.get("note"):
            L.append(f"    拥挤: {crowd.get('note')}")
        # 综合信号
        L.append(f"    信号: {it['signal']}")
    if report.get("degraded_sources"):
        L.append("")
        L.append("⚠️ 数据降级:")
        for s in report["degraded_sources"]:
            L.append(f"    - {s}")
    L.append("")
    L.append("免责声明：三源资金披露有滞后，大宗折溢价为自算，拥挤度分位需足够历史窗口。仅供研究参考，不构成投资建议。")
    return "\n".join(L)


def to_markdown(report: dict) -> str:
    p = report["params"]
    L = [f"# 跨市场资金面/拥挤监测 — {report['generated_at']}", ""]
    L.append(f"标的 {report['universe_size']} 只 · 后端 `{report['backend']}` · "
             f"窗口 {p['window_days']}天 · 拥挤回溯 {p['crowding_lookback']}天")
    L.append("")
    L.append("| 代码 | 综合强度 | 两融 | 北向 | 大宗 | 共识 | 拥挤度分位 | 信号 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for it in report["items"]:
        f = it["flows"]
        mg = f.get("margin", {}).get("strength")
        nb = f.get("northbound", {}).get("strength")
        bk = f.get("block", {}).get("strength")
        cons = it["consensus"]
        cons_txt = "共识" if cons.get("is_consensus") else ("背离" if cons.get("divergence") else "中性")
        crowd = it["crowding"]
        pct = crowd.get("crowding_pct")
        pct_txt = (f"{'🔴' if crowd.get('alert') else ''}{pct:.0f}%" if pct is not None else "—")

        def _n(x):
            return f"{x:+.2f}" if isinstance(x, (int, float)) else "—"
        L.append(f"| {it['symbol']} | {_n(it['composite_strength'])} | {_n(mg)} | {_n(nb)} | {_n(bk)} | "
                 f"{cons_txt} | {pct_txt} | {it['signal']} |")
    L.append("")
    if report.get("degraded_sources"):
        L.append("**数据降级：**")
        for s in report["degraded_sources"]:
            L.append(f"- {s}")
        L.append("")
    L.append("> 大宗折溢价为自算（成交价 vs 当日收盘），三源披露有滞后。仅供研究参考，不构成投资建议。")
    return "\n".join(L)
