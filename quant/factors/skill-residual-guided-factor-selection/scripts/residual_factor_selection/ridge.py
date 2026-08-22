from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class RidgeModel:
    intercept: float
    coefficients: pd.Series
    alpha: float

    def predict(self, features: pd.DataFrame) -> pd.Series:
        aligned = features.reindex(columns=self.coefficients.index).fillna(0.0)
        values = self.intercept + aligned.to_numpy(dtype=float) @ self.coefficients.to_numpy(dtype=float)
        return pd.Series(values, index=features.index, name="prediction")


def _date_weights(index: pd.MultiIndex) -> np.ndarray:
    dates = pd.Series(index.get_level_values("datetime"), index=index)
    counts = dates.groupby(dates).transform("size").to_numpy(dtype=float)
    return 1.0 / counts


def fit_ridge(
    features: pd.DataFrame,
    target: pd.Series,
    alpha: float,
    equal_date_weight: bool = True,
) -> RidgeModel:
    joined = features.join(target.rename("target"), how="inner").dropna(subset=["target"])
    if joined.empty:
        raise ValueError("No finite training observations")
    x = joined[features.columns].fillna(0.0).to_numpy(dtype=float)
    y = joined["target"].to_numpy(dtype=float)
    design = np.column_stack([np.ones(len(x)), x])
    weights = _date_weights(joined.index) if equal_date_weight else np.ones(len(joined))
    root_weight = np.sqrt(weights)
    weighted_design = design * root_weight[:, None]
    weighted_target = y * root_weight
    penalty = np.eye(design.shape[1]) * float(alpha)
    penalty[0, 0] = 0.0
    lhs = weighted_design.T @ weighted_design + penalty
    rhs = weighted_design.T @ weighted_target
    solution = np.linalg.pinv(lhs) @ rhs
    return RidgeModel(
        intercept=float(solution[0]),
        coefficients=pd.Series(solution[1:], index=features.columns, dtype=float),
        alpha=float(alpha),
    )
