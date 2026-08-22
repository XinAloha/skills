"""
Build bounds and constraints for the optimisers.

Supported constraints
----------------------
  full_investment   : sum(w) == 1
  long_only         : w >= 0           (else lower bound = -weight_cap)
  weight_cap        : |w_i| <= cap
  sector_neutral    : for each sector, sum(w in sector) == target (default 0,
                      i.e. dollar-neutral by sector for a long-short book)
  exposure_neutral  : X' w == 0  for an exposure matrix X (factor neutrality)
  turnover_limit    : sum(|w - w_prev|) <= tau
  fully_invested... : combine as needed

A `Constraints` object exposes `.bounds` and `.scipy_constraints` consumed by
optimizers._solve.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class Constraints:
    n: int
    bounds: list = field(default_factory=list)
    scipy_constraints: list = field(default_factory=list)


def build_constraints(
    n: int,
    long_only: bool = True,
    full_investment: bool = True,
    weight_cap: Optional[float] = None,
    sectors: Optional[np.ndarray] = None,
    sector_targets: Optional[dict] = None,
    exposures: Optional[np.ndarray] = None,
    w_prev: Optional[np.ndarray] = None,
    turnover_limit: Optional[float] = None,
    net_exposure: Optional[float] = None,
) -> Constraints:
    """
    Parameters
    ----------
    n : number of assets.
    long_only : if True lower bound 0; else lower bound -(weight_cap or 1).
    full_investment : if True, enforce sum(w) == 1 (a fully-invested book).
    weight_cap : upper bound on |w_i|.
    sectors : length-n array of sector labels (for sector_neutral).
    sector_targets : {sector_label: target_sum}; default 0 for every sector.
    exposures : (n, k) factor-exposure matrix; enforces X' w == 0.
    w_prev : previous weights, required for turnover_limit.
    turnover_limit : max sum(|w - w_prev|).
    net_exposure : when `full_investment` is False, enforce sum(w) == net_exposure
        (use 0.0 for a dollar-neutral long-short book). This anchors objectives
        that carry a return term (mean_variance / max_sharpe). NOTE: variance-only
        objectives (min_variance / risk_parity) are NOT anchored by net_exposure
        alone — with sum(w)=0 the zero portfolio is still feasible (zero variance).
        For those, use a fully-invested long-only book (full_investment=True).
    """
    cap = weight_cap if weight_cap is not None else 1.0
    lo = 0.0 if long_only else -cap
    bounds = [(lo, cap)] * n

    cons = []
    if full_investment:
        cons.append({"type": "eq", "fun": lambda w: np.sum(w) - 1.0})
    elif net_exposure is not None:
        cons.append({"type": "eq", "fun": (lambda w, t=float(net_exposure): np.sum(w) - t)})
    elif sectors is None and exposures is None:
        # No sum/net anchor and no neutrality constraints: min_variance /
        # risk_parity will happily return w=0 (zero variance is feasible).
        warnings.warn(
            "Unanchored portfolio: full_investment=False with no net_exposure, "
            "sectors or exposures. Variance-only objectives (min_variance, "
            "risk_parity) collapse to the all-zero portfolio. Pass net_exposure=0.0 "
            "for a return-driven long-short book (mean_variance/max_sharpe), or use "
            "full_investment=True for a long-only variance book.",
            stacklevel=2,
        )

    if sectors is not None:
        sectors = np.asarray(sectors)
        targets = sector_targets or {}
        for s in np.unique(sectors):
            mask = (sectors == s).astype(float)
            tgt = float(targets.get(s, 0.0))
            cons.append({"type": "eq", "fun": (lambda w, m=mask, t=tgt: m @ w - t)})

    if exposures is not None:
        X = np.asarray(exposures, float)            # (n, k)
        for k in range(X.shape[1]):
            col = X[:, k]
            cons.append({"type": "eq", "fun": (lambda w, c=col: c @ w)})

    if turnover_limit is not None:
        if w_prev is None:
            raise ValueError("turnover_limit requires w_prev")
        wp = np.asarray(w_prev, float)
        # inequality g(w) >= 0 : tau - sum|w - wp| >= 0
        cons.append({"type": "ineq",
                     "fun": (lambda w, p=wp, t=turnover_limit: t - np.sum(np.abs(w - p)))})

    return Constraints(n=n, bounds=bounds, scipy_constraints=cons)


def turnover(weights, w_prev) -> float:
    return float(np.sum(np.abs(np.asarray(weights, float) - np.asarray(w_prev, float))))
