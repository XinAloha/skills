#!/usr/bin/env python3
"""
capital_report.py — 跨市场资金面/拥挤监测 CLI 入口

用法:
  python scripts/capital_report.py --symbols 600519.SH,000858.SZ \
      --window 60 --crowding-lookback 250 \
      --out report.json --md report.md

无凭证自动回退内置样本（examples/sample_data/）。
输出 CapitalFlowReport：items[] + degraded_sources[]。
"""
from __future__ import annotations
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_source import DataSource   # noqa: E402
import flows as fl                   # noqa: E402
import crowding as cr                # noqa: E402
import formatters                    # noqa: E402


def parse_symbols(raw: str) -> list[str]:
    """解析代码列表；也支持文件路径。行业/概念名交由 agent 先展开成成分再传入。"""
    if Path(raw).exists():
        text = Path(raw).read_text(encoding="utf-8")
        toks = [t.strip() for line in text.splitlines() for t in line.replace(",", " ").split()]
    else:
        toks = [t.strip() for t in raw.replace(",", " ").split()]
    return [t.upper() for t in toks if t]


def _daily_flow_history(margin_rows, hsgt_rows) -> list[float]:
    """
    构造逐日"时序资金强度"历史序列，用于拥挤度分位。

    拥挤度须"苹果对苹果"：用**有连续时序的两源**（融资融券余额变化率、北向持股比例差分）
    各自全窗口 z 标准化后逐日平均，得到一条逐日强度序列。该序列的**末值即当前时序强度**，
    与整条序列比分位 → 拥挤度。大宗交易是零星事件（无逐日时序），不进拥挤分位，
    但仍进综合强度与共识判断。

    返回逐日序列（末值 = 当前时序强度）。样本不足时返回可用部分。
    """
    import statistics
    m = fl._sorted_by_date(margin_rows)
    h = fl._sorted_by_date(hsgt_rows)

    mbal = [r.get("margin_balance") for r in m if r.get("margin_balance") is not None]
    m_chg = fl.pct_change_series(mbal)  # 逐日融资余额变化率
    hr = [r.get("holding_ratio") for r in h if r.get("holding_ratio") is not None]
    h_diff = [hr[i] - hr[i - 1] for i in range(1, len(hr))]  # 逐日北向持股比例差分

    def _zseries(seq):
        if len(seq) < 2:
            return seq[:]
        mu = statistics.fmean(seq)
        sd = statistics.pstdev(seq) or 1.0
        return [(v - mu) / sd for v in seq]

    m_z = _zseries(m_chg)
    h_z = _zseries(h_diff)

    n = max(len(m_z), len(h_z))
    hist = []
    for i in range(n):
        parts = []
        if i < len(m_z):
            parts.append(m_z[i])
        if i < len(h_z):
            parts.append(h_z[i])
        if parts:
            hist.append(sum(parts) / len(parts))
    return hist


def build_report(symbols, window_days=60, crowding_lookback=250,
                 dimensions="all", prefer=None) -> dict:
    ds = DataSource(prefer=prefer)
    today = datetime.now()
    d_end = today.strftime("%Y%m%d")
    d_start = (today - timedelta(days=max(window_days, crowding_lookback) + 10)).strftime("%Y%m%d")

    use_margin = dimensions in ("all", "margin")
    use_nb = dimensions in ("all", "northbound")
    use_block = dimensions in ("all", "block")

    degraded = set()
    items = []
    for sym in symbols:
        margin_rows = ds.margin(sym, d_start, d_end) if use_margin else []
        hsgt_rows = ds.hsgt_hold(sym, d_start, d_end) if use_nb else []
        block_rows = ds.block_trade(sym, d_start, d_end) if use_block else []

        # 大宗折溢价须自算：取个股日线收盘价
        close_map = {}
        if use_block and block_rows:
            sd_rows = ds.stock_daily(sym, d_start, d_end)
            close_map = fl.build_close_map(sd_rows)
            if not close_map:
                degraded.add(f"{sym}: 无个股收盘价，大宗折溢价降级（仅按机构方向/规模）")

        source_flows = []
        if use_margin:
            mf = fl.margin_flow(margin_rows)
            source_flows.append(mf)
            if mf["strength"] is None:
                degraded.add(f"{sym}: 融资融券数据不足")
        if use_nb:
            nf = fl.northbound_flow(hsgt_rows)
            source_flows.append(nf)
            if nf["strength"] is None:
                degraded.add(f"{sym}: 北向持股数据不足")
        if use_block:
            bf = fl.block_flow(block_rows, close_map)
            source_flows.append(bf)
            if bf["strength"] is None:
                degraded.add(f"{sym}: 无大宗交易记录")

        comp = cr.composite_strength(source_flows)
        cons = cr.consensus(source_flows)
        # 拥挤度：用有连续时序的两源逐日强度序列，比"当前时序强度(末值)"在历史中的分位
        hist = _daily_flow_history(margin_rows, hsgt_rows)
        hist = hist[-crowding_lookback:] if len(hist) > crowding_lookback else hist
        current_ts_strength = hist[-1] if hist else None
        crowd = cr.crowding(hist, current_ts_strength)
        signal = cr.overall_signal(cons, crowd)

        items.append({
            "symbol": sym,
            "composite_strength": round(comp, 3) if comp is not None else None,
            "flows": {f["source"]: f for f in source_flows},
            "consensus": cons,
            "crowding": crowd,
            "signal": signal,
        })

    # 排序：先高拥挤预警，再共识买入，再按综合强度绝对值
    def _key(it):
        alert = it["crowding"].get("alert") or False
        is_cons = it["consensus"].get("is_consensus") or False
        cs = abs(it["composite_strength"]) if it["composite_strength"] is not None else -1
        return (alert, is_cons, cs)
    items.sort(key=_key, reverse=True)

    return {
        "generated_at": today.strftime("%Y-%m-%d %H:%M"),
        "backend": ds.backend,
        "universe_size": len(symbols),
        "params": {"window_days": window_days, "crowding_lookback": crowding_lookback,
                   "dimensions": dimensions},
        "items": items,
        "degraded_sources": sorted(degraded),
    }


def main():
    ap = argparse.ArgumentParser(description="A股跨市场资金面/拥挤度监测（两融+北向+大宗）")
    ap.add_argument("--symbols", required=True, help="逗号分隔股票代码，或含代码的文件路径")
    ap.add_argument("--window", type=int, default=60, help="观察窗口（天）")
    ap.add_argument("--crowding-lookback", type=int, default=250, help="拥挤度分位回溯（天）")
    ap.add_argument("--dimensions", choices=["all", "margin", "northbound", "block"], default="all")
    ap.add_argument("--prefer", choices=["sdk", "sample"], default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--md", default=None)
    args = ap.parse_args()

    symbols = parse_symbols(args.symbols)
    if not symbols:
        print("未解析到有效股票代码", file=sys.stderr)
        sys.exit(2)

    report = build_report(symbols, window_days=args.window,
                          crowding_lookback=args.crowding_lookback,
                          dimensions=args.dimensions, prefer=args.prefer)
    print(formatters.to_text(report))
    if args.out:
        Path(args.out).write_text(formatters.to_json(report), encoding="utf-8")
        print(f"\n[已写出 JSON] {args.out}")
    if args.md:
        Path(args.md).write_text(formatters.to_markdown(report), encoding="utf-8")
        print(f"[已写出 Markdown] {args.md}")


if __name__ == "__main__":
    main()
