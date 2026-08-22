"""
crowding.py — 一致性/背离 + 拥挤度分位（纯标准库/手写）

两个核心量：
  1) 共识/背离：三源资金流方向的一致性。三源全同向=共识（信号强）；打架=背离（分歧）。
  2) 拥挤度分位：把"当前综合资金强度"放进历史 N 天分布求分位。
     >90% 分位 → 高拥挤预警（交易过挤、反转风险）；<10% → 冷门/被抛弃。

综合资金强度 = 三源强度分的（可缺失容错）平均。
"""
from __future__ import annotations


# ---------- 综合强度 ----------

def composite_strength(source_flows: list[dict]) -> float | None:
    """三源强度分平均（None 跳过）。全缺失返回 None。"""
    vals = [f["strength"] for f in source_flows if f.get("strength") is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


# ---------- 共识 / 背离 ----------

def consensus(source_flows: list[dict]) -> dict:
    """
    统计三源方向（sign），给出共识分与背离标注。
    consensus_score ∈ [0,1]：1=全同向（强共识），0.5=两两分歧，0=无有效源。
    """
    signed = []
    for f in source_flows:
        s = f.get("strength")
        if s is None:
            continue
        if s > 0.05:
            signed.append((f["source"], 1))
        elif s < -0.05:
            signed.append((f["source"], -1))
        else:
            signed.append((f["source"], 0))  # 中性

    active = [(src, sg) for src, sg in signed if sg != 0]
    n = len(active)
    if n == 0:
        return {"consensus_score": 0.0, "direction": "中性/无明显方向",
                "is_consensus": False, "divergence": [], "active_sources": 0}

    pos = [src for src, sg in active if sg > 0]
    neg = [src for src, sg in active if sg < 0]

    # 共识分：多数方向占比（|多-少| / 总）
    majority = max(len(pos), len(neg))
    score = majority / n

    if len(neg) == 0:
        direction = "三源同向净流入（做多共识）" if n >= 3 else "净流入"
    elif len(pos) == 0:
        direction = "三源同向净流出（做空/减仓共识）" if n >= 3 else "净流出"
    else:
        direction = "方向背离（分歧）"

    # 背离标注：少数派是谁
    divergence = []
    if pos and neg:
        minority = neg if len(neg) <= len(pos) else pos
        majority_dir = "净流入" if len(pos) >= len(neg) else "净流出"
        minority_dir = "净流出" if majority_dir == "净流入" else "净流入"
        for src in minority:
            divergence.append(f"{_cn(src)}与主流({majority_dir})相反（{minority_dir}）")

    is_consensus = (score >= 0.99 and n >= 2 and not (pos and neg))
    return {"consensus_score": round(score, 3), "direction": direction,
            "is_consensus": is_consensus, "divergence": divergence, "active_sources": n}


def _cn(source: str) -> str:
    return {"margin": "融资融券", "northbound": "北向", "block": "大宗"}.get(source, source)


# ---------- 拥挤度分位（手写百分位） ----------

def percentile_rank(hist: list[float], current: float) -> float:
    """
    当前值在历史序列中的分位（0~100）。手写：小于等于 current 的占比。
    采用 "≤" 计数 + 相等折半，得到接近连续分位的结果。
    """
    vals = [float(v) for v in hist if v is not None]
    if not vals:
        return 50.0
    below = sum(1 for v in vals if v < current)
    equal = sum(1 for v in vals if v == current)
    rank = (below + 0.5 * equal) / len(vals) * 100.0
    return round(rank, 1)


def crowding(composite_hist: list[float], current_strength: float | None) -> dict:
    """
    拥挤度：当前综合强度在历史分布的分位。
    hi_alert >90 分位 → 过挤；lo <10 → 冷门。
    """
    if current_strength is None:
        return {"crowding_pct": None, "level": "数据不足", "alert": False,
                "note": "综合资金强度缺失，无法计算拥挤度分位"}
    if len(composite_hist) < 20:
        pct = percentile_rank(composite_hist, current_strength) if composite_hist else None
        return {"crowding_pct": pct, "level": "样本不足(建议≥250天)", "alert": False,
                "note": f"历史样本仅 {len(composite_hist)} 天，分位统计意义弱"}

    pct = percentile_rank(composite_hist, current_strength)
    if pct >= 90:
        level, alert, note = "高拥挤", True, "资金强度处历史极高分位，交易过挤，警惕反转"
    elif pct >= 75:
        level, alert, note = "偏拥挤", False, "资金强度偏高，接近拥挤区，留意"
    elif pct <= 10:
        level, alert, note = "冷门/被抛弃", False, "资金强度处历史极低分位，关注度低"
    else:
        level, alert, note = "正常", False, "资金强度处历史中位区间"
    return {"crowding_pct": pct, "level": level, "alert": alert, "note": note}


# ---------- 综合信号 ----------

def overall_signal(cons: dict, crowd: dict) -> str:
    """把共识 + 拥挤合成一句人话信号。"""
    is_cons = cons.get("is_consensus")
    direction = cons.get("direction", "")
    crowd_alert = crowd.get("alert")
    pct = crowd.get("crowding_pct")

    if crowd_alert:
        if is_cons and "流入" in direction:
            return "⚠️ 共识做多但已高度拥挤——合力做多却过热，反转风险最高，谨慎追高"
        return f"⚠️ 高拥挤预警（分位 {pct}%）——交易过挤，警惕反转"
    if is_cons and "流入" in direction:
        return "✅ 三源共识买入且未过热——资金合力做多、拥挤度可控，最优形态"
    if is_cons and "流出" in direction:
        return "🔻 三源共识流出——资金合力撤离，趋势性减仓"
    if cons.get("divergence"):
        return "↔️ 资金背离——三源方向打架，分歧大，信号弱化：" + "；".join(cons["divergence"])
    return "· 资金面中性/无明显合力"
