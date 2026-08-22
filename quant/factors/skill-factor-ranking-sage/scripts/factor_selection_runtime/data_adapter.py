"""Load and align local factor and label panels."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .config_utils import ConfigError, file_sha256


@dataclass
class PanelData:
    panel: pd.DataFrame
    feature_columns: list[str]
    metadata: dict[str, Any]
    warnings: list[str]


def normalize_dates(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip()
    numeric = text.str.fullmatch(r"\d{8}")
    result = pd.Series(index=series.index, dtype="int64")
    if numeric.any():
        result.loc[numeric] = text.loc[numeric].astype("int64")
    if (~numeric).any():
        parsed = pd.to_datetime(text.loc[~numeric], errors="raise")
        result.loc[~numeric] = parsed.dt.strftime("%Y%m%d").astype("int64")
    return result.astype("int64")


def _read_csv(path: str) -> pd.DataFrame:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Input file does not exist: {source}")
    if source.suffix.lower() != ".csv":
        raise ConfigError("Only CSV factor and label files are supported")
    return pd.read_csv(source)


def _standardize_keys(frame: pd.DataFrame, date_col: str, ticker_col: str, name: str) -> pd.DataFrame:
    missing = [col for col in (date_col, ticker_col) if col not in frame.columns]
    if missing:
        raise ConfigError(f"{name} is missing key columns: {missing}")
    out = frame.copy()
    out["date"] = normalize_dates(out[date_col])
    out["ticker"] = out[ticker_col].astype(str).str.strip()
    if date_col != "date":
        out = out.drop(columns=[date_col])
    if ticker_col != "ticker":
        out = out.drop(columns=[ticker_col])
    duplicates = int(out.duplicated(["date", "ticker"]).sum())
    if duplicates:
        raise ValueError(f"{name} contains {duplicates} duplicated (date, ticker) rows")
    return out


def build_panel(cfg: Mapping[str, Any]) -> PanelData:
    data_cfg = cfg["data"]
    date_col = str(data_cfg["date_col"])
    ticker_col = str(data_cfg["ticker_col"])
    label_col = str(data_cfg["label_col"])
    features = _standardize_keys(
        _read_csv(cfg["input"]["feature_path"]), date_col, ticker_col, "feature table"
    )
    labels = _standardize_keys(
        _read_csv(cfg["input"]["label_path"]), date_col, ticker_col, "label table"
    )
    if label_col not in labels.columns:
        raise ConfigError(f"Label table is missing data.label_col={label_col!r}")
    if label_col in features.columns:
        raise ConfigError("Factor table must not contain the configured label column")

    include = list(data_cfg.get("feature_include") or [])
    exclude = set(data_cfg.get("feature_exclude") or [])
    reserved = {"date", "ticker", label_col, "available_date"}
    factors = include or [column for column in features.columns if column not in reserved]
    factors = [column for column in factors if column not in exclude]
    missing = [column for column in factors if column not in features.columns]
    if missing:
        raise ConfigError(f"Configured factor columns are missing: {missing}")
    non_numeric = [column for column in factors if not pd.api.types.is_numeric_dtype(features[column])]
    if non_numeric:
        raise ConfigError(f"Factor columns must be numeric: {non_numeric}")
    if not factors:
        raise ConfigError("No factor columns remain after include/exclude filtering")

    labels = labels[["date", "ticker", label_col]].rename(columns={label_col: "y"})
    labels["y"] = pd.to_numeric(labels["y"], errors="coerce")
    panel = features[["date", "ticker", *factors]].merge(labels, on=["date", "ticker"], how="inner")
    panel = panel.dropna(subset=["y"]).sort_values(["date", "ticker"]).reset_index(drop=True)
    if panel.empty:
        raise ValueError("Aligned factor/label panel is empty")

    warnings: list[str] = []
    if "available_date" not in features.columns:
        warnings.append("point_in_time_risk: available_date is absent; source timing cannot be verified")
    metadata = {
        "feature_path": cfg["input"]["feature_path"],
        "feature_sha256": file_sha256(cfg["input"]["feature_path"]),
        "label_path": cfg["input"]["label_path"],
        "label_sha256": file_sha256(cfg["input"]["label_path"]),
        "num_rows": int(len(panel)),
        "num_dates": int(panel["date"].nunique()),
        "num_tickers": int(panel["ticker"].nunique()),
        "num_factors": int(len(factors)),
    }
    return PanelData(panel, factors, metadata, warnings)
