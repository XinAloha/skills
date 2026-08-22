from __future__ import annotations

import numpy as np
import pandas as pd


def daily_correlation(left: pd.Series, right: pd.Series, method: str = "pearson", min_count: int = 8) -> pd.Series:
    frame = pd.concat([left.rename("left"), right.rename("right")], axis=1).dropna()

    def correlate(group: pd.DataFrame) -> float:
        if len(group) < min_count or group["left"].nunique() < 2 or group["right"].nunique() < 2:
            return np.nan
        return float(group["left"].corr(group["right"], method=method))

    return frame.groupby(level="datetime").apply(correlate).dropna()


def prediction_metrics(prediction: pd.Series, target: pd.Series, method: str = "pearson", min_count: int = 8) -> dict[str, float]:
    aligned = pd.concat([prediction.rename("prediction"), target.rename("target")], axis=1).dropna()
    if aligned.empty:
        return {"mean_ic": np.nan, "icir": np.nan, "mse": np.nan, "observations": 0.0, "dates": 0.0}
    daily_ic = daily_correlation(aligned["prediction"], aligned["target"], method=method, min_count=min_count)
    ic_std = daily_ic.std(ddof=1)
    return {
        "mean_ic": float(daily_ic.mean()) if len(daily_ic) else np.nan,
        "icir": float(daily_ic.mean() / ic_std) if len(daily_ic) > 1 and ic_std > 0 else np.nan,
        "mse": float(np.mean((aligned["prediction"] - aligned["target"]) ** 2)),
        "observations": float(len(aligned)),
        "dates": float(aligned.index.get_level_values("datetime").nunique()),
    }
