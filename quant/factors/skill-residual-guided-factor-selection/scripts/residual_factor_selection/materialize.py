from __future__ import annotations

import importlib.util
import json
import multiprocessing as mp
import sys
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


_ALPHA158_WORKER_STATE: dict[str, Any] = {}


def _compute_alpha158_spec(spec_index: int) -> dict[str, Any]:
    spec = _ALPHA158_WORKER_STATE["specs"][spec_index]
    bar_frames = _ALPHA158_WORKER_STATE["bar_frames"]
    output_root = _ALPHA158_WORKER_STATE["output_root"]
    force = _ALPHA158_WORKER_STATE["force"]
    factor_name = spec["factor_name"]
    output_path = output_root / f"{factor_name}.parquet"
    if force or not output_path.exists():
        columns: dict[str, pd.Series] = {}
        for symbol, frame in bar_frames.items():
            result = spec["function"](frame, **spec["params"])
            if not isinstance(result, pd.DataFrame) or "signal" not in result:
                raise ValueError(f"{factor_name} must return a DataFrame with a signal column")
            columns[symbol] = pd.to_numeric(result["signal"], errors="coerce")
        wide = pd.DataFrame(columns).sort_index()
        wide.index.name = "datetime"
        wide.to_parquet(output_path)
    return {
        "factor_name": factor_name,
        "variant": spec["variant"],
        "params": json.dumps(spec["params"], ensure_ascii=False, sort_keys=True),
        "category": spec["category"],
        "formula": spec["formula"],
        "source_path": str(spec["source_path"]),
        "factor_path": str(output_path),
        "status": "ok",
    }


def import_module(path: Path):
    spec = importlib.util.spec_from_file_location(f"residual_factor_selection_alpha158_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def discover_factor_specs(source_dir: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source_path in sorted(Path(source_dir).glob("*.py")):
        module = import_module(source_path)
        for function_name, spec in getattr(module, "FACTOR_SPECS").items():
            variants = spec.get("variants") or {"base": {}}
            for variant, params in variants.items():
                factor_name = function_name if variant == "base" else f"{function_name}_{variant}"
                rows.append(
                    {
                        "factor_name": factor_name,
                        "function_name": function_name,
                        "variant": variant,
                        "params": params,
                        "category": spec.get("category", ""),
                        "formula": spec.get("formula", ""),
                        "source_path": source_path,
                        "function": spec["function"],
                    }
                )
    return rows


def _bar_paths(bar_dir: str | Path, symbols: Iterable[str] | None) -> list[Path]:
    paths = sorted(path for path in Path(bar_dir).glob("*.parquet") if not path.name.startswith("_"))
    if symbols is not None:
        requested = {symbol.upper() for symbol in symbols}
        paths = [path for path in paths if path.stem.upper() in requested]
    if not paths:
        raise FileNotFoundError(f"No bar parquet files found in {bar_dir}")
    return paths


def _read_bar(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    if "trade_date" in frame.columns:
        frame = frame.set_index("trade_date")
    frame.index = pd.to_datetime(frame.index, errors="coerce")
    frame = frame.loc[frame.index.notna()].sort_index()
    if frame.empty or frame.index.max().year < 1990:
        raise ValueError(f"Invalid trading-date index in {path}")
    return frame


def materialize_alpha158(
    source_dir: str | Path,
    bar_dir: str | Path,
    output_dir: str | Path,
    manifest_path: str | Path,
    factor_names: Iterable[str] | None = None,
    symbols: Iterable[str] | None = None,
    force: bool = False,
    n_jobs: int = 1,
) -> pd.DataFrame:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    requested = None if factor_names is None else set(factor_names)
    bar_frames: dict[str, pd.DataFrame] = {}
    for bar_path in _bar_paths(bar_dir, symbols):
        frame = _read_bar(bar_path)
        bar_frames[bar_path.stem.upper()] = frame
    specs = [
        spec
        for spec in discover_factor_specs(source_dir)
        if requested is None or spec["factor_name"] in requested
    ]

    workers = max(1, min(int(n_jobs), len(specs)))
    _ALPHA158_WORKER_STATE.clear()
    _ALPHA158_WORKER_STATE.update(
        {"specs": specs, "bar_frames": bar_frames, "output_root": output_root, "force": force}
    )
    if workers == 1:
        manifest = [_compute_alpha158_spec(index) for index in range(len(specs))]
    else:
        with mp.get_context("fork").Pool(processes=workers) as pool:
            manifest = pool.map(_compute_alpha158_spec, range(len(specs)))
    _ALPHA158_WORKER_STATE.clear()
    frame = pd.DataFrame(manifest).sort_values("factor_name").reset_index(drop=True)
    destination = Path(manifest_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False)
    return frame


def _build_bar_matrices(
    bar_dir: str | Path,
    symbols: Iterable[str] | None,
) -> dict[str, pd.DataFrame]:
    fields = ["open", "high", "low", "close", "volume", "amount", "vwap"]
    columns: dict[str, dict[str, pd.Series]] = {field: {} for field in fields}
    for bar_path in _bar_paths(bar_dir, symbols):
        frame = _read_bar(bar_path)
        symbol = bar_path.stem.upper()
        for field in fields:
            if field in frame:
                columns[field][symbol] = pd.to_numeric(frame[field], errors="coerce")
    matrices = {
        field: pd.DataFrame(values).sort_index().replace([np.inf, -np.inf], np.nan)
        for field, values in columns.items()
        if values
    }
    required = {"open", "high", "low", "close", "volume"}
    missing = sorted(required.difference(matrices))
    if missing:
        raise ValueError(f"Panda bars are missing required fields: {missing}")
    return matrices


def _load_alpha_compute(source_repo: str | Path, library: str):
    scripts_dir = Path(source_repo) / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    if library == "alpha101":
        from alpha_runtime.alpha101_formulas import compute_all_alpha101

        return compute_all_alpha101
    if library == "alpha191":
        from alpha_runtime.alpha191_formulas import compute_all_alpha191

        return compute_all_alpha191
    raise ValueError(f"Unsupported alpha library: {library}")


def materialize_formula_library(
    library: str,
    source_repo: str | Path,
    bar_dir: str | Path,
    output_dir: str | Path,
    symbols: Iterable[str] | None = None,
    factor_names: Iterable[str] | None = None,
    force: bool = False,
    n_jobs: int = 1,
) -> pd.DataFrame:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    matrices = _build_bar_matrices(bar_dir, symbols)
    compute = _load_alpha_compute(source_repo, library)
    if library == "alpha101":
        results = compute(matrices, factor_names, n_jobs=n_jobs, show_progress=True)
    else:
        results = compute(matrices, None, factor_names, n_jobs=n_jobs, show_progress=True)

    manifest: list[dict[str, Any]] = []
    for raw_name, values in sorted(results.items()):
        factor_name = f"F_{library}_{raw_name.removeprefix('alpha_')}"
        output_path = output_root / f"{factor_name}.parquet"
        status = "unavailable" if values is None else "ok"
        if values is not None and (force or not output_path.exists()):
            wide = values.copy().sort_index().replace([np.inf, -np.inf], np.nan)
            wide.index = pd.to_datetime(wide.index.astype(str), errors="coerce")
            wide = wide.loc[wide.index.notna()]
            wide.index.name = "datetime"
            wide.columns = wide.columns.astype(str).str.upper()
            wide.to_parquet(output_path)
        manifest.append(
            {
                "factor_name": factor_name,
                "library": library,
                "source_name": raw_name,
                "source_path": str(source_repo),
                "factor_path": str(output_path) if status == "ok" else "",
                "status": status,
            }
        )
    return pd.DataFrame(manifest)


def materialize_factorbank(
    config: dict[str, Any],
    libraries: Iterable[str],
    factor_names: Iterable[str] | None = None,
    symbols: Iterable[str] | None = None,
    force: bool = False,
    n_jobs: int = 1,
) -> pd.DataFrame:
    data = config["data"]
    selected_libraries = list(libraries)
    manifests: list[pd.DataFrame] = []
    destination = Path(data["factor_manifest"])
    if destination.exists():
        existing = pd.read_csv(destination)
        if "library" in existing:
            manifests.append(existing.loc[~existing["library"].isin(selected_libraries)])
    for library in selected_libraries:
        if library == "alpha158":
            frame = materialize_alpha158(
                source_dir=data["alpha158_source_dir"],
                bar_dir=data["bar_dir"],
                output_dir=data["factor_dir"],
                manifest_path=data["factor_manifest"],
                factor_names=factor_names,
                symbols=symbols,
                force=force,
                n_jobs=n_jobs,
            )
            frame["library"] = "alpha158"
            manifests.append(frame)
        else:
            manifests.append(
                materialize_formula_library(
                    library=library,
                    source_repo=data["alpha_formula_source_repo"],
                    bar_dir=data["bar_dir"],
                    output_dir=data["factor_dir"],
                    symbols=symbols,
                    factor_names=factor_names,
                    force=force,
                    n_jobs=n_jobs,
                )
            )
    manifest = pd.concat(manifests, ignore_index=True, sort=False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest.sort_values(["library", "factor_name"]).to_csv(destination, index=False)
    return manifest
