"""
Style-factor exposures for a Barra-style structural risk model.

Given a returns panel and market caps, build cross-sectionally standardised
style exposures. Each style is winsorised and z-scored *each date* so factor
returns are comparable through time.

Styles computed from returns + market cap (always available):
    SIZE        : ln(market cap)
    MOMENTUM    : cumulative return over [t-252, t-21]  (12-1 month)
    SHORT_REV   : trailing 21-day return (short-term reversal)
    VOLATILITY  : trailing 60-day return stdev (annualised)
    BETA        : 120-day rolling beta to the cap-weighted market

VALUE / LIQUIDITY require extra fields (book value, turnover); pass them via
`extra_exposures` if available — they are standardised the same way.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _winsorize(s: pd.Series, k: float = 3.0) -> pd.Series:
    med = s.median()
    mad = (s - med).abs().median()
    if mad == 0 or np.isnan(mad):
        return s
    lo, hi = med - k * 1.4826 * mad, med + k * 1.4826 * mad
    return s.clip(lo, hi)


def _zscore(s: pd.Series) -> pd.Series:
    sd = s.std(ddof=0)
    if sd == 0 or np.isnan(sd):
        return s * 0.0
    return (s - s.mean()) / sd


def standardize_cross_section(df: pd.DataFrame) -> pd.DataFrame:
    """Winsorise + z-score each column (one date's cross-section)."""
    return df.apply(lambda col: _zscore(_winsorize(col.dropna())).reindex(col.index))


def market_return(returns: pd.DataFrame, market_cap: pd.DataFrame) -> pd.Series:
    """Cap-weighted market return series."""
    w = market_cap.reindex_like(returns).shift(1)
    w = w.div(w.sum(axis=1), axis=0)
    return (returns * w).sum(axis=1)


def compute_exposures(
    returns: pd.DataFrame,
    market_cap: pd.DataFrame,
    asof: pd.Timestamp | None = None,
    extra_exposures: dict[str, pd.Series] | None = None,
) -> pd.DataFrame:
    """
    Compute standardised style exposures as of `asof` (default: last date).

    Returns a DataFrame indexed by symbol, columns = style factors.
    """
    if asof is None:
        asof = returns.index[-1]
    hist = returns.loc[:asof]
    if hist.shape[0] < 130:
        raise ValueError("need >= ~130 observations to build momentum/beta exposures")

    cap_hist = market_cap.loc[:asof]
    if cap_hist.empty:
        raise ValueError(
            f"market_cap has no observations on/before {asof:%Y-%m-%d}; its range "
            f"({market_cap.index.min()}..{market_cap.index.max()}) does not overlap "
            f"the returns history — pass an aligned --market-cap panel")
    cap_asof = cap_hist.iloc[-1]

    size = np.log(cap_asof.replace(0, np.nan))
    mom = (1 + hist.iloc[-252:-21]).prod() - 1 if hist.shape[0] > 252 else (1 + hist.iloc[:-21]).prod() - 1
    short_rev = (1 + hist.iloc[-21:]).prod() - 1
    vol = hist.iloc[-60:].std(ddof=0) * np.sqrt(252)

    # Beta only needs the trailing 120-day window, so compute the cap-weighted
    # market over just that slice (avoids an O(T) market recompute every call,
    # which made the rolling-regression loop O(T^2)).
    win = hist.iloc[-120:]
    mkt_win = market_return(win, market_cap)
    var_m = mkt_win.var(ddof=0)
    beta = win.apply(lambda col: col.cov(mkt_win) / var_m if var_m > 0 else np.nan)

    raw = pd.DataFrame({
        "SIZE": size,
        "MOMENTUM": mom,
        "SHORT_REV": short_rev,
        "VOLATILITY": vol,
        "BETA": beta,
    })
    if extra_exposures:
        for name, series in extra_exposures.items():
            raw[name] = series

    std = standardize_cross_section(raw)
    return std.dropna(how="all")


def industry_dummies(industry: pd.Series, symbols: list[str]) -> pd.DataFrame:
    """One-hot industry matrix (symbols x industries)."""
    ind = industry.reindex(symbols)
    dummies = pd.get_dummies(ind, prefix="IND").astype(float)
    dummies.index = symbols
    return dummies


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent))
    from data_source import get_return_panel, get_market_cap, get_industry

    syms = ["000001.SZ", "600000.SH", "000333.SZ", "600519.SH",
            "000651.SZ", "601318.SH", "600036.SH", "000858.SZ"]
    rets = get_return_panel(syms, "20220101", "20231231")
    cap = get_market_cap(syms, "20220101", "20231231")
    X = compute_exposures(rets, cap)
    print("exposures as of", rets.index[-1].date())
    print(X.round(3))
    print("\nindustry dummies:")
    print(industry_dummies(get_industry(syms), syms).head())
