"""Grid-search trial generation for model hyperparameter search."""

from __future__ import annotations

import copy
import json
import math
import random
from typing import Any, Mapping

import numpy as np

from config_utils import ConfigError, json_default
from search_space import normalize_model_params, validate_search_space


NUMERIC_TYPES = {"uniform", "loguniform", "quniform", "qloguniform"}


def resolve_grid_trials(
    *,
    search_cfg: Mapping[str, Any],
    search_space: Mapping[str, Mapping[str, Any]],
    model_type: str,
    max_trials: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Resolve explicit or generated grid trials.

    Explicit ``search.grid_trials`` remains the most reproducible path. When it
    is absent, ``search.grid`` generates a bounded Cartesian grid from
    ``search.space`` and selects at most ``max_trials`` deterministic points.
    """

    raw_trials = search_cfg.get("grid_trials") or []
    if raw_trials:
        trials = _normalize_explicit_trials(raw_trials, model_type=model_type)
        selected = trials[: max(0, min(int(max_trials), len(trials)))]
        return selected, {
            "enabled": True,
            "strategy": "explicit",
            "source": "search.grid_trials",
            "num_candidates_generated": len(trials),
            "num_trials_selected": len(selected),
            "max_trials": int(max_trials),
            "truncated": len(selected) < len(trials),
            "seed": None,
            "selection": "input_order",
            "space_param_order": list(search_space.keys()),
        }

    grid_cfg = search_cfg.get("grid") or {}
    if not isinstance(grid_cfg, Mapping) or not grid_cfg:
        raise ConfigError("grid search requires search.grid or search.grid_trials")
    strategy = str(grid_cfg.get("strategy", "budgeted_cartesian")).strip().lower()
    if strategy != "budgeted_cartesian":
        raise ConfigError("search.grid.strategy currently supports only budgeted_cartesian")
    return _build_budgeted_cartesian(
        search_space=search_space,
        model_type=model_type,
        grid_cfg=grid_cfg,
        max_trials=int(max_trials),
    )


def _normalize_explicit_trials(raw_trials: Any, *, model_type: str) -> list[dict[str, Any]]:
    if not isinstance(raw_trials, list):
        raise ConfigError("search.grid_trials must be a list of parameter mappings")
    trials: list[dict[str, Any]] = []
    for idx, raw_params in enumerate(raw_trials):
        if not isinstance(raw_params, Mapping):
            raise ConfigError(f"search.grid_trials[{idx}] must be a parameter mapping")
        trials.append(normalize_model_params(model_type, raw_params))
    if not trials:
        raise ConfigError("search.grid_trials must not be empty")
    return _dedupe_trials(trials)


def _build_budgeted_cartesian(
    *,
    search_space: Mapping[str, Mapping[str, Any]],
    model_type: str,
    grid_cfg: Mapping[str, Any],
    max_trials: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if max_trials <= 0:
        raise ConfigError("search.max_trials must be positive for grid search")
    validate_search_space(search_space)
    param_order = list(search_space.keys())
    value_grid = [_values_for_param(name, search_space[name], grid_cfg) for name in param_order]
    candidate_count = 1
    for values in value_grid:
        candidate_count *= len(values)
    if candidate_count <= 0:
        raise ConfigError("grid search generated no candidate points")

    seed = int(grid_cfg.get("seed", 42))
    selection = str(grid_cfg.get("selection", "evenly_spaced")).strip().lower()
    shuffle = bool(grid_cfg.get("shuffle", False))
    selected_count = min(max_trials, candidate_count)
    indices = _select_indices(candidate_count, selected_count, selection=selection, shuffle=shuffle, seed=seed)

    trials: list[dict[str, Any]] = []
    for index in indices:
        raw_params = _params_from_flat_index(index, param_order, value_grid)
        trials.append(normalize_model_params(model_type, raw_params))
    trials = _dedupe_trials(trials)

    manifest = {
        "enabled": True,
        "strategy": "budgeted_cartesian",
        "source": "search.grid",
        "num_candidates_generated": int(candidate_count),
        "num_trials_selected": int(len(trials)),
        "max_trials": int(max_trials),
        "truncated": bool(candidate_count > len(trials)),
        "seed": seed,
        "selection": selection,
        "shuffle": shuffle,
        "numeric_levels": int(grid_cfg.get("numeric_levels", 3)),
        "log_levels": int(grid_cfg.get("log_levels", grid_cfg.get("numeric_levels", 3))),
        "choice_policy": str(grid_cfg.get("choice_policy", "all")),
        "space_param_order": param_order,
        "param_value_counts": {name: len(values) for name, values in zip(param_order, value_grid)},
    }
    return trials, manifest


def _values_for_param(name: str, spec: Mapping[str, Any], grid_cfg: Mapping[str, Any]) -> list[Any]:
    kind = str(spec.get("type"))
    if kind == "choice":
        values = list(spec.get("values") or [])
        if not values:
            raise ConfigError(f"choice grid for {name} produced no values")
        choice_policy = str(grid_cfg.get("choice_policy", "all")).strip().lower()
        max_choice_values = grid_cfg.get("max_choice_values")
        if choice_policy not in {"all", "first_last", "first_middle_last"}:
            raise ConfigError("search.grid.choice_policy must be all, first_last, or first_middle_last")
        if choice_policy == "first_last" and len(values) > 2:
            values = [values[0], values[-1]]
        elif choice_policy == "first_middle_last" and len(values) > 3:
            values = [values[0], values[len(values) // 2], values[-1]]
        if max_choice_values not in (None, ""):
            max_n = int(max_choice_values)
            if max_n <= 0:
                raise ConfigError("search.grid.max_choice_values must be positive")
            values = values[:max_n]
        return [copy.deepcopy(value) for value in values]

    if kind in NUMERIC_TYPES:
        levels_key = "log_levels" if "log" in kind else "numeric_levels"
        default_levels = int(grid_cfg.get("numeric_levels", 3))
        levels = int(grid_cfg.get(levels_key, default_levels))
        if levels <= 0:
            raise ConfigError(f"search.grid.{levels_key} must be positive")
        low = float(spec["low"])
        high = float(spec["high"])
        if high < low:
            raise ConfigError(f"search.space.{name}.high must be >= low")
        if "log" in kind and (low <= 0 or high <= 0):
            raise ConfigError(f"log grid for {name} requires positive low/high")
        if levels == 1:
            values = [math.sqrt(low * high) if "log" in kind else (low + high) / 2.0]
        elif "log" in kind:
            values = np.exp(np.linspace(math.log(low), math.log(high), levels)).tolist()
        else:
            values = np.linspace(low, high, levels).tolist()
        if kind in {"quniform", "qloguniform"}:
            values = [_quantize(value, spec) for value in values]
        return _dedupe_values(values)

    raise ConfigError(f"Unsupported grid search space type for {name}: {kind}")


def _select_indices(candidate_count: int, selected_count: int, *, selection: str, shuffle: bool, seed: int) -> list[int]:
    if selected_count >= candidate_count:
        indices = list(range(candidate_count))
    elif selection == "evenly_spaced":
        indices = np.linspace(0, candidate_count - 1, selected_count, dtype=int).tolist()
    elif selection in {"random", "seeded_random"}:
        rng = random.Random(seed)
        indices = sorted(rng.sample(range(candidate_count), selected_count))
    else:
        raise ConfigError("search.grid.selection must be evenly_spaced or random")
    if shuffle:
        rng = random.Random(seed)
        rng.shuffle(indices)
    return indices


def _params_from_flat_index(index: int, param_order: list[str], value_grid: list[list[Any]]) -> dict[str, Any]:
    values_by_name: dict[str, Any] = {}
    remainder = int(index)
    positions: list[int] = []
    for values in reversed(value_grid):
        positions.append(remainder % len(values))
        remainder //= len(values)
    positions.reverse()
    for name, values, pos in zip(param_order, value_grid, positions):
        values_by_name[name] = copy.deepcopy(values[pos])
    return values_by_name


def _quantize(value: float, spec: Mapping[str, Any]) -> float:
    q = float(spec.get("q", 1.0))
    low = float(spec["low"])
    high = float(spec["high"])
    if q <= 0:
        raise ConfigError("quantized grid requires positive q")
    quantized = low + round((float(value) - low) / q) * q
    return float(min(max(quantized, low), high))


def _dedupe_values(values: list[Any]) -> list[Any]:
    seen: set[str] = set()
    out: list[Any] = []
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True, default=json_default)
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _dedupe_trials(trials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for trial in trials:
        key = json.dumps(trial, ensure_ascii=False, sort_keys=True, default=json_default)
        if key in seen:
            continue
        seen.add(key)
        out.append(trial)
    return out
