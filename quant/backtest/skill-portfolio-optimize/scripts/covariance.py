"""
Covariance estimation for portfolio optimisation.

Sample covariance is noisy and often non-invertible when the number of assets
approaches the number of observations. Ledoit-Wolf shrinkage pulls the sample
covariance toward a structured target, producing a well-conditioned, positive
definite estimate.

Reference
---------
Ledoit, O., & Wolf, M. (2004). "A well-conditioned estimator for large-
    dimensional covariance matrices." Journal of Multivariate Analysis, 88(2).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sample_cov(returns: pd.DataFrame) -> pd.DataFrame:
    return returns.cov()


def ledoit_wolf_cov(returns: pd.DataFrame) -> pd.DataFrame:
    """Ledoit-Wolf shrunk covariance (annualisation left to the caller)."""
    from sklearn.covariance import LedoitWolf

    X = returns.dropna(how="any")
    lw = LedoitWolf().fit(X.values)
    cov = pd.DataFrame(lw.covariance_, index=returns.columns, columns=returns.columns)
    return cov


def nearest_psd(cov: pd.DataFrame, epsilon: float = 1e-10) -> pd.DataFrame:
    """Clip negative eigenvalues so the matrix is positive semi-definite."""
    vals, vecs = np.linalg.eigh(cov.values)
    vals = np.clip(vals, epsilon, None)
    psd = (vecs * vals) @ vecs.T
    psd = (psd + psd.T) / 2.0
    return pd.DataFrame(psd, index=cov.index, columns=cov.columns)


def estimate_cov(returns: pd.DataFrame, method: str = "ledoit_wolf",
                 periods_per_year: int = 252) -> pd.DataFrame:
    """
    Estimate an annualised, PSD covariance matrix.

    method : 'ledoit_wolf' (default) | 'sample'
    """
    if method == "sample":
        cov = sample_cov(returns)
    elif method == "ledoit_wolf":
        cov = ledoit_wolf_cov(returns)
    else:
        raise ValueError(f"unknown method: {method}")
    cov = nearest_psd(cov)
    return cov * periods_per_year


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    R = pd.DataFrame(rng.normal(0, 0.01, size=(252, 8)),
                     columns=[f"A{i}" for i in range(8)])
    cov = estimate_cov(R)
    vals = np.linalg.eigvalsh(cov.values)
    print("annualised cov shape:", cov.shape, "| min eigenvalue:", round(vals.min(), 6),
          "| PSD:", bool(vals.min() >= 0))
