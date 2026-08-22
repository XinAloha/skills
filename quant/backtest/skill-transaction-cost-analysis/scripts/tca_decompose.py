"""
tca_decompose.py — Implementation Shortfall 五项成本分解

框架（Perold 1988 implementation shortfall），全部以 bps（万分之一，相对基准价）计，
且统一为"对投资者不利为正"的符号约定（成本越大越差）。

对一笔成交 fill（side, price, qty）与其成交区间的分钟线：
  决策价 arrival、区间 VWAP、区间 TWAP、年化波动 σ、当日 ADV。

  1) 择时 timing   = 方向 · (benchmark − arrival) / arrival × 1e4
       决策到所选执行基准的价格漂移；arrival 基准下定义为 0。
  2) 冲击 impact   = k · σ_bar · sqrt(Q / ADV) × 1e4          （square-root 模型）
       σ_bar 为区间尺度波动（年化 σ 折算到成交所处的分钟窗口）；恒为正（自身交易推价）。
  3) 点差 spread   = 0.5 · (mean(high−low)/mid) × 1e4          （分钟高低价代理半价差）
       无逐笔盘口，用分钟内高低幅的一半近似半点差；恒为正。
  4) 费用 fees     = commission_bps + 印花税(A 股卖出 0.05%=5bps) + 过户费近似
  5) 滑点 slippage = 方向 · (price − benchmark) / benchmark × 1e4
       实际成交价相对所选 VWAP/TWAP/arrival 基准的残差。

约定：side=buy → dir=+1；side=sell → dir=−1。
      成交价高于基准，对买方是成本(+)，对卖方是收益(−)，dir 已吸收该符号。

⚠️ 局限：Pandadata 无逐笔 tick/盘口，impact 与 spread 均为分钟级近似，
        真实半点差通常小于分钟高低幅估计（见 references/methodology.md）。
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field, asdict
from datetime import timedelta

import benchmarks as bm

# 默认参数
DEFAULT_COMMISSION_BPS = 2.5      # 单边佣金（含规费），bps
STAMP_DUTY_BPS = 5.0             # A 股卖出印花税 0.05% = 5bps（2023.8 起单边）
TRANSFER_FEE_BPS = 0.1           # 沪市过户费近似（万分之0.1量级），统一小额计入
IMPACT_COEF = 0.1                # square-root 冲击系数 k 经验默认
A_SHARE_MINUTES_PER_DAY = bm.A_SHARE_MINUTES_PER_DAY


@dataclass
class FillCost:
    symbol: str
    side: str
    datetime: str
    price: float
    qty: float
    notional: float
    benchmark_price: float | None
    arrival_price: float | None
    # 五项成本（bps，正=对投资者不利）
    timing: float = 0.0
    impact: float = 0.0
    spread: float = 0.0
    fees: float = 0.0
    slippage: float = 0.0
    total_bps: float = 0.0
    degraded: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def _dir(side: str) -> int:
    return 1 if str(side).lower().startswith("b") else -1


def _bps(numer_ratio: float) -> float:
    return numer_ratio * 1e4


def _interval_sigma(sigma_annual: float, n_minutes: int) -> float:
    """把年化波动折算到成交窗口尺度（时间平方根缩放），用于冲击的波动输入。"""
    n = max(1, n_minutes)
    frac = n / (A_SHARE_MINUTES_PER_DAY * bm.TRADING_DAYS)
    return sigma_annual * math.sqrt(frac)


def decompose_fill(fill: dict, all_bars: "bm.MinuteBars",
                   benchmark: str = "vwap",
                   commission_bps: float = DEFAULT_COMMISSION_BPS,
                   impact_coef: float = IMPACT_COEF,
                   window_minutes: int = 30) -> FillCost:
    """
    对单笔成交做五项分解。成交区间取 [成交时刻 − window/2, 成交时刻 + window/2]，
    在该区间上算 VWAP/TWAP/点差；σ、ADV 用全量分钟线估计。
    """
    side = str(fill.get("side", "buy"))
    d = _dir(side)
    price = float(fill.get("price", 0.0) or 0.0)
    qty = float(fill.get("qty", 0.0) or 0.0)
    symbol = str(fill.get("symbol", ""))
    fdt = bm.parse_dt(fill.get("datetime"))
    notional = price * qty

    degraded: list[str] = []

    # --- 成交区间分钟线 ---
    if fdt is not None:
        half = timedelta(minutes=window_minutes / 2)
        seg = all_bars.slice(fdt - half, fdt + half)
    else:
        seg = all_bars.bars
        degraded.append("成交时间缺失/无法解析，区间退化为全量分钟线")

    vwap = bm.interval_vwap(seg)
    twap = bm.interval_twap(seg)
    arrival = bm.arrival_price(all_bars, fdt) if fdt else (
        bm.interval_vwap(all_bars.bars) if all_bars.bars else None)

    if not seg:
        degraded.append("成交区间无分钟线，基准/冲击不可用")

    # 选定执行基准价
    if benchmark == "twap":
        bench = twap or vwap
    elif benchmark == "arrival":
        bench = arrival or vwap
    else:
        bench = vwap or twap
    if bench is None:
        bench = price
        degraded.append("无有效基准价，回退用成交价（timing/slippage 归零）")

    fc = FillCost(symbol=symbol, side=side,
                  datetime=str(fill.get("datetime", "")),
                  price=price, qty=qty, notional=round(notional, 2),
                  benchmark_price=round(bench, 6) if bench else None,
                  arrival_price=round(arrival, 6) if arrival else None)

    # --- 1) 择时：arrival → 所选基准的不利漂移 ---
    if benchmark == "arrival" and arrival:
        fc.timing = 0.0
    elif arrival and bench:
        fc.timing = round(_bps(d * (bench - arrival) / arrival), 2)
    else:
        degraded.append("缺决策价或所选基准价，timing 无法计算")

    # --- 2) 冲击：square-root 模型 k·σ·sqrt(Q/ADV) ---
    sigma = bm.realized_vol(all_bars)
    adv = bm.adv_from_bars(all_bars)
    if adv > 0 and qty > 0:
        sigma_bar = _interval_sigma(sigma, len(seg) or 1)
        # 用区间尺度波动仍偏小，冲击对波动更敏感于日尺度，这里取日尺度 σ_day 更贴经验
        sigma_day = sigma / math.sqrt(bm.TRADING_DAYS)
        participation = qty / adv
        impact_ratio = impact_coef * sigma_day * math.sqrt(participation)
        fc.impact = round(_bps(impact_ratio), 2)
    else:
        degraded.append("ADV 不可估，冲击成本无法计算")

    # --- 3) 点差：分钟高低幅的一半近似半点差 ---
    if seg:
        halfs = []
        for b in seg:
            h, l, c = bm._f(b.get("high")), bm._f(b.get("low")), bm._f(b.get("close"))
            mid = c or ((h + l) / 2 if (h and l) else 0)
            if h and l and mid > 0:
                halfs.append(0.5 * (h - l) / mid)
        if halfs:
            fc.spread = round(_bps(sum(halfs) / len(halfs)), 2)
        else:
            degraded.append("分钟高低价缺失，点差用 0（可能低估）")

    # --- 4) 费用：佣金 + A 股卖出印花税 + 过户费 ---
    fees_bps = commission_bps + TRANSFER_FEE_BPS
    if d < 0 and symbol.upper().endswith((".SH", ".SZ", ".BJ")):
        fees_bps += STAMP_DUTY_BPS
    fc.fees = round(fees_bps, 2)

    # --- 5) 滑点：成交价相对所选执行基准的残差 ---
    if bench:
        fc.slippage = round(_bps(d * (price - bench) / bench), 2)
    else:
        degraded.append("无所选基准价，slippage 无法计算")

    fc.total_bps = round(fc.timing + fc.impact + fc.spread + fc.fees + fc.slippage, 2)
    fc.degraded = degraded
    return fc


def notional_weighted(items: list[FillCost], attr: str) -> float:
    """按成交额加权聚合某一成本分项（bps）。"""
    tot = sum(i.notional for i in items)
    if tot <= 0:
        return 0.0
    return round(sum(getattr(i, attr) * i.notional for i in items) / tot, 2)


def aggregate(items: list[FillCost]) -> dict:
    """把逐笔成本按成交额加权汇总为总账 + 五项瀑布。"""
    if not items:
        return {"total_cost_bps": 0.0,
                "breakdown": {k: 0.0 for k in
                              ("timing", "impact", "spread", "fees", "slippage")},
                "notional": 0.0, "n_fills": 0}
    breakdown = {k: notional_weighted(items, k)
                 for k in ("timing", "impact", "spread", "fees", "slippage")}
    return {
        "total_cost_bps": round(sum(breakdown.values()), 2),
        "breakdown": breakdown,
        "notional": round(sum(i.notional for i in items), 2),
        "n_fills": len(items),
    }
