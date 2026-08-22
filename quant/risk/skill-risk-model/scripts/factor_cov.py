"""
Factor covariance matrix F and specific-risk vector Delta.

  * Factor covariance: EWMA of the factor-return cross-products (so recent
    regimes weigh more), then PSD-clipped and annualised. A Ledoit-Wolf option
    is provided for short samples.
  * Specific risk: EWMA of squared specific returns per stock.

References
---------
RiskMetrics (1996) EWMA covariance; Ledoit & Wolf (2004) shrinkage.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _ewma_weights(n: int, halflife: float) -> np.ndarray:
    lam = 0.5 ** (1.0 / halflife)
    w = lam ** np.arange(n - 1, -1, -1)     # oldest..newest
    return w / w.sum()


def _nearest_psd(cov: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    vals, vecs = np.linalg.eigh(cov)
    vals = np.clip(vals, eps, None)
    out = (vecs * vals) @ vecs.T
    return (out + out.T) / 2.0


def factor_covariance(
    factor_returns: pd.DataFrame,
    halflife: float = 90.0,
    periods_per_year: int = 252,
    method: str = "ewma",
) -> pd.DataFrame:
    """Annualised factor covariance matrix F (factor x factor)."""
    F = factor_returns.dropna(how="any")
    cols = F.columns
    X = F.to_numpy(float)

    if method == "ledoit_wolf":
        from sklearn.covariance import LedoitWolf
        cov = LedoitWolf().fit(X - X.mean(axis=0, keepdims=True)).covariance_
    else:  # ewma
        w = _ewma_weights(X.shape[0], halflife)
        # Demean with the EWMA-weighted mean (consistent with specific_risk),
        # then form the EWMA-weighted second moment as a true weighted covariance.
        wmean = (X * w[:, None]).sum(axis=0, keepdims=True)
        Xc = X - wmean
        cov = (Xc * w[:, None]).T @ Xc        # weighted cross-product, sum(w)=1

    cov = _nearest_psd(cov) * periods_per_year
    return pd.DataFrame(cov, index=cols, columns=cols)


def specific_risk(
    specific_returns: pd.DataFrame,
    halflife: float = 60.0,
    periods_per_year: int = 252,
) -> pd.Series:
    """Annualised specific (idiosyncratic) variance per symbol."""
    out = {}
    for sym in specific_returns.columns:
        u = specific_returns[sym].dropna().to_numpy(float)
        if u.size < 5:
            continue
        w = _ewma_weights(u.size, halflife)
        var = float(np.sum(w * (u - np.average(u, weights=w)) ** 2))
        out[sym] = var * periods_per_year
    return pd.Series(out, name="specific_var")


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent))
    from data_source import get_return_panel, get_market_cap, get_industry
    from cross_section_reg import estimate_factor_returns

    syms = [f"{600000 + i:06d}.SH" if i % 2 else f"{i + 1:06d}.SZ" for i in range(40)]
    rets = get_return_panel(syms, "20210101", "20231231")
    cap = get_market_cap(syms, "20210101", "20231231")
    out = estimate_factor_returns(rets, cap, get_industry(syms))
    F = factor_covariance(out["factor_returns"])
    D = specific_risk(out["specific_returns"])
    print("factor cov shape:", F.shape, "| PSD:", bool(np.linalg.eigvalsh(F).min() >= 0))
    print("annualised factor vols:")
    print((np.sqrt(np.diag(F)) ).round(4))
    print("\nspecific vol (annualised):")
    print(np.sqrt(D).round(4))
