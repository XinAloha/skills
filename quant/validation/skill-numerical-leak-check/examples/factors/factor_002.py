from __future__ import annotations

import numpy as np
import pandas as pd


def compute_factor(data: pd.DataFrame, period: int = 9) -> pd.DataFrame:
    close = pd.to_numeric(data["close"], errors="coerce").astype(float).to_numpy()
    period = max(1, int(period))
    kernel = np.ones(period, dtype=float)

    rolling_sum = np.convolve(close, kernel, mode="full")[: len(close)]
    counts = np.minimum(np.arange(len(close)) + 1, period).astype(float)
    mean = rolling_sum / counts

    signal = close - mean
    return pd.DataFrame({"signal": signal}, index=data.index)
