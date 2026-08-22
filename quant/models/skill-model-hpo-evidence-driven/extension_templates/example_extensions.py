"""Copyable examples of user-owned factor, feature, and model extensions.

Keep production extensions outside the skill directory. Point
extensions.plugin_roots at that directory and list this module name without
the .py suffix.
"""

from __future__ import annotations

from typing import Any, Mapping

from extension_api import ModelCapabilities


__version__ = "1.0.0"
HPO_EXTENSION_API_VERSION = 2


class ExampleFilePanelProvider:
    """Delegate file loading, then optionally retain an explicit factor list."""

    def __init__(self, params: Mapping[str, Any]):
        self.params = dict(params)

    def load(self, cfg):
        from data_adapter import _build_file_panel

        data = _build_file_panel(cfg)
        retain = list(self.params.get("retain_features") or [])
        if retain:
            missing = [name for name in retain if name not in data.feature_columns]
            if missing:
                raise ValueError(f"Example provider cannot retain missing factors: {missing}")
            data.feature_columns = retain
        data.metadata["example_provider"] = True
        return data


class ExampleIdentityPipeline:
    """A stateless pipeline; model plugins receive raw numeric factor values."""

    def __init__(self, params: Mapping[str, Any]):
        self.params = dict(params)

    def fit(self, features, target, context, feature_columns, cfg, *, normalize_method, preserve_nan):
        return self

    def transform(self, features, context, feature_columns, cfg, *, normalize_method, preserve_nan):
        return features[feature_columns].copy()


class _RidgeModel:
    def __init__(self, params):
        from sklearn.linear_model import Ridge

        self.model = Ridge(**dict(params))
        self._num_features = 0

    def fit(self, X, y, *, sample_weight=None):
        self._num_features = int(X.shape[1])
        self.model.fit(X, y, sample_weight=sample_weight)

    def predict(self, X):
        return self.model.predict(X)

    def complexity(self):
        return {
            "num_features": self._num_features,
            "model_family_complexity": 1.0,
        }


class ExampleRidgePlugin:
    name = "example_ridge"
    aliases = ("ridge_example",)
    capabilities = ModelCapabilities(accepts_nan=False, supports_sample_weight=True)

    def default_search_space(self):
        return {"alpha": {"type": "loguniform", "low": 0.001, "high": 100.0}}

    def normalize_params(self, params):
        out = dict(params)
        if "alpha" in out:
            out["alpha"] = float(out["alpha"])
        return out

    def create(self, params, seed):
        return _RidgeModel(params)

    def prepare_features(self, features, cfg):
        return features.replace([float("inf"), float("-inf")], float("nan")).fillna(0.0)


def register(registry):
    """Required entrypoint called by the controlled plugin loader."""

    registry.register_factor_provider("example_file_panel", ExampleFilePanelProvider)
    registry.register_feature_pipeline("example_identity", ExampleIdentityPipeline)
    registry.register_model_plugin(ExampleRidgePlugin())
