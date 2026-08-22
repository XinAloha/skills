"""
Portfolio optimisation orchestrator.

Turns an alpha signal + a covariance matrix (+ constraints) into target weights
plus a diagnostics report: realised exposures, risk contributions, turnover and
whether each constraint binds.

Programmatic
------------
    from optimize_report import build_portfolio
    out = build_portfolio(objective="mean_variance", mu=alpha, cov=Sigma,
                          long_only=True, weight_cap=0.05,
                          sectors=sector_labels)
    print(out["report_text"]); weights = out["weights"]

CLI
---
    python optimize_report.py --signal alpha.csv --returns returns.csv \
        --objective mean_variance --weight-cap 0.05 --out weights.csv
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from constraints import build_constraints, turnover as _turnover
from covariance import estimate_cov
from optimizers import optimize, risk_contributions


def build_portfolio(
    objective: str,
    cov: pd.DataFrame,
    mu: pd.Series | None = None,
    long_only: bool = True,
    full_investment: bool = True,
    weight_cap: float | None = None,
    sectors: pd.Series | None = None,
    exposures: pd.DataFrame | None = None,
    w_prev: pd.Series | None = None,
    turnover_limit: float | None = None,
    net_exposure: float | None = None,
    risk_aversion: float = 5.0,
) -> dict:
    assets = list(cov.index)
    n = len(assets)

    mu_v = None if mu is None else mu.reindex(assets).fillna(0.0).to_numpy()
    sec_v = None if sectors is None else sectors.reindex(assets).to_numpy()
    exp_v = None if exposures is None else exposures.reindex(assets).to_numpy()
    wp_v = None if w_prev is None else w_prev.reindex(assets).fillna(0.0).to_numpy()

    cons = build_constraints(
        n, long_only=long_only, full_investment=full_investment,
        weight_cap=weight_cap, sectors=sec_v, exposures=exp_v,
        w_prev=wp_v, turnover_limit=turnover_limit, net_exposure=net_exposure,
    )

    res = optimize(objective, cov.to_numpy(), mu=mu_v, constraints=cons,
                   risk_aversion=risk_aversion)
    w = pd.Series(res.weights, index=assets)
    w[w.abs() < 1e-6] = 0.0  # drop dust

    rc = pd.Series(risk_contributions(res.weights, cov.to_numpy()), index=assets)
    port_vol = float(np.sqrt(res.weights @ cov.to_numpy() @ res.weights))

    diagnostics = {
        "objective": objective,
        "solver_success": bool(res.success),
        "solver_message": res.message,
        "n_assets": n,
        "n_holdings": int((w.abs() > 1e-6).sum()),
        "sum_weights": float(w.sum()),
        "max_weight": float(w.max()),
        "min_weight": float(w.min()),
        "gross_exposure": float(w.abs().sum()),
        "portfolio_volatility_annual": round(port_vol, 4),
        "top_risk_contributors": rc.sort_values(ascending=False).head(5).round(4).to_dict(),
    }
    if mu is not None:
        diagnostics["expected_return_annual"] = round(float(w @ mu_v), 4)
    if sectors is not None:
        sec_exp = w.groupby(sec_v).sum().round(4)
        diagnostics["sector_exposure"] = sec_exp.to_dict()
    if exposures is not None:
        diagnostics["factor_exposure"] = pd.Series(
            exp_v.T @ res.weights, index=exposures.columns).round(4).to_dict()
    if w_prev is not None:
        diagnostics["turnover"] = round(_turnover(res.weights, wp_v), 4)

    return {
        "weights": w,
        "diagnostics": diagnostics,
        "report_text": _render(w, diagnostics),
    }


def _render(weights: pd.Series, d: dict) -> str:
    lines = [
        "=" * 60,
        f" PORTFOLIO OPTIMISATION - {d['objective']}",
        "=" * 60,
        f" solver            : {'OK' if d['solver_success'] else 'FAILED'} ({d['solver_message']})",
        f" holdings          : {d['n_holdings']} / {d['n_assets']}",
        f" sum / gross       : {d['sum_weights']:.4f} / {d['gross_exposure']:.4f}",
        f" weight range      : [{d['min_weight']:.4f}, {d['max_weight']:.4f}]",
        f" portfolio vol(ann): {d['portfolio_volatility_annual']}",
    ]
    if "expected_return_annual" in d:
        lines.append(f" exp. return(ann)  : {d['expected_return_annual']}")
    if "turnover" in d:
        lines.append(f" turnover          : {d['turnover']}")
    if "sector_exposure" in d:
        lines.append(f" sector exposure   : {d['sector_exposure']}")
    if "factor_exposure" in d:
        lines.append(f" factor exposure   : {d['factor_exposure']}")
    lines.append("-" * 60)
    lines.append(" top weights:")
    for k, v in weights[weights.abs() > 1e-6].sort_values(ascending=False).head(8).items():
        lines.append(f"   {k:<12} {v:+.4f}")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    try:
        import sys
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Portfolio optimiser")
    ap.add_argument("--returns", help="CSV [date x symbol] returns, for covariance")
    ap.add_argument("--signal", help="CSV symbol,alpha for expected returns")
    ap.add_argument("--objective", default="mean_variance",
                    choices=["min_variance", "mean_variance", "max_sharpe",
                             "risk_parity", "max_diversification"])
    ap.add_argument("--weight-cap", type=float, default=None)
    ap.add_argument("--risk-aversion", type=float, default=5.0)
    ap.add_argument("--long-short", action="store_true", help="allow short positions")
    ap.add_argument("--out", help="write weights CSV here")
    ap.add_argument("--demo", action="store_true", help="run on synthetic data")
    args = ap.parse_args()

    if args.demo or not args.returns:
        from data_source import get_return_panel
        rets = get_return_panel(
            ["000001.SZ", "600000.SH", "000333.SZ", "600519.SH",
             "000651.SZ", "601318.SH", "600036.SH", "000858.SZ"],
            "20230101", "20231231")
    else:
        rets = pd.read_csv(args.returns, index_col=0, parse_dates=True)

    cov = estimate_cov(rets)
    mu = None
    if args.signal:
        s = pd.read_csv(args.signal)
        mu = s.set_index(s.columns[0])[s.columns[1]]
    elif args.objective in ("mean_variance", "max_sharpe"):
        mu = rets.mean() * 252  # naive momentum-ish prior for the demo

    out = build_portfolio(args.objective, cov, mu=mu,
                          long_only=not args.long_short,
                          weight_cap=args.weight_cap,
                          risk_aversion=args.risk_aversion)
    print(out["report_text"])
    if args.out:
        out["weights"].to_csv(args.out, header=["weight"])
        print(f"\nweights written to {args.out}")


if __name__ == "__main__":
    main()
