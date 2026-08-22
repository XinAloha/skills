"""Per-window preprocessing without validation leakage."""

from __future__ import annotations

import numpy as np
import pandas as pd


class FeatureTransformer:
    def __init__(self, model_type: str):
        self.model_type = model_type
        self.columns: list[str] = []
        self.medians = pd.Series(dtype="float64")
        self.means = pd.Series(dtype="float64")
        self.stds = pd.Series(dtype="float64")

    def fit(self, frame: pd.DataFrame) -> "FeatureTransformer":
        self.columns = list(frame.columns)
        clean = frame.replace([np.inf, -np.inf], np.nan).astype("float64")
        self.medians = clean.median().fillna(0.0)
        filled = clean.fillna(self.medians)
        self.means = filled.mean()
        self.stds = filled.std(ddof=0).replace(0.0, 1.0).fillna(1.0)
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        clean = frame[self.columns].replace([np.inf, -np.inf], np.nan).astype("float64")
        if self.model_type == "lgbm":
            return clean
        filled = clean.fillna(self.medians)
        if self.model_type == "mlp":
            return (filled - self.means) / self.stds
        return filled

    def neutral_values(self) -> pd.Series:
        neutral = pd.DataFrame([self.medians], columns=self.columns)
        return self.transform(neutral).iloc[0]
