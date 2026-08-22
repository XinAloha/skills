"""Purged / embargoed walk-forward validation for cross-sectional signals.

Research protocol (not a full backtester):
- expanding or rolling train windows
- optional embargo gap between train and test (López de Prado AFML ch.7 style)
- dual IC (Spearman / Pearson), ICIR, Q5-Q1 spread, OOS Sharpe
- train→test degradation, bootstrap CI, multi-gate scorecard
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass
class FoldResult:
    fold: int
    train_start: int
    train_end: int
    train_nominal_end: int
    purged_rows: int
    test_start: int
    test_end: int
    embargo: int
    train_ic: float
    test_ic: float
    test_pearson_ic: float
    test_icir: float
    test_sharpe: float
    test_mean_ret: float
    test_q5_q1: float
    ic_degradation: float  # 1 - test_ic/train_ic when train_ic>0


@dataclass
class WalkForwardReport:
    mode: str
    n_folds: int
    train_size: int
    test_size: int
    step: int
    embargo: int
    label_horizon: int
    n_oos_days: int
    mean_test_ic: float
    std_test_ic: float
    test_ic_ci95: tuple[float, float]
    mean_test_pearson_ic: float
    mean_test_icir: float
    mean_test_sharpe: float
    std_test_sharpe: float
    mean_q5_q1: float
    positive_ic_ratio: float
    mean_ic_degradation: float
    score: float
    gates: dict[str, bool]
    verdict: str
    folds: list[FoldResult]
    notes: list[str]


def _rank_ic(signal: np.ndarray, forward: np.ndarray) -> float:
    mask = np.isfinite(signal) & np.isfinite(forward)
    if mask.sum() < 5:
        return float("nan")
    s = pd.Series(signal[mask]).rank()
    f = pd.Series(forward[mask]).rank()
    return float(s.corr(f))


def _pearson_ic(signal: np.ndarray, forward: np.ndarray) -> float:
    mask = np.isfinite(signal) & np.isfinite(forward)
    if mask.sum() < 5:
        return float("nan")
    return float(np.corrcoef(signal[mask], forward[mask])[0, 1])


def _sharpe(returns: Iterable[float], periods_per_year: int = 252) -> float:
    arr = np.asarray(list(returns), dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size < 2 or arr.std(ddof=1) == 0:
        return float("nan")
    return float(arr.mean() / arr.std(ddof=1) * np.sqrt(periods_per_year))


def _icir(daily_ics: list[float]) -> float:
    arr = np.asarray(daily_ics, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size < 2 or arr.std(ddof=1) == 0:
        return float("nan")
    return float(arr.mean() / arr.std(ddof=1) * np.sqrt(252))


def long_short_return(signal_row: np.ndarray, fwd_row: np.ndarray, top_frac: float = 0.2) -> float:
    mask = np.isfinite(signal_row) & np.isfinite(fwd_row)
    s = signal_row[mask]
    f = fwd_row[mask]
    if s.size < 10:
        return float("nan")
    k = max(1, int(s.size * top_frac))
    order = np.argsort(s)
    return float(f[order[-k:]].mean() - f[order[:k]].mean())


def quintile_spread(signal_row: np.ndarray, fwd_row: np.ndarray) -> float:
    mask = np.isfinite(signal_row) & np.isfinite(fwd_row)
    s = signal_row[mask]
    f = fwd_row[mask]
    if s.size < 20:
        return float("nan")
    q = pd.qcut(pd.Series(s), 5, labels=False, duplicates="drop")
    if q.nunique() < 5:
        return float("nan")
    means = pd.Series(f).groupby(q).mean()
    return float(means.iloc[-1] - means.iloc[0])


def _block_bootstrap_ci(
    values: np.ndarray,
    n_boot: int = 1000,
    block_size: int = 5,
    seed: int = 0,
) -> tuple[float, float]:
    """Moving-block bootstrap CI for serially dependent daily IC observations."""
    vals = values[np.isfinite(values)]
    if vals.size == 0:
        return (float("nan"), float("nan"))
    if vals.size == 1:
        return (float(vals[0]), float(vals[0]))
    block_size = min(max(1, block_size), vals.size)
    rng = np.random.default_rng(seed)
    starts = np.arange(vals.size - block_size + 1)
    means = []
    blocks_needed = int(np.ceil(vals.size / block_size))
    for _ in range(n_boot):
        chosen = rng.choice(starts, size=blocks_needed, replace=True)
        sample = np.concatenate([vals[s : s + block_size] for s in chosen])[: vals.size]
        means.append(float(sample.mean()))
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def _validate_inputs(
    signal: np.ndarray,
    forward: np.ndarray,
    train_size: int,
    test_size: int,
    step: int,
    top_frac: float,
    embargo: int,
    label_horizon: int,
) -> None:
    if signal.ndim != 2 or forward.ndim != 2:
        raise ValueError("signal and forward must be 2D [T, N] arrays")
    if signal.shape != forward.shape:
        raise ValueError("signal and forward must share shape [T, N]")
    if signal.shape[1] < 10:
        raise ValueError("at least 10 cross-sectional names are required")
    if min(train_size, test_size, step, label_horizon) <= 0 or embargo < 0:
        raise ValueError("window sizes, step and label_horizon must be positive; embargo >= 0")
    if not 0 < top_frac < 0.5:
        raise ValueError("top_frac must be between 0 and 0.5")


def walk_forward(
    signal: np.ndarray,
    forward: np.ndarray,
    train_size: int = 120,
    test_size: int = 40,
    step: int = 40,
    top_frac: float = 0.2,
    embargo: int = 5,
    label_horizon: int = 1,
    mode: str = "rolling",
    periods_per_year: int = 252,
) -> WalkForwardReport:
    """Validate signal[T,N] against forward[T,N] with purged walk-forward folds."""
    _validate_inputs(
        signal, forward, train_size, test_size, step, top_frac, embargo, label_horizon
    )
    if mode not in {"rolling", "expanding"}:
        raise ValueError("mode must be 'rolling' or 'expanding'")

    t = signal.shape[0]
    folds: list[FoldResult] = []
    fold_id = 0
    start = 0
    notes = [
        "Training rows whose forward label reaches the test start are purged.",
        "Embargo adds an optional calendar gap after the nominal training window.",
        "PASS requires multi-gate scorecard, not a single mean IC threshold.",
    ]
    all_test_ics: list[float] = []

    while True:
        if mode == "rolling":
            tr0, nominal_tr1 = start, start + train_size
        else:
            tr0, nominal_tr1 = 0, start + train_size
        te0 = nominal_tr1 + embargo
        te1 = te0 + test_size
        if te1 > t:
            break
        # A label observed at row i spans through i + label_horizon. Purge rows
        # whose labels would overlap the first test observation.
        tr1 = min(nominal_tr1, te0 - label_horizon)
        if tr1 - tr0 < 20:
            raise ValueError("purging leaves fewer than 20 training rows")

        train_ics = [_rank_ic(signal[i], forward[i]) for i in range(tr0, tr1)]
        test_ics = [_rank_ic(signal[i], forward[i]) for i in range(te0, te1)]
        all_test_ics.extend(test_ics)
        test_pearson = [_pearson_ic(signal[i], forward[i]) for i in range(te0, te1)]
        test_rets = [long_short_return(signal[i], forward[i], top_frac=top_frac) for i in range(te0, te1)]
        spreads = [quintile_spread(signal[i], forward[i]) for i in range(te0, te1)]

        train_ic = float(np.nanmean(train_ics))
        test_ic = float(np.nanmean(test_ics))
        deg = float("nan")
        if np.isfinite(train_ic) and abs(train_ic) > 1e-8:
            # Positive means the absolute IC weakened out of sample; works for
            # both positive- and negative-direction factors.
            deg = float(1.0 - abs(test_ic) / abs(train_ic))

        folds.append(
            FoldResult(
                fold=fold_id,
                train_start=tr0,
                train_end=tr1,
                train_nominal_end=nominal_tr1,
                purged_rows=nominal_tr1 - tr1,
                test_start=te0,
                test_end=te1,
                embargo=embargo,
                train_ic=train_ic,
                test_ic=test_ic,
                test_pearson_ic=float(np.nanmean(test_pearson)),
                test_icir=_icir(test_ics),
                test_sharpe=_sharpe(test_rets, periods_per_year=periods_per_year),
                test_mean_ret=float(np.nanmean(test_rets)),
                test_q5_q1=float(np.nanmean(spreads)),
                ic_degradation=deg,
            )
        )
        fold_id += 1
        start += step

    if not folds:
        raise ValueError("not enough rows for walk-forward with given window/embargo sizes")

    test_ics = np.array([f.test_ic for f in folds], dtype=float)
    test_sharpes = np.array([f.test_sharpe for f in folds], dtype=float)
    pearsons = np.array([f.test_pearson_ic for f in folds], dtype=float)
    icirs = np.array([f.test_icir for f in folds], dtype=float)
    spreads = np.array([f.test_q5_q1 for f in folds], dtype=float)
    degs = np.array([f.ic_degradation for f in folds], dtype=float)

    pos_ratio = float(np.nanmean(test_ics > 0))
    mean_ic = float(np.nanmean(test_ics))
    mean_sharpe = float(np.nanmean(test_sharpes))
    mean_deg = float(np.nanmean(degs))
    daily_test_ics = np.asarray(all_test_ics, dtype=float)
    ci = _block_bootstrap_ci(daily_test_ics)

    gates = {
        "positive_ic_ratio>=0.60": bool(pos_ratio >= 0.60),
        "mean_test_ic>0": bool(mean_ic > 0),
        "mean_test_sharpe>0": bool(mean_sharpe > 0),
        "mean_q5_q1>0": bool(float(np.nanmean(spreads)) > 0),
        "ic_ci95_lower>0": bool(ci[0] > 0),
        "mean_degradation<0.70": bool(np.isfinite(mean_deg) and mean_deg < 0.70),
    }
    score = float(np.mean(list(gates.values())))
    # Require the hard OOS gates; soft gates only upgrade FAIL -> WEAK_PASS
    hard = gates["mean_test_ic>0"] and gates["positive_ic_ratio>=0.60"] and gates["ic_ci95_lower>0"]
    verdict = "PASS" if score >= 5 / 6 and hard else ("WEAK_PASS" if hard else "FAIL")

    return WalkForwardReport(
        mode=mode,
        n_folds=len(folds),
        train_size=train_size,
        test_size=test_size,
        step=step,
        embargo=embargo,
        label_horizon=label_horizon,
        n_oos_days=int(np.isfinite(daily_test_ics).sum()),
        mean_test_ic=mean_ic,
        std_test_ic=float(np.nanstd(test_ics, ddof=1)) if len(folds) > 1 else 0.0,
        test_ic_ci95=ci,
        mean_test_pearson_ic=float(np.nanmean(pearsons)),
        mean_test_icir=float(np.nanmean(icirs)),
        mean_test_sharpe=mean_sharpe,
        std_test_sharpe=float(np.nanstd(test_sharpes, ddof=1)) if len(folds) > 1 else 0.0,
        mean_q5_q1=float(np.nanmean(spreads)),
        positive_ic_ratio=pos_ratio,
        mean_ic_degradation=mean_deg,
        score=score,
        gates=gates,
        verdict=verdict,
        folds=folds,
        notes=notes,
    )


def render_text(report: WalkForwardReport) -> str:
    lines = [
        "=== Walk-Forward Validation Report ===",
        f"mode={report.mode} folds={report.n_folds} train={report.train_size} "
        f"test={report.test_size} step={report.step} embargo={report.embargo} "
        f"label_horizon={report.label_horizon} oos_days={report.n_oos_days}",
        f"mean_test_rank_ic={report.mean_test_ic:.4f} (±{report.std_test_ic:.4f}) "
        f"CI95=[{report.test_ic_ci95[0]:.4f}, {report.test_ic_ci95[1]:.4f}]",
        f"mean_test_pearson_ic={report.mean_test_pearson_ic:.4f}  mean_test_icir={report.mean_test_icir:.3f}",
        f"mean_test_sharpe={report.mean_test_sharpe:.3f} (±{report.std_test_sharpe:.3f})  "
        f"mean_q5_q1={report.mean_q5_q1:.5f}",
        f"positive_ic_ratio={report.positive_ic_ratio:.1%}  "
        f"mean_ic_degradation={report.mean_ic_degradation:.2f}",
        f"scorecard={report.score:.0%}  verdict={report.verdict}",
        "",
        "gates:",
    ]
    for k, v in report.gates.items():
        lines.append(f"  [{'PASS' if v else 'FAIL'}] {k}")
    lines += ["", "fold | purged | train_ic | test_ic | pearson | icir | sharpe | q5-q1 | degrade"]
    for f in report.folds:
        lines.append(
            f"{f.fold:4d} | {f.purged_rows:6d} | {f.train_ic:8.4f} | {f.test_ic:7.4f} | "
            f"{f.test_pearson_ic:7.4f} | "
            f"{f.test_icir:5.2f} | {f.test_sharpe:6.2f} | {f.test_q5_q1:6.4f} | {f.ic_degradation:7.2f}"
        )
    lines += ["", "notes:"]
    lines += [f"- {n}" for n in report.notes]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Purged walk-forward validate a signal panel")
    parser.add_argument("--signal", required=True, help="CSV [T x N] signal panel")
    parser.add_argument("--forward", required=True, help="CSV [T x N] forward returns")
    parser.add_argument("--train-size", type=int, default=120)
    parser.add_argument("--test-size", type=int, default=40)
    parser.add_argument("--step", type=int, default=40)
    parser.add_argument("--embargo", type=int, default=5)
    parser.add_argument(
        "--label-horizon",
        type=int,
        default=1,
        help="Number of rows covered by each forward-return label",
    )
    parser.add_argument("--top-frac", type=float, default=0.2)
    parser.add_argument("--mode", choices=["rolling", "expanding"], default="rolling")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    signal_df = pd.read_csv(args.signal, index_col=0)
    forward_df = pd.read_csv(args.forward, index_col=0)
    if not signal_df.index.equals(forward_df.index):
        raise ValueError("signal and forward CSV indices must match exactly")
    if list(signal_df.columns) != list(forward_df.columns):
        raise ValueError("signal and forward CSV asset columns must match exactly")
    signal = signal_df.to_numpy(dtype=float)
    forward = forward_df.to_numpy(dtype=float)
    report = walk_forward(
        signal,
        forward,
        train_size=args.train_size,
        test_size=args.test_size,
        step=args.step,
        embargo=args.embargo,
        label_horizon=args.label_horizon,
        top_frac=args.top_frac,
        mode=args.mode,
    )
    print(render_text(report))
    if args.out:
        args.out.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
