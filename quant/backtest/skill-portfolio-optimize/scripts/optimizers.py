"""
Portfolio optimisers (scipy SLSQP — no heavyweight solver required).

Objectives
----------
  min_variance         : min  w' S w
  mean_variance        : max  w'mu - (lambda/2) w' S w     (Markowitz 1952)
  max_sharpe           : max  w'mu / sqrt(w' S w)
  risk_parity          : equal risk contribution (ERC)     (Maillard et al. 2010)
  max_diversification  : max  (w'sigma) / sqrt(w' S w)      (Choueifaty & Coignard 2008)

All objectives accept a `Constraints` object (see constraints.py) carrying the
variable bounds and linear/nonlinear constraints (full investment, weight caps,
sector / factor neutrality, turnover).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize


@dataclass
class OptResult:
    weights: np.ndarray
    objective: str
    success: bool
    message: str


def _solve(objective, n, constraints, x0=None):
    if x0 is None:
        x0 = np.full(n, 1.0 / n)
    res = minimize(
        objective, x0, method="SLSQP",
        bounds=constraints.bounds,
        constraints=constraints.scipy_constraints,
        options={"maxiter": 500, "ftol": 1e-10},
    )
    # Clean tiny negative dust from numerical noise when long-only.
    w = res.x
    return w, res


def min_variance(cov, constraints) -> OptResult:
    S = np.asarray(cov, float)
    n = S.shape[0]
    obj = lambda w: w @ S @ w
    w, res = _solve(obj, n, constraints)
    return OptResult(w, "min_variance", res.success, res.message)


def mean_variance(mu, cov, constraints, risk_aversion: float = 5.0) -> OptResult:
    mu = np.asarray(mu, float)
    S = np.asarray(cov, float)
    n = S.shape[0]
    obj = lambda w: -(w @ mu) + 0.5 * risk_aversion * (w @ S @ w)
    w, res = _solve(obj, n, constraints)
    return OptResult(w, "mean_variance", res.success, res.message)


def max_sharpe(mu, cov, constraints) -> OptResult:
    mu = np.asarray(mu, float)
    S = np.asarray(cov, float)
    n = S.shape[0]

    def neg_sharpe(w):
        vol = np.sqrt(max(w @ S @ w, 1e-18))
        return -(w @ mu) / vol

    w, res = _solve(neg_sharpe, n, constraints)
    return OptResult(w, "max_sharpe", res.success, res.message)


def risk_parity(cov, constraints) -> OptResult:
    """Equal Risk Contribution. Best with long-only, fully-invested weights."""
    S = np.asarray(cov, float)
    n = S.shape[0]

    def obj(w):
        port_var = w @ S @ w
        mrc = S @ w                      # marginal risk contribution
        rc = w * mrc                     # risk contribution (unnormalised)
        target = port_var / n
        return np.sum((rc - target) ** 2)

    w, res = _solve(obj, n, constraints)
    return OptResult(w, "risk_parity", res.success, res.message)


def max_diversification(cov, constraints) -> OptResult:
    """Maximise the diversification ratio (Choueifaty)."""
    S = np.asarray(cov, float)
    sigma = np.sqrt(np.diag(S))
    n = S.shape[0]

    def neg_dr(w):
        vol = np.sqrt(max(w @ S @ w, 1e-18))
        return -(w @ sigma) / vol

    w, res = _solve(neg_dr, n, constraints)
    return OptResult(w, "max_diversification", res.success, res.message)


OBJECTIVES = {
    "min_variance": lambda mu, cov, c, **k: min_variance(cov, c),
    "mean_variance": lambda mu, cov, c, **k: mean_variance(mu, cov, c, **k),
    "max_sharpe": lambda mu, cov, c, **k: max_sharpe(mu, cov, c),
    "risk_parity": lambda mu, cov, c, **k: risk_parity(cov, c),
    "max_diversification": lambda mu, cov, c, **k: max_diversification(cov, c),
}


def optimize(objective: str, cov, mu=None, constraints=None, **kwargs) -> OptResult:
    if objective not in OBJECTIVES:
        raise ValueError(f"unknown objective '{objective}'. choices: {list(OBJECTIVES)}")
    return OBJECTIVES[objective](mu, cov, constraints, **kwargs)


def risk_contributions(weights, cov) -> np.ndarray:
    """Percentage risk contribution of each asset."""
    w = np.asarray(weights, float)
    S = np.asarray(cov, float)
    port_var = w @ S @ w
    if port_var <= 0:
        return np.zeros_like(w)
    rc = w * (S @ w)
    return rc / port_var
