"""
Daily cross-sectional WLS regression -> factor returns and specific returns.

Model (Barra-style):
    r_{i,t+1} = sum_k X_{i,k,t} * f_{k,t} + u_{i,t}

For each date t we regress next-period stock returns on the exposures
(style factors + industry dummies) with weights proportional to sqrt(market
cap) -- larger names get more weight, as in commercial risk models. The fitted
coefficients are the *factor returns* f_t; the residuals are the *specific
(idiosyncratic) returns* u_t.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from exposures import compute_exposures, industry_dummies


def _wls(y: np.ndarray, X: np.ndarray, w: np.ndarray):
    """Weighted least squares via normal equations with a small ridge."""
    sw = np.sqrt(w)
    Xw = X * sw[:, None]
    yw = y * sw
    XtX = Xw.T @ Xw
    XtX += np.eye(XtX.shape[0]) * 1e-8        # tiny ridge for stability
    beta = np.linalg.solve(XtX, Xw.T @ yw)
    resid = y - X @ beta
    return beta, resid


def estimate_factor_returns(
    returns: pd.DataFrame,
    market_cap: pd.DataFrame,
    industry: pd.Series,
    start: pd.Timestamp | None = None,
    min_history: int = 130,
) -> dict:
    """
    Roll the cross-sectional regression forward.

    Returns
    -------
    dict with:
      factor_returns : DataFrame [date x factor]    (style + industry)
      specific_returns : DataFrame [date x symbol]
      last_exposures : DataFrame [symbol x factor]  (most recent date)
    """
    dates = returns.index
    symbols = list(returns.columns)
    ind_dum = industry_dummies(industry, symbols)

    fac_rows, spec_rows, dates_used = [], [], []
    last_exposures = None

    for t in range(min_history, len(dates) - 1):
        asof = dates[t]
        try:
            styles = compute_exposures(returns, market_cap, asof=asof)
        except ValueError:
            continue
        styles = styles.reindex(symbols)
        X = pd.concat([styles, ind_dum], axis=1).dropna(how="any")
        if X.shape[0] < X.shape[1] + 2:
            continue  # need more cross-sectional names than factors

        fwd = returns.iloc[t + 1].reindex(X.index)
        cap = market_cap.loc[:asof].iloc[-1].reindex(X.index).fillna(0.0)
        valid = fwd.notna() & (cap > 0)
        if valid.sum() < X.shape[1] + 2:
            continue
        Xv, yv, wv = X[valid].to_numpy(float), fwd[valid].to_numpy(float), np.sqrt(cap[valid].to_numpy(float))

        beta, resid = _wls(yv, Xv, wv)
        fac_rows.append(pd.Series(beta, index=X.columns, name=asof))
        spec_rows.append(pd.Series(resid, index=X.index[valid], name=asof))
        dates_used.append(asof)
        last_exposures = X

    factor_returns = pd.DataFrame(fac_rows)
    specific_returns = pd.DataFrame(spec_rows)
    return {
        "factor_returns": factor_returns,
        "specific_returns": specific_returns,
        "last_exposures": last_exposures,
        "n_periods": len(dates_used),
    }


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent))
    from data_source import get_return_panel, get_market_cap, get_industry

    # A structural model needs many more names than factors; use a 40-name set.
    syms = [f"{600000 + i:06d}.SH" if i % 2 else f"{i + 1:06d}.SZ" for i in range(40)]
    rets = get_return_panel(syms, "20210101", "20231231")
    cap = get_market_cap(syms, "20210101", "20231231")
    ind = get_industry(syms)
    out = estimate_factor_returns(rets, cap, ind)
    print("periods:", out["n_periods"])
    print("\nannualised mean factor returns:")
    print((out["factor_returns"].mean() * 252).round(4))
