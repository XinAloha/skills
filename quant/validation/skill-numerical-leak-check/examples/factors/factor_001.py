from __future__ import annotations

import numpy as np
import pandas as pd


def compute_factor(data: pd.DataFrame, period: int = 9) -> pd.DataFrame:
    close = pd.to_numeric(data["close"], errors="coerce").astype(float).to_numpy()
    period = max(1, int(period))
    kernel = np.ones(period, dtype=float) / period

    raw_mean = np.convolve(close, kernel, mode="same")
    if len(raw_mean) != len(close):
        start = (len(raw_mean) - len(close)) // 2
        mean = raw_mean[start : start + len(close)]
    else:
        mean = raw_mean

    signal = close - mean
    return pd.DataFrame({"signal": signal}, index=data.index)
