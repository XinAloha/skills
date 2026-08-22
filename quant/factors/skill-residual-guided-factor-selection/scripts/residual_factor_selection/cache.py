from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from .serialization import json_ready, write_json


CACHE_SCHEMA_VERSION = 1


def cache_manifest_path(cache_path: str | Path) -> Path:
    path = Path(cache_path)
    return path.with_name(f"{path.name}.meta.json")


def _index_hash(index: pd.MultiIndex) -> str:
    values = pd.util.hash_pandas_object(index, index=True).to_numpy()
    return hashlib.sha256(values.tobytes()).hexdigest()


def _config_digest(payload: dict) -> str:
    encoded = json.dumps(
        json_ready(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_frame(
    frame: pd.DataFrame,
    expected_index: pd.MultiIndex,
    expected_factor_names: Iterable[str] | None,
) -> None:
    if not isinstance(frame.index, pd.MultiIndex):
        raise ValueError("Prepared feature cache must use a MultiIndex")
    if list(frame.index.names) != ["datetime", "symbol"]:
        raise ValueError("Prepared feature cache index names must be ['datetime', 'symbol']")
    if not frame.index.is_unique:
        raise ValueError("Prepared feature cache index contains duplicate keys")
    if not frame.index.equals(expected_index):
        raise ValueError("Prepared feature cache keys do not exactly match the configured label splits")
    factor_names = [str(name) for name in frame.columns]
    if len(factor_names) != len(set(factor_names)):
        raise ValueError("Prepared feature cache contains duplicate factor names")
    if expected_factor_names is not None and factor_names != [str(name) for name in expected_factor_names]:
        raise ValueError("Prepared feature cache factor list does not match factor_dir")


def build_cache_metadata(
    frame: pd.DataFrame,
    universe: Iterable[str],
    preprocess: dict,
    split: dict,
) -> dict:
    dates = frame.index.get_level_values("datetime")
    factor_names = [str(name) for name in frame.columns]
    binding = {
        "factor_names": factor_names,
        "universe": [str(symbol) for symbol in universe],
        "preprocess": preprocess,
        "split": split,
    }
    return {
        "schema_version": CACHE_SCHEMA_VERSION,
        **binding,
        "row_count": int(len(frame)),
        "date_min": pd.Timestamp(dates.min()).isoformat(),
        "date_max": pd.Timestamp(dates.max()).isoformat(),
        "index_hash": _index_hash(frame.index),
        "binding_hash": _config_digest(binding),
    }


def write_prepared_cache(
    cache_path: str | Path,
    frame: pd.DataFrame,
    expected_index: pd.MultiIndex,
    universe: Iterable[str],
    preprocess: dict,
    split: dict,
) -> dict:
    path = Path(cache_path)
    prepared = frame.sort_index()
    prepared.columns = prepared.columns.astype(str)
    _validate_frame(prepared, expected_index, prepared.columns)
    path.parent.mkdir(parents=True, exist_ok=True)
    prepared.to_parquet(path)
    metadata = build_cache_metadata(prepared, universe, preprocess, split)
    write_json(cache_manifest_path(path), metadata)
    return metadata


def write_cache_manifest(
    cache_path: str | Path,
    expected_index: pd.MultiIndex,
    universe: Iterable[str],
    preprocess: dict,
    split: dict,
    expected_factor_names: Iterable[str] | None = None,
) -> dict:
    path = Path(cache_path)
    frame = pd.read_parquet(path)
    frame.columns = frame.columns.astype(str)
    _validate_frame(frame, expected_index, expected_factor_names)
    metadata = build_cache_metadata(frame, universe, preprocess, split)
    write_json(cache_manifest_path(path), metadata)
    return metadata


def load_prepared_cache(
    cache_path: str | Path,
    expected_index: pd.MultiIndex,
    universe: Iterable[str],
    preprocess: dict,
    split: dict,
    expected_factor_names: Iterable[str] | None = None,
) -> pd.DataFrame:
    path = Path(cache_path)
    metadata_path = cache_manifest_path(path)
    if not metadata_path.exists():
        raise ValueError(
            f"Prepared cache manifest is missing: {metadata_path}. "
            "Run validate-cache --write-manifest after verifying the existing cache."
        )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    frame = pd.read_parquet(path)
    frame.columns = frame.columns.astype(str)
    _validate_frame(frame, expected_index, expected_factor_names)
    actual = build_cache_metadata(frame, universe, preprocess, split)
    if metadata != actual:
        raise ValueError("Prepared feature cache manifest does not match the cache or current configuration")
    return frame
