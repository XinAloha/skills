"""Stable contracts for user-defined HPO data, feature, and model extensions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable

import pandas as pd


EXTENSION_API_VERSION = 2


@dataclass(frozen=True)
class ModelCapabilities:
    """Runtime behavior required by a model implementation."""

    accepts_nan: bool = False
    supports_sample_weight: bool = False
    supports_validation_set: bool = False


@runtime_checkable
class FactorProvider(Protocol):
    """Load factors and labels into the canonical PanelData contract."""

    def load(self, cfg: Mapping[str, Any]) -> Any:
        ...


@runtime_checkable
class FeaturePipeline(Protocol):
    """Fit on training features and transform features without target access."""

    def fit(
        self,
        features: pd.DataFrame,
        target: pd.Series,
        context: pd.DataFrame,
        feature_columns: list[str],
        cfg: Mapping[str, Any],
        *,
        normalize_method: str | None,
        preserve_nan: bool,
    ) -> "FeaturePipeline":
        ...

    def transform(
        self,
        features: pd.DataFrame,
        context: pd.DataFrame,
        feature_columns: list[str],
        cfg: Mapping[str, Any],
        *,
        normalize_method: str | None,
        preserve_nan: bool,
    ) -> pd.DataFrame:
        ...


@runtime_checkable
class TrainableModel(Protocol):
    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        *,
        sample_weight: pd.Series | None = None,
    ) -> None:
        ...

    def predict(self, X: pd.DataFrame) -> Any:
        ...

    def complexity(self) -> dict[str, Any]:
        ...


@runtime_checkable
class ModelPlugin(Protocol):
    """Create models and define only model-specific behavior."""

    name: str
    aliases: tuple[str, ...]
    capabilities: ModelCapabilities

    def default_search_space(self) -> dict[str, dict[str, Any]]:
        ...

    def normalize_params(self, params: Mapping[str, Any]) -> dict[str, Any]:
        ...

    def create(self, params: Mapping[str, Any], seed: int) -> TrainableModel:
        ...

    def prepare_features(
        self,
        features: pd.DataFrame,
        cfg: Mapping[str, Any],
    ) -> pd.DataFrame:
        ...
