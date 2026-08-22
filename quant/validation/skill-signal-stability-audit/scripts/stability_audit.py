"""Cross-sectional signal stability / turnover diagnostics.

Answers: how sticky are ranks, how much does the top basket churn, what rebalance
horizon is implied, and what transaction-cost drag that churn implies.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class StabilityReport:
    n_dates: int
    n_names: int
    top_frac: float
    mean_rank_autocorr: float
    lag_autocorr: dict[str, float]
    half_life_days: float
    mean_top_jaccard: float
    mean_bottom_jaccard: float
    mean_one_way_turnover: float
    mean_sign_flip_rate: float
    mean_kendall_tau: float
    rank_autocorr_p10: float
    top_jaccard_p10: float
    cost_bps: float
    rebalance_days: int
    annual_cost_drag: float
    recommended_rebalance: str
    quintile_transition: list[list[float]]
    verdict: str
    score: float
    gates: dict[str, bool]
    series: dict[str, list[float | None]]
    notes: list[str]


def _rank_rows(panel: np.ndarray) -> np.ndarray:
    out = np.full_like(panel, np.nan, dtype=float)
    for i in range(panel.shape[0]):
        row = panel[i]
        mask = np.isfinite(row)
        if mask.sum() == 0:
            continue
        out[i, mask] = pd.Series(row[mask]).rank(method="average").to_numpy()
    return out


def _jaccard(a: set[int], b: set[int]) -> float:
    union = a | b
    if not union:
        return float("nan")
    return len(a & b) / len(union)


def _kendall_tau(x: np.ndarray, y: np.ndarray) -> float:
    """O(n^2) Kendall tau-b with tie correction; avoids SciPy dependency."""
    n = x.size
    if n < 3:
        return float("nan")
    conc = disc = ties_x = ties_y = 0
    for i in range(n - 1):
        dx = x[i + 1 :] - x[i]
        dy = y[i + 1 :] - y[i]
        prod = dx * dy
        conc += int(np.sum(prod > 0))
        disc += int(np.sum(prod < 0))
        ties_x += int(np.sum((dx == 0) & (dy != 0)))
        ties_y += int(np.sum((dy == 0) & (dx != 0)))
    denom = np.sqrt((conc + disc + ties_x) * (conc + disc + ties_y))
    if denom == 0:
        return float("nan")
    return float((conc - disc) / denom)


def _half_life(lag_corrs: dict[int, float]) -> float:
    """Fit rho(lag)=exp(-lag/hl) on positive autocorr lags."""
    xs, ys = [], []
    for lag, rho in lag_corrs.items():
        if np.isfinite(rho) and rho > 0:
            xs.append(lag)
            ys.append(np.log(rho))
    if len(xs) < 2:
        rho1 = lag_corrs.get(1, float("nan"))
        if np.isfinite(rho1) and 0 < rho1 < 1:
            return float(-np.log(2) / np.log(rho1))
        return float("nan")
    slope = float(np.polyfit(xs, ys, 1)[0])
    if slope >= 0:
        return float("nan")
    return float(-np.log(2) / slope)


def _quintile_transition(signal: np.ndarray) -> np.ndarray:
    mat = np.zeros((5, 5), dtype=float)
    t = signal.shape[0]
    for i in range(1, t):
        r0, r1 = signal[i - 1], signal[i]
        mask = np.isfinite(r0) & np.isfinite(r1)
        if mask.sum() < 20:
            continue
        q0 = pd.qcut(pd.Series(r0[mask]), 5, labels=False, duplicates="drop")
        q1 = pd.qcut(pd.Series(r1[mask]), 5, labels=False, duplicates="drop")
        if q0.nunique() < 5 or q1.nunique() < 5:
            continue
        for a, b in zip(q0, q1):
            mat[int(a), int(b)] += 1
    row_sum = mat.sum(axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        probs = np.divide(mat, row_sum, out=np.full_like(mat, np.nan), where=row_sum > 0)
    return probs


def audit_stability(
    signal: np.ndarray,
    top_frac: float = 0.1,
    cost_bps: float = 15.0,
    max_lag: int = 5,
    rebalance_days: int | None = None,
) -> StabilityReport:
    if signal.ndim != 2 or signal.shape[0] < 10 or signal.shape[1] < 10:
        raise ValueError("signal must be a 2D panel with at least 10 dates and 10 names")
    if not 0 < top_frac < 0.5 or cost_bps < 0 or max_lag < 1:
        raise ValueError("require 0<top_frac<0.5, cost_bps>=0 and max_lag>=1")
    ranks = _rank_rows(signal)
    t, n = signal.shape
    autocorr: list[float] = []
    top_j: list[float] = []
    bot_j: list[float] = []
    flip: list[float] = []
    kendall: list[float] = []
    turnover: list[float] = []

    for i in range(1, t):
        r0, r1 = ranks[i - 1], ranks[i]
        mask = np.isfinite(r0) & np.isfinite(r1)
        if mask.sum() < 5:
            for lst in (autocorr, top_j, bot_j, flip, kendall, turnover):
                lst.append(float("nan"))
            continue
        s0 = pd.Series(r0[mask])
        s1 = pd.Series(r1[mask])
        autocorr.append(float(s0.corr(s1)))
        # subsample for speed on wide cross-sections
        idx_m = np.where(mask)[0]
        if idx_m.size > 80:
            pick = np.linspace(0, idx_m.size - 1, 80).astype(int)
            kendall.append(_kendall_tau(r0[mask][pick], r1[mask][pick]))
        else:
            kendall.append(_kendall_tau(r0[mask], r1[mask]))
        k = max(1, int(mask.sum() * top_frac))
        idx = np.where(mask)[0]
        order0 = np.argsort(r0[mask])
        order1 = np.argsort(r1[mask])
        top0, top1 = set(idx[order0[-k:]]), set(idx[order1[-k:]])
        bot0, bot1 = set(idx[order0[:k]]), set(idx[order1[:k]])
        j_top = _jaccard(top0, top1)
        top_j.append(j_top)
        bot_j.append(_jaccard(bot0, bot1))
        turnover.append(float(1.0 - j_top) if np.isfinite(j_top) else float("nan"))
        med0, med1 = np.nanmedian(signal[i - 1]), np.nanmedian(signal[i])
        s_sign0 = np.sign(signal[i - 1, mask] - med0)
        s_sign1 = np.sign(signal[i, mask] - med1)
        flip.append(float(np.mean(s_sign0 != s_sign1)))

    lag_corr: dict[int, float] = {}
    for lag in range(1, max_lag + 1):
        vals = []
        for i in range(lag, t):
            m = np.isfinite(ranks[i - lag]) & np.isfinite(ranks[i])
            if m.sum() < 5:
                continue
            vals.append(float(pd.Series(ranks[i - lag, m]).corr(pd.Series(ranks[i, m]))))
        lag_corr[lag] = float(np.nanmean(vals)) if vals else float("nan")

    mean_ac = float(np.nanmean(autocorr))
    mean_top = float(np.nanmean(top_j))
    mean_bot = float(np.nanmean(bot_j))
    mean_to = float(np.nanmean(turnover))
    mean_flip = float(np.nanmean(flip))
    mean_k = float(np.nanmean(kendall))
    hl = _half_life(lag_corr)
    if np.isfinite(hl):
        if hl >= 20:
            rebalance = "weekly_or_slower"
        elif hl >= 5:
            rebalance = "2-5_trading_days"
        else:
            rebalance = "daily_or_intraday"
    else:
        rebalance = "unstable_estimate"
    if rebalance_days is None:
        rebalance_days = (
            max(1, min(20, int(round(hl)))) if np.isfinite(hl) else 1
        )
    if rebalance_days < 1:
        raise ValueError("rebalance_days must be >= 1")
    annual_drag = (
        float(mean_to * 2.0 * (cost_bps / 1e4) * (252 / rebalance_days))
        if np.isfinite(mean_to)
        else float("nan")
    )

    gates = {
        "rank_autocorr>=0.30": bool(mean_ac >= 0.30),
        "top_jaccard>=0.20": bool(mean_top >= 0.20),
        "half_life>=3d": bool(np.isfinite(hl) and hl >= 3),
        "annual_cost_drag<15%": bool(np.isfinite(annual_drag) and annual_drag < 0.15),
        "kendall>=0.20": bool(mean_k >= 0.20),
    }
    score = float(np.mean(list(gates.values())))
    if score >= 0.8:
        verdict = "STABLE"
    elif score >= 0.4:
        verdict = "MIXED"
    else:
        verdict = "UNSTABLE"

    trans = _quintile_transition(signal)
    return StabilityReport(
        n_dates=t,
        n_names=n,
        top_frac=top_frac,
        mean_rank_autocorr=mean_ac,
        lag_autocorr={f"lag{k}": v for k, v in lag_corr.items()},
        half_life_days=hl,
        mean_top_jaccard=mean_top,
        mean_bottom_jaccard=mean_bot,
        mean_one_way_turnover=mean_to,
        mean_sign_flip_rate=mean_flip,
        mean_kendall_tau=mean_k,
        rank_autocorr_p10=float(np.nanpercentile(autocorr, 10)),
        top_jaccard_p10=float(np.nanpercentile(top_j, 10)),
        cost_bps=cost_bps,
        rebalance_days=rebalance_days,
        annual_cost_drag=annual_drag,
        recommended_rebalance=rebalance,
        quintile_transition=[[float(x) if np.isfinite(x) else None for x in row] for row in trans],  # type: ignore[list-item]
        verdict=verdict,
        score=score,
        gates=gates,
        series={
            "rank_autocorr": [float(x) if np.isfinite(x) else None for x in autocorr],
            "top_jaccard": [float(x) if np.isfinite(x) else None for x in top_j],
            "one_way_turnover": [float(x) if np.isfinite(x) else None for x in turnover],
            "sign_flip_rate": [float(x) if np.isfinite(x) else None for x in flip],
        },
        notes=[
            "One-way turnover ≈ 1 - top Jaccard (membership churn proxy, not share-level turnover).",
            f"Annual cost drag uses a {rebalance_days}-trading-day rebalance interval.",
            "Half-life from lag1..K rank autocorr exponential fit.",
        ],
    )


def render_text(report: StabilityReport) -> str:
    lines = [
        "=== Signal Stability Audit ===",
        f"shape=[{report.n_dates} x {report.n_names}] top_frac={report.top_frac}",
        f"mean_rank_autocorr={report.mean_rank_autocorr:.3f} (p10={report.rank_autocorr_p10:.3f})  "
        f"kendall={report.mean_kendall_tau:.3f}",
        f"lag_autocorr=" + ", ".join(f"{k}={v:.3f}" for k, v in report.lag_autocorr.items()),
        f"half_life_days={report.half_life_days:.2f}  recommended_rebalance={report.recommended_rebalance}",
        f"top_jaccard={report.mean_top_jaccard:.3f} (p10={report.top_jaccard_p10:.3f})  "
        f"bottom_jaccard={report.mean_bottom_jaccard:.3f}",
        f"one_way_turnover={report.mean_one_way_turnover:.3f}  sign_flip={report.mean_sign_flip_rate:.3f}",
        f"cost_assumption={report.cost_bps:.1f}bp/{report.rebalance_days}d  "
        f"annual_cost_drag≈{report.annual_cost_drag:.2%}",
        f"scorecard={report.score:.0%}  verdict={report.verdict}",
        "",
        "gates:",
    ]
    for k, v in report.gates.items():
        lines.append(f"  [{'PASS' if v else 'FAIL'}] {k}")
    lines += ["", "quintile transition P(to|from) rows=from Q1..Q5, cols=to Q1..Q5:"]
    for i, row in enumerate(report.quintile_transition, start=1):
        cells = " ".join(f"{(x if x is not None else float('nan')):5.2f}" for x in row)
        lines.append(f"  Q{i}: {cells}")
    lines += ["", "notes:"]
    lines += [f"- {n}" for n in report.notes]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit signal stability and turnover")
    parser.add_argument("--signal", required=True, help="CSV [T x N] signal panel")
    parser.add_argument("--top-frac", type=float, default=0.1)
    parser.add_argument("--cost-bps", type=float, default=15.0)
    parser.add_argument(
        "--rebalance-days",
        type=int,
        default=None,
        help="Actual rebalance interval; default derives from signal half-life",
    )
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    signal = pd.read_csv(args.signal, index_col=0).to_numpy(dtype=float)
    report = audit_stability(
        signal,
        top_frac=args.top_frac,
        cost_bps=args.cost_bps,
        rebalance_days=args.rebalance_days,
    )
    print(render_text(report))
    if args.out:
        args.out.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
