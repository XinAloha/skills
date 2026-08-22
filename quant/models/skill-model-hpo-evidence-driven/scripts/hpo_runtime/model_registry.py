"""Model registry for ridge, LightGBM, and simple MLP candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
import pandas as pd

from config_utils import ConfigError


@dataclass(frozen=True)
class ModelSpec:
    name: str
    type: str
    params: dict[str, Any]


class BaseModel:
    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        *,
        sample_weight: pd.Series | None = None,
    ) -> None:
        raise NotImplementedError

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError

    def complexity(self) -> dict[str, Any]:
        return {}


class RidgeModel(BaseModel):
    def __init__(self, params: Mapping[str, Any]):
        from sklearn.linear_model import Ridge

        self.model = Ridge(**dict(params))
        self._num_features = 0

    def fit(self, X: pd.DataFrame, y: pd.Series, *, sample_weight: pd.Series | None = None) -> None:
        self._num_features = X.shape[1]
        self.model.fit(X, y, sample_weight=sample_weight)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict(X)

    def complexity(self) -> dict[str, Any]:
        coef = getattr(self.model, "coef_", np.array([]))
        return {
            "num_features": int(self._num_features),
            "nonzero_coefficients": int(np.sum(np.abs(coef) > 1e-12)) if coef is not None else 0,
            "model_family_complexity": 1.0,
        }


class LightGBMModel(BaseModel):
    def __init__(self, params: Mapping[str, Any]):
        from lightgbm import LGBMRegressor

        self.params = dict(params)
        self.model = LGBMRegressor(**self.params)

    def fit(self, X: pd.DataFrame, y: pd.Series, *, sample_weight: pd.Series | None = None) -> None:
        self.model.fit(X, y, sample_weight=sample_weight)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict(X)

    def complexity(self) -> dict[str, Any]:
        booster = getattr(self.model, "booster_", None)
        num_trees = booster.num_trees() if booster is not None else self.params.get("n_estimators")
        return {
            "num_trees": int(num_trees) if num_trees is not None else None,
            "num_leaves": self.params.get("num_leaves"),
            "max_depth": self.params.get("max_depth"),
            "model_family_complexity": 3.0,
        }


class SimpleMLPModel(BaseModel):
    def __init__(self, params: Mapping[str, Any], seed: int):
        import torch
        import torch.nn as nn

        self.torch = torch
        self.nn = nn
        self.params = dict(params)
        self.seed = seed
        self.model: nn.Module | None = None
        self.num_params = 0

    def _build(self, n_features: int):
        torch = self.torch
        nn = self.nn
        torch.manual_seed(self.seed)
        hidden_layers = list(self.params.get("hidden_layers", [128, 64]))
        if len(hidden_layers) > 4:
            raise ConfigError("MLP hidden_layers may not exceed 4 layers in this harness")
        activation_name = str(self.params.get("activation", "relu")).lower()
        activation_cls = {"relu": nn.ReLU, "gelu": nn.GELU, "silu": nn.SiLU}.get(activation_name)
        if activation_cls is None:
            raise ConfigError("MLP activation must be one of: relu, gelu, silu")
        dropout = float(self.params.get("dropout", 0.0))
        layers: list[nn.Module] = []
        in_dim = n_features
        for hidden in hidden_layers:
            hidden = int(hidden)
            layers.append(nn.Linear(in_dim, hidden))
            layers.append(activation_cls())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            in_dim = hidden
        layers.append(nn.Linear(in_dim, 1))
        model = nn.Sequential(*layers)
        self.num_params = int(sum(p.numel() for p in model.parameters()))
        self.model = model

    def fit(self, X: pd.DataFrame, y: pd.Series, *, sample_weight: pd.Series | None = None) -> None:
        torch = self.torch
        if self.model is None:
            self._build(X.shape[1])
        assert self.model is not None
        self.model.train()
        x_tensor = torch.tensor(X.to_numpy(dtype="float32"), dtype=torch.float32)
        y_tensor = torch.tensor(y.to_numpy(dtype="float32").reshape(-1, 1), dtype=torch.float32)
        weight_tensor = None
        if sample_weight is not None:
            weight_tensor = torch.tensor(
                sample_weight.to_numpy(dtype="float32").reshape(-1, 1),
                dtype=torch.float32,
            )
        lr = float(self.params.get("learning_rate", 1e-3))
        wd = float(self.params.get("weight_decay", 0.0))
        batch_size = int(self.params.get("batch_size", 4096))
        max_epochs = int(self.params.get("max_epochs", 30))
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=wd)
        generator = torch.Generator().manual_seed(self.seed)
        n = x_tensor.shape[0]
        for _ in range(max_epochs):
            perm = torch.randperm(n, generator=generator)
            for start in range(0, n, batch_size):
                idx = perm[start : start + batch_size]
                pred = self.model(x_tensor[idx])
                squared_error = (pred - y_tensor[idx]) ** 2
                if weight_tensor is None:
                    loss = squared_error.mean()
                else:
                    batch_weight = weight_tensor[idx]
                    loss = (squared_error * batch_weight).sum() / batch_weight.sum().clamp_min(1e-12)
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                clip_norm = float(self.params.get("gradient_clip_norm", 0.0) or 0.0)
                if clip_norm > 0:
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), clip_norm)
                optimizer.step()

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        torch = self.torch
        assert self.model is not None
        self.model.eval()
        with torch.no_grad():
            x_tensor = torch.tensor(X.to_numpy(dtype="float32"), dtype=torch.float32)
            pred = self.model(x_tensor).squeeze(-1).cpu().numpy()
        return pred

    def complexity(self) -> dict[str, Any]:
        return {
            "num_parameters": int(self.num_params),
            "model_family_complexity": 5.0,
        }


def parse_model_specs(cfg: Mapping[str, Any], experiment: Any) -> list[ModelSpec]:
    candidates = getattr(experiment, "MODEL_CANDIDATES", None)
    if candidates is None:
        candidates = cfg.get("models", {}).get("candidates", [])
    if not isinstance(candidates, list) or not candidates:
        raise ConfigError("Model candidates must be a non-empty list")
    specs: list[ModelSpec] = []
    seen: set[str] = set()
    for item in candidates:
        if not isinstance(item, Mapping):
            raise ConfigError("Each model candidate must be a mapping")
        name = str(item.get("name", ""))
        model_type = str(item.get("type", ""))
        params = dict(item.get("params", {}))
        if not name or not model_type:
            raise ConfigError("Each model candidate must define name and type")
        if name in seen:
            raise ConfigError(f"Duplicate model candidate name: {name}")
        seen.add(name)
        specs.append(ModelSpec(name=name, type=model_type, params=params))
    return specs


def create_model(spec: ModelSpec, seed: int) -> BaseModel:
    """Compatibility facade backed by the extension registry."""
    from extension_registry import REGISTRY
    from plugin_loader import ensure_builtin_extensions

    ensure_builtin_extensions()
    plugin = REGISTRY.get_model_plugin(spec.type)
    return plugin.create(spec.params, seed)
