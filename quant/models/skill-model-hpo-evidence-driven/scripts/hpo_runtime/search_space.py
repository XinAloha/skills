"""Search-space definitions and adaptive sampling for model hyperparameter search."""

from __future__ import annotations

import copy
import math
from collections import Counter
from typing import Any, Mapping

import numpy as np

from builtin_extensions import LGBM_SEARCH_SPACE, MLP_SEARCH_SPACE
from config_utils import ConfigError
from extension_registry import REGISTRY
from plugin_loader import ensure_builtin_extensions, model_plugin_name


DEFAULT_SEARCH_SPACES: dict[str, dict[str, dict[str, Any]]] = {
    "lgbm": LGBM_SEARCH_SPACE,
    "mlp": MLP_SEARCH_SPACE,
}

NUMERIC_TYPES = {"uniform", "loguniform", "quniform", "qloguniform"}
LGBM_PROBE_SEQUENCE = ["center", "high_capacity", "low_capacity", "strong_regularization", "weak_regularization", "lr_tree_tradeoff"]
MLP_PROBE_SEQUENCE = ["center", "high_capacity", "low_capacity", "strong_regularization", "weak_regularization", "lr_epoch_tradeoff"]


def resolve_model_type(cfg: Mapping[str, Any]) -> str:
    ensure_builtin_extensions()
    return REGISTRY.canonical_model_name(model_plugin_name(cfg))


def resolve_search_space(cfg: Mapping[str, Any], model_type: str) -> dict[str, dict[str, Any]]:
    search_cfg = cfg.get("search", {})
    if not isinstance(search_cfg, Mapping):
        raise ConfigError("search config must be a mapping")
    configured = search_cfg.get("space")
    if configured:
        if not isinstance(configured, Mapping):
            raise ConfigError("search.space must be a mapping")
        space = copy.deepcopy(dict(configured))
    else:
        ensure_builtin_extensions()
        space = copy.deepcopy(REGISTRY.get_model_plugin(model_type).default_search_space())
    fixed_params = search_cfg.get("fixed_params") or {}
    if fixed_params:
        if not isinstance(fixed_params, Mapping):
            raise ConfigError("search.fixed_params must be a mapping")
        for key, value in fixed_params.items():
            space[str(key)] = {"type": "choice", "values": [value]}
    validate_search_space(space)
    return space


def validate_search_space(space: Mapping[str, Any]) -> None:
    if not space:
        raise ConfigError("search space is empty")
    for name, spec in space.items():
        if not isinstance(spec, Mapping):
            raise ConfigError(f"search space spec for {name} must be a mapping")
        kind = spec.get("type")
        if kind == "choice":
            values = spec.get("values")
            if not isinstance(values, list) or not values:
                raise ConfigError(f"choice search space for {name} must define a non-empty values list")
        elif kind in NUMERIC_TYPES:
            if "low" not in spec or "high" not in spec:
                raise ConfigError(f"{kind} search space for {name} must define low and high")
            low = float(spec["low"])
            high = float(spec["high"])
            if not low < high:
                raise ConfigError(f"search space for {name} must satisfy low < high")
            if "log" in str(kind) and low <= 0:
                raise ConfigError(f"log search space for {name} requires low > 0")
            if kind.startswith("q") and float(spec.get("q", 1.0)) <= 0:
                raise ConfigError(f"quantized search space for {name} requires q > 0")
        else:
            raise ConfigError(f"Unsupported search space type for {name}: {kind}")


def normalize_model_params(model_type: str, params: Mapping[str, Any]) -> dict[str, Any]:
    ensure_builtin_extensions()
    return REGISTRY.get_model_plugin(model_type).normalize_params(params)


def sample_params(
    space: Mapping[str, Mapping[str, Any]],
    rng: np.random.Generator,
    history: list[dict[str, Any]],
    *,
    model_type: str,
    method: str,
    random_start_trials: int,
    top_fraction: float,
    sampler: str = "adaptive",
    probe_fraction: float = 0.0,
    trial_in_round: int | None = None,
    trials_per_round: int | None = None,
) -> dict[str, Any]:
    params, _ = sample_params_with_metadata(
        space,
        rng,
        history,
        model_type=model_type,
        method=method,
        random_start_trials=random_start_trials,
        top_fraction=top_fraction,
        sampler=sampler,
        probe_fraction=probe_fraction,
        trial_in_round=trial_in_round,
        trials_per_round=trials_per_round,
    )
    return params


def sample_params_with_metadata(
    space: Mapping[str, Mapping[str, Any]],
    rng: np.random.Generator,
    history: list[dict[str, Any]],
    *,
    model_type: str,
    method: str,
    random_start_trials: int,
    top_fraction: float,
    sampler: str = "adaptive",
    probe_fraction: float = 0.0,
    trial_in_round: int | None = None,
    trials_per_round: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    method = method.lower()
    sampler = str(sampler or "adaptive").lower()
    ok_history = [row for row in history if row.get("status") == "ok" and np.isfinite(float(row.get("score", np.nan)))]
    use_adaptive = method in {
        "adaptive_top_fraction",
        "adaptive_tpe",
        "tpe",
        "tpe_like",
    } and len(ok_history) >= random_start_trials
    top_rows = _top_rows(ok_history, top_fraction) if use_adaptive else []
    use_probe = (
        sampler in {"evidence_probe", "structured_probe", "local_probe"}
        and bool(top_rows)
        and rng.random() < max(0.0, min(float(probe_fraction), 1.0))
    )
    if use_probe:
        probe_type = _probe_type(model_type, trial_in_round)
        params = _sample_probe_params(space, top_rows, rng, model_type=model_type, probe_type=probe_type)
        return normalize_model_params(model_type, params), {
            "sampler": sampler,
            "probe_applied": True,
            "probe_type": probe_type,
            "top_trials_used": len(top_rows),
            "trial_in_round": trial_in_round,
            "trials_per_round": trials_per_round,
        }
    params = {
        name: _sample_one(name, spec, rng, top_rows if use_adaptive else [])
        for name, spec in space.items()
    }
    fallback_sampler = "adaptive_top_fraction" if use_adaptive else "random"
    return normalize_model_params(model_type, params), {
        "sampler": fallback_sampler if sampler == "adaptive" else sampler,
        "probe_applied": False,
        "probe_type": fallback_sampler,
        "top_trials_used": len(top_rows),
        "trial_in_round": trial_in_round,
        "trials_per_round": trials_per_round,
    }


def _top_rows(history: list[dict[str, Any]], top_fraction: float) -> list[dict[str, Any]]:
    if not 0 < top_fraction <= 1:
        raise ConfigError("search.top_fraction must be in (0, 1]")
    rows = sorted(history, key=lambda row: float(row.get("score", -np.inf)), reverse=True)
    count = max(3, int(math.ceil(len(rows) * top_fraction)))
    return rows[: min(count, len(rows))]


def _sample_one(name: str, spec: Mapping[str, Any], rng: np.random.Generator, top_rows: list[dict[str, Any]]) -> Any:
    kind = str(spec["type"])
    preferred = [row.get("params", {}).get(name) for row in top_rows if name in row.get("params", {})]
    if kind == "choice":
        return _sample_choice(spec, rng, preferred)
    if kind in {"uniform", "quniform"}:
        low, high = _adaptive_numeric_bounds(spec, preferred, log_scale=False)
        value = float(rng.uniform(low, high))
        return _quantize(value, spec) if kind == "quniform" else value
    if kind in {"loguniform", "qloguniform"}:
        low, high = _adaptive_numeric_bounds(spec, preferred, log_scale=True)
        value = float(math.exp(rng.uniform(math.log(low), math.log(high))))
        return _quantize(value, spec) if kind == "qloguniform" else value
    raise ConfigError(f"Unsupported search space type: {kind}")


def _sample_choice(spec: Mapping[str, Any], rng: np.random.Generator, preferred: list[Any]) -> Any:
    values = list(spec["values"])
    if not preferred:
        return copy.deepcopy(values[int(rng.integers(0, len(values)))])
    weights = np.ones(len(values), dtype="float64")
    for item in preferred:
        for idx, value in enumerate(values):
            if item == value:
                weights[idx] += 2.0
    weights = weights / weights.sum()
    idx = int(rng.choice(np.arange(len(values)), p=weights))
    return copy.deepcopy(values[idx])


def _adaptive_numeric_bounds(spec: Mapping[str, Any], preferred: list[Any], *, log_scale: bool) -> tuple[float, float]:
    low = float(spec["low"])
    high = float(spec["high"])
    numeric = np.array([float(x) for x in preferred if x is not None and np.isfinite(float(x))], dtype="float64")
    if len(numeric) < 3:
        return low, high
    if log_scale:
        numeric = np.log(np.clip(numeric, low, high))
        base_low, base_high = math.log(low), math.log(high)
    else:
        numeric = np.clip(numeric, low, high)
        base_low, base_high = low, high
    q_low, q_high = np.quantile(numeric, [0.2, 0.8])
    span = max(float(q_high - q_low), 0.10 * float(base_high - base_low))
    refined_low = max(base_low, float(q_low - 0.5 * span))
    refined_high = min(base_high, float(q_high + 0.5 * span))
    if refined_low >= refined_high:
        refined_low, refined_high = base_low, base_high
    if log_scale:
        return float(math.exp(refined_low)), float(math.exp(refined_high))
    return float(refined_low), float(refined_high)


def _sample_probe_params(
    space: Mapping[str, Mapping[str, Any]],
    top_rows: list[dict[str, Any]],
    rng: np.random.Generator,
    *,
    model_type: str,
    probe_type: str,
) -> dict[str, Any]:
    params = _center_params(space, top_rows, rng)
    directions = _probe_directions(model_type, probe_type)
    for name, direction in directions.items():
        if name not in space or name not in params:
            continue
        spec = space[name]
        kind = str(spec.get("type"))
        if kind == "choice":
            params[name] = _nudge_choice(spec, params[name], direction)
        elif kind in NUMERIC_TYPES:
            params[name] = _nudge_numeric(spec, params[name], direction)
    return params


def _center_params(space: Mapping[str, Mapping[str, Any]], top_rows: list[dict[str, Any]], rng: np.random.Generator) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for name, spec in space.items():
        values = [row.get("params", {}).get(name) for row in top_rows if name in row.get("params", {})]
        kind = str(spec.get("type"))
        if kind == "choice":
            params[name] = _mode_choice(spec, values, rng)
        elif kind in NUMERIC_TYPES:
            numeric = [float(v) for v in values if v is not None and np.isfinite(float(v))]
            if numeric:
                params[name] = _clip_numeric(spec, float(np.median(numeric)))
            else:
                params[name] = _sample_one(name, spec, rng, [])
        else:
            params[name] = _sample_one(name, spec, rng, [])
    return params


def _mode_choice(spec: Mapping[str, Any], values: list[Any], rng: np.random.Generator) -> Any:
    allowed = list(spec.get("values", []))
    if not allowed:
        return None
    allowed_by_key = {_canonical(value): value for value in allowed}
    counts = Counter(_canonical(value) for value in values if _canonical(value) in allowed_by_key)
    if not counts:
        return copy.deepcopy(allowed[int(rng.integers(0, len(allowed)))])
    key, _ = counts.most_common(1)[0]
    return copy.deepcopy(allowed_by_key[key])


def _probe_type(model_type: str, trial_in_round: int | None) -> str:
    sequence = MLP_PROBE_SEQUENCE if model_type == "mlp" else LGBM_PROBE_SEQUENCE
    idx = int(trial_in_round or 0) % len(sequence)
    return sequence[idx]


def _probe_directions(model_type: str, probe_type: str) -> dict[str, str]:
    if model_type == "mlp":
        mapping = {
            "high_capacity": {"hidden_layers": "up", "max_epochs": "up", "batch_size": "down"},
            "low_capacity": {"hidden_layers": "down", "max_epochs": "down", "batch_size": "up"},
            "strong_regularization": {"dropout": "up", "weight_decay": "up", "gradient_clip_norm": "up", "learning_rate": "down"},
            "weak_regularization": {"dropout": "down", "weight_decay": "down", "gradient_clip_norm": "down"},
            "lr_epoch_tradeoff": {"learning_rate": "down", "max_epochs": "up"},
        }
    else:
        mapping = {
            "high_capacity": {
                "num_leaves": "up",
                "max_depth": "up",
                "n_estimators": "up",
                "min_child_samples": "down",
                "subsample": "up",
                "colsample_bytree": "up",
                "lambda_l1": "down",
                "lambda_l2": "down",
                "min_split_gain": "down",
            },
            "low_capacity": {
                "num_leaves": "down",
                "max_depth": "down",
                "n_estimators": "down",
                "min_child_samples": "up",
            },
            "strong_regularization": {
                "min_child_samples": "up",
                "subsample": "down",
                "colsample_bytree": "down",
                "lambda_l1": "up",
                "lambda_l2": "up",
                "min_split_gain": "up",
            },
            "weak_regularization": {
                "subsample": "up",
                "colsample_bytree": "up",
                "lambda_l1": "down",
                "lambda_l2": "down",
                "min_split_gain": "down",
            },
            "lr_tree_tradeoff": {"learning_rate": "down", "n_estimators": "up"},
        }
    return mapping.get(probe_type, {})


def _nudge_choice(spec: Mapping[str, Any], current: Any, direction: str) -> Any:
    values = list(spec.get("values", []))
    if not values:
        return current
    keys = [_canonical(value) for value in values]
    current_key = _canonical(current)
    try:
        idx = keys.index(current_key)
    except ValueError:
        idx = len(values) // 2
    if direction == "up":
        idx = min(idx + 1, len(values) - 1)
    elif direction == "down":
        idx = max(idx - 1, 0)
    return copy.deepcopy(values[idx])


def _nudge_numeric(spec: Mapping[str, Any], current: Any, direction: str, step_ratio: float = 0.25) -> float | int:
    kind = str(spec.get("type"))
    low = float(spec["low"])
    high = float(spec["high"])
    value = _clip_numeric(spec, float(current))
    log_scale = "log" in kind
    if log_scale:
        low_t, high_t = math.log(low), math.log(high)
        value_t = math.log(max(value, low))
    else:
        low_t, high_t = low, high
        value_t = value
    span = high_t - low_t
    if direction == "up":
        value_t += step_ratio * span
    elif direction == "down":
        value_t -= step_ratio * span
    value_t = min(max(value_t, low_t), high_t)
    out = math.exp(value_t) if log_scale else value_t
    return _quantize(out, spec) if kind in {"quniform", "qloguniform"} else float(out)


def _clip_numeric(spec: Mapping[str, Any], value: float) -> float:
    return float(min(max(value, float(spec["low"])), float(spec["high"])))


def _quantize(value: float, spec: Mapping[str, Any]) -> int | float:
    q = float(spec.get("q", 1.0))
    low = float(spec["low"])
    high = float(spec["high"])
    if q <= 0:
        raise ConfigError("quantized search space requires q > 0")
    quantized = low + round((float(value) - low) / q) * q
    quantized = min(max(quantized, low), high)
    dtype = spec.get("dtype")
    if dtype == "float":
        return float(quantized)
    return int(round(quantized))


def _canonical(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)
