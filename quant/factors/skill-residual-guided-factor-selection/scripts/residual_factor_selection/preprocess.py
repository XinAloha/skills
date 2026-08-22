from __future__ import annotations

import numpy as np
import pandas as pd


def _process_group(
    values: pd.Series,
    lower: float,
    upper: float,
    zscore: bool,
    min_cross_section: int,
) -> pd.Series:
    finite = values.replace([np.inf, -np.inf], np.nan)
    if finite.notna().sum() < min_cross_section:
        return pd.Series(np.nan, index=values.index, dtype=float)
    clipped = finite.clip(finite.quantile(lower), finite.quantile(upper))
    if not zscore:
        return clipped
    centered = clipped - clipped.mean()
    scale = centered.abs().max()
    if not np.isfinite(scale) or scale <= 0:
        return pd.Series(np.nan, index=values.index, dtype=float)
    scaled = centered / scale
    std = scaled.std(ddof=0)
    if not np.isfinite(std) or std <= 0:
        return pd.Series(np.nan, index=values.index, dtype=float)
    return scaled / std


def preprocess_factor(series: pd.Series, config: dict) -> pd.Series:
    if config.get("factor_transform", "cross_sectional") == "rolling_median_zscore":
        wide = series.unstack("symbol")
        processed = preprocess_factor_wide(wide, config).stack(future_stack=True)
        processed.index.names = series.index.names
        return processed.reindex(series.index).astype(float).rename(series.name)
    processed = series.groupby(level="datetime", group_keys=False).apply(
        _process_group,
        lower=float(config["winsor_lower"]),
        upper=float(config["winsor_upper"]),
        zscore=bool(config["cross_sectional_zscore"]),
        min_cross_section=int(config["min_cross_section"]),
    )
    return processed.fillna(0.0).astype(float).rename(series.name)


def preprocess_factor_wide(frame: pd.DataFrame, config: dict) -> pd.DataFrame:
    finite = frame.replace([np.inf, -np.inf], np.nan).astype(float)
    transform = config.get("factor_transform", "cross_sectional")
    if transform == "rolling_median_zscore":
        window = int(config.get("rolling_window", 252))
        min_periods = int(config.get("rolling_min_periods", 63))
        median = finite.rolling(window=window, min_periods=min_periods).median()
        std = finite.rolling(window=window, min_periods=min_periods).std(ddof=0).replace(0.0, np.nan)
        clip = float(config.get("rolling_clip", 3.0))
        return finite.sub(median).div(std).clip(-clip, clip).fillna(0.0)
    if transform != "cross_sectional":
        raise ValueError(f"Unknown factor_transform: {transform}")
    counts = finite.notna().sum(axis=1)
    lower = finite.quantile(float(config["winsor_lower"]), axis=1)
    upper = finite.quantile(float(config["winsor_upper"]), axis=1)
    clipped = finite.clip(lower=lower, upper=upper, axis=0)
    if config["cross_sectional_zscore"]:
        centered = clipped.sub(clipped.mean(axis=1), axis=0)
        scales = centered.abs().max(axis=1).replace(0.0, np.nan)
        scaled = centered.div(scales, axis=0)
        stds = scaled.std(axis=1, ddof=0).replace(0.0, np.nan)
        clipped = scaled.div(stds, axis=0)
    clipped = clipped.where(counts >= int(config["min_cross_section"]))
    return clipped.fillna(0.0)


def preprocess_label(series: pd.Series, config: dict) -> pd.Series:
    label = series.replace([np.inf, -np.inf], np.nan).astype(float)
    transform = config.get("label_transform", "raw")
    if transform == "cross_sectional_rank":
        label = label.groupby(level="datetime").rank(pct=True, method="average") - 0.5
    elif transform != "raw":
        raise ValueError(f"Unknown label_transform: {transform}")
    if config.get("demean_label", True):
        label = label - label.groupby(level="datetime").transform("mean")
    counts = label.groupby(level="datetime").transform("count")
    return label.where(counts >= int(config["min_cross_section"])).rename("target")
