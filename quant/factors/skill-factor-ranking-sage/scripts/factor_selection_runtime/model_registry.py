"""LGBM and MLP adapters used only by SAGE mode."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

import numpy as np
import pandas as pd

from .config_utils import ConfigError


class ModelAdapter(Protocol):
    def fit(self, X: pd.DataFrame, y: pd.Series) -> Any: ...
    def predict(self, X: pd.DataFrame) -> np.ndarray: ...


class LGBMAdapter:
    def __init__(self, params: Mapping[str, Any], seed: int):
        try:
            from lightgbm import LGBMRegressor
        except ImportError as exc:
            raise RuntimeError("LightGBM is required for model.type=lgbm") from exc
        defaults = {
            "objective": "regression",
            "n_estimators": 80,
            "learning_rate": 0.05,
            "num_leaves": 15,
            "min_child_samples": 10,
            "random_state": seed,
            "n_jobs": 1,
            "verbosity": -1,
        }
        defaults.update(dict(params))
        self.model = LGBMRegressor(**defaults)

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        self.model.fit(X, y)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.asarray(self.model.predict(X), dtype="float64")


class MLPAdapter:
    def __init__(self, params: Mapping[str, Any], seed: int):
        from sklearn.neural_network import MLPRegressor

        defaults = {
            "hidden_layer_sizes": (32, 16),
            "activation": "relu",
            "solver": "adam",
            "alpha": 0.0001,
            "batch_size": "auto",
            "learning_rate_init": 0.001,
            "max_iter": 120,
            "early_stopping": False,
            "random_state": seed,
        }
        defaults.update(dict(params))
        if isinstance(defaults.get("hidden_layer_sizes"), list):
            defaults["hidden_layer_sizes"] = tuple(defaults["hidden_layer_sizes"])
        self.model = MLPRegressor(**defaults)

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        self.model.fit(X, y)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.asarray(self.model.predict(X), dtype="float64")


def create_model(model_cfg: Mapping[str, Any], seed: int) -> ModelAdapter:
    model_type = str(model_cfg["type"])
    params = dict(model_cfg.get("params", {}))
    if model_type == "lgbm":
        return LGBMAdapter(params, seed)
    if model_type == "mlp":
        return MLPAdapter(params, seed)
    raise ConfigError(f"Unsupported model type: {model_type}")
