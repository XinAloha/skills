"""
flows.py — 三源资金流标准化（纯标准库：statistics + 手写）

把三类互不相通的资金数据统一成 [-∞,∞] 的"资金强度分"（正=净流入/加仓，负=净流出/减仓），
使三源可比、可加权合成。标准化方法：窗口内序列的 z-score（当前值相对历史均值的标准差倍数）。

三源口径：
  - 融资融券：融资余额(margin_balance) 的窗口变化 → 杠杆资金净增减。
  - 北向持股：持股比例(holding_ratio) 的窗口变化 → 外资加/减仓。
  - 大宗交易：净成交额（承接方向 × 规模）+ 平均折溢价 → 机构接盘/出货强度。
    大宗折溢价须自算：(成交价 price - 当日收盘价 close) / close × 100。
"""
from __future__ import annotations
import statistics


# ---------- 通用工具（纯标准库/手写） ----------

def _sorted_by_date(rows, date_key="date"):
    return sorted([r for r in rows if r.get(date_key)], key=lambda x: str(x[date_key]))


def zscore(series: list[float]) -> float:
    """序列末值相对全序列的 z-score。序列<2 或无波动时退化为 0。"""
    vals = [float(v) for v in series if v is not None]
    if len(vals) < 2:
        return 0.0
    mu = statistics.fmean(vals)
    try:
        sd = statistics.pstdev(vals)
    except statistics.StatisticsError:
        return 0.0
    if sd == 0:
        return 0.0
    return (vals[-1] - mu) / sd


def pct_change_series(series: list[float]) -> list[float]:
    """把水平序列转成逐日变化率序列（衡量'流入/流出'而非'存量'）。"""
    vals = [float(v) for v in series if v is not None]
    out = []
    for i in range(1, len(vals)):
        prev = vals[i - 1]
        if prev == 0:
            out.append(0.0)
        else:
            out.append((vals[i] - prev) / abs(prev))
    return out


def _is_institution(party: str | None) -> bool:
    """营业部是否为机构（大宗交易买卖方判机构/游资）。"""
    if not party:
        return False
    return "机构专用" in party


# ---------- 融资融券 ----------

def margin_flow(margin_rows) -> dict:
    """
    融资余额窗口变化 → z-score 强度分。
    返回 {source, strength(z), latest_balance, chg_pct(末日变化率), detail}
    """
    rows = _sorted_by_date(margin_rows)
    # 只取融资(cash)口径的余额；若无 margin_type 则用 margin_balance 兜底
    cash_rows = [r for r in rows if r.get("margin_type") in (None, "cash")] or rows
    bal = [r.get("margin_balance") for r in cash_rows if r.get("margin_balance") is not None]
    if len(bal) < 2:
        return {"source": "margin", "strength": None, "latest_balance": bal[-1] if bal else None,
                "chg_pct": None, "detail": "融资余额样本不足"}
    chg = pct_change_series(bal)
    strength = zscore(chg) if len(chg) >= 2 else 0.0
    last_chg = chg[-1] if chg else 0.0
    # 区间累计变化（首→末），避免只看末日环比误读整体趋势
    window_chg = (bal[-1] - bal[0]) / abs(bal[0]) if bal[0] else 0.0
    return {
        "source": "margin",
        "strength": round(strength, 3),
        "latest_balance": bal[-1],
        "chg_pct": round(last_chg * 100, 3),
        "window_chg_pct": round(window_chg * 100, 3),
        "detail": f"融资余额区间累计{'增' if window_chg >= 0 else '减'} {abs(window_chg) * 100:.2f}%"
                  f"（末日环比{'+' if last_chg >= 0 else ''}{last_chg * 100:.2f}%）",
    }


# ---------- 北向持股 ----------

def northbound_flow(hsgt_rows) -> dict:
    """
    北向持股比例窗口变化 → z-score 强度分。
    返回 {source, strength(z), latest_ratio, chg_ratio(末日变化,百分点), detail}
    """
    rows = _sorted_by_date(hsgt_rows)
    ratio = [r.get("holding_ratio") for r in rows if r.get("holding_ratio") is not None]
    if len(ratio) < 2:
        return {"source": "northbound", "strength": None,
                "latest_ratio": ratio[-1] if ratio else None,
                "chg_ratio": None, "detail": "北向持股样本不足"}
    # 持股比例本身是百分比，用逐日差分（百分点变化）作为流入流出强度
    diffs = [ratio[i] - ratio[i - 1] for i in range(1, len(ratio))]
    strength = zscore(diffs) if len(diffs) >= 2 else 0.0
    last_diff = diffs[-1] if diffs else 0.0
    return {
        "source": "northbound",
        "strength": round(strength, 3),
        "latest_ratio": round(float(ratio[-1]), 4),
        "chg_ratio": round(last_diff, 4),
        "detail": f"北向持股比例{'升' if last_diff >= 0 else '降'} {abs(last_diff):.4f} 个百分点（末日）",
    }


# ---------- 大宗交易（含自算折溢价） ----------

def block_premium(price, close) -> float | None:
    """大宗折溢价%（正=溢价买入/承接意愿强，负=折价出货）。price=成交价, close=当日收盘价。"""
    if price is None or close is None or float(close) == 0:
        return None
    return (float(price) - float(close)) / float(close) * 100.0


def block_flow(block_rows, close_map: dict) -> dict:
    """
    大宗交易强度：以"净承接额 + 平均折溢价倾向"合成方向与强度。
      - 机构专用买方 → 承接（正），机构专用卖方 → 出货（负）；均为机构记全额，否则半权。
      - 折溢价正（溢价）加分，负（折价）减分。
    close_map: {(symbol, date): close} 用于自算折溢价。
    返回 {source, strength, net_amount_wan, avg_premium_pct, inst_buy_cnt, inst_sell_cnt, detail}
    """
    rows = _sorted_by_date(block_rows)
    if not rows:
        return {"source": "block", "strength": None, "net_amount_wan": None,
                "avg_premium_pct": None, "inst_buy_cnt": 0, "inst_sell_cnt": 0,
                "detail": "无大宗交易记录"}

    net_amount = 0.0
    premiums = []
    inst_buy = inst_sell = 0
    for r in rows:
        amt = float(r.get("amount") or 0)
        buyer_inst = _is_institution(r.get("buyer"))
        seller_inst = _is_institution(r.get("seller"))
        # 方向：机构买 = 承接(+)，机构卖 = 出货(-)；两端都机构则净轧差为 0
        direction = 0.0
        if buyer_inst and not seller_inst:
            direction = 1.0
            inst_buy += 1
        elif seller_inst and not buyer_inst:
            direction = -1.0
            inst_sell += 1
        else:
            # 无明确机构方向：以折溢价倾向作为弱方向信号（溢价承接 / 折价甩卖）
            direction = 0.0
        net_amount += direction * amt

        prem = block_premium(r.get("price"), close_map.get((r.get("symbol"), r.get("date"))))
        if prem is not None:
            premiums.append(prem)

    avg_prem = statistics.fmean(premiums) if premiums else None
    net_amount_wan = net_amount / 1e4

    # 强度合成：净承接额规模（对数压缩到量级）× 折溢价倾向修正
    # 用符号 × log10(1+|万元额|) 做尺度压缩，避免大额单笔碾压 z 尺度
    import math
    mag = math.log10(1 + abs(net_amount_wan)) if net_amount_wan else 0.0
    sign = 1.0 if net_amount_wan > 0 else (-1.0 if net_amount_wan < 0 else 0.0)
    prem_adj = 0.0
    if avg_prem is not None:
        prem_adj = max(-1.0, min(1.0, avg_prem / 5.0))  # ±5% 折溢价映射到 ±1
    # 若无机构方向，用折溢价倾向定方向
    if sign == 0 and avg_prem is not None:
        sign = 1.0 if avg_prem >= 0 else -1.0
        mag = max(mag, 0.5)
    strength = sign * mag + 0.5 * prem_adj

    return {
        "source": "block",
        "strength": round(strength, 3),
        "net_amount_wan": round(net_amount_wan, 1),
        "avg_premium_pct": round(avg_prem, 3) if avg_prem is not None else None,
        "inst_buy_cnt": inst_buy,
        "inst_sell_cnt": inst_sell,
        "detail": (f"机构承接{inst_buy}笔/出货{inst_sell}笔，净额{net_amount_wan:+.0f}万，"
                   f"均折溢价{avg_prem:+.2f}%" if avg_prem is not None
                   else f"机构承接{inst_buy}笔/出货{inst_sell}笔，净额{net_amount_wan:+.0f}万"),
    }


def build_close_map(stock_daily_rows) -> dict:
    """从 get_stock_daily 构造 {(symbol,date): close}，供大宗折溢价自算。"""
    m = {}
    for r in stock_daily_rows or []:
        sym = r.get("symbol")
        dt = r.get("date")
        close = r.get("close")
        if sym and dt and close is not None:
            m[(sym, dt)] = close
    return m
