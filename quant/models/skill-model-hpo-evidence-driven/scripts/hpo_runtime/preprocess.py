"""Cross-sectional preprocessing for model inputs."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd

from config_utils import ConfigError, optional_value, require_mapping


def _winsorize_by_date(frame: pd.DataFrame, columns: list[str], lower: float, upper: float) -> pd.DataFrame:
    out = frame.copy()
    grouped = out.groupby("date", sort=False)
    for col in columns:
        lo = grouped[col].transform(lambda x: x.quantile(lower))
        hi = grouped[col].transform(lambda x: x.quantile(upper))
        out[col] = out[col].clip(lower=lo, upper=hi)
    return out


def _fillna(frame: pd.DataFrame, columns: list[str], method: str) -> pd.DataFrame:
    out = frame.copy()
    if method == "none":
        return out
    if method == "zero":
        out[columns] = out[columns].fillna(0.0)
        return out
    if method == "cross_sectional_median":
        grouped = out.groupby("date", sort=False)
        for col in columns:
            med = grouped[col].transform("median")
            out[col] = out[col].fillna(med)
        return out
    raise ConfigError("preprocess.fillna.method must be one of: none, zero, cross_sectional_median")


def _normalize(frame: pd.DataFrame, columns: list[str], method: str) -> pd.DataFrame:
    out = frame.copy()
    grouped = out.groupby("date", sort=False)
    if method == "none":
        return out
    if method == "rank_by_date":
        out[columns] = grouped[columns].rank(pct=True)
        return out
    if method == "zscore_by_date":
        for col in columns:
            mean = grouped[col].transform("mean")
            std = grouped[col].transform("std").replace(0.0, np.nan)
            out[col] = (out[col] - mean) / std
        return out
    raise ConfigError("preprocess.normalize.method must be one of: none, rank_by_date, zscore_by_date")


def preprocess_panel(
    panel: pd.DataFrame,
    feature_columns: list[str],
    cfg: Mapping[str, Any],
    normalize_method: str | None = None,
    preserve_nan: bool = False,
) -> pd.DataFrame:
    preprocess_cfg = require_mapping(cfg, ["preprocess"])
    out = panel[["date", "ticker", "y", *feature_columns]].copy()
    winsor_cfg = preprocess_cfg.get("winsorize", {})
    if winsor_cfg.get("enabled", False):
        lower = float(winsor_cfg["lower"])
        upper = float(winsor_cfg["upper"])
        if not (0 <= lower < upper <= 1):
            raise ConfigError("winsorize lower/upper must satisfy 0 <= lower < upper <= 1")
        if winsor_cfg.get("by") != "date":
            raise ConfigError("Only winsorize.by=date is implemented")
        out = _winsorize_by_date(out, feature_columns, lower, upper)
    if not preserve_nan:
        fill_method = str(preprocess_cfg.get("fillna", {}).get("method", "none"))
        out = _fillna(out, feature_columns, fill_method)
    if normalize_method is None:
        normalize_method = str(preprocess_cfg.get("normalize", {}).get("method", "none"))
    out = _normalize(out, feature_columns, normalize_method)
    if not preserve_nan:
        out = _fillna(out, feature_columns, str(optional_value(cfg, ["preprocess", "after_normalize_fillna"], "none")))
    out = out.replace([np.inf, -np.inf], np.nan)
    return out


def preprocess_features(
    features: pd.DataFrame,
    context: pd.DataFrame,
    feature_columns: list[str],
    cfg: Mapping[str, Any],
    normalize_method: str | None = None,
    preserve_nan: bool = False,
) -> pd.DataFrame:
    """Preprocess features using date context without exposing any target."""
    required_context = {"date", "ticker"}
    missing_context = sorted(required_context - set(context.columns))
    if missing_context:
        raise ConfigError(f"Feature context is missing columns: {missing_context}")
    missing_features = [column for column in feature_columns if column not in features.columns]
    if missing_features:
        raise ConfigError(f"Feature frame is missing columns: {missing_features}")
    if len(features) != len(context):
        raise ConfigError("Feature frame and context must have the same row count")
    panel = context[["date", "ticker"]].reset_index(drop=True).copy()
    panel["y"] = 0.0
    panel[feature_columns] = features[feature_columns].reset_index(drop=True)
    processed = preprocess_panel(
        panel,
        feature_columns,
        cfg,
        normalize_method=normalize_method,
        preserve_nan=preserve_nan,
    )
    return processed[feature_columns].set_axis(features.index)
