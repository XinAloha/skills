"""
benchmarks.py — 从分钟线重建执行基准与市场统计量

提供：
  - parse_dt / bar_dt        : 时间解析（成交时间 & 分钟线时间戳）
  - MinuteBars               : 单标的分钟线容器，统一字段访问
  - interval_vwap / twap     : 成交区间的成交量加权 / 时间加权均价
  - arrival_price            : 到达价（首笔成交前一根分钟线收盘价代理）
  - realized_vol             : 分钟收益年化波动率（用于 square-root 冲击）
  - adv_from_bars            : 用分钟成交量估当日 ADV（回退：分钟量×当日分钟数）

字段口径（get_stock_min）：
  date, minute, datetime, symbol, open, close, high, low, volume, amount, num_trades
"""
from __future__ import annotations
import math
from datetime import datetime

# A 股每交易日分钟数（9:30-11:30 + 13:00-15:00 = 240 分钟）
A_SHARE_MINUTES_PER_DAY = 240
# 年化交易日
TRADING_DAYS = 244


def parse_dt(s) -> datetime | None:
    """解析成交/分钟时间戳，兼容多种常见格式。"""
    if s is None:
        return None
    if isinstance(s, datetime):
        return s
    s = str(s).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y%m%d %H:%M:%S",
                "%Y%m%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def bar_dt(bar: dict) -> datetime | None:
    """分钟线时间戳：优先 datetime 字段，否则拼 date+minute。"""
    dt = parse_dt(bar.get("datetime"))
    if dt:
        return dt
    d, m = bar.get("date"), bar.get("minute")
    if d is not None and m is not None:
        return parse_dt(f"{d} {m}")
    return parse_dt(d)


def _f(x, default=0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


class MinuteBars:
    """单标的分钟线，按时间排序，提供区间切片与统计。"""

    def __init__(self, rows: list[dict]):
        self.bars = sorted(
            [b for b in rows if bar_dt(b) is not None],
            key=lambda b: bar_dt(b),
        )

    def __len__(self):
        return len(self.bars)

    def slice(self, start: datetime, end: datetime) -> list[dict]:
        """取 [start, end] 闭区间内的分钟线；若为空则回退到最近一根。"""
        sel = [b for b in self.bars if start <= bar_dt(b) <= end]
        if sel:
            return sel
        # 单笔瞬时成交也要有基准：取最接近成交时刻的一根
        if self.bars:
            anchor = start
            return [min(self.bars, key=lambda b: abs((bar_dt(b) - anchor).total_seconds()))]
        return []


def interval_vwap(bars: list[dict]) -> float | None:
    """区间成交量加权均价：Σ(amount) / Σ(volume)，无 amount 时用 close×volume 近似。"""
    tot_amt = tot_vol = 0.0
    for b in bars:
        vol = _f(b.get("volume"))
        amt = _f(b.get("amount")) or _f(b.get("close")) * vol
        tot_amt += amt
        tot_vol += vol
    if tot_vol <= 0:
        return None
    return tot_amt / tot_vol


def interval_twap(bars: list[dict]) -> float | None:
    """区间时间加权均价：各分钟典型价 (H+L+C)/3 的等权平均。"""
    if not bars:
        return None
    px = []
    for b in bars:
        h, l, c = _f(b.get("high")), _f(b.get("low")), _f(b.get("close"))
        typ = (h + l + c) / 3 if (h and l and c) else c
        if typ:
            px.append(typ)
    return sum(px) / len(px) if px else None


def arrival_price(all_bars: MinuteBars, first_fill_dt: datetime) -> float | None:
    """到达价：首笔成交时刻前最后一根分钟线的收盘价（决策价代理）。"""
    prior = [b for b in all_bars.bars if bar_dt(b) < first_fill_dt]
    if prior:
        return _f(prior[-1].get("close")) or None
    # 无更早分钟线时用首根开盘价
    if all_bars.bars:
        return _f(all_bars.bars[0].get("open")) or _f(all_bars.bars[0].get("close")) or None
    return None


def realized_vol(all_bars: MinuteBars) -> float:
    """
    分钟对数收益的年化波动率，供 square-root 冲击模型使用。
    σ_annual = std(分钟对数收益) × sqrt(每日分钟数 × 年化交易日)
    样本不足时回退经验值 0.30。
    """
    closes = [_f(b.get("close")) for b in all_bars.bars if _f(b.get("close")) > 0]
    if len(closes) < 3:
        return 0.30
    rets = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))
            if closes[i - 1] > 0]
    if len(rets) < 2:
        return 0.30
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    minute_vol = math.sqrt(var)
    ann = minute_vol * math.sqrt(A_SHARE_MINUTES_PER_DAY * TRADING_DAYS)
    return ann if ann > 0 else 0.30


def adv_from_bars(all_bars: MinuteBars) -> float:
    """
    用分钟线估当日日均成交量(股) ADV。
    口径：把区间内分钟量按覆盖的自然交易日聚合，取日总量的均值；
    覆盖不足一日时，用 (分钟均量 × 每日分钟数) 外推为整日量。
    """
    if not all_bars.bars:
        return 0.0
    by_day: dict[str, float] = {}
    for b in all_bars.bars:
        d = str(b.get("date") or (bar_dt(b).strftime("%Y%m%d") if bar_dt(b) else ""))
        by_day[d] = by_day.get(d, 0.0) + _f(b.get("volume"))
    day_totals = [v for v in by_day.values() if v > 0]
    if not day_totals:
        return 0.0
    # 若任一日分钟数明显不足 240（区间只覆盖了部分交易时段），外推为整日
    bars_per_day = len(all_bars.bars) / max(1, len(by_day))
    avg_day = sum(day_totals) / len(day_totals)
    if bars_per_day < A_SHARE_MINUTES_PER_DAY * 0.5:
        minute_avg = sum(_f(b.get("volume")) for b in all_bars.bars) / len(all_bars.bars)
        avg_day = max(avg_day, minute_avg * A_SHARE_MINUTES_PER_DAY)
    return avg_day
