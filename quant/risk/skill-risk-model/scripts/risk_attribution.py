r"""
Portfolio risk decomposition and attribution.

Given weights w, exposure matrix X (n x K), factor covariance F (K x K) and
specific variance D (n,), the total portfolio variance is:

    sigma_p^2 = w' (X F X' + diag(D)) w
              = (X'w)' F (X'w)   +   w' diag(D) w
                \___factor___/       \__specific__/

We report:
  * factor vs specific risk split,
  * portfolio factor exposures b = X'w,
  * each factor's contribution to variance (CCTR) and to volatility (MCTR),
    via Euler decomposition so contributions sum to the total.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def decompose_risk(
    weights: pd.Series,
    exposures: pd.DataFrame,      # symbol x factor
    factor_cov: pd.DataFrame,     # factor x factor
    specific_var: pd.Series,      # symbol -> variance
) -> dict:
    factors = list(factor_cov.index)
    symbols = list(exposures.index)

    w = weights.reindex(symbols).fillna(0.0).to_numpy(float)
    X = exposures.reindex(index=symbols, columns=factors).fillna(0.0).to_numpy(float)
    F = factor_cov.to_numpy(float)
    D = specific_var.reindex(symbols).fillna(specific_var.median()).to_numpy(float)

    b = X.T @ w                                   # portfolio factor exposure (K,)
    factor_var = float(b @ F @ b)
    specific_variance = float(np.sum((w ** 2) * D))
    total_var = factor_var + specific_variance
    total_vol = float(np.sqrt(max(total_var, 0.0)))

    # Euler / component contribution of each factor to *variance*:
    # CCTR_k = b_k * (F b)_k ; sum_k CCTR_k = factor_var
    Fb = F @ b
    cctr = b * Fb
    # COMPONENT contribution to volatility (Euler), normalised so the factor
    # components plus the specific component sum to total volatility. (This is
    # the component/CCTV, not the marginal MCTR = (Fb)_k / sigma_p.)
    if total_vol > 0:
        cctv = cctr / total_vol                   # variance-contrib / vol
        specific_vol_contrib = specific_variance / total_vol
    else:
        cctv = np.zeros_like(cctr)
        specific_vol_contrib = 0.0

    factor_tbl = pd.DataFrame({
        "exposure": b,
        "var_contribution": cctr,
        "vol_contribution": cctv,
        "pct_of_total_var": cctr / total_var if total_var > 0 else np.zeros_like(cctr),
    }, index=factors).sort_values("pct_of_total_var", ascending=False)

    return {
        "total_vol_annual": round(total_vol, 4),
        "factor_var": factor_var,
        "specific_var": specific_variance,
        "pct_factor_risk": round(factor_var / total_var, 4) if total_var > 0 else float("nan"),
        "pct_specific_risk": round(specific_variance / total_var, 4) if total_var > 0 else float("nan"),
        "specific_vol_contribution": round(specific_vol_contrib, 4),
        "factor_table": factor_tbl,
    }


def render_attribution(d: dict) -> str:
    lines = [
        "=" * 64,
        " PORTFOLIO RISK ATTRIBUTION",
        "=" * 64,
        f" total volatility (annual) : {d['total_vol_annual']:.2%}",
        f" factor risk share         : {d['pct_factor_risk']:.1%}",
        f" specific risk share       : {d['pct_specific_risk']:.1%}",
        "-" * 64,
        " factor contributions (sorted by % of total variance):",
        f"   {'factor':<14}{'exposure':>10}{'%var':>10}",
    ]
    for fac, row in d["factor_table"].iterrows():
        lines.append(f"   {fac:<14}{row['exposure']:>10.3f}{row['pct_of_total_var']:>10.1%}")
    lines.append("=" * 64)
    return "\n".join(lines)
