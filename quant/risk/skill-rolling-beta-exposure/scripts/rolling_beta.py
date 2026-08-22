"""Rolling CAPM-style exposure diagnostics with up/down beta and shrinkage."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class BetaReport:
    window: int
    n_obs: int
    latest_alpha: float
    latest_beta: float
    latest_beta_se: float
    latest_beta_ci95: tuple[float, float]
    latest_r2: float
    latest_resid_vol_ann: float
    mean_beta: float
    std_beta: float
    min_beta: float
    max_beta: float
    mean_r2: float
    up_beta: float
    down_beta: float
    beta_asymmetry: float
    shrunk_latest_beta: float
    max_abs_beta_change: float
    beta_above_1_ratio: float
    verdict: str
    score: float
    gates: dict[str, bool]
    series: dict[str, list[float | None]]
    notes: list[str]


def _ols_capm(y: np.ndarray, x: np.ndarray) -> tuple[float, float, float, float, float]:
    """Return alpha, beta, HC1-robust beta_se, r2 and residual std."""
    mask = np.isfinite(y) & np.isfinite(x)
    if mask.sum() < 8:
        return (float("nan"),) * 5
    yy, xx = y[mask], x[mask]
    n = yy.size
    x_design = np.column_stack([np.ones(n), xx])
    try:
        coef, _, _, _ = np.linalg.lstsq(x_design, yy, rcond=None)
    except np.linalg.LinAlgError:
        return (float("nan"),) * 5
    alpha, beta = float(coef[0]), float(coef[1])
    resid = yy - x_design @ coef
    dof = max(n - 2, 1)
    xtx_inv = np.linalg.pinv(x_design.T @ x_design)
    # White HC1 covariance is safer for heteroskedastic financial returns.
    meat = (x_design * resid[:, None]).T @ (x_design * resid[:, None])
    robust_cov = (n / dof) * xtx_inv @ meat @ xtx_inv
    beta_se = float(np.sqrt(max(robust_cov[1, 1], 0.0)))
    ss_tot = float(np.sum((yy - yy.mean()) ** 2))
    r2 = float(1 - np.sum(resid**2) / ss_tot) if ss_tot > 0 else float("nan")
    resid_std = float(np.sqrt(np.sum(resid**2) / dof))
    return alpha, beta, beta_se, r2, resid_std


def _conditional_beta(y: np.ndarray, x: np.ndarray, positive: bool) -> float:
    mask = np.isfinite(y) & np.isfinite(x)
    if positive:
        mask &= x > 0
    else:
        mask &= x < 0
    if mask.sum() < 8:
        return float("nan")
    _, beta, _, _, _ = _ols_capm(y[mask], x[mask])
    return beta


def _vasicek_shrink(beta: float, beta_se: float, prior_mean: float = 1.0, prior_var: float = 0.25) -> float:
    if not (np.isfinite(beta) and np.isfinite(beta_se)) or beta_se <= 0:
        return beta
    sample_var = beta_se**2
    sample_weight = prior_var / (prior_var + sample_var)
    return float(sample_weight * beta + (1 - sample_weight) * prior_mean)


def rolling_beta(
    asset: np.ndarray,
    market: np.ndarray,
    window: int = 60,
    periods_per_year: int = 252,
) -> BetaReport:
    if asset.ndim != 1 or market.ndim != 1 or asset.shape != market.shape:
        raise ValueError("asset and market must be same length")
    if window < 20 or len(asset) < window:
        raise ValueError("window must be >=20 and no larger than the input series")
    n = len(asset)
    alphas: list[float] = []
    betas: list[float] = []
    ses: list[float] = []
    r2s: list[float] = []
    resid_vols: list[float] = []

    for i in range(n):
        if i + 1 < window:
            for lst in (alphas, betas, ses, r2s, resid_vols):
                lst.append(float("nan"))
            continue
        a, b, se, r2, rv = _ols_capm(asset[i + 1 - window : i + 1], market[i + 1 - window : i + 1])
        alphas.append(a)
        betas.append(b)
        ses.append(se)
        r2s.append(r2)
        resid_vols.append(rv * np.sqrt(periods_per_year))

    valid = np.array([b for b in betas if np.isfinite(b)], dtype=float)
    if valid.size == 0:
        raise ValueError("no valid rolling windows")

    def _last(xs: list[float]) -> float:
        return next(v for v in reversed(xs) if np.isfinite(v))

    latest_beta = _last(betas)
    latest_se = _last(ses)
    latest_alpha = _last(alphas)
    latest_r2 = _last(r2s)
    latest_rv = _last(resid_vols)
    ci = (latest_beta - 1.96 * latest_se, latest_beta + 1.96 * latest_se)

    latest_asset = asset[-window:]
    latest_market = market[-window:]
    up_b = _conditional_beta(latest_asset, latest_market, positive=True)
    down_b = _conditional_beta(latest_asset, latest_market, positive=False)
    asym = float(up_b - down_b) if np.isfinite(up_b) and np.isfinite(down_b) else float("nan")
    shrunk = _vasicek_shrink(latest_beta, latest_se)

    beta_changes = np.diff(valid)
    max_chg = float(np.max(np.abs(beta_changes))) if beta_changes.size else 0.0
    mean_b = float(valid.mean())
    above = float(np.mean(np.abs(valid) > 1.0))
    mean_r2 = float(np.nanmean(r2s))

    if mean_b >= 1.2 or above >= 0.5:
        regime = "HIGH_BETA"
    elif abs(mean_b) <= 0.5:
        regime = "LOW_BETA"
    else:
        regime = "MODERATE_BETA"
    if np.isfinite(asym) and abs(asym) >= 0.35:
        regime = f"{regime}_ASYMMETRIC"

    gates = {
        "mean_r2>=0.20": bool(mean_r2 >= 0.20),
        "latest_beta_se<0.25": bool(latest_se < 0.25),
        "max_abs_beta_change<0.50": bool(max_chg < 0.50),
        "resid_vol_ann<0.40": bool(latest_rv < 0.40),
        "latest_beta_ci_width<0.75": bool((ci[1] - ci[0]) < 0.75),
        "conditional_betas_available": bool(np.isfinite(up_b) and np.isfinite(down_b)),
    }
    score = float(np.mean(list(gates.values())))

    return BetaReport(
        window=window,
        n_obs=n,
        latest_alpha=float(latest_alpha),
        latest_beta=float(latest_beta),
        latest_beta_se=float(latest_se),
        latest_beta_ci95=(float(ci[0]), float(ci[1])),
        latest_r2=float(latest_r2),
        latest_resid_vol_ann=float(latest_rv),
        mean_beta=mean_b,
        std_beta=float(valid.std(ddof=1)) if valid.size > 1 else 0.0,
        min_beta=float(valid.min()),
        max_beta=float(valid.max()),
        mean_r2=mean_r2,
        up_beta=float(up_b),
        down_beta=float(down_b),
        beta_asymmetry=asym,
        shrunk_latest_beta=float(shrunk),
        max_abs_beta_change=max_chg,
        beta_above_1_ratio=above,
        verdict=regime,
        score=score,
        gates=gates,
        series={
            "alpha": [float(x) if np.isfinite(x) else None for x in alphas],
            "beta": [float(x) if np.isfinite(x) else None for x in betas],
            "beta_se": [float(x) if np.isfinite(x) else None for x in ses],
            "r2": [float(x) if np.isfinite(x) else None for x in r2s],
            "resid_vol_ann": [float(x) if np.isfinite(x) else None for x in resid_vols],
        },
        notes=[
            "CAPM-style OLS with intercept and HC1 heteroskedasticity-robust beta SE.",
            "Up/Down beta uses the same latest rolling window as latest beta.",
            "Shrunk beta uses Vasicek/Bayes shrink toward prior mean=1, prior_var=0.25.",
        ],
    )


def render_text(report: BetaReport) -> str:
    lines = [
        "=== Rolling Beta / CAPM Exposure ===",
        f"window={report.window} n_obs={report.n_obs}",
        f"latest_alpha={report.latest_alpha:.5f}  latest_beta={report.latest_beta:.3f} "
        f"(se={report.latest_beta_se:.3f}, CI95=[{report.latest_beta_ci95[0]:.3f}, {report.latest_beta_ci95[1]:.3f}])",
        f"shrunk_beta={report.shrunk_latest_beta:.3f}  latest_r2={report.latest_r2:.3f}  "
        f"resid_vol_ann={report.latest_resid_vol_ann:.2%}",
        f"mean_beta={report.mean_beta:.3f} (±{report.std_beta:.3f}) "
        f"range=[{report.min_beta:.3f}, {report.max_beta:.3f}] mean_r2={report.mean_r2:.3f}",
        f"up_beta={report.up_beta:.3f} down_beta={report.down_beta:.3f} "
        f"asymmetry(up-down)={report.beta_asymmetry:.3f}",
        f"max_abs_beta_change={report.max_abs_beta_change:.3f} |P(|beta|>1)|={report.beta_above_1_ratio:.1%}",
        f"quality_score={report.score:.0%}  verdict={report.verdict}",
        "",
        "gates:",
    ]
    for k, v in report.gates.items():
        lines.append(f"  [{'PASS' if v else 'FAIL'}] {k}")
    lines += ["", "notes:"]
    lines += [f"- {n}" for n in report.notes]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rolling CAPM beta diagnostics")
    parser.add_argument("--asset", required=True, help="CSV single-column asset returns")
    parser.add_argument("--market", required=True, help="CSV single-column market returns")
    parser.add_argument("--window", type=int, default=60)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    asset = pd.read_csv(args.asset).iloc[:, -1].to_numpy(dtype=float)
    market = pd.read_csv(args.market).iloc[:, -1].to_numpy(dtype=float)
    report = rolling_beta(asset, market, window=args.window)
    print(render_text(report))
    if args.out:
        args.out.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
