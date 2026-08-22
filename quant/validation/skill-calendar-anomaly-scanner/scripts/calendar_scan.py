"""Calendar anomaly scanner with HAC t-stats, FDR control and half-sample robustness."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from math import erfc, sqrt
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class BucketStat:
    bucket: str
    family: str
    n: int
    mean: float
    excess_mean: float
    tstat: float
    hac_tstat: float
    hac_p: float
    sharpe_ann: float
    bootstrap_p: float
    bh_q: float
    half_sample_same_sign: bool


@dataclass
class CalendarReport:
    n_obs: int
    overall_mean: float
    overall_sharpe_ann: float
    weekday: list[BucketStat]
    month: list[BucketStat]
    month_edge: list[BucketStat]
    turn_of_month: list[BucketStat]
    strongest: str
    n_raw_significant: int
    n_bh_significant: int
    verdict: str
    score: float
    gates: dict[str, bool]
    notes: list[str]


def _dummy_contrast(y: np.ndarray, indicator: np.ndarray, lag: int = 5) -> tuple[float, float, float]:
    """OLS bucket-vs-complement contrast with classical and Newey-West t-stats."""
    mask = np.isfinite(y)
    yy = y[mask]
    dd = indicator[mask].astype(float)
    n = yy.size
    if n < lag + 5 or dd.sum() < 5 or (1 - dd).sum() < 5:
        return (float("nan"),) * 3
    n1 = int(dd.sum())
    n0 = n - n1
    mean1 = float(yy[dd == 1].mean())
    mean0 = float(yy[dd == 0].mean())
    effect = mean1 - mean0
    fitted = np.where(dd == 1, mean1, mean0)
    resid = yy - fitted
    var1 = float(np.sum(resid[dd == 1] ** 2) / max(n1 - 1, 1))
    var0 = float(np.sum(resid[dd == 0] ** 2) / max(n0 - 1, 1))
    classical_se = float(np.sqrt(max(var1 / n1 + var0 / n0, 0.0)))
    classical_t = float(effect / classical_se) if classical_se > 0 else float("nan")

    # Influence sequence for mean(bucket) - mean(complement). Newey-West
    # variance is the long-run variance of these weighted residual scores.
    influence = resid * np.where(dd == 1, 1.0 / n1, -1.0 / n0)
    hac_var = float(np.sum(influence**2))
    for ell in range(1, lag + 1):
        weight = 1.0 - ell / (lag + 1.0)
        hac_var += 2.0 * weight * float(
            np.sum(influence[ell:] * influence[:-ell])
        )
    hac_se = float(np.sqrt(max(hac_var, 0.0)))
    hac_t = float(effect / hac_se) if hac_se > 0 else float("nan")
    return float(effect), classical_t, hac_t


def _block_bootstrap_p(
    y: np.ndarray,
    indicator: np.ndarray,
    observed: float,
    n_boot: int = 500,
    block_size: int = 5,
    seed: int = 0,
) -> float:
    """Residual moving-block bootstrap for the bucket-vs-complement contrast."""
    mask = np.isfinite(y)
    yy = y[mask]
    dd = indicator[mask]
    if yy.size < 10 or not np.isfinite(observed):
        return float("nan")
    rng = np.random.default_rng(seed)
    residual = yy - yy.mean()
    block_size = min(max(1, block_size), yy.size)
    starts = np.arange(yy.size - block_size + 1)
    blocks_needed = int(np.ceil(yy.size / block_size))
    count = 0
    for _ in range(n_boot):
        chosen = rng.choice(starts, size=blocks_needed, replace=True)
        sampled = np.concatenate(
            [residual[s : s + block_size] for s in chosen]
        )[: yy.size]
        synthetic = yy.mean() + sampled
        effect = float(synthetic[dd].mean() - synthetic[~dd].mean())
        if abs(effect) >= abs(observed):
            count += 1
    return float((count + 1) / (n_boot + 1))


def _bh_qvalues(pvals: list[float]) -> list[float]:
    """Benjamini-Hochberg q-values; non-finite p treated as 1.0."""
    m = len(pvals)
    p = np.array([v if np.isfinite(v) else 1.0 for v in pvals], dtype=float)
    order = np.argsort(p)
    q = np.ones(m, dtype=float)
    prev = 1.0
    for rank in range(m, 0, -1):
        idx = int(order[rank - 1])
        prev = min(prev, p[idx] * m / rank)
        q[idx] = prev
    return [float(v) for v in q]


def _family_stats(
    returns: pd.Series,
    labels: pd.Series,
    family: str,
    periods_per_year: int,
    nw_lag: int,
) -> list[BucketStat]:
    out: list[BucketStat] = []
    y = returns.to_numpy(dtype=float)
    aligned_labels = pd.Series(labels, index=returns.index).to_numpy()
    for key, grp in returns.groupby(labels):
        arr = grp.to_numpy(dtype=float)
        arr = arr[np.isfinite(arr)]
        n = int(arr.size)
        if n < 5:
            out.append(
                BucketStat(
                    str(key), family, n, float("nan"), float("nan"), float("nan"),
                    float("nan"), float("nan"), float("nan"), float("nan"),
                    float("nan"), False,
                )
            )
            continue
        mean = float(arr.mean())
        std = float(arr.std(ddof=1))
        indicator = aligned_labels == key
        contrast, tstat, hac = _dummy_contrast(y, indicator, lag=nw_lag)
        sharpe = float(mean / std * np.sqrt(periods_per_year)) if std > 0 else float("nan")
        hac_p = float(erfc(abs(hac) / sqrt(2))) if np.isfinite(hac) else float("nan")
        stable_seed = sum(ord(c) for c in f"{family}:{key}")
        boot_p = _block_bootstrap_p(y, indicator, contrast, seed=stable_seed)
        # Compare the same bucket-vs-complement contrast in chronological halves.
        same = False
        cut = len(y) // 2
        if indicator[:cut].sum() >= 5 and indicator[cut:].sum() >= 5:
            c1 = float(y[:cut][indicator[:cut]].mean() - y[:cut][~indicator[:cut]].mean())
            c2 = float(y[cut:][indicator[cut:]].mean() - y[cut:][~indicator[cut:]].mean())
            same = bool(np.sign(c1) == np.sign(c2) and np.sign(c1) != 0)
        out.append(
            BucketStat(
                bucket=str(key),
                family=family,
                n=n,
                mean=mean,
                excess_mean=contrast,
                tstat=tstat,
                hac_tstat=hac,
                hac_p=hac_p,
                sharpe_ann=sharpe,
                bootstrap_p=boot_p,
                bh_q=float("nan"),
                half_sample_same_sign=same,
            )
        )
    return out


def scan_calendar(
    dates: pd.DatetimeIndex,
    returns: np.ndarray,
    periods_per_year: int = 252,
    nw_lag: int = 5,
    alpha: float = 0.05,
) -> CalendarReport:
    s = pd.Series(returns, index=pd.DatetimeIndex(dates), dtype=float)
    s = s[np.isfinite(s.to_numpy(dtype=float))]
    if not s.index.is_unique:
        raise ValueError("dates must be unique")
    s = s.sort_index()
    overall = float(s.mean())
    overall_std = float(s.std(ddof=1))
    overall_sharpe = float(overall / overall_std * np.sqrt(periods_per_year)) if overall_std > 0 else float("nan")

    weekday_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    weekday = _family_stats(s, s.index.weekday.map(weekday_map), "weekday", periods_per_year, nw_lag)
    month = _family_stats(s, s.index.month.map(lambda m: f"M{m:02d}"), "month", periods_per_year, nw_lag)

    edge = pd.Series("mid", index=s.index)
    edge[s.index.day <= 3] = "month_start"
    edge[s.index.is_month_end | (s.index.day >= 28)] = "month_end"
    month_edge = _family_stats(s, edge, "month_edge", periods_per_year, nw_lag)

    # Turn-of-month: last 1 trading day of month + first 3
    tom = pd.Series("other", index=s.index)
    # mark month starts
    month_starts = s.index.to_series().groupby([s.index.year, s.index.month]).head(3).index
    month_ends = s.index.to_series().groupby([s.index.year, s.index.month]).tail(1).index
    tom.loc[tom.index.isin(month_ends)] = "tom_window"
    tom.loc[tom.index.isin(month_starts)] = "tom_window"
    turn_of_month = _family_stats(s, tom, "turn_of_month", periods_per_year, nw_lag)

    all_stats = weekday + month + month_edge + turn_of_month
    # FDR is applied to one coherent p-value family: asymptotic HAC p-values.
    pvals = [b.hac_p if np.isfinite(b.hac_p) else 1.0 for b in all_stats]
    qvals = _bh_qvalues(pvals)
    for b, q in zip(all_stats, qvals):
        b.bh_q = q

    def _sort(items: list[BucketStat]) -> list[BucketStat]:
        return sorted(items, key=lambda x: abs(x.hac_tstat) if np.isfinite(x.hac_tstat) else -1, reverse=True)

    weekday, month, month_edge, turn_of_month = map(_sort, (weekday, month, month_edge, turn_of_month))
    all_stats = weekday + month + month_edge + turn_of_month

    valid = [b for b in all_stats if np.isfinite(b.hac_tstat)]
    strongest_stat = max(valid, key=lambda x: abs(x.hac_tstat)) if valid else None
    strongest = (
        f"{strongest_stat.family}:{strongest_stat.bucket}" if strongest_stat else "none"
    )
    n_raw = sum(1 for b in valid if abs(b.hac_tstat) >= 1.96)
    n_bh = sum(1 for b in all_stats if np.isfinite(b.bh_q) and b.bh_q <= alpha)
    robust = [b for b in all_stats if np.isfinite(b.bh_q) and b.bh_q <= alpha and b.half_sample_same_sign]

    if robust:
        verdict = "ROBUST_ANOMALY"
    elif n_bh > 0:
        verdict = "ANOMALY_AFTER_FDR"
    elif n_raw > 0:
        verdict = "RAW_ONLY_ANOMALY"
    else:
        verdict = "NO_CLEAR_ANOMALY"

    gates = {
        "has_bh_significant": bool(n_bh > 0),
        "has_half_sample_robust": bool(len(robust) > 0),
        "strongest_hac_|t|>=2": bool(valid and abs(valid[0].hac_tstat) >= 2),
        "not_only_small_sample": bool(
            strongest_stat is not None and strongest_stat.n >= 30
        ),
    }
    score = float(np.mean(list(gates.values())))

    return CalendarReport(
        n_obs=int(s.shape[0]),
        overall_mean=overall,
        overall_sharpe_ann=overall_sharpe,
        weekday=weekday,
        month=month,
        month_edge=month_edge,
        turn_of_month=turn_of_month,
        strongest=strongest,
        n_raw_significant=n_raw,
        n_bh_significant=n_bh,
        verdict=verdict,
        score=score,
        gates=gates,
        notes=[
            "HAC t-stat uses Newey-West with Bartlett weights.",
            "Each effect is bucket mean minus its complement; HAC and bootstrap test that same contrast.",
            "BH q-values use HAC normal-approximation p-values across all calendar buckets.",
            "Bootstrap p-values are reported separately and are not mixed into BH.",
            "Half-sample checks repeat the same contrast in chronological halves.",
            "Multiple testing means raw |t|>=2 is not enough for a claim.",
        ],
    )


def render_text(report: CalendarReport) -> str:
    def block(title: str, items: list[BucketStat]) -> list[str]:
        lines = [title, "bucket | n | contrast | hac_t | hac_p | boot_p | bh_q | half"]
        for b in items:
            lines.append(
                f"{b.bucket:12s} | {b.n:4d} | {b.excess_mean:8.5f} | {b.hac_tstat:5.2f} | "
                f"{b.hac_p:5.3f} | {b.bootstrap_p:6.3f} | {b.bh_q:5.3f} | "
                f"{'Y' if b.half_sample_same_sign else 'N'}"
            )
        return lines

    lines = [
        "=== Calendar Anomaly Scanner ===",
        f"n_obs={report.n_obs} overall_mean={report.overall_mean:.5f} "
        f"overall_sharpe={report.overall_sharpe_ann:.2f}",
        f"strongest={report.strongest}  raw_sig={report.n_raw_significant}  "
        f"bh_sig={report.n_bh_significant}  verdict={report.verdict}",
        f"quality_score={report.score:.0%}",
        "",
        "gates:",
    ]
    for k, v in report.gates.items():
        lines.append(f"  [{'PASS' if v else 'FAIL'}] {k}")
    lines += [""]
    lines += block("Weekday", report.weekday) + [""]
    lines += block("Month", report.month) + [""]
    lines += block("Month edge", report.month_edge) + [""]
    lines += block("Turn of month", report.turn_of_month) + [""]
    lines += ["notes:"]
    lines += [f"- {n}" for n in report.notes]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan calendar anomalies with FDR control")
    parser.add_argument("--input", required=True, help="CSV with date,return columns")
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--return-col", default="return")
    parser.add_argument("--nw-lag", type=int, default=5)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    df = pd.read_csv(args.input)
    dates = pd.to_datetime(df[args.date_col])
    rets = df[args.return_col].to_numpy(dtype=float)
    report = scan_calendar(dates, rets, nw_lag=args.nw_lag, alpha=args.alpha)
    print(render_text(report))
    if args.out:
        args.out.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
