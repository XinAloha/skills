"""
Efficient frontier: sweep risk-aversion and trace (risk, return) pairs.
"""
from __future__ import annotations

import numpy as np

from optimizers import mean_variance


def efficient_frontier(mu, cov, constraints, n_points: int = 25,
                       lambda_range=(0.5, 50.0)):
    """
    Returns a list of dicts: {risk_aversion, expected_return, volatility, weights}.
    """
    mu = np.asarray(mu, float)
    S = np.asarray(cov, float)
    lambdas = np.geomspace(lambda_range[0], lambda_range[1], n_points)
    out = []
    for lam in lambdas:
        res = mean_variance(mu, S, constraints, risk_aversion=float(lam))
        w = res.weights
        out.append({
            "risk_aversion": float(lam),
            "expected_return": float(w @ mu),
            "volatility": float(np.sqrt(max(w @ S @ w, 0.0))),
            "weights": w,
            "success": res.success,
        })
    return out


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent))
    from constraints import build_constraints

    rng = np.random.default_rng(0)
    n = 6
    mu = rng.normal(0.08, 0.03, n)
    A = rng.normal(0, 1, (n, n))
    cov = (A @ A.T) / n * 0.04
    c = build_constraints(n, long_only=True)
    fr = efficient_frontier(mu, cov, c, n_points=6)
    for p in fr:
        print(f"lambda={p['risk_aversion']:6.2f}  ret={p['expected_return']:.4f}  "
              f"vol={p['volatility']:.4f}")
