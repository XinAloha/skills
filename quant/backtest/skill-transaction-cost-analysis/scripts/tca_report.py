#!/usr/bin/env python3
"""
tca_report.py — 交易成本分析 CLI 入口

用法:
  python scripts/tca_report.py --fills fills.csv --benchmark vwap \
      --commission-bps 2.5 --impact-coef 0.1 \
      --out report.json --md report.md

fills CSV 列: symbol, side(buy/sell), datetime, price, qty
无凭证时自动回退内置样本分钟线（examples/sample_data/get_stock_min.json）。
"""
from __future__ import annotations
import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_source import DataSource          # noqa: E402
import benchmarks as bm                      # noqa: E402
import tca_decompose as td                   # noqa: E402
import formatters                            # noqa: E402


def read_fills(path: str) -> list[dict]:
    """读成交 CSV，标准化字段。"""
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            r = {k.strip().lower(): (v.strip() if isinstance(v, str) else v)
                 for k, v in r.items()}
            if not r.get("symbol"):
                continue
            rows.append({
                "symbol": r["symbol"].upper(),
                "side": r.get("side", "buy").lower(),
                "datetime": r.get("datetime", ""),
                "price": float(r.get("price", 0) or 0),
                "qty": float(r.get("qty", 0) or 0),
            })
    return rows


def _minute_window(fills: list[dict], pad_minutes: int = 60):
    """由成交时间跨度推算需要拉取分钟线的日期区间（YYYYMMDD）。"""
    dts = [bm.parse_dt(f["datetime"]) for f in fills]
    dts = [d for d in dts if d]
    if not dts:
        today = datetime.now()
        return today.strftime("%Y%m%d"), today.strftime("%Y%m%d")
    lo, hi = min(dts), max(dts)
    return lo.strftime("%Y%m%d"), hi.strftime("%Y%m%d")


def build_report(fills_path: str, benchmark="vwap",
                 commission_bps=td.DEFAULT_COMMISSION_BPS,
                 impact_coef=td.IMPACT_COEF, frequency="5m",
                 prefer=None) -> dict:
    ds = DataSource(prefer=prefer)
    fills = read_fills(fills_path)
    if not fills:
        raise SystemExit("未从 fills 解析到有效成交记录")

    start, end = _minute_window(fills)

    # 每个标的拉一次分钟线，缓存
    bars_cache: dict[str, bm.MinuteBars] = {}
    degraded: set[str] = set()
    for sym in {f["symbol"] for f in fills}:
        rows = ds.stock_min(sym, start, end, frequency=frequency)
        bars_cache[sym] = bm.MinuteBars(rows)
        if not rows:
            degraded.add(f"{sym}: 未取到分钟线，成本项大量退化")

    # 逐笔分解
    fill_costs: list[td.FillCost] = []
    for f in fills:
        fc = td.decompose_fill(f, bars_cache[f["symbol"]], benchmark=benchmark,
                               commission_bps=commission_bps, impact_coef=impact_coef)
        fill_costs.append(fc)
        for d in fc.degraded:
            degraded.add(f"{f['symbol']}: {d}")

    total = td.aggregate(fill_costs)

    # 按方向聚合
    by_side = []
    side_groups = defaultdict(list)
    for fc in fill_costs:
        side_groups[fc.side].append(fc)
    for side, items in side_groups.items():
        agg = td.aggregate(items)
        by_side.append({"side": side, "total_cost_bps": agg["total_cost_bps"],
                        "breakdown": agg["breakdown"], "notional": agg["notional"],
                        "n_fills": agg["n_fills"]})

    # 按标的聚合
    by_symbol = []
    sym_groups = defaultdict(list)
    for fc in fill_costs:
        sym_groups[fc.symbol].append(fc)
    for sym, items in sym_groups.items():
        agg = td.aggregate(items)
        by_symbol.append({"symbol": sym, "total_cost_bps": agg["total_cost_bps"],
                          "breakdown": agg["breakdown"], "notional": agg["notional"],
                          "n_fills": agg["n_fills"]})
    by_symbol.sort(key=lambda r: abs(r["total_cost_bps"]), reverse=True)

    insights = _insights(total, by_symbol, fill_costs)

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "backend": ds.backend,
        "benchmark": benchmark,
        "params": {"commission_bps": commission_bps, "impact_coef": impact_coef,
                   "frequency": frequency},
        "n_fills": total["n_fills"],
        "notional": total["notional"],
        "total_cost_bps": total["total_cost_bps"],
        "breakdown": total["breakdown"],
        "by_side": by_side,
        "by_symbol": by_symbol,
        "fills": [fc.to_dict() for fc in fill_costs],
        "insights": insights,
        "degraded": sorted(degraded),
    }


def _insights(total: dict, by_symbol: list[dict], fills: list[td.FillCost]) -> list[str]:
    """基于分解结果给出中文结论与改进方向。"""
    out = []
    bd = total["breakdown"]
    if total["n_fills"] == 0:
        return ["无有效成交，无法给出结论。"]
    # 主要成本来源
    main = max(formatters.COST_ORDER, key=lambda k: abs(bd.get(k, 0.0)))
    out.append(f"总成本 {total['total_cost_bps']:.2f} bps，主要来源是"
               f"「{formatters.COST_CN[main]}」({bd[main]:.2f} bps)。")
    # 冲击 vs 择时的定性判断
    if bd["impact"] > bd["timing"] and bd["impact"] > 5:
        out.append("冲击占比高，说明单笔相对 ADV 偏大，建议拆单/拉长执行窗口或用 VWAP/TWAP 算法降参与率。")
    if bd["timing"] > 5:
        out.append("择时成本偏高，决策到成交期间价格已向不利方向漂移，建议缩短下单延迟或改用更被动的挂单。")
    if bd["slippage"] > 5:
        out.append("滑点偏高，成交价明显劣于区间 VWAP，检查是否频繁吃对手价/追价。")
    # 异常大单
    if fills:
        worst = max(fills, key=lambda f: abs(f.total_bps))
        if abs(worst.total_bps) > abs(total["total_cost_bps"]) * 1.5:
            out.append(f"异常笔：{worst.symbol} {worst.datetime[:16]} 单笔 {worst.total_bps:.1f} bps，"
                       f"显著高于组合均值，值得复盘。")
    return out


def main():
    ap = argparse.ArgumentParser(description="A股/跨市场 交易成本分析 (TCA)")
    ap.add_argument("--fills", required=True, help="成交 CSV: symbol,side,datetime,price,qty")
    ap.add_argument("--benchmark", choices=["vwap", "twap", "arrival"], default="vwap")
    ap.add_argument("--commission-bps", type=float, default=td.DEFAULT_COMMISSION_BPS)
    ap.add_argument("--impact-coef", type=float, default=td.IMPACT_COEF)
    ap.add_argument("--frequency", choices=["1m", "5m", "15m", "60m"], default="5m")
    ap.add_argument("--prefer", choices=["sdk", "sample"], default=None)
    ap.add_argument("--out", default=None, help="JSON 输出路径")
    ap.add_argument("--md", default=None, help="Markdown 输出路径")
    args = ap.parse_args()

    report = build_report(args.fills, benchmark=args.benchmark,
                          commission_bps=args.commission_bps,
                          impact_coef=args.impact_coef,
                          frequency=args.frequency, prefer=args.prefer)

    print(formatters.to_text(report))
    if args.out:
        Path(args.out).write_text(formatters.to_json(report), encoding="utf-8")
        print(f"\n[已写出 JSON] {args.out}")
    if args.md:
        Path(args.md).write_text(formatters.to_markdown(report), encoding="utf-8")
        print(f"[已写出 Markdown] {args.md}")


if __name__ == "__main__":
    main()
