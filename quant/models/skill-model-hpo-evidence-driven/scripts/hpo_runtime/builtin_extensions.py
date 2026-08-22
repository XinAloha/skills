"""Built-in adapters preserving the original file, LGBM, and MLP behavior."""

from __future__ import annotations

import copy
from typing import Any, Mapping

from config_utils import optional_value
from extension_api import ModelCapabilities
from extension_registry import ExtensionRegistry


LGBM_SEARCH_SPACE: dict[str, dict[str, Any]] = {
    "num_leaves": {"type": "choice", "values": [15, 31, 63]},
    "max_depth": {"type": "choice", "values": [-1, 4, 6, 8]},
    "learning_rate": {"type": "loguniform", "low": 0.005, "high": 0.08},
    "n_estimators": {"type": "choice", "values": [80, 150, 300]},
    "min_child_samples": {"type": "choice", "values": [30, 80, 150, 300]},
    "subsample": {"type": "uniform", "low": 0.6, "high": 1.0},
    "colsample_bytree": {"type": "uniform", "low": 0.5, "high": 1.0},
    "lambda_l1": {"type": "loguniform", "low": 1e-6, "high": 10.0},
    "lambda_l2": {"type": "loguniform", "low": 1e-6, "high": 20.0},
    "min_split_gain": {"type": "choice", "values": [0.0, 0.01, 0.05]},
}

MLP_SEARCH_SPACE: dict[str, dict[str, Any]] = {
    "hidden_layers": {"type": "choice", "values": [[64], [128], [128, 64], [256, 128]]},
    "activation": {"type": "choice", "values": ["relu", "gelu", "silu"]},
    "dropout": {"type": "uniform", "low": 0.0, "high": 0.3},
    "learning_rate": {"type": "loguniform", "low": 1e-4, "high": 3e-3},
    "weight_decay": {"type": "loguniform", "low": 1e-6, "high": 1e-2},
    "batch_size": {"type": "choice", "values": [512, 1024, 2048, 4096]},
    "max_epochs": {"type": "choice", "values": [5, 10, 20]},
    "gradient_clip_norm": {"type": "choice", "values": [0.0, 1.0, 5.0]},
}


class FilePanelProvider:
    def __init__(self, params: Mapping[str, Any]):
        self.params = dict(params)

    def load(self, cfg: Mapping[str, Any]) -> Any:
        from data_adapter import _build_file_panel

        return _build_file_panel(cfg)


class CrossSectionalPipeline:
    def __init__(self, params: Mapping[str, Any]):
        self.params = dict(params)

    def _cfg(self, cfg: Mapping[str, Any]) -> dict[str, Any]:
        if not self.params:
            return dict(cfg)
        out = dict(cfg)
        preprocess = copy.deepcopy(dict(cfg.get("preprocess", {})))
        overrides = self.params.get("preprocess", self.params)
        if isinstance(overrides, Mapping):
            for key, value in overrides.items():
                if isinstance(value, Mapping) and isinstance(preprocess.get(key), Mapping):
                    merged = dict(preprocess[key])
                    merged.update(dict(value))
                    preprocess[key] = merged
                else:
                    preprocess[key] = copy.deepcopy(value)
        out["preprocess"] = preprocess
        return out

    def fit(self, features, target, context, feature_columns, cfg, *, normalize_method, preserve_nan):
        return self

    def transform(self, features, context, feature_columns, cfg, *, normalize_method, preserve_nan):
        from preprocess import preprocess_features

        return preprocess_features(
            features,
            context,
            feature_columns,
            self._cfg(cfg),
            normalize_method=normalize_method,
            preserve_nan=preserve_nan,
        )


class LGBMPlugin:
    name = "lgbm"
    aliases = ("lightgbm",)
    capabilities = ModelCapabilities(accepts_nan=True, supports_sample_weight=True)

    def default_search_space(self):
        return copy.deepcopy(LGBM_SEARCH_SPACE)

    def normalize_params(self, params):
        out = dict(params)
        for key in ("num_leaves", "max_depth", "n_estimators", "min_child_samples"):
            if key in out:
                out[key] = int(out[key])
        out["objective"] = "regression"
        out["metric"] = "rmse"
        out.setdefault("n_jobs", 1)
        out.setdefault("force_col_wise", True)
        if "subsample" in out and float(out["subsample"]) < 1.0:
            out.setdefault("subsample_freq", 1)
        return out

    def create(self, params, seed):
        from model_registry import LightGBMModel

        out = dict(params)
        out["objective"] = "regression"
        out["metric"] = "rmse"
        out.setdefault("random_state", seed)
        out.setdefault("verbose", -1)
        return LightGBMModel(out)

    def prepare_features(self, features, cfg):
        return features


class RidgePlugin:
    name = "ridge"
    aliases: tuple[str, ...] = ()
    capabilities = ModelCapabilities(accepts_nan=False, supports_sample_weight=True)

    def default_search_space(self):
        return {"alpha": {"type": "loguniform", "low": 0.001, "high": 100.0}}

    def normalize_params(self, params):
        out = dict(params)
        if "alpha" in out:
            out["alpha"] = float(out["alpha"])
        return out

    def create(self, params, seed):
        from model_registry import RidgeModel

        return RidgeModel(params)

    def prepare_features(self, features, cfg):
        fill_value = float(optional_value(cfg, ["model_missing", "mlp_fill_value"], 0.0))
        return features.fillna(fill_value)


class MLPPlugin:
    name = "mlp"
    aliases: tuple[str, ...] = ()
    capabilities = ModelCapabilities(accepts_nan=False, supports_sample_weight=True)

    def default_search_space(self):
        return copy.deepcopy(MLP_SEARCH_SPACE)

    def normalize_params(self, params):
        out = dict(params)
        if "hidden_layers" in out:
            out["hidden_layers"] = [int(x) for x in list(out["hidden_layers"])]
        for key in ("batch_size", "max_epochs"):
            if key in out:
                out[key] = int(out[key])
        for key in ("dropout", "learning_rate", "weight_decay", "gradient_clip_norm"):
            if key in out:
                out[key] = float(out[key])
        return out

    def create(self, params, seed):
        from model_registry import SimpleMLPModel

        return SimpleMLPModel(params, seed=seed)

    def prepare_features(self, features, cfg):
        fill_value = float(optional_value(cfg, ["model_missing", "mlp_fill_value"], 0.0))
        return features.fillna(fill_value)


def register_builtin_extensions(registry: ExtensionRegistry) -> None:
    registry.register_factor_provider("file_panel", FilePanelProvider)
    registry.register_feature_pipeline("cross_sectional", CrossSectionalPipeline)
    registry.register_model_plugin(RidgePlugin())
    registry.register_model_plugin(LGBMPlugin())
    registry.register_model_plugin(MLPPlugin())
