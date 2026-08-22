"""
Risk-model orchestrator.

Builds a Barra-style structural risk model from a returns panel and produces:
  * factor returns (style + industry),
  * annualised factor covariance F and specific variance D,
  * the most recent exposure matrix,
  * (optionally) a full risk attribution for a given portfolio.

Programmatic
------------
    from risk_model import build_risk_model
    model = build_risk_model(returns, market_cap, industry)
    # model["factor_cov"], model["specific_var"], model["exposures"]
    from risk_attribution import decompose_risk, render_attribution
    attr = decompose_risk(weights, model["exposures"], model["factor_cov"], model["specific_var"])
    print(render_attribution(attr))

CLI
---
    python risk_model.py --demo
    python risk_model.py --returns returns.csv --weights weights.csv --out model.json
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import pandas as pd

from cross_section_reg import estimate_factor_returns
from factor_cov import factor_covariance, specific_risk
from risk_attribution import decompose_risk, render_attribution


def asset_covariance(
    exposures: pd.DataFrame,        # symbol x factor
    factor_cov: pd.DataFrame,       # factor x factor (K x K)
    specific_var: pd.Series,        # symbol -> variance
) -> pd.DataFrame:
    """
    Assemble the full asset covariance  Sigma = X F X' + diag(Delta)  as a
    [symbol x symbol] matrix. THIS is what skill-portfolio-optimize consumes as
    its `cov` input (NOT the K x K factor_cov). Missing specific variances are
    filled with the median.
    """
    syms = list(exposures.index)
    facs = list(factor_cov.index)
    X = exposures.reindex(index=syms, columns=facs).fillna(0.0).to_numpy(float)
    F = factor_cov.to_numpy(float)
    D = specific_var.reindex(syms).fillna(specific_var.median()).to_numpy(float)
    Sigma = X @ F @ X.T + np.diag(D)
    Sigma = (Sigma + Sigma.T) / 2.0     # symmetrise against fp noise
    return pd.DataFrame(Sigma, index=syms, columns=syms)


def build_risk_model(
    returns: pd.DataFrame,
    market_cap: pd.DataFrame,
    industry: pd.Series,
    factor_halflife: float = 90.0,
    specific_halflife: float = 60.0,
    cov_method: str = "ewma",
) -> dict:
    fr = estimate_factor_returns(returns, market_cap, industry)
    if fr["n_periods"] < 20:
        raise ValueError(f"too few regression periods ({fr['n_periods']}); need a longer history")
    F = factor_covariance(fr["factor_returns"], halflife=factor_halflife, method=cov_method)
    D = specific_risk(fr["specific_returns"], halflife=specific_halflife)
    exposures = fr["last_exposures"]
    return {
        "factor_returns": fr["factor_returns"],
        "factor_cov": F,                                      # K x K factor covariance
        "specific_var": D,
        "exposures": exposures,
        "asset_cov": asset_covariance(exposures, F, D),       # symbol x symbol Sigma=XFX'+D
        "n_periods": fr["n_periods"],
        "factors": list(F.index),
    }


def summarize(model: dict) -> dict:
    F = model["factor_cov"]
    fr = model["factor_returns"]
    return {
        "n_periods": model["n_periods"],
        "n_factors": len(model["factors"]),
        "factors": model["factors"],
        "annualised_factor_vol": (np.sqrt(np.diag(F))).round(4).to_dict()
            if hasattr(np.sqrt(np.diag(F)), "to_dict") else
            dict(zip(model["factors"], np.sqrt(np.diag(F)).round(4))),
        "annualised_factor_return": (fr.mean() * 252).round(4).to_dict(),
    }


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Barra-style structural risk model")
    ap.add_argument("--returns", help="CSV [date x symbol] returns")
    ap.add_argument("--market-cap", dest="market_cap",
                    help="CSV [date x symbol] market cap (optional; else sourced from panda_data over the returns window)")
    ap.add_argument("--weights", help="CSV symbol,weight for risk attribution")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--out", help="write JSON summary + attribution here")
    args = ap.parse_args()

    from data_source import get_return_panel, get_market_cap, get_industry
    if args.demo or not args.returns:
        syms = [f"{600000 + i:06d}.SH" if i % 2 else f"{i + 1:06d}.SZ" for i in range(40)]
        rets = get_return_panel(syms, "20210101", "20231231")
        cap = get_market_cap(syms, "20210101", "20231231")
        ind = get_industry(syms)
    else:
        rets = pd.read_csv(args.returns, index_col=0, parse_dates=True)
        syms = list(rets.columns)
        # Derive the market-cap window from the user's returns, not a fixed
        # hardcoded range, so any history works without crashing.
        start = rets.index.min().strftime("%Y%m%d")
        end = rets.index.max().strftime("%Y%m%d")
        if args.market_cap:
            cap = pd.read_csv(args.market_cap, index_col=0, parse_dates=True)
        else:
            cap = get_market_cap(syms, start, end)
        ind = get_industry(syms)

    model = build_risk_model(rets, cap, ind)
    summary = summarize(model)
    print("=" * 64)
    print(" RISK MODEL SUMMARY")
    print("=" * 64)
    print(f" regression periods : {summary['n_periods']}")
    print(f" factors ({summary['n_factors']}) : {', '.join(summary['factors'])}")
    print(" annualised factor volatility:")
    for k, v in summary["annualised_factor_vol"].items():
        print(f"   {k:<14} {v:.4f}")

    attr = None
    if args.weights:
        w = pd.read_csv(args.weights)
        weights = w.set_index(w.columns[0])[w.columns[1]]
    else:
        weights = pd.Series(1.0 / len(syms), index=model["exposures"].index)  # equal weight
    attr = decompose_risk(weights, model["exposures"], model["factor_cov"], model["specific_var"])
    print("\n" + render_attribution(attr))

    if args.out:
        payload = {
            "summary": summary,
            "attribution": {
                "total_vol_annual": attr["total_vol_annual"],
                "pct_factor_risk": attr["pct_factor_risk"],
                "pct_specific_risk": attr["pct_specific_risk"],
                "factor_table": attr["factor_table"].round(6).to_dict(orient="index"),
            },
        }
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"\nJSON written to {args.out}")


if __name__ == "__main__":
    main()
