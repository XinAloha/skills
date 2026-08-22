"""Shared low-level utility functions for Alpha191 and Alpha101 computation.

All functions operate on pandas DataFrames indexed by date (rows) × symbol (columns),
following the same layout produced by ``build_matrices`` in ``alpha_ops.py``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import rankdata


# ─── Time-series operations ───────────────────────────────────────────────────

def delay(x: pd.DataFrame, n: int) -> pd.DataFrame:
    return x.shift(n)


def delta(x: pd.DataFrame, n: int) -> pd.DataFrame:
    return x.diff(n)


def ts_sum(x: pd.DataFrame, n: int) -> pd.DataFrame:
    return x.rolling(n).sum()


def ts_mean(x: pd.DataFrame, n: int) -> pd.DataFrame:
    return x.rolling(n).mean()


def ts_std(x: pd.DataFrame, n: int) -> pd.DataFrame:
    return x.rolling(n).std()


def ts_max(x: pd.DataFrame, n: int) -> pd.DataFrame:
    return x.rolling(n).max()


def ts_min(x: pd.DataFrame, n: int) -> pd.DataFrame:
    return x.rolling(n).min()


def ts_rank(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """Rolling normalized rank of the last observation within a window."""
    return x.rolling(n).apply(
        lambda a: float(rankdata(a, method="average")[-1]) / float(n), raw=True
    )


def ts_argmax(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """1-indexed position of the rolling maximum within the last n bars."""
    return x.rolling(n).apply(lambda a: float(np.argmax(a)) + 1.0, raw=True)


def ts_argmin(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """1-indexed position of the rolling minimum within the last n bars."""
    return x.rolling(n).apply(lambda a: float(np.argmin(a)) + 1.0, raw=True)


def product(x: pd.DataFrame, n: int) -> pd.DataFrame:
    return x.rolling(n).apply(np.prod, raw=True)


# ─── Cross-sectional operations ───────────────────────────────────────────────

def rank(x: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional percentile rank at each date (0-1)."""
    return x.rank(axis=1, method="average", pct=True)


def scale(x: pd.DataFrame, k: float = 1.0) -> pd.DataFrame:
    """Cross-sectional rescaling so that sum(|x|) == k at each date."""
    row_sums = x.abs().sum(axis=1).replace(0, np.nan)
    return x.div(row_sums, axis=0) * k


# ─── Rolling statistics ───────────────────────────────────────────────────────

def corr(x: pd.DataFrame, y: pd.DataFrame, n: int) -> pd.DataFrame:
    """Rolling Pearson correlation; fills NaN/Inf with 0."""
    return x.rolling(n).corr(y).fillna(0).replace([np.inf, -np.inf], 0)


def cov(x: pd.DataFrame, y: pd.DataFrame, n: int) -> pd.DataFrame:
    """Rolling covariance."""
    return x.rolling(n).cov(y)


def ema(x: pd.DataFrame, n: int, m: int) -> pd.DataFrame:
    """Exponential moving average with smoothing factor alpha = m/n (adjust=False).

    This is referred to as SMA in the Alpha191 codebase.
    """
    return x.ewm(alpha=m / n, adjust=False).mean()


# ─── Element-wise helpers ─────────────────────────────────────────────────────

def sign(x) -> pd.DataFrame:
    return np.sign(x)


def log(x) -> pd.DataFrame:
    return np.log(x)


def absv(x) -> pd.DataFrame:
    return x.abs()


def emax(x, y) -> pd.DataFrame:
    """Element-wise maximum."""
    return np.maximum(x, y)


def emin(x, y) -> pd.DataFrame:
    """Element-wise minimum."""
    return np.minimum(x, y)


def row_max(x: pd.DataFrame) -> pd.Series:
    """Maximum value across all symbols at each date."""
    return x.max(axis=1)


def row_min(x: pd.DataFrame) -> pd.Series:
    """Minimum value across all symbols at each date."""
    return x.min(axis=1)


# ─── Advanced rolling helpers ─────────────────────────────────────────────────

def decay_linear(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """Linearly-decayed weighted moving average over n periods."""
    weights = np.arange(1, n + 1, dtype=float)
    sum_w = weights.sum()
    return x.rolling(n).apply(lambda a: np.dot(weights, a) / sum_w, raw=True)


def regbeta(x: pd.DataFrame, y: np.ndarray) -> pd.DataFrame:
    """Rolling OLS slope: regress x (rolling window) on deterministic y."""
    n = len(y)
    return x.rolling(n).apply(lambda a: np.polyfit(y, a, 1)[0], raw=True)


def lowday(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """Number of periods since the latest rolling minimum (0 = today is the min)."""
    return x.rolling(n).apply(lambda a: float(np.argmin(a[::-1])), raw=True)


def highday(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """Number of periods since the latest rolling maximum (0 = today is the max)."""
    return x.rolling(n).apply(lambda a: float(np.argmax(a[::-1])), raw=True)


def count(cond: pd.DataFrame, n: int) -> pd.DataFrame:
    """Rolling count of True observations."""
    return cond.astype(float).rolling(n).sum()


def sumif(x: pd.DataFrame, n: int, cond: pd.DataFrame) -> pd.DataFrame:
    """Rolling sum of x where cond is True, 0 elsewhere."""
    filtered = x.copy()
    filtered[~cond] = 0.0
    return filtered.rolling(n).sum()


def wma(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """Weighted moving average with geometrically-decaying weights (base 0.9)."""
    weights = np.array([0.9 ** (n - 1 - i) for i in range(n)])
    sum_w = weights.sum()
    return x.rolling(n).apply(lambda a: np.dot(weights, a) / sum_w, raw=True)


def adv(volume: pd.DataFrame, n: int) -> pd.DataFrame:
    """Average daily volume over n periods."""
    return ts_mean(volume, n)


def sequence(n: int) -> np.ndarray:
    """Generate 1…n integer sequence (used by Regbeta)."""
    return np.arange(1, n + 1, dtype=float)


def returns(close: pd.DataFrame) -> pd.DataFrame:
    """Daily simple returns."""
    return close.pct_change()
