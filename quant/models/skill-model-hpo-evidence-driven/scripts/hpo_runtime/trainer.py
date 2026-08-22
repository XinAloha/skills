"""Walk-forward model training and prediction."""

from __future__ import annotations

import time
from typing import Any, Mapping

import numpy as np
import pandas as pd

from config_utils import ConfigError, optional_value
from data_adapter import Window
from extension_registry import REGISTRY
from model_registry import ModelSpec
from plugin_loader import ensure_builtin_extensions, feature_pipeline_config


def _complexity_penalty(complexity: dict[str, Any]) -> float:
    family = float(complexity.get("model_family_complexity") or 0.0)
    params = float(complexity.get("num_parameters") or 0.0)
    trees = float(complexity.get("num_trees") or 0.0)
    raw = family / 10.0 + min(params / 1_000_000.0, 1.0) + min(trees / 1000.0, 1.0)
    return float(np.clip(raw / 3.0, 0.0, 1.0))


def _regression_metrics(y_true: pd.Series | np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    y_arr = np.asarray(y_true, dtype="float64")
    pred_arr = np.asarray(y_pred, dtype="float64")
    mask = np.isfinite(y_arr) & np.isfinite(pred_arr)
    if not mask.any():
        return {"rmse": float("nan"), "mae": float("nan"), "r2": float("nan")}
    residuals = y_arr[mask] - pred_arr[mask]
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    mae = float(np.mean(np.abs(residuals)))
    ss_res = float(np.dot(residuals, residuals))
    centered = y_arr[mask] - float(np.mean(y_arr[mask]))
    ss_tot = float(np.dot(centered, centered))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return {"rmse": rmse, "mae": mae, "r2": float(r2)}


def _validate_transformed_features(
    transformed: Any,
    source: pd.DataFrame,
    feature_columns: list[str],
    pipeline_name: str,
) -> pd.DataFrame:
    if not isinstance(transformed, pd.DataFrame):
        raise ValueError(f"Feature pipeline {pipeline_name!r} must return a pandas DataFrame")
    required = list(feature_columns)
    missing = [column for column in required if column not in transformed.columns]
    if missing:
        raise ValueError(f"Feature pipeline {pipeline_name!r} output is missing columns: {missing}")
    if len(transformed) != len(source):
        raise ValueError(f"Feature pipeline {pipeline_name!r} must preserve row count")
    if not transformed.index.equals(source.index):
        raise ValueError(f"Feature pipeline {pipeline_name!r} must preserve row index and order")
    non_numeric = [
        column
        for column in feature_columns
        if not pd.api.types.is_numeric_dtype(transformed[column])
    ]
    if non_numeric:
        raise ValueError(f"Feature pipeline {pipeline_name!r} produced non-numeric features: {non_numeric}")
    return transformed[feature_columns]


def _purge_training_rows(frame: pd.DataFrame, window: Window) -> pd.DataFrame:
    if "label_end_date" not in frame.columns:
        return frame
    label_end = pd.to_numeric(frame["label_end_date"], errors="coerce")
    return frame[label_end < int(window.valid_start)].copy()


def _transform_training_target(frame: pd.DataFrame, cfg: Mapping[str, Any]) -> pd.Series:
    raw_cfg = optional_value(cfg, ["training", "label_transform"], {"method": "none"})
    if isinstance(raw_cfg, str):
        method = raw_cfg
    elif isinstance(raw_cfg, Mapping):
        method = str(raw_cfg.get("method", "none"))
    else:
        raise ConfigError("training.label_transform must be a string or mapping")
    method = method.lower()
    target = frame["y"].astype("float64")
    grouped = frame.assign(_target=target).groupby("date", sort=False)["_target"]
    if method == "none":
        return target
    if method == "rank_by_date":
        return grouped.rank(pct=True).astype("float64") - 0.5
    if method == "zscore_by_date":
        mean = grouped.transform("mean")
        std = grouped.transform("std").replace(0.0, np.nan)
        return ((target - mean) / std).fillna(0.0)
    raise ConfigError("training.label_transform.method must be one of: none, rank_by_date, zscore_by_date")


def _training_sample_weight(frame: pd.DataFrame, cfg: Mapping[str, Any]) -> pd.Series | None:
    raw_cfg = optional_value(cfg, ["training", "sample_weight"], {"method": "equal_date"})
    if isinstance(raw_cfg, str):
        method = raw_cfg
    elif isinstance(raw_cfg, Mapping):
        method = str(raw_cfg.get("method", "equal_date"))
    else:
        raise ConfigError("training.sample_weight must be a string or mapping")
    method = method.lower()
    if method == "none":
        return None
    if method != "equal_date":
        raise ConfigError("training.sample_weight.method must be one of: none, equal_date")
    counts = frame.groupby("date", sort=False)["date"].transform("size").astype("float64")
    weights = 1.0 / counts
    return weights / float(weights.mean())


def _mean_daily_rank_corr(prediction: np.ndarray, target: pd.Series, dates: pd.Series) -> float:
    frame = pd.DataFrame(
        {
            "prediction": np.asarray(prediction, dtype="float64"),
            "target": target.reset_index(drop=True).to_numpy(dtype="float64"),
            "date": dates.reset_index(drop=True).to_numpy(),
        }
    )
    values = [
        group["prediction"].corr(group["target"], method="spearman")
        for _, group in frame.groupby("date", sort=False)
    ]
    numeric = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    return float(numeric.mean()) if not numeric.empty else float("nan")


def train_and_predict(
    panel: pd.DataFrame,
    feature_columns: list[str],
    windows: list[Window],
    specs: list[ModelSpec],
    cfg: Mapping[str, Any],
    seed: int,
    normalize_method: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_builtin_extensions()
    pipeline_cfg = feature_pipeline_config(cfg)
    rows: list[pd.DataFrame] = []
    window_metric_rows: list[dict[str, Any]] = []
    for window in windows:
        for spec in specs:
            plugin = REGISTRY.get_model_plugin(spec.type)
            raw_train = panel[panel["date"].isin(window.train_dates)].dropna(subset=["y"]).copy()
            raw_valid = panel[panel["date"].isin(window.valid_dates)].dropna(subset=["y"]).copy()
            raw_train = _purge_training_rows(raw_train, window)
            if raw_train.empty or raw_valid.empty:
                continue
            pipeline = REGISTRY.create_feature_pipeline(pipeline_cfg["name"], pipeline_cfg["params"])
            pipeline.fit(
                raw_train[feature_columns].copy(),
                raw_train["y"].astype("float64").copy(),
                raw_train[["date", "ticker"]].copy(),
                feature_columns,
                cfg,
                normalize_method=normalize_method,
                preserve_nan=bool(plugin.capabilities.accepts_nan),
            )
            train_features = _validate_transformed_features(
                pipeline.transform(
                    raw_train[feature_columns].copy(),
                    raw_train[["date", "ticker"]].copy(),
                    feature_columns,
                    cfg,
                    normalize_method=normalize_method,
                    preserve_nan=bool(plugin.capabilities.accepts_nan),
                ),
                raw_train[feature_columns],
                feature_columns,
                pipeline_cfg["name"],
            )
            valid_features = _validate_transformed_features(
                pipeline.transform(
                    raw_valid[feature_columns].copy(),
                    raw_valid[["date", "ticker"]].copy(),
                    feature_columns,
                    cfg,
                    normalize_method=normalize_method,
                    preserve_nan=bool(plugin.capabilities.accepts_nan),
                ),
                raw_valid[feature_columns],
                feature_columns,
                pipeline_cfg["name"],
            )
            y_train_raw = raw_train["y"].astype("float64")
            y_train = _transform_training_target(raw_train, cfg)
            sample_weight = _training_sample_weight(raw_train, cfg)
            X_train = plugin.prepare_features(train_features, cfg)
            X_valid = plugin.prepare_features(valid_features, cfg)
            started = time.time()
            model = plugin.create(spec.params, seed=seed + window.window_id)
            if sample_weight is not None and not bool(plugin.capabilities.supports_sample_weight):
                raise ConfigError(
                    f"Model plugin {spec.type!r} does not support configured sample weights"
                )
            model.fit(X_train, y_train, sample_weight=sample_weight)
            train_pred = model.predict(X_train)
            valid_pred = model.predict(X_valid)
            elapsed = time.time() - started
            metric_policy = str(
                optional_value(
                    cfg,
                    ["evaluation", "metric_policy"],
                    "legacy_pooled",
                )
            ).lower()
            if metric_policy == "legacy_pooled":
                train_corr = pd.Series(train_pred).corr(
                    y_train_raw.reset_index(drop=True),
                    method="spearman",
                )
                valid_corr = pd.Series(valid_pred).corr(
                    raw_valid["y"].reset_index(drop=True),
                    method="spearman",
                )
            elif metric_policy == "cross_sectional":
                train_corr = _mean_daily_rank_corr(
                    train_pred,
                    y_train_raw,
                    raw_train["date"],
                )
                valid_corr = _mean_daily_rank_corr(
                    valid_pred,
                    raw_valid["y"],
                    raw_valid["date"],
                )
            else:
                raise ConfigError(
                    "evaluation.metric_policy must be one of: "
                    "legacy_pooled, cross_sectional"
                )
            train_loss_metrics = _regression_metrics(y_train, train_pred)
            valid_loss_metrics = _regression_metrics(raw_valid["y"], valid_pred)
            overfit_penalty = max(0.0, float(train_corr - valid_corr)) if pd.notna(train_corr) and pd.notna(valid_corr) else 0.0
            complexity = model.complexity()
            c_penalty = _complexity_penalty(complexity)
            pred_frame = raw_valid[["date", "ticker", "y"]].copy()
            pred_frame["prediction"] = valid_pred
            pred_frame["model_name"] = spec.name
            pred_frame["model_type"] = spec.type
            pred_frame["window_id"] = window.window_id
            pred_frame["complexity_penalty"] = c_penalty
            pred_frame["overfit_penalty"] = overfit_penalty
            pred_frame["train_rmse"] = train_loss_metrics["rmse"]
            pred_frame["valid_rmse"] = valid_loss_metrics["rmse"]
            pred_frame["train_mae"] = train_loss_metrics["mae"]
            pred_frame["valid_mae"] = valid_loss_metrics["mae"]
            pred_frame["train_r2"] = train_loss_metrics["r2"]
            pred_frame["valid_r2"] = valid_loss_metrics["r2"]
            rows.append(pred_frame)
            window_metric_rows.append(
                {
                    **window.to_dict(),
                    "model_name": spec.name,
                    "model_type": spec.type,
                    "train_rank_corr": train_corr,
                    "valid_rank_corr": valid_corr,
                    "train_rmse": train_loss_metrics["rmse"],
                    "valid_rmse": valid_loss_metrics["rmse"],
                    "train_mae": train_loss_metrics["mae"],
                    "valid_mae": valid_loss_metrics["mae"],
                    "train_r2": train_loss_metrics["r2"],
                    "valid_r2": valid_loss_metrics["r2"],
                    "overfit_penalty": overfit_penalty,
                    "complexity_penalty": c_penalty,
                    "training_seconds": elapsed,
                    **complexity,
                }
            )
    if not rows:
        raise ValueError("No model predictions were produced")
    predictions = pd.concat(rows, ignore_index=True)
    window_metrics = pd.DataFrame(window_metric_rows)
    return predictions, window_metrics
