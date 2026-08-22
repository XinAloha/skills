#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import random
import sys
import textwrap
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.metrics import mutual_info_score


SKILL_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = SKILL_ROOT.parent

ALPHA_LIBRARY_ROOT: Path | None = None
Alpha101Engine = None
Alpha191Engine = None
build_alpha_output_frame = None
compute_engine_alpha_methods = None
build_matrices = None
convert_to_unadjusted_price = None
load_benchmark_matrices = None
load_market_data_frame = None
resolve_alpha_selection = None


JsonDict = dict[str, Any]


@dataclass
class FactorCandidate:
    name: str
    generation: int
    operator: str
    source: str
    parents: list[str]
    expression: str
    values: pd.Series
    description: str = ""
    formula: str | None = None
    code: str | None = None
    metrics: JsonDict = field(default_factory=dict)
    metadata: JsonDict = field(default_factory=dict)

    def summary_dict(self, *, use_abs_metrics: bool) -> JsonDict:
        payload: JsonDict = {
            "name": self.name,
            "generation": self.generation,
            "operator": self.operator,
            "source": self.source,
            "parents": self.parents,
            "expression": self.expression,
            "description": self.description,
            "formula": self.formula,
            "code": self.code,
            "lineage_depth": len(self.parents),
            **self.metrics,
        }
        rank_ic = _metric_value(self.metrics.get("rank_ic"))
        rank_icir = _metric_value(self.metrics.get("rank_icir"))
        payload["abs_rank_ic"] = abs(rank_ic) if rank_ic is not None else None
        payload["abs_rank_icir"] = abs(rank_icir) if rank_icir is not None else None
        payload["primary_score"] = _sortable_metric(rank_ic, use_abs_metrics)
        payload["secondary_score"] = _sortable_metric(rank_icir, use_abs_metrics)
        payload["recommended_sign"] = -1 if rank_icir is not None and rank_icir < 0 else 1
        return payload


@dataclass(frozen=True)
class EvolutionContext:
    dates: pd.Series
    instruments: pd.Series


@dataclass(frozen=True)
class DailyICRecord:
    alpha_name: str
    date: Any
    ic: float | None
    rank_ic: float | None
    mi: float | None
    sample_count: int
    skipped: bool = False
    skip_reason: str | None = None

    def to_dict(self) -> JsonDict:
        return {
            "alpha_name": self.alpha_name,
            "date": self.date.isoformat() if hasattr(self.date, "isoformat") else self.date,
            "ic": self.ic,
            "rank_ic": self.rank_ic,
            "mi": self.mi,
            "sample_count": self.sample_count,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
        }


@dataclass(frozen=True)
class FactorMetrics:
    alpha_name: str
    ic: float | None
    rank_ic: float | None
    valid_days: int
    valid_samples: int
    skipped_days: int
    icir: float | None = None
    rank_icir: float | None = None
    mi: float | None = None
    failure_reason: str | None = None
    daily_records: list[DailyICRecord] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (
            self.failure_reason is None
            and self.ic is not None
            and self.rank_ic is not None
            and self.mi is not None
        )

    def to_summary_dict(self) -> JsonDict:
        return {
            "alpha_name": self.alpha_name,
            "ic": self.ic,
            "rank_ic": self.rank_ic,
            "icir": self.icir,
            "rank_icir": self.rank_icir,
            "mi": self.mi,
            "valid_days": self.valid_days,
            "valid_samples": self.valid_samples,
            "skipped_days": self.skipped_days,
            "evaluation_passed": self.passed,
            "failure_reason": self.failure_reason,
        }


MutationSpec = tuple[str, Callable[[pd.Series, EvolutionContext], pd.Series], Callable[[str], str]]
CrossoverSpec = tuple[
    str,
    Callable[[pd.Series, pd.Series, EvolutionContext], pd.Series],
    Callable[[str, str], str],
]


def _add_sys_path(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _resolve_alpha_library_root(config: JsonDict | None) -> Path | None:
    candidates: list[Path] = []
    if config is not None:
        raw = str(config.get("alpha_library_root", "") or "").strip()
        if raw:
            candidates.append(Path(raw).expanduser())

    env_raw = os.environ.get("COGALPHA_FACTOR_POOL_ALPHA_LIBRARY_ROOT", "").strip()
    if env_raw:
        candidates.append(Path(env_raw).expanduser())

    candidates.extend(
        [
            SKILL_ROOT / "vendor" / "skill-factor-alpha191-alpha101-main",
            WORKSPACE_ROOT / "skill-factor-alpha191-alpha101-main",
        ]
    )

    for candidate in candidates:
        candidate = candidate.resolve()
        scripts_dir = candidate / "scripts"
        if scripts_dir.is_dir() and (scripts_dir / "alpha_runtime").is_dir():
            return candidate
        if candidate.is_dir() and (candidate / "alpha_runtime").is_dir():
            return candidate.parent
    return None


def _bootstrap_alpha_library_dependencies(config: JsonDict | None = None) -> None:
    global ALPHA_LIBRARY_ROOT
    global Alpha101Engine, Alpha191Engine
    global build_alpha_output_frame, compute_engine_alpha_methods
    global build_matrices, convert_to_unadjusted_price, load_benchmark_matrices, load_market_data_frame, resolve_alpha_selection

    if all(
        dependency is not None
        for dependency in (
            Alpha101Engine,
            Alpha191Engine,
            build_alpha_output_frame,
            compute_engine_alpha_methods,
            build_matrices,
            convert_to_unadjusted_price,
            load_benchmark_matrices,
            load_market_data_frame,
            resolve_alpha_selection,
        )
    ):
        return

    library_root = _resolve_alpha_library_root(config)
    if library_root is not None:
        scripts_dir = library_root / "scripts"
        if scripts_dir.is_dir():
            _add_sys_path(scripts_dir)
        ALPHA_LIBRARY_ROOT = library_root

    try:
        alpha101_module = importlib.import_module("alpha_runtime.alpha101_formulas")
        alpha191_module = importlib.import_module("alpha_runtime.alpha191_formulas")
        alpha_compute_module = importlib.import_module("alpha_runtime.alpha_compute")
        alpha_data_module = importlib.import_module("alpha_runtime.data")
        alpha_selector_module = importlib.import_module("alpha_runtime.selector")
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Unable to import the Alpha101/Alpha191 library runtime. "
            "Set `alpha_library_root` in the input JSON or set the env var "
            "`COGALPHA_FACTOR_POOL_ALPHA_LIBRARY_ROOT` to the skill-factor-alpha191-alpha101-main directory."
        ) from exc

    Alpha101Engine = alpha101_module.Alpha101Engine
    Alpha191Engine = alpha191_module.Alpha191Engine
    build_alpha_output_frame = alpha_compute_module.build_alpha_output_frame
    compute_engine_alpha_methods = alpha_compute_module.compute_engine_alpha_methods
    build_matrices = alpha_data_module.build_matrices
    convert_to_unadjusted_price = alpha_data_module.convert_to_unadjusted_price
    load_benchmark_matrices = alpha_data_module.load_benchmark_matrices
    load_market_data_frame = alpha_data_module.load_market_data_frame
    resolve_alpha_selection = alpha_selector_module.resolve_alpha_selection
    if ALPHA_LIBRARY_ROOT is None:
        ALPHA_LIBRARY_ROOT = Path(alpha101_module.__file__).resolve().parents[2]


def _require_columns(data: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _build_forward_return_target(
    data: pd.DataFrame,
    horizon_days: int = 10,
    price_col: str = "open",
    target_col: str = "target_return",
    instrument_col: str = "instrument",
    date_col: str = "date",
) -> pd.DataFrame:
    if horizon_days <= 0:
        raise ValueError("horizon_days must be positive")
    _require_columns(data, [instrument_col, date_col, price_col])

    result = data.copy()
    result[date_col] = pd.to_datetime(result[date_col], errors="coerce")
    result = result.dropna(subset=[instrument_col, date_col])
    result = result.sort_values([instrument_col, date_col]).copy()

    price = pd.to_numeric(result[price_col], errors="coerce")
    grouped_price = price.groupby(result[instrument_col], sort=False)
    entry_price = grouped_price.shift(-1)
    exit_price = grouped_price.shift(-(horizon_days + 1))
    result[target_col] = (exit_price / entry_price) - 1.0
    result[target_col] = result[target_col].replace([np.inf, -np.inf], np.nan)
    return result.sort_values([date_col, instrument_col]).reset_index(drop=True)


def _information_ratio(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    series = pd.Series(values, dtype="float64")
    std = float(series.std(ddof=0))
    if not np.isfinite(std) or std <= 0.0:
        return None
    mean = float(series.mean())
    return mean / std


def _clean_daily_frame(frame: pd.DataFrame, factor_col: str, target_col: str) -> pd.DataFrame:
    clean = frame.loc[:, [factor_col, target_col]].copy()
    clean[factor_col] = pd.to_numeric(clean[factor_col], errors="coerce")
    clean[target_col] = pd.to_numeric(clean[target_col], errors="coerce")
    clean = clean.replace([np.inf, -np.inf], np.nan)
    return clean.dropna(subset=[factor_col, target_col])


def _daily_skip_reason(frame: pd.DataFrame, factor_col: str, target_col: str, min_periods: int) -> str | None:
    if len(frame) < min_periods:
        return "insufficient_samples"
    if frame[factor_col].nunique() < 2:
        return "constant_factor"
    if frame[target_col].nunique() < 2:
        return "constant_target"
    return None


def _pearson_corr(left: pd.Series, right: pd.Series) -> float | None:
    if len(left) < 2 or left.nunique() < 2 or right.nunique() < 2:
        return None
    value = left.corr(right, method="pearson")
    if pd.isna(value) or not np.isfinite(value):
        return None
    return float(value)


def _mutual_information(left: pd.Series, right: pd.Series, n_bins: int = 10) -> float:
    if len(left) == 0:
        return 0.0
    left_bins = pd.qcut(left.rank(method="first"), q=min(n_bins, len(left)), labels=False, duplicates="drop")
    right_bins = pd.qcut(right.rank(method="first"), q=min(n_bins, len(right)), labels=False, duplicates="drop")
    if left_bins is None or right_bins is None:
        return 0.0
    return float(mutual_info_score(left_bins, right_bins))


def _evaluate_factor_ic_rankic(
    frame: pd.DataFrame,
    factor_col: str,
    target_col: str = "target_return",
    date_col: str = "date",
    min_periods: int = 3,
    mi_bins: int = 10,
) -> FactorMetrics:
    _require_columns(frame, [date_col, factor_col, target_col])
    daily_records: list[DailyICRecord] = []
    valid_ic_values: list[float] = []
    valid_rank_ic_values: list[float] = []
    valid_mi_values: list[float] = []
    valid_samples = 0

    for date_value, group in frame.groupby(date_col, sort=True):
        clean = _clean_daily_frame(group, factor_col=factor_col, target_col=target_col)
        sample_count = int(len(clean))
        skip_reason = _daily_skip_reason(clean, factor_col, target_col, min_periods)
        if skip_reason is not None:
            daily_records.append(
                DailyICRecord(
                    alpha_name=factor_col,
                    date=date_value,
                    ic=None,
                    rank_ic=None,
                    mi=None,
                    sample_count=sample_count,
                    skipped=True,
                    skip_reason=skip_reason,
                )
            )
            continue

        ic = _pearson_corr(clean[factor_col], clean[target_col])
        factor_rank = clean[factor_col].rank(method="average")
        target_rank = clean[target_col].rank(method="average")
        rank_ic = _pearson_corr(factor_rank, target_rank)
        mi = _mutual_information(clean[factor_col], clean[target_col], n_bins=mi_bins)
        if ic is None or rank_ic is None:
            daily_records.append(
                DailyICRecord(
                    alpha_name=factor_col,
                    date=date_value,
                    ic=ic,
                    rank_ic=rank_ic,
                    mi=mi,
                    sample_count=sample_count,
                    skipped=True,
                    skip_reason="correlation_unavailable",
                )
            )
            continue

        daily_records.append(
            DailyICRecord(
                alpha_name=factor_col,
                date=date_value,
                ic=ic,
                rank_ic=rank_ic,
                mi=mi,
                sample_count=sample_count,
            )
        )
        valid_ic_values.append(ic)
        valid_rank_ic_values.append(rank_ic)
        valid_mi_values.append(mi)
        valid_samples += sample_count

    valid_days = len(valid_ic_values)
    skipped_days = len(daily_records) - valid_days
    if valid_days == 0:
        return FactorMetrics(
            alpha_name=factor_col,
            ic=None,
            rank_ic=None,
            valid_days=0,
            valid_samples=0,
            skipped_days=skipped_days,
            icir=None,
            rank_icir=None,
            mi=None,
            failure_reason="no_valid_daily_cross_sections",
            daily_records=daily_records,
        )

    return FactorMetrics(
        alpha_name=factor_col,
        ic=float(np.mean(valid_ic_values)),
        rank_ic=float(np.mean(valid_rank_ic_values)),
        icir=_information_ratio(valid_ic_values),
        rank_icir=_information_ratio(valid_rank_ic_values),
        mi=float(np.mean(valid_mi_values)),
        valid_days=valid_days,
        valid_samples=valid_samples,
        skipped_days=skipped_days,
        daily_records=daily_records,
    )


def _evaluate_factor_frame(
    frame: pd.DataFrame,
    factor_cols: list[str],
    target_col: str = "target_return",
    date_col: str = "date",
    min_periods: int = 3,
    mi_bins: int = 10,
) -> list[FactorMetrics]:
    return [
        _evaluate_factor_ic_rankic(
            frame=frame,
            factor_col=factor_col,
            target_col=target_col,
            date_col=date_col,
            min_periods=min_periods,
            mi_bins=mi_bins,
        )
        for factor_col in factor_cols
    ]


def _daily_records_to_frame(metrics: list[FactorMetrics]) -> pd.DataFrame:
    records = [
        daily_record.to_dict()
        for factor_metrics in metrics
        for daily_record in factor_metrics.daily_records
    ]
    return pd.DataFrame(records)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a simplified CogAlpha factor-pool evolution workflow."
    )
    parser.add_argument("--input", required=True, help="Path to evolution_input.json.")
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output directory override. Relative paths are resolved from the current working directory.",
    )
    return parser.parse_args()


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[JsonDict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        for row in rows:
            file_obj.write(json.dumps(row, ensure_ascii=False, default=_json_default))
            file_obj.write("\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _resolve_path(raw_path: str, *, input_dir: Path) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path.resolve()
    candidates = [
        (input_dir / path).resolve(),
        (SKILL_ROOT / path).resolve(),
        (WORKSPACE_ROOT / path).resolve(),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _resolve_output_dir(config: JsonDict, *, input_dir: Path, cli_output: str | None) -> Path:
    raw_path = cli_output or str(config.get("output_dir", "outputs/factor_pool_evolution_run")).strip()
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path.resolve()
    if cli_output:
        return (Path.cwd() / path).resolve()
    return (SKILL_ROOT / path).resolve()


def _progress(enabled: bool, message: str) -> None:
    if enabled:
        print(f"[Factor Pool Evolution] {message}", file=sys.stderr, flush=True)


def _load_input(path: Path) -> JsonDict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("input JSON must be an object")
    return payload


def _load_json_any(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _required_list(config: JsonDict, key: str) -> list[str]:
    value = config.get(key, [])
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list or string")
    return [str(item).strip() for item in value if str(item).strip()]


def _prepare_market_frames(config: JsonDict, *, input_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    _bootstrap_alpha_library_dependencies(config)
    raw_market = load_market_data_frame(config, input_dir=input_dir, skill_root=ALPHA_LIBRARY_ROOT)
    raw_market = raw_market.sort_values(["date", "symbol"]).reset_index(drop=True)

    eval_market = raw_market.rename(columns={"symbol": "instrument"}).copy()
    eval_market = _build_forward_return_target(
        eval_market,
        horizon_days=int(config.get("target_horizon_days", 5) or 5),
        price_col=str(config.get("target_price_col", "open") or "open"),
        target_col="target_return",
        instrument_col="instrument",
        date_col="date",
    )
    eval_market["instrument"] = eval_market["instrument"].astype(str)
    eval_market["date"] = pd.to_datetime(eval_market["date"], errors="coerce")
    eval_market = eval_market.sort_values(["date", "instrument"]).reset_index(drop=True)
    return raw_market, eval_market


def _compute_library_seed_frame(
    config: JsonDict,
    *,
    input_dir: Path,
    raw_market: pd.DataFrame,
    show_progress: bool,
) -> tuple[pd.DataFrame | None, dict[str, str]]:
    _bootstrap_alpha_library_dependencies(config)
    seed_alpha_names = _required_list(config, "seed_alpha_names")
    if not seed_alpha_names:
        return None, {}

    selection = resolve_alpha_selection(
        {
            "alpha_sets": config.get("seed_alpha_sets", []),
            "alpha_names": seed_alpha_names,
            "exclude_alpha_names": config.get("exclude_seed_alpha_names", []),
        }
    )

    matrices = convert_to_unadjusted_price(build_matrices(raw_market))
    symbols = sorted(str(symbol) for symbol in raw_market["symbol"].unique())
    benchmark = load_benchmark_matrices(
        config,
        input_dir=input_dir,
        skill_root=ALPHA_LIBRARY_ROOT,
        symbols=symbols,
    )

    n_jobs = int(config.get("n_jobs", 1) or 1)
    alpha_results: dict[str, pd.DataFrame] = {}
    source_by_name: dict[str, str] = {}
    ordered_names: list[str] = []

    for alpha_set, names in selection.items():
        _progress(show_progress, f"computing seed factors from {alpha_set}: requested={len(names)}")
        if alpha_set == "alpha101":
            computed = compute_engine_alpha_methods(
                engine=Alpha101Engine(matrices),
                names=names,
                n_jobs=n_jobs,
                show_progress=show_progress,
                label="Alpha101",
                backend="thread",
            )
        elif alpha_set == "alpha191":
            computed = compute_engine_alpha_methods(
                engine=Alpha191Engine(matrices, benchmark),
                names=names,
                n_jobs=n_jobs,
                show_progress=show_progress,
                label="Alpha191",
                backend="thread",
            )
        else:
            raise ValueError(f"unsupported alpha set: {alpha_set}")

        for name, factor_df in computed.items():
            qualified_name = f"{alpha_set}:{name}"
            alpha_results[qualified_name] = factor_df
            source_by_name[qualified_name] = alpha_set
            ordered_names.append(qualified_name)

    if not alpha_results:
        return None, {}

    factor_frame, _ = build_alpha_output_frame(raw_market, alpha_results, alpha_order=ordered_names)
    factor_frame["date"] = pd.to_datetime(factor_frame["date"], errors="coerce")
    factor_frame["instrument"] = factor_frame["symbol"].astype(str)
    factor_frame = factor_frame.drop(columns=["symbol"])
    return factor_frame, source_by_name


def _compute_custom_seed_frame(
    config: JsonDict,
    *,
    input_dir: Path,
    eval_market: pd.DataFrame,
) -> tuple[pd.DataFrame | None, dict[str, str]]:
    custom_path_raw = str(config.get("custom_seed_factors_json_path", "") or "").strip()
    if not custom_path_raw:
        return None, {}

    custom_path = _resolve_path(custom_path_raw, input_dir=input_dir)
    payload = _load_json_any(custom_path)
    factor_items = payload.get("factors") if isinstance(payload, dict) else None
    if factor_items is None and isinstance(payload, list):
        factor_items = payload
    if not isinstance(factor_items, list):
        raise ValueError("custom seed factor JSON must be a list or an object with a 'factors' field")
    output = eval_market.loc[:, ["date", "instrument"]].copy()
    source_by_name: dict[str, str] = {}
    loaded_any = False
    for index, item in enumerate(factor_items):
        if not isinstance(item, dict):
            continue
        raw_name = str(item.get("name", "")).strip()
        if not raw_name:
            raise ValueError(f"custom factor at index {index} is missing name")
        qualified_name = raw_name if raw_name.startswith("custom:") else f"custom:{raw_name}"
        factor_series = _execute_custom_factor(
            code=str(item.get("code") or ""),
            factor_name=qualified_name,
            data=eval_market,
        )
        output[qualified_name] = factor_series.to_numpy()
        source_by_name[qualified_name] = "custom_seed_pool"
        loaded_any = True

    if not loaded_any:
        return None, {}
    factor_cols = [column for column in output.columns if column not in {"date", "instrument"}]
    if not factor_cols:
        return None, {}
    return output, source_by_name


def _merge_seed_frames(
    eval_market: pd.DataFrame,
    library_frame: pd.DataFrame | None,
    custom_frame: pd.DataFrame | None,
) -> pd.DataFrame:
    base = eval_market.loc[:, ["date", "instrument", "target_return"]].copy()
    if library_frame is not None:
        base = base.merge(library_frame, on=["date", "instrument"], how="left")
    if custom_frame is not None:
        custom_only = [column for column in custom_frame.columns if column not in {"date", "instrument"}]
        for column in custom_only:
            base[column] = custom_frame[column].to_numpy()
    factor_cols = [column for column in base.columns if column not in {"date", "instrument", "target_return"}]
    if not factor_cols:
        raise ValueError("no seed factors were computed from the configured sources")
    return base


def _evaluate_factor_candidates(
    frame: pd.DataFrame,
    candidates: list[FactorCandidate],
    *,
    min_periods: int,
    mi_bins: int,
) -> list[JsonDict]:
    factor_cols = [candidate.name for candidate in candidates]
    metrics = _evaluate_factor_frame(
        frame,
        factor_cols=factor_cols,
        target_col="target_return",
        date_col="date",
        min_periods=min_periods,
        mi_bins=mi_bins,
    )
    metric_map = {metric.alpha_name: metric for metric in metrics}
    for candidate in candidates:
        metric = metric_map.get(candidate.name)
        if metric is None:
            candidate.metrics = {
                "evaluation_passed": False,
                "failure_reason": "missing_metrics",
            }
            continue
        candidate.metrics = metric.to_summary_dict()
    return metrics


def _load_custom_factor_function(code: str, factor_name: str):
    if not code.strip():
        raise ValueError(f"custom factor {factor_name} is missing code")
    namespace: dict[str, Any] = {}
    exec_globals = {
        "__builtins__": {
            "abs": abs,
            "float": float,
            "int": int,
            "len": len,
            "max": max,
            "min": min,
            "range": range,
            "Exception": Exception,
            "RuntimeError": RuntimeError,
            "TypeError": TypeError,
            "ValueError": ValueError,
        },
        "np": np,
        "pd": pd,
        "math": math,
    }
    exec(code, exec_globals, namespace)
    short_name = factor_name.split("custom:", 1)[-1]
    candidates = [namespace.get("alpha"), namespace.get(short_name)]
    factor_functions = [
        value for name, value in namespace.items() if name.startswith("factor_") and callable(value)
    ]
    candidates.extend(factor_functions)
    for candidate in candidates:
        if callable(candidate):
            return candidate
    raise ValueError(f"custom factor {factor_name} must define callable `alpha(...)` or `{short_name}(...)`")


def _coerce_custom_factor_series(raw_factor: Any, data: pd.DataFrame, factor_name: str) -> pd.Series:
    if isinstance(raw_factor, pd.Series):
        factor = raw_factor.copy()
    else:
        factor = pd.Series(raw_factor, index=data.index)
    if len(factor) != len(data):
        raise ValueError(f"custom factor {factor_name} returned length mismatch")
    factor = pd.to_numeric(factor, errors="coerce")
    factor = factor.replace([np.inf, -np.inf], np.nan)
    factor.index = data.index
    factor.name = factor_name
    return factor


def _execute_custom_factor(code: str, factor_name: str, data: pd.DataFrame) -> pd.Series:
    factor_fn = _load_custom_factor_function(code, factor_name)
    raw_factor = factor_fn(data.copy())
    return _coerce_custom_factor_series(raw_factor, data, factor_name)


def _slug(text: str) -> str:
    safe = "".join(char if char.isalnum() else "_" for char in text.lower())
    safe = "_".join(part for part in safe.split("_") if part)
    return safe[:48] or "factor"


def _format_float(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6f}"


def _available_market_columns(eval_market: pd.DataFrame) -> list[str]:
    hidden = {"date", "instrument", "target_return"}
    return [column for column in eval_market.columns if column not in hidden]


def _seed_description(candidate: FactorCandidate) -> str:
    rank_ic = _metric_value(candidate.metrics.get("rank_ic"))
    rank_icir = _metric_value(candidate.metrics.get("rank_icir"))
    return (
        f"seed={candidate.name}; "
        f"rank_ic={_format_float(rank_ic)}; "
        f"rank_icir={_format_float(rank_icir)}; "
        f"expression={candidate.expression}"
    )


def _mutation_prompt(
    *,
    parent: FactorCandidate,
    available_columns: list[str],
    run_note: str,
) -> str:
    return "\n\n".join(
        [
            "You are a quantitative factor researcher improving one existing stock alpha factor.",
            "Task: study the parent factor carefully, summarize its core economic logic, and produce exactly one mutated stock alpha factor.",
            "Required reasoning discipline:",
            "- first infer what the parent factor is trying to measure economically",
            "- preserve the parent factor's basic logic rather than replacing it with an unrelated idea",
            "- mutate only one or two structural components such as window, normalization, nonlinearity, gating, smoothing, or feature interaction",
            "- if you change the direction or signal shape, explain why that still preserves the parent logic",
            "Hard requirements:",
            "- the new factor must be implementable using only the provided market columns",
            "- avoid future leakage and target leakage",
            "- keep the formula concise, interpretable, and executable",
            f"Available market columns: {', '.join(available_columns)}",
            "Do not use target_return or any future label column.",
            f"Parent factor summary: {_seed_description(parent)}",
            f"Extra guidance: {run_note}",
            "Return JSON only with keys name, description, formula, code, preserved_logic, mutation_rationale, expected_edge.",
            (
                '{"name":"factor_xxx","description":"...","formula":"...","preserved_logic":"...",'
                '"mutation_rationale":"...","expected_edge":"...","code":"def factor_xxx(df):\\n'
                '    ...\\n'
                '    return df_copy[factor_name]\\n"}'
            ),
        ]
    )


def _crossover_prompt(
    *,
    left: FactorCandidate,
    right: FactorCandidate,
    available_columns: list[str],
    run_note: str,
    variant_index: int,
) -> str:
    return "\n\n".join(
        [
            "You are a quantitative factor researcher combining two existing stock alpha factors.",
            "Task: study the logic of both factors, identify where they are complementary, and produce exactly one crossover stock alpha factor.",
            "Required reasoning discipline:",
            "- treat the stronger factor as the primary logic anchor",
            "- analyze the lower-correlation factor as a diversity and complementarity source",
            "- preserve the primary factor's basic logic rather than discarding it",
            "- borrow only the complementary part of the partner factor",
            "- do not create an unrelated third idea disconnected from both parents",
            "Hard requirements:",
            "- the new factor must be implementable using only the provided market columns",
            "- avoid future leakage and target leakage",
            "- keep the formula concise, interpretable, and executable",
            f"Available market columns: {', '.join(available_columns)}",
            "Do not use target_return or any future label column.",
            f"Primary parent summary: {_seed_description(left)}",
            f"Diversity parent summary: {_seed_description(right)}",
            f"Variant index for this pair: {variant_index}",
            f"Extra guidance: {run_note}",
            "Return JSON only with keys name, description, formula, code, preserved_logic, complementarity_note, crossover_rationale, expected_edge.",
            (
                '{"name":"factor_xxx","description":"...","formula":"...","preserved_logic":"...",'
                '"complementarity_note":"...","crossover_rationale":"...","expected_edge":"...",'
                '"code":"def factor_xxx(df):\\n'
                '    ...\\n'
                '    return df_copy[factor_name]\\n"}'
            ),
        ]
    )


def _llm_config(config: JsonDict) -> JsonDict:
    api_key = str(config.get("llm_api_key") or os.environ.get("OPENAI_API_KEY", "")).strip()
    return {
        "enabled": bool(config.get("use_llm", True)),
        "api_key": api_key,
        "model": str(config.get("llm_model", "gpt-4.1-mini")),
        "base_url": str(config.get("llm_base_url", "https://api.openai.com/v1")).rstrip("/"),
        "timeout_seconds": int(config.get("llm_timeout_seconds", 90) or 90),
        "temperature": float(config.get("llm_temperature", 0.7) or 0.7),
        "required": bool(config.get("llm_required", False)),
        "fallback_on_failure": bool(config.get("fallback_on_llm_failure", True)),
        "save_artifacts": bool(config.get("save_llm_artifacts", True)),
    }


def _request_llm_json(prompt: str, llm_cfg: JsonDict) -> tuple[JsonDict | None, str | None, str | None]:
    if not llm_cfg["enabled"] or not llm_cfg["api_key"]:
        return None, None, "llm_disabled_or_missing_api_key"

    url = f"{llm_cfg['base_url']}/chat/completions"
    payload = {
        "model": llm_cfg["model"],
        "temperature": llm_cfg["temperature"],
        "messages": [
            {"role": "system", "content": "Return strict JSON only."},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {llm_cfg['api_key']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=llm_cfg["timeout_seconds"]) as response:
            response_text = response.read().decode("utf-8")
            payload = json.loads(response_text)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return None, None, f"request_failed:{exc}"

    try:
        content = payload["choices"][0]["message"]["content"]
        return json.loads(content), content, None
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        return None, None, f"parse_failed:{exc}"


def _build_llm_candidate(
    payload: JsonDict | None,
    *,
    fallback_name: str,
    fallback_description: str,
    fallback_formula: str,
    fallback_code: str,
    operator: str,
    parents: list[str],
    generation: int,
    source: str,
    data: pd.DataFrame,
) -> FactorCandidate | None:
    factor_name = str((payload or {}).get("name") or fallback_name).strip() or fallback_name
    description = str((payload or {}).get("description") or fallback_description).strip() or fallback_description
    formula = str((payload or {}).get("formula") or fallback_formula).strip() or fallback_formula
    code = str((payload or {}).get("code") or fallback_code).strip()
    qualified_name = factor_name if factor_name.startswith("custom:") else f"custom:{factor_name}"
    try:
        values = _execute_custom_factor(code, qualified_name, data)
    except Exception:
        return None
    return FactorCandidate(
        name=qualified_name,
        generation=generation,
        operator=operator,
        source=source,
        parents=parents,
        expression=formula,
        description=description,
        formula=formula,
        code=code,
        values=values,
        metadata={
            key: value
            for key, value in (payload or {}).items()
            if key not in {"name", "description", "formula", "code"}
        },
    )


def _mutation_fallback_spec(index: int) -> tuple[str, str, str]:
    templates = [
        (
            "close_open_strength",
            "Intraday close-to-open strength.",
            textwrap.dedent(
                """
                def {func_name}(df):
                    df_copy = df.copy()
                    factor_name = "{factor_name}"
                    df_copy.loc[:, factor_name] = df_copy["close"] / df_copy["open"] - 1.0
                    return df_copy[factor_name]
                """
            ).strip(),
        ),
        (
            "momentum_5d_close",
            "Five-day close momentum by instrument.",
            textwrap.dedent(
                """
                def {func_name}(df):
                    df_copy = df.copy()
                    grouped = df_copy.groupby("instrument", sort=False)
                    lag_close = grouped["close"].shift(5)
                    factor_name = "{factor_name}"
                    df_copy.loc[:, factor_name] = df_copy["close"] / lag_close - 1.0
                    return df_copy[factor_name]
                """
            ).strip(),
        ),
        (
            "reversal_5d_close",
            "Negative five-day close momentum.",
            textwrap.dedent(
                """
                def {func_name}(df):
                    df_copy = df.copy()
                    grouped = df_copy.groupby("instrument", sort=False)
                    lag_close = grouped["close"].shift(5)
                    factor_name = "{factor_name}"
                    df_copy.loc[:, factor_name] = -(df_copy["close"] / lag_close - 1.0)
                    return df_copy[factor_name]
                """
            ).strip(),
        ),
        (
            "volume_change_5d",
            "Five-day volume change.",
            textwrap.dedent(
                """
                def {func_name}(df):
                    df_copy = df.copy()
                    grouped = df_copy.groupby("instrument", sort=False)
                    lag_volume = grouped["volume"].shift(5)
                    factor_name = "{factor_name}"
                    df_copy.loc[:, factor_name] = df_copy["volume"].astype(float) / lag_volume - 1.0
                    return df_copy[factor_name]
                """
            ).strip(),
        ),
        (
            "range_position",
            "Close location inside the daily price range.",
            textwrap.dedent(
                """
                def {func_name}(df):
                    df_copy = df.copy()
                    spread = (df_copy["high"] - df_copy["low"]).replace(0.0, np.nan)
                    factor_name = "{factor_name}"
                    df_copy.loc[:, factor_name] = (df_copy["close"] - df_copy["low"]) / spread - 0.5
                    return df_copy[factor_name]
                """
            ).strip(),
        ),
    ]
    return templates[index % len(templates)]


def _crossover_fallback_spec(index: int) -> tuple[str, str, str]:
    templates = [
        (
            "price_volume_mix",
            "Blend price momentum and volume change.",
            textwrap.dedent(
                """
                def {func_name}(df):
                    df_copy = df.copy()
                    grouped = df_copy.groupby("instrument", sort=False)
                    lag_close = grouped["close"].shift(5)
                    lag_volume = grouped["volume"].shift(5)
                    price_momentum = df_copy["close"] / lag_close - 1.0
                    volume_change = df_copy["volume"].astype(float) / lag_volume - 1.0
                    factor_name = "{factor_name}"
                    df_copy.loc[:, factor_name] = 0.5 * price_momentum + 0.5 * volume_change
                    return df_copy[factor_name]
                """
            ).strip(),
        ),
        (
            "range_volume_coherence",
            "Interaction between daily range and volume change.",
            textwrap.dedent(
                """
                def {func_name}(df):
                    df_copy = df.copy()
                    grouped = df_copy.groupby("instrument", sort=False)
                    lag_volume = grouped["volume"].shift(3)
                    volume_change = df_copy["volume"].astype(float) / lag_volume - 1.0
                    intraday_range = (df_copy["high"] - df_copy["low"]) / df_copy["close"]
                    factor_name = "{factor_name}"
                    df_copy.loc[:, factor_name] = intraday_range * volume_change
                    return df_copy[factor_name]
                """
            ).strip(),
        ),
        (
            "momentum_strength_mix",
            "Blend short momentum with intraday strength.",
            textwrap.dedent(
                """
                def {func_name}(df):
                    df_copy = df.copy()
                    grouped = df_copy.groupby("instrument", sort=False)
                    lag_close = grouped["close"].shift(3)
                    momentum = df_copy["close"] / lag_close - 1.0
                    intraday_strength = df_copy["close"] / df_copy["open"] - 1.0
                    factor_name = "{factor_name}"
                    df_copy.loc[:, factor_name] = 0.5 * momentum + 0.5 * intraday_strength
                    return df_copy[factor_name]
                """
            ).strip(),
        ),
    ]
    return templates[index % len(templates)]


def _fallback_candidate(
    *,
    operator: str,
    generation: int,
    parents: list[str],
    data: pd.DataFrame,
    index: int,
    source_note: str,
) -> FactorCandidate:
    if operator == "mutation":
        slug, description, template = _mutation_fallback_spec(index)
    else:
        slug, description, template = _crossover_fallback_spec(index)
    factor_name = f"factor_{operator}_{generation:02d}_{index:03d}_{slug}"
    code = template.format(func_name=factor_name, factor_name=factor_name)
    qualified_name = f"custom:{factor_name}"
    values = _execute_custom_factor(code, qualified_name, data)
    return FactorCandidate(
        name=qualified_name,
        generation=generation,
        operator=operator,
        source=source_note,
        parents=parents,
        expression=slug,
        description=description,
        formula=slug,
        code=code,
        values=values,
    )


def _max_abs_correlation_to_pool(candidate: FactorCandidate, pool: list[FactorCandidate]) -> float | None:
    correlations = []
    for pool_candidate in pool:
        corr = _series_corr(candidate.values, pool_candidate.values)
        if corr is not None:
            correlations.append(abs(corr))
    if not correlations:
        return None
    return max(correlations)


def _score_generated_candidates(
    candidates: list[FactorCandidate],
    input_pool: list[FactorCandidate],
    *,
    use_abs_metrics: bool,
) -> pd.DataFrame:
    base_rows: list[JsonDict] = []

    for candidate in candidates:
        rank_ic = _metric_value(candidate.metrics.get("rank_ic"))
        rank_icir = _metric_value(candidate.metrics.get("rank_icir"))
        max_abs_corr = _max_abs_correlation_to_pool(candidate, input_pool)
        row = candidate.summary_dict(use_abs_metrics=use_abs_metrics)
        row["maxcorr_to_input_pool"] = max_abs_corr
        row["rank_ic_score"] = abs(rank_ic) if use_abs_metrics and rank_ic is not None else rank_ic
        row["rank_icir_score"] = abs(rank_icir) if use_abs_metrics and rank_icir is not None else rank_icir
        base_rows.append(row)

    ranked = pd.DataFrame(base_rows)
    if ranked.empty:
        return ranked
    return ranked.sort_values(
        ["rank_ic_score", "rank_icir_score", "abs_rank_ic", "abs_rank_icir"],
        ascending=False,
    ).reset_index(drop=True)


def _annotate_recommendations_without_filter(
    ranked_recommendations: pd.DataFrame,
    candidates: list[FactorCandidate],
    *,
    top_k: int,
    use_abs_corr: bool,
) -> tuple[list[str], pd.DataFrame]:
    candidate_map = {candidate.name: candidate for candidate in candidates}
    selected_names = ranked_recommendations.head(top_k)["name"].tolist()
    selected_candidates = [candidate_map[name] for name in selected_names if name in candidate_map]

    annotated = ranked_recommendations.copy()
    annotated["selected_for_recommendation"] = False
    annotated["skip_reason"] = ""
    annotated["corr_blocking_factor"] = ""
    annotated["maxcorr_to_selected"] = np.nan

    for index, row in annotated.iterrows():
        name = row["name"]
        if name in selected_names:
            annotated.at[index, "selected_for_recommendation"] = True

        candidate = candidate_map.get(name)
        if candidate is None:
            annotated.at[index, "skip_reason"] = "missing_candidate"
            continue

        compare_pool = [selected for selected in selected_candidates if selected.name != name]
        maxcorr_to_selected = None
        for selected in compare_pool:
            corr = _series_corr(candidate.values, selected.values)
            if corr is None:
                continue
            compare_value = abs(corr) if use_abs_corr else corr
            if maxcorr_to_selected is None or compare_value > maxcorr_to_selected:
                maxcorr_to_selected = compare_value

        if maxcorr_to_selected is not None:
            annotated.at[index, "maxcorr_to_selected"] = maxcorr_to_selected

    return selected_names, annotated


def _select_strong_pool(seeds: list[FactorCandidate], *, use_abs_metrics: bool) -> list[FactorCandidate]:
    if not seeds:
        return []
    sorted_seeds = sorted(
        seeds,
        key=lambda item: _candidate_sort_key(item, use_abs_metrics=use_abs_metrics),
        reverse=True,
    )
    cutoff = max(1, math.ceil(len(sorted_seeds) * 0.5))
    return sorted_seeds[:cutoff]


def _select_crossover_pairs(
    seeds: list[FactorCandidate],
    *,
    use_abs_metrics: bool,
) -> list[tuple[FactorCandidate, FactorCandidate]]:
    strong_pool = _select_strong_pool(seeds, use_abs_metrics=use_abs_metrics)
    if len(seeds) < 2:
        return []
    lower_priority_names = {candidate.name for candidate in seeds if candidate not in strong_pool}
    pairs: list[tuple[FactorCandidate, FactorCandidate]] = []

    for leader in strong_pool:
        candidates = [seed for seed in seeds if seed.name != leader.name]
        if lower_priority_names:
            candidates = sorted(
                candidates,
                key=lambda seed: (seed.name not in lower_priority_names, abs(_series_corr(leader.values, seed.values) or 1.0)),
            )
        else:
            candidates = sorted(
                candidates,
                key=lambda seed: abs(_series_corr(leader.values, seed.values) or 1.0),
            )
        if candidates:
            pairs.append((leader, candidates[0]))
    return pairs


def _seed_candidates_from_frame(
    frame: pd.DataFrame,
    *,
    factor_sources: dict[str, str],
) -> list[FactorCandidate]:
    candidates: list[FactorCandidate] = []
    factor_cols = [column for column in frame.columns if column not in {"date", "instrument", "target_return"}]
    for name in factor_cols:
        source = factor_sources.get(name, "seed")
        candidates.append(
            FactorCandidate(
                name=name,
                generation=0,
                operator="seed",
                source=source,
                parents=[],
                expression=name,
                values=pd.to_numeric(frame[name], errors="coerce"),
            )
        )
    return candidates


def _metric_value(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _sortable_metric(value: float | None, use_abs: bool) -> float:
    if value is None:
        return float("-inf")
    return abs(value) if use_abs else value


def _candidate_sort_key(candidate: FactorCandidate, *, use_abs_metrics: bool) -> tuple[float, float, float, float, int, str]:
    metrics = candidate.metrics
    return (
        _sortable_metric(_metric_value(metrics.get("rank_icir")), use_abs_metrics),
        _sortable_metric(_metric_value(metrics.get("rank_ic")), use_abs_metrics),
        _sortable_metric(_metric_value(metrics.get("icir")), use_abs_metrics),
        _sortable_metric(_metric_value(metrics.get("ic")), use_abs_metrics),
        candidate.generation,
        candidate.name,
    )


def _series_corr(left: pd.Series, right: pd.Series) -> float | None:
    left_num = pd.to_numeric(left, errors="coerce")
    right_num = pd.to_numeric(right, errors="coerce")
    aligned = pd.concat([left_num.rename("left"), right_num.rename("right")], axis=1).dropna()
    if len(aligned) < 3:
        return None
    corr = aligned["left"].corr(aligned["right"])
    if corr is None or pd.isna(corr):
        return None
    return float(corr)


def _passes_thresholds(candidate: FactorCandidate, *, min_abs_rank_ic: float, min_abs_rank_icir: float) -> bool:
    rank_ic = _metric_value(candidate.metrics.get("rank_ic"))
    rank_icir = _metric_value(candidate.metrics.get("rank_icir"))
    passed = bool(candidate.metrics.get("evaluation_passed", False))
    if not passed or rank_ic is None or rank_icir is None:
        return False
    return abs(rank_ic) >= min_abs_rank_ic and abs(rank_icir) >= min_abs_rank_icir


def _select_top_candidates(
    candidates: list[FactorCandidate],
    *,
    limit: int,
    use_abs_metrics: bool,
    dedupe_threshold: float,
    min_abs_rank_ic: float,
    min_abs_rank_icir: float,
) -> list[FactorCandidate]:
    selected: list[FactorCandidate] = []
    for candidate in sorted(candidates, key=lambda item: _candidate_sort_key(item, use_abs_metrics=use_abs_metrics), reverse=True):
        if not _passes_thresholds(
            candidate,
            min_abs_rank_ic=min_abs_rank_ic,
            min_abs_rank_icir=min_abs_rank_icir,
        ):
            continue
        too_similar = False
        for kept in selected:
            corr = _series_corr(candidate.values, kept.values)
            if corr is not None and abs(corr) >= dedupe_threshold:
                too_similar = True
                break
        if too_similar:
            continue
        selected.append(candidate)
        if len(selected) >= limit:
            break
    return selected


def _cs_rank(series: pd.Series, dates: pd.Series) -> pd.Series:
    ranked = series.groupby(dates, sort=False).rank(pct=True)
    return ranked - 0.5


def _cs_zscore(series: pd.Series, dates: pd.Series) -> pd.Series:
    grouped = series.groupby(dates, sort=False)
    mean = grouped.transform("mean")
    std = grouped.transform("std").replace(0.0, np.nan)
    return (series - mean) / std


def _ts_mean(series: pd.Series, instruments: pd.Series, window: int) -> pd.Series:
    return series.groupby(instruments, sort=False).transform(
        lambda values: values.rolling(window, min_periods=max(2, window // 2)).mean()
    )


def _ts_zscore(series: pd.Series, instruments: pd.Series, window: int) -> pd.Series:
    grouped = series.groupby(instruments, sort=False)
    rolling_mean = grouped.transform(
        lambda values: values.rolling(window, min_periods=max(2, window // 2)).mean()
    )
    rolling_std = grouped.transform(
        lambda values: values.rolling(window, min_periods=max(2, window // 2)).std()
    ).replace(0.0, np.nan)
    return (series - rolling_mean) / rolling_std


def _ts_ewm_mean(series: pd.Series, instruments: pd.Series, span: int) -> pd.Series:
    return series.groupby(instruments, sort=False).transform(
        lambda values: values.ewm(span=span, adjust=False, min_periods=max(2, span // 2)).mean()
    )


def _ts_delta(series: pd.Series, instruments: pd.Series, periods: int) -> pd.Series:
    return series.groupby(instruments, sort=False).transform(lambda values: values.diff(periods))


def _signed_sqrt(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return np.sign(numeric) * np.sqrt(np.abs(numeric))


def _tanh(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    return pd.Series(np.tanh(numeric), index=series.index)


def _max_pair(left: pd.Series, right: pd.Series) -> pd.Series:
    return pd.Series(np.maximum(left.to_numpy(dtype=float), right.to_numpy(dtype=float)), index=left.index)


def _min_pair(left: pd.Series, right: pd.Series) -> pd.Series:
    return pd.Series(np.minimum(left.to_numpy(dtype=float), right.to_numpy(dtype=float)), index=left.index)


def _mutation_specs() -> list[MutationSpec]:
    return [
        ("sign_flip", lambda series, _: -series, lambda expr: f"-({expr})"),
        ("cs_rank", lambda series, ctx: _cs_rank(series, ctx.dates), lambda expr: f"cs_rank({expr})"),
        ("ts_mean_5", lambda series, ctx: _ts_mean(series, ctx.instruments, 5), lambda expr: f"ts_mean_5({expr})"),
        ("ts_mean_10", lambda series, ctx: _ts_mean(series, ctx.instruments, 10), lambda expr: f"ts_mean_10({expr})"),
        ("ts_zscore_5", lambda series, ctx: _ts_zscore(series, ctx.instruments, 5), lambda expr: f"ts_zscore_5({expr})"),
        ("ts_zscore_10", lambda series, ctx: _ts_zscore(series, ctx.instruments, 10), lambda expr: f"ts_zscore_10({expr})"),
        ("cs_zscore", lambda series, ctx: _cs_zscore(series, ctx.dates), lambda expr: f"cs_zscore({expr})"),
        ("ewm_mean_5", lambda series, ctx: _ts_ewm_mean(series, ctx.instruments, 5), lambda expr: f"ewm_mean_5({expr})"),
        ("delta_3", lambda series, ctx: _ts_delta(series, ctx.instruments, 3), lambda expr: f"delta_3({expr})"),
        ("signed_sqrt", lambda series, _: _signed_sqrt(series), lambda expr: f"signed_sqrt({expr})"),
        ("tanh_cs_zscore", lambda series, ctx: _tanh(_cs_zscore(series, ctx.dates)), lambda expr: f"tanh(cs_zscore({expr}))"),
    ]


def _crossover_specs() -> list[CrossoverSpec]:
    return [
        (
            "avg_cs_rank",
            lambda left, right, ctx: 0.5 * _cs_rank(left, ctx.dates) + 0.5 * _cs_rank(right, ctx.dates),
            lambda left, right: f"0.5 * cs_rank({left}) + 0.5 * cs_rank({right})",
        ),
        (
            "spread_cs_rank",
            lambda left, right, ctx: _cs_rank(left, ctx.dates) - _cs_rank(right, ctx.dates),
            lambda left, right: f"cs_rank({left}) - cs_rank({right})",
        ),
        (
            "avg_ts_zscore",
            lambda left, right, ctx: 0.5 * _ts_zscore(left, ctx.instruments, 5) + 0.5 * _ts_zscore(right, ctx.instruments, 5),
            lambda left, right: f"0.5 * ts_zscore_5({left}) + 0.5 * ts_zscore_5({right})",
        ),
        (
            "product_cs_zscore",
            lambda left, right, ctx: _cs_zscore(left, ctx.dates) * _cs_zscore(right, ctx.dates),
            lambda left, right: f"cs_zscore({left}) * cs_zscore({right})",
        ),
        (
            "sum_cs_zscore",
            lambda left, right, ctx: _cs_zscore(left, ctx.dates) + _cs_zscore(right, ctx.dates),
            lambda left, right: f"cs_zscore({left}) + cs_zscore({right})",
        ),
        (
            "spread_ts_mean_5",
            lambda left, right, ctx: _ts_mean(left, ctx.instruments, 5) - _ts_mean(right, ctx.instruments, 5),
            lambda left, right: f"ts_mean_5({left}) - ts_mean_5({right})",
        ),
        (
            "rank_of_product",
            lambda left, right, ctx: _cs_rank(left * right, ctx.dates),
            lambda left, right: f"cs_rank({left} * {right})",
        ),
        (
            "zscore_rank_mix",
            lambda left, right, ctx: _cs_zscore(left, ctx.dates) * _cs_rank(right, ctx.dates),
            lambda left, right: f"cs_zscore({left}) * cs_rank({right})",
        ),
        (
            "avg_ewm_5",
            lambda left, right, ctx: 0.5 * _ts_ewm_mean(left, ctx.instruments, 5) + 0.5 * _ts_ewm_mean(right, ctx.instruments, 5),
            lambda left, right: f"0.5 * ewm_mean_5({left}) + 0.5 * ewm_mean_5({right})",
        ),
        (
            "max_cs_rank",
            lambda left, right, ctx: _cs_rank(_max_pair(left, right), ctx.dates),
            lambda left, right: f"cs_rank(max({left}, {right}))",
        ),
        (
            "min_cs_rank",
            lambda left, right, ctx: _cs_rank(_min_pair(left, right), ctx.dates),
            lambda left, right: f"cs_rank(min({left}, {right}))",
        ),
    ]


def _crossover_mutation_specs() -> list[CrossoverSpec]:
    return [
        (
            "avg_then_rank",
            lambda left, right, ctx: _cs_rank(0.5 * left + 0.5 * right, ctx.dates),
            lambda left, right: f"cs_rank(0.5 * {left} + 0.5 * {right})",
        ),
        (
            "spread_then_mean_5",
            lambda left, right, ctx: _ts_mean(_cs_rank(left, ctx.dates) - _cs_rank(right, ctx.dates), ctx.instruments, 5),
            lambda left, right: f"ts_mean_5(cs_rank({left}) - cs_rank({right}))",
        ),
        (
            "product_then_zscore_5",
            lambda left, right, ctx: _ts_zscore(_cs_zscore(left, ctx.dates) * _cs_zscore(right, ctx.dates), ctx.instruments, 5),
            lambda left, right: f"ts_zscore_5(cs_zscore({left}) * cs_zscore({right}))",
        ),
        (
            "avg_then_ewm_5",
            lambda left, right, ctx: _ts_ewm_mean(0.5 * left + 0.5 * right, ctx.instruments, 5),
            lambda left, right: f"ewm_mean_5(0.5 * {left} + 0.5 * {right})",
        ),
        (
            "spread_then_rank",
            lambda left, right, ctx: _cs_rank(left - right, ctx.dates),
            lambda left, right: f"cs_rank({left} - {right})",
        ),
        (
            "sum_zscore_then_tanh",
            lambda left, right, ctx: _tanh(_cs_zscore(left, ctx.dates) + _cs_zscore(right, ctx.dates)),
            lambda left, right: f"tanh(cs_zscore({left}) + cs_zscore({right}))",
        ),
        (
            "product_then_mean_5",
            lambda left, right, ctx: _ts_mean(left * right, ctx.instruments, 5),
            lambda left, right: f"ts_mean_5({left} * {right})",
        ),
        (
            "spread_then_zscore_10",
            lambda left, right, ctx: _ts_zscore(_cs_rank(left, ctx.dates) - _cs_rank(right, ctx.dates), ctx.instruments, 10),
            lambda left, right: f"ts_zscore_10(cs_rank({left}) - cs_rank({right}))",
        ),
        (
            "avg_rank_then_delta_3",
            lambda left, right, ctx: _ts_delta(_cs_rank(0.5 * left + 0.5 * right, ctx.dates), ctx.instruments, 3),
            lambda left, right: f"delta_3(cs_rank(0.5 * {left} + 0.5 * {right}))",
        ),
        (
            "max_then_rank",
            lambda left, right, ctx: _cs_rank(_max_pair(left, right), ctx.dates),
            lambda left, right: f"cs_rank(max({left}, {right}))",
        ),
        (
            "min_then_rank",
            lambda left, right, ctx: _cs_rank(_min_pair(left, right), ctx.dates),
            lambda left, right: f"cs_rank(min({left}, {right}))",
        ),
    ]


def _sample_specs(
    specs: list[MutationSpec] | list[CrossoverSpec],
    *,
    sample_size: int,
    rng: random.Random,
) -> list[Any]:
    if not specs or sample_size <= 0:
        return []
    normalized_sample_size = min(sample_size, len(specs))
    return list(rng.sample(specs, normalized_sample_size))


def _generate_mutation_children(
    parents: list[FactorCandidate],
    *,
    generation: int,
    count: int,
    context: EvolutionContext,
    specs: list[MutationSpec],
) -> list[FactorCandidate]:
    if not parents or count <= 0 or not specs:
        return []
    children: list[FactorCandidate] = []
    for index in range(count):
        parent = parents[index % len(parents)]
        spec_name, transform, expr_builder = specs[(generation + index) % len(specs)]
        child_name = f"g{generation:02d}_mutation_{index:03d}_{spec_name}"
        children.append(
            FactorCandidate(
                name=child_name,
                generation=generation,
                operator="mutation",
                source="deterministic_evolution",
                parents=[parent.name],
                expression=expr_builder(parent.expression),
                values=transform(parent.values, context),
                metadata={"mutation_spec": spec_name},
            )
        )
    return children


def _generate_pair_children(
    parents: list[FactorCandidate],
    *,
    generation: int,
    count: int,
    context: EvolutionContext,
    operator: str,
    specs: list[CrossoverSpec],
) -> list[FactorCandidate]:
    pairs = list(combinations(parents, 2))
    if not pairs or count <= 0 or not specs:
        return []
    children: list[FactorCandidate] = []
    for index in range(count):
        left, right = pairs[index % len(pairs)]
        spec_name, transform, expr_builder = specs[(generation + index) % len(specs)]
        child_name = f"g{generation:02d}_{operator}_{index:03d}_{spec_name}"
        children.append(
            FactorCandidate(
                name=child_name,
                generation=generation,
                operator=operator,
                source="deterministic_evolution",
                parents=[left.name, right.name],
                expression=expr_builder(left.expression, right.expression),
                values=transform(left.values, right.values, context),
                metadata={f"{operator}_spec": spec_name},
            )
        )
    return children


def _summaries_frame(candidates: list[FactorCandidate], *, use_abs_metrics: bool) -> pd.DataFrame:
    return pd.DataFrame([candidate.summary_dict(use_abs_metrics=use_abs_metrics) for candidate in candidates])


def _write_round_artifacts(
    output_dir: Path,
    *,
    round_index: int,
    children: list[FactorCandidate],
    metrics: list[Any],
    selected_parents: list[FactorCandidate],
    use_abs_metrics: bool,
    selected_methods: JsonDict,
) -> None:
    round_dir = output_dir / "rounds" / f"round_{round_index:03d}"
    round_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(
        round_dir / "candidates.jsonl",
        [candidate.summary_dict(use_abs_metrics=use_abs_metrics) for candidate in children],
    )
    _summaries_frame(children, use_abs_metrics=use_abs_metrics).to_csv(
        round_dir / "metrics.csv",
        index=False,
    )
    _daily_records_to_frame(metrics).to_csv(round_dir / "daily_metrics.csv", index=False)
    _write_json(
        round_dir / "selected_parents.json",
        [candidate.summary_dict(use_abs_metrics=use_abs_metrics) for candidate in selected_parents],
    )
    _write_json(round_dir / "selected_methods.json", selected_methods)


def _write_seed_artifacts(
    output_dir: Path,
    *,
    seeds: list[FactorCandidate],
    metrics: list[Any],
    selected_parents: list[FactorCandidate],
    use_abs_metrics: bool,
) -> None:
    seed_dir = output_dir / "seeds"
    seed_dir.mkdir(parents=True, exist_ok=True)
    _summaries_frame(seeds, use_abs_metrics=use_abs_metrics).to_csv(
        seed_dir / "seed_metrics.csv",
        index=False,
    )
    _daily_records_to_frame(metrics).to_csv(seed_dir / "seed_daily_metrics.csv", index=False)
    _write_json(
        seed_dir / "seed_selected_parents.json",
        [candidate.summary_dict(use_abs_metrics=use_abs_metrics) for candidate in selected_parents],
    )


def _build_final_values_frame(base_frame: pd.DataFrame, final_candidates: list[FactorCandidate]) -> pd.DataFrame:
    output = base_frame.loc[:, ["date", "instrument"]].copy()
    for candidate in final_candidates:
        output[candidate.name] = candidate.values.to_numpy()
    return output


def _pair_summary_dict(left: FactorCandidate, right: FactorCandidate) -> JsonDict:
    return {
        "leader": left.name,
        "partner": right.name,
        "leader_rank_ic": _metric_value(left.metrics.get("rank_ic")),
        "leader_rank_icir": _metric_value(left.metrics.get("rank_icir")),
        "partner_rank_ic": _metric_value(right.metrics.get("rank_ic")),
        "partner_rank_icir": _metric_value(right.metrics.get("rank_icir")),
        "pair_abs_correlation": abs(_series_corr(left.values, right.values) or 0.0),
    }


def _write_input_artifacts(
    output_dir: Path,
    *,
    seed_candidates: list[FactorCandidate],
    seed_metrics: list[FactorMetrics],
    strong_pool: list[FactorCandidate],
    crossover_pairs: list[tuple[FactorCandidate, FactorCandidate]],
    use_abs_metrics: bool,
) -> None:
    input_dir = output_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    _summaries_frame(seed_candidates, use_abs_metrics=use_abs_metrics).to_csv(
        input_dir / "input_factor_metrics.csv",
        index=False,
    )
    correlation_rows: list[JsonDict] = []
    for left, right in combinations(seed_candidates, 2):
        corr = _series_corr(left.values, right.values)
        correlation_rows.append(
            {
                "left": left.name,
                "right": right.name,
                "correlation": corr,
                "abs_correlation": abs(corr) if corr is not None else None,
            }
        )
    pd.DataFrame(correlation_rows).to_csv(input_dir / "input_factor_correlations.csv", index=False)
    _write_json(
        input_dir / "strong_pool.json",
        [candidate.summary_dict(use_abs_metrics=use_abs_metrics) for candidate in strong_pool],
    )
    _write_json(
        input_dir / "crossover_pairs.json",
        [_pair_summary_dict(left, right) for left, right in crossover_pairs],
    )
    _daily_records_to_frame(seed_metrics).to_csv(input_dir / "input_factor_daily_metrics.csv", index=False)


def _build_mutation_task(
    *,
    task_id: str,
    parent: FactorCandidate,
    available_columns: list[str],
    prompt_note: str,
) -> JsonDict:
    return {
        "task_id": task_id,
        "operator": "mutation",
        "parents": [parent.name],
        "parent_summary": _seed_description(parent),
        "available_columns": available_columns,
        "prompt_note": prompt_note,
        "output_schema": {
            "name": "factor_xxx",
            "description": "...",
            "formula": "...",
            "code": "def factor_xxx(df): ...",
        },
        "name": "",
        "description": "",
        "formula": "",
        "code": "",
    }


def _build_crossover_task(
    *,
    task_id: str,
    left: FactorCandidate,
    right: FactorCandidate,
    available_columns: list[str],
    prompt_note: str,
    variant_index: int,
) -> JsonDict:
    return {
        "task_id": task_id,
        "operator": "crossover",
        "parents": [left.name, right.name],
        "primary_parent_summary": _seed_description(left),
        "diversity_parent_summary": _seed_description(right),
        "available_columns": available_columns,
        "prompt_note": prompt_note,
        "variant_index": variant_index,
        "output_schema": {
            "name": "factor_xxx",
            "description": "...",
            "formula": "...",
            "code": "def factor_xxx(df): ...",
        },
        "name": "",
        "description": "",
        "formula": "",
        "code": "",
    }


def _write_generation_preparation_artifacts(
    output_dir: Path,
    *,
    seed_candidates: list[FactorCandidate],
    strong_pool: list[FactorCandidate],
    crossover_pairs: list[tuple[FactorCandidate, FactorCandidate]],
    eval_market: pd.DataFrame,
    config: JsonDict,
) -> Path:
    generation_dir = output_dir / "generation"
    prompts_dir = generation_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    available_columns = _available_market_columns(eval_market)
    mutation_prompt_note = str(
        config.get(
            "mutation_prompt_note",
            "Preserve the factor's core economic logic and only improve one or two structural components.",
        )
    )
    crossover_prompt_note = str(
        config.get(
            "crossover_prompt_note",
            "Use the stronger factor as the main logic anchor and borrow only complementary low-correlation structure.",
        )
    )

    mutation_tasks: list[JsonDict] = []
    mutation_pool = strong_pool if config.get("mutate_strong_pool_only", False) else seed_candidates
    for index, parent in enumerate(mutation_pool):
        task_id = f"mutation_{index:03d}"
        prompt = _mutation_prompt(parent=parent, available_columns=available_columns, run_note=mutation_prompt_note)
        _write_text(prompts_dir / f"{task_id}.prompt.txt", prompt)
        mutation_tasks.append(
            _build_mutation_task(
                task_id=task_id,
                parent=parent,
                available_columns=available_columns,
                prompt_note=mutation_prompt_note,
            )
        )

    crossover_tasks: list[JsonDict] = []
    for pair_index, (left, right) in enumerate(crossover_pairs):
        for variant_index in range(2):
            task_id = f"crossover_{pair_index:03d}_{variant_index:02d}"
            prompt = _crossover_prompt(
                left=left,
                right=right,
                available_columns=available_columns,
                run_note=crossover_prompt_note,
                variant_index=variant_index,
            )
            _write_text(prompts_dir / f"{task_id}.prompt.txt", prompt)
            crossover_tasks.append(
                _build_crossover_task(
                    task_id=task_id,
                    left=left,
                    right=right,
                    available_columns=available_columns,
                    prompt_note=crossover_prompt_note,
                    variant_index=variant_index,
                )
            )

    template = {
        "mutation_candidates": mutation_tasks,
        "crossover_candidates": crossover_tasks,
        "notes": "Fill name/description/formula/code for each task after using the prompts. Leave unused tasks blank.",
    }
    template_path = generation_dir / "generated_candidates_template.json"
    _write_json(template_path, template)
    return template_path


def _candidate_template_path(output_dir: Path, config: JsonDict) -> Path:
    raw = str(config.get("generated_candidates_json_path", "") or "").strip()
    if raw:
        path = Path(raw).expanduser()
        if path.is_absolute():
            return path
        return (output_dir / path).resolve()
    return output_dir / "generation" / "generated_candidates.json"


def _load_generated_candidate_specs(path: Path) -> list[JsonDict]:
    if not path.exists():
        return []
    payload = _load_json_any(path)
    candidates: list[JsonDict] = []
    if isinstance(payload, dict):
        for key in ("mutation_candidates", "crossover_candidates", "candidates"):
            value = payload.get(key)
            if isinstance(value, list):
                candidates.extend(item for item in value if isinstance(item, dict))
    elif isinstance(payload, list):
        candidates.extend(item for item in payload if isinstance(item, dict))
    return candidates


def _build_generated_candidate_from_spec(spec: JsonDict, eval_market: pd.DataFrame) -> FactorCandidate | None:
    code = str(spec.get("code", "") or "").strip()
    raw_name = str(spec.get("name", "") or "").strip()
    if not code or not raw_name:
        return None
    qualified_name = raw_name if raw_name.startswith("custom:") else f"custom:{raw_name}"
    values = _execute_custom_factor(code, qualified_name, eval_market)
    return FactorCandidate(
        name=qualified_name,
        generation=1,
        operator=str(spec.get("operator") or "generated"),
        source="user_model_generated",
        parents=[str(parent) for parent in spec.get("parents", []) if str(parent).strip()],
        expression=str(spec.get("formula") or qualified_name),
        description=str(spec.get("description") or qualified_name),
        formula=str(spec.get("formula") or qualified_name),
        code=code,
        values=values,
        metadata={
            key: value
            for key, value in spec.items()
            if key not in {"name", "description", "formula", "code", "operator", "parents"}
        },
    )


def _split_generated_candidates(candidates: list[FactorCandidate]) -> tuple[list[FactorCandidate], list[FactorCandidate]]:
    mutations = [candidate for candidate in candidates if candidate.operator == "mutation"]
    crossovers = [candidate for candidate in candidates if candidate.operator == "crossover"]
    others = [candidate for candidate in candidates if candidate.operator not in {"mutation", "crossover"}]
    return mutations + others, crossovers


def _write_generation_artifacts(
    output_dir: Path,
    *,
    mutation_candidates: list[FactorCandidate],
    crossover_candidates: list[FactorCandidate],
    generated_metrics: list[FactorMetrics],
    ranked_recommendations: pd.DataFrame,
    use_abs_metrics: bool,
) -> None:
    generation_dir = output_dir / "generation"
    generation_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(
        generation_dir / "mutation_candidates.jsonl",
        [candidate.summary_dict(use_abs_metrics=use_abs_metrics) for candidate in mutation_candidates],
    )
    _write_jsonl(
        generation_dir / "crossover_candidates.jsonl",
        [candidate.summary_dict(use_abs_metrics=use_abs_metrics) for candidate in crossover_candidates],
    )
    _summaries_frame(mutation_candidates, use_abs_metrics=use_abs_metrics).to_csv(
        generation_dir / "mutation_metrics.csv",
        index=False,
    )
    _summaries_frame(crossover_candidates, use_abs_metrics=use_abs_metrics).to_csv(
        generation_dir / "crossover_metrics.csv",
        index=False,
    )
    _summaries_frame(
        [*mutation_candidates, *crossover_candidates],
        use_abs_metrics=use_abs_metrics,
    ).to_csv(generation_dir / "generated_factor_metrics.csv", index=False)
    _daily_records_to_frame(generated_metrics).to_csv(
        generation_dir / "generated_factor_daily_metrics.csv",
        index=False,
    )
    ranked_recommendations.to_csv(generation_dir / "ranked_recommendations.csv", index=False)


def _build_next_round_seed_payload(candidates: list[FactorCandidate]) -> JsonDict:
    factors = []
    for index, candidate in enumerate(candidates):
        if not candidate.code:
            continue
        factors.append(
            {
                "alpha_id": f"recommended_{index:03d}",
                "name": candidate.name.split("custom:", 1)[-1],
                "description": candidate.description,
                "formula": candidate.formula,
                "code": candidate.code,
                "metadata": {
                    "recommended_sign": -1 if _metric_value(candidate.metrics.get("rank_icir")) and _metric_value(candidate.metrics.get("rank_icir")) < 0 else 1,
                    "source_operator": candidate.operator,
                    "parents": candidate.parents,
                },
            }
        )
    return {"factors": factors}


def _build_recommendation_report(
    *,
    config: JsonDict,
    seed_candidates: list[FactorCandidate],
    strong_pool: list[FactorCandidate],
    crossover_pairs: list[tuple[FactorCandidate, FactorCandidate]],
    mutation_candidates: list[FactorCandidate],
    crossover_candidates: list[FactorCandidate],
    recommended_candidates: list[FactorCandidate],
    ranked_recommendations: pd.DataFrame,
) -> str:
    lines = [
        "# Factor Pool Recommendation Report",
        "",
        "## Run Setup",
        "",
        f"- Input factor count: {len(seed_candidates)}",
        f"- Strong pool count: {len(strong_pool)}",
        f"- Crossover pair count: {len(crossover_pairs)}",
        f"- Mutation candidates generated: {len(mutation_candidates)}",
        f"- Crossover candidates generated: {len(crossover_candidates)}",
        f"- Recommendation top k: {len(recommended_candidates)}",
        f"- use_llm requested: {bool(config.get('use_llm', True))}",
        f"- llm required: {bool(config.get('llm_required', False))}",
        f"- random seed: {config.get('random_seed', 42)}",
        f"- LLM mutation hits: {sum(candidate.source == 'llm_mutation' for candidate in mutation_candidates)}",
        f"- LLM crossover hits: {sum(candidate.source == 'llm_crossover' for candidate in crossover_candidates)}",
        "",
        "## Input Factors",
        "",
        "| Factor | RankIC | RankICIR | Recommended Sign |",
        "| --- | --- | --- | --- |",
    ]
    for candidate in sorted(seed_candidates, key=lambda item: _candidate_sort_key(item, use_abs_metrics=True), reverse=True):
        rank_ic = _metric_value(candidate.metrics.get("rank_ic"))
        rank_icir = _metric_value(candidate.metrics.get("rank_icir"))
        recommended_sign = -1 if rank_icir is not None and rank_icir < 0 else 1
        lines.append(
            f"| {candidate.name} | {_format_metric(rank_ic)} | {_format_metric(rank_icir)} | {recommended_sign} |"
        )

    lines.extend(
        [
            "",
            "## Strong Pool",
            "",
        ]
    )
    for candidate in strong_pool:
        lines.append(f"- {candidate.name}")

    lines.extend(
        [
            "",
            "## Crossover Pairs",
            "",
        ]
    )
    for left, right in crossover_pairs:
        corr = _series_corr(left.values, right.values)
        lines.append(
            f"- {left.name} x {right.name} (abs corr={abs(corr) if corr is not None else 'n/a'})"
        )

    lines.extend(
        [
            "",
            "## Recommended Factors",
            "",
            "| Factor | Operator | Source | RankIC | RankICIR | MaxCorr(Input) | MaxCorr(Selected) | Recommended Sign |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    recommended_names = {candidate.name for candidate in recommended_candidates}
    filtered_ranked = ranked_recommendations[ranked_recommendations["name"].isin(recommended_names)]
    for _, row in filtered_ranked.iterrows():
        lines.append(
            "| {name} | {operator} | {source} | {rank_ic} | {rank_icir} | {maxcorr_input} | {maxcorr_selected} | {sign} |".format(
                name=row["name"],
                operator=row["operator"],
                source=row["source"],
                rank_ic=_format_metric(row.get("rank_ic")),
                rank_icir=_format_metric(row.get("rank_icir")),
                maxcorr_input=_format_metric(row.get("maxcorr_to_input_pool")),
                maxcorr_selected=_format_metric(row.get("maxcorr_to_selected")),
                sign=row.get("recommended_sign", 1),
            )
        )

    lines.extend(
        [
            "",
            "## Iteration Note",
            "",
            "This skill runs one recommendation round only. If the user wants to continue iterating, use the recommended factors from `next_round_custom_seed_factors.json` as the next run's custom seed pool.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def _generate_mutation_recommendations(
    *,
    seeds: list[FactorCandidate],
    eval_market: pd.DataFrame,
    config: JsonDict,
    trace_dir: Path | None = None,
) -> list[FactorCandidate]:
    llm_cfg = _llm_config(config)
    available_columns = _available_market_columns(eval_market)
    run_note = str(config.get("mutation_prompt_note", "Focus on economic meaning and concise structure."))
    if llm_cfg["required"] and not llm_cfg["api_key"]:
        raise RuntimeError("llm_required=true but no OPENAI_API_KEY/llm_api_key was provided")
    generated: list[FactorCandidate] = []
    for index, seed in enumerate(seeds):
        prompt_text = _mutation_prompt(parent=seed, available_columns=available_columns, run_note=run_note)
        fallback = _fallback_candidate(
            operator="mutation",
            generation=1,
            parents=[seed.name],
            data=eval_market,
            index=index,
            source_note="deterministic_mutation_fallback",
        )
        payload, raw_response, llm_error = _request_llm_json(prompt_text, llm_cfg)
        if trace_dir is not None and llm_cfg["save_artifacts"]:
            base = trace_dir / f"mutation_{index:03d}"
            _write_text(base.with_suffix(".prompt.txt"), prompt_text)
            if raw_response is not None:
                _write_text(base.with_suffix(".response.json"), raw_response)
            if llm_error is not None:
                _write_text(base.with_suffix(".error.txt"), llm_error)
        candidate = _build_llm_candidate(
            payload,
            fallback_name=fallback.name.split("custom:", 1)[-1],
            fallback_description=fallback.description or "fallback mutation",
            fallback_formula=fallback.formula or fallback.expression,
            fallback_code=fallback.code or "",
            operator="mutation",
            parents=[seed.name],
            generation=1,
            source="llm_mutation" if payload is not None else fallback.source,
            data=eval_market,
        )
        if candidate is None and llm_cfg["required"] and not llm_cfg["fallback_on_failure"]:
            raise RuntimeError(f"LLM mutation generation failed for {seed.name}: {llm_error or 'unknown_error'}")
        generated.append(candidate or fallback)
    return generated


def _generate_crossover_recommendations(
    *,
    pairs: list[tuple[FactorCandidate, FactorCandidate]],
    eval_market: pd.DataFrame,
    config: JsonDict,
    trace_dir: Path | None = None,
) -> list[FactorCandidate]:
    llm_cfg = _llm_config(config)
    available_columns = _available_market_columns(eval_market)
    run_note = str(
        config.get(
            "crossover_prompt_note",
            "Prefer combining strong factors with low-correlation partners to increase diversity.",
        )
    )
    if llm_cfg["required"] and not llm_cfg["api_key"]:
        raise RuntimeError("llm_required=true but no OPENAI_API_KEY/llm_api_key was provided")
    generated: list[FactorCandidate] = []
    for pair_index, (left, right) in enumerate(pairs):
        for variant_index in range(2):
            prompt_text = _crossover_prompt(
                left=left,
                right=right,
                available_columns=available_columns,
                run_note=run_note,
                variant_index=variant_index,
            )
            fallback = _fallback_candidate(
                operator="crossover",
                generation=1,
                parents=[left.name, right.name],
                data=eval_market,
                index=pair_index * 2 + variant_index,
                source_note="deterministic_crossover_fallback",
            )
            payload, raw_response, llm_error = _request_llm_json(prompt_text, llm_cfg)
            if trace_dir is not None and llm_cfg["save_artifacts"]:
                base = trace_dir / f"crossover_{pair_index:03d}_{variant_index:02d}"
                _write_text(base.with_suffix(".prompt.txt"), prompt_text)
                if raw_response is not None:
                    _write_text(base.with_suffix(".response.json"), raw_response)
                if llm_error is not None:
                    _write_text(base.with_suffix(".error.txt"), llm_error)
            candidate = _build_llm_candidate(
                payload,
                fallback_name=fallback.name.split("custom:", 1)[-1],
                fallback_description=fallback.description or "fallback crossover",
                fallback_formula=fallback.formula or fallback.expression,
                fallback_code=fallback.code or "",
                operator="crossover",
                parents=[left.name, right.name],
                generation=1,
                source="llm_crossover" if payload is not None else fallback.source,
                data=eval_market,
            )
            if candidate is None and llm_cfg["required"] and not llm_cfg["fallback_on_failure"]:
                raise RuntimeError(
                    f"LLM crossover generation failed for {left.name} x {right.name}: {llm_error or 'unknown_error'}"
                )
            generated.append(candidate or fallback)
    return generated


def _build_report(
    **kwargs,
) -> str:
    return _build_recommendation_report(**kwargs)


def _format_metric(value: Any) -> str:
    numeric = _metric_value(value)
    return "n/a" if numeric is None else f"{numeric:.6f}"


def run_evolution(input_path: Path, output_dir: Path) -> JsonDict:
    config = _load_input(input_path)
    show_progress = bool(config.get("show_progress", True))
    mode = str(config.get("mode", "auto") or "auto").strip().lower()
    if mode not in {"auto", "prepare", "evaluate"}:
        raise ValueError("mode must be one of: auto, prepare, evaluate")

    output_dir.mkdir(parents=True, exist_ok=True)

    raw_market, eval_market = _prepare_market_frames(config, input_dir=input_path.parent)
    _progress(show_progress, f"market data prepared: rows={len(eval_market)}")

    library_frame, library_sources = _compute_library_seed_frame(
        config,
        input_dir=input_path.parent,
        raw_market=raw_market,
        show_progress=show_progress,
    )
    custom_frame, custom_sources = _compute_custom_seed_frame(
        config,
        input_dir=input_path.parent,
        eval_market=eval_market,
    )
    merged_seed_frame = _merge_seed_frames(eval_market, library_frame, custom_frame)
    factor_sources = {**library_sources, **custom_sources}

    min_periods = int(config.get("min_cross_section_samples", 3) or 3)
    mi_bins = int(config.get("mi_bins", 10) or 10)
    use_abs_metrics = bool(config.get("use_abs_metrics", True))
    random_seed = int(config.get("random_seed", 42) or 42)
    llm_cfg = _llm_config(config)

    seed_candidates = _seed_candidates_from_frame(
        merged_seed_frame,
        factor_sources=factor_sources,
    )
    seed_metrics = _evaluate_factor_candidates(
        merged_seed_frame,
        seed_candidates,
        min_periods=min_periods,
        mi_bins=mi_bins,
    )
    strong_pool = _select_strong_pool(seed_candidates, use_abs_metrics=use_abs_metrics)
    crossover_pairs = _select_crossover_pairs(seed_candidates, use_abs_metrics=use_abs_metrics)
    _write_input_artifacts(
        output_dir,
        seed_candidates=seed_candidates,
        seed_metrics=seed_metrics,
        strong_pool=strong_pool,
        crossover_pairs=crossover_pairs,
        use_abs_metrics=use_abs_metrics,
    )
    _progress(show_progress, f"input factor pool evaluated: total={len(seed_candidates)} strong_pool={len(strong_pool)}")

    template_path = _write_generation_preparation_artifacts(
        output_dir,
        seed_candidates=seed_candidates,
        strong_pool=strong_pool,
        crossover_pairs=crossover_pairs,
        eval_market=eval_market,
        config=config,
    )
    generated_candidates_path = _candidate_template_path(output_dir, config)
    if not generated_candidates_path.exists():
        generated_candidates_path.parent.mkdir(parents=True, exist_ok=True)
        generated_candidates_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")

    candidate_specs = _load_generated_candidate_specs(generated_candidates_path)
    generated_candidates = [
        candidate
        for candidate in (
            _build_generated_candidate_from_spec(spec, eval_market) for spec in candidate_specs
        )
        if candidate is not None
    ]

    if mode == "prepare" or (mode == "auto" and not generated_candidates):
        manifest = {
            "ok": True,
            "stage": "prepared",
            "input_path": str(input_path),
            "output_dir": str(output_dir),
            "market_data_csv_path": str(_resolve_path(str(config["market_data_csv_path"]), input_dir=input_path.parent)),
            "alpha_library_root": str(ALPHA_LIBRARY_ROOT) if ALPHA_LIBRARY_ROOT is not None else "",
            "seed_factor_count": len(seed_candidates),
            "seed_factor_sources": {
                "alpha_library": len(library_sources),
                "custom_seed_pool": len(custom_sources),
            },
            "strong_pool_count": len(strong_pool),
            "crossover_pair_count": len(crossover_pairs),
            "generated_candidates_template_path": str(template_path),
            "generated_candidates_json_path": str(generated_candidates_path),
            "prompt_dir": str(output_dir / "generation" / "prompts"),
            "message": "Prompt pack prepared. Ask the current model to fill generated_candidates_json_path, then rerun in evaluate or auto mode.",
        }
        _write_json(output_dir / "00_manifest.json", manifest)
        return manifest

    if mode == "evaluate" and not generated_candidates:
        raise ValueError(
            f"mode=evaluate requires generated candidates at {generated_candidates_path}, but no usable name/code pairs were found"
        )

    mutation_candidates, crossover_candidates = _split_generated_candidates(generated_candidates)
    for candidate in generated_candidates:
        merged_seed_frame[candidate.name] = candidate.values.to_numpy()

    generated_metrics = _evaluate_factor_candidates(
        merged_seed_frame,
        generated_candidates,
        min_periods=min_periods,
        mi_bins=mi_bins,
    )
    ranked_recommendations = _score_generated_candidates(
        generated_candidates,
        seed_candidates,
        use_abs_metrics=use_abs_metrics,
    )
    recommendation_top_k_raw = int(config.get("recommendation_top_k", 0) or 0)
    recommendation_top_k = recommendation_top_k_raw if recommendation_top_k_raw > 0 else len(seed_candidates)
    recommendation_use_abs_corr = bool(config.get("recommendation_use_abs_corr", True))
    recommended_names, ranked_recommendations = _annotate_recommendations_without_filter(
        ranked_recommendations,
        generated_candidates,
        top_k=recommendation_top_k,
        use_abs_corr=recommendation_use_abs_corr,
    )
    recommended_candidates = [candidate for candidate in generated_candidates if candidate.name in recommended_names]
    recommended_candidates = sorted(
        recommended_candidates,
        key=lambda item: recommended_names.index(item.name),
    )

    _write_generation_artifacts(
        output_dir,
        mutation_candidates=mutation_candidates,
        crossover_candidates=crossover_candidates,
        generated_metrics=generated_metrics,
        ranked_recommendations=ranked_recommendations,
        use_abs_metrics=use_abs_metrics,
    )

    final_dir = output_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        final_dir / "recommended_factors.json",
        [candidate.summary_dict(use_abs_metrics=use_abs_metrics) for candidate in recommended_candidates],
    )
    _build_final_values_frame(merged_seed_frame, recommended_candidates).to_csv(
        final_dir / "recommended_factor_values.csv",
        index=False,
    )
    next_round_payload = _build_next_round_seed_payload(recommended_candidates)
    _write_json(final_dir / "next_round_custom_seed_factors.json", next_round_payload)
    report_text = _build_report(
        config=config,
        seed_candidates=seed_candidates,
        strong_pool=strong_pool,
        crossover_pairs=crossover_pairs,
        mutation_candidates=mutation_candidates,
        crossover_candidates=crossover_candidates,
        recommended_candidates=recommended_candidates,
        ranked_recommendations=ranked_recommendations,
    )
    (final_dir / "recommendation_report.md").write_text(report_text, encoding="utf-8")

    manifest = {
        "ok": True,
        "input_path": str(input_path),
        "output_dir": str(output_dir),
        "market_data_csv_path": str(_resolve_path(str(config["market_data_csv_path"]), input_dir=input_path.parent)),
        "alpha_library_root": str(ALPHA_LIBRARY_ROOT) if ALPHA_LIBRARY_ROOT is not None else "",
        "seed_factor_count": len(seed_candidates),
        "seed_factor_sources": {
            "alpha_library": len(library_sources),
            "custom_seed_pool": len(custom_sources),
        },
        "strong_pool_count": len(strong_pool),
        "crossover_pair_count": len(crossover_pairs),
        "generated_factor_count": len(generated_candidates),
        "mutation_count": len(mutation_candidates),
        "crossover_count": len(crossover_candidates),
        "recommendation_top_k": recommendation_top_k,
        "recommendation_use_abs_corr": recommendation_use_abs_corr,
        "random_seed": random_seed,
        "mode": "evaluated",
        "generated_candidates_template_path": str(template_path),
        "generated_candidates_json_path": str(generated_candidates_path),
        "prompt_dir": str(output_dir / "generation" / "prompts"),
        "recommended_factors_path": str(final_dir / "recommended_factors.json"),
        "recommended_factor_values_path": str(final_dir / "recommended_factor_values.csv"),
        "next_round_custom_seed_factors_path": str(final_dir / "next_round_custom_seed_factors.json"),
        "report_path": str(final_dir / "recommendation_report.md"),
    }
    _write_json(output_dir / "00_manifest.json", manifest)
    return manifest


def main() -> int:
    args = _parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"input JSON not found: {input_path}")
    config = _load_input(input_path)
    output_dir = _resolve_output_dir(config, input_dir=input_path.parent, cli_output=args.output)

    try:
        manifest = run_evolution(input_path, output_dir)
    except Exception as exc:
        error_payload = {
            "ok": False,
            "input_path": str(input_path),
            "output_dir": str(output_dir),
            "error": f"{type(exc).__name__}: {exc}",
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json(output_dir / "00_manifest.json", error_payload)
        print(json.dumps(error_payload, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
