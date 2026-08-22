"""Build budget-aware model search spaces for auto search."""

from __future__ import annotations

import copy
from typing import Any, Mapping

from config_utils import ConfigError
from extension_registry import REGISTRY
from plugin_loader import ensure_builtin_extensions
from search_space import validate_search_space


BUDGET_PRESETS: dict[str, dict[str, int]] = {
    "fast": {"max_trials": 8, "max_rounds": 2, "trials_per_round": 4, "random_start_trials": 2},
    "standard": {"max_trials": 24, "max_rounds": 3, "trials_per_round": 8, "random_start_trials": 6},
    "deep": {"max_trials": 60, "max_rounds": 4, "trials_per_round": 15, "random_start_trials": 10},
}


def _lgbm_space(budget: str, missing_rate: float) -> dict[str, dict[str, Any]]:
    if budget == "fast":
        space = {
            "num_leaves": {"type": "choice", "values": [15, 31]},
            "max_depth": {"type": "choice", "values": [4, 6, -1]},
            "learning_rate": {"type": "choice", "values": [0.02, 0.05, 0.08]},
            "n_estimators": {"type": "choice", "values": [50, 100]},
            "min_child_samples": {"type": "choice", "values": [50, 100, 200]},
            "subsample": {"type": "choice", "values": [0.8, 0.95]},
            "colsample_bytree": {"type": "choice", "values": [0.7, 0.9]},
            "lambda_l2": {"type": "choice", "values": [0.1, 1.0, 5.0]},
        }
    else:
        space = {
            "num_leaves": {"type": "choice", "values": [15, 31, 63]},
            "max_depth": {"type": "choice", "values": [-1, 4, 6, 8]},
            "learning_rate": {"type": "loguniform", "low": 0.005, "high": 0.08},
            "n_estimators": {"type": "choice", "values": [80, 150, 300]},
            "min_child_samples": {"type": "choice", "values": [30, 80, 150, 300]},
            "subsample": {"type": "uniform", "low": 0.6, "high": 1.0},
            "colsample_bytree": {"type": "uniform", "low": 0.5, "high": 1.0},
            "lambda_l1": {"type": "loguniform", "low": 1e-6, "high": 10.0},
            "lambda_l2": {"type": "loguniform", "low": 1e-6, "high": 20.0},
            "min_split_gain": {"type": "choice", "values": [0.0, 0.01, 0.05]},
        }
    if missing_rate > 0.15:
        space["num_leaves"] = {"type": "choice", "values": [15, 31]}
        space["min_child_samples"] = {"type": "choice", "values": [100, 200, 300]}
        space["lambda_l2"] = {"type": "loguniform", "low": 0.1, "high": 30.0}
    return space


def _mlp_space(budget: str) -> dict[str, dict[str, Any]]:
    if budget == "fast":
        return {
            "hidden_layers": {"type": "choice", "values": [[64], [128]]},
            "activation": {"type": "choice", "values": ["relu", "gelu"]},
            "dropout": {"type": "uniform", "low": 0.0, "high": 0.2},
            "learning_rate": {"type": "loguniform", "low": 1e-4, "high": 2e-3},
            "weight_decay": {"type": "loguniform", "low": 1e-6, "high": 1e-3},
            "batch_size": {"type": "choice", "values": [1024, 2048, 4096]},
            "max_epochs": {"type": "choice", "values": [3, 5]},
            "gradient_clip_norm": {"type": "choice", "values": [1.0, 5.0]},
        }
    return {
        "hidden_layers": {"type": "choice", "values": [[64], [128], [128, 64], [256, 128]]},
        "activation": {"type": "choice", "values": ["relu", "gelu", "silu"]},
        "dropout": {"type": "uniform", "low": 0.0, "high": 0.3},
        "learning_rate": {"type": "loguniform", "low": 1e-4, "high": 3e-3},
        "weight_decay": {"type": "loguniform", "low": 1e-6, "high": 1e-2},
        "batch_size": {"type": "choice", "values": [512, 1024, 2048, 4096]},
        "max_epochs": {"type": "choice", "values": [5, 10, 20]},
        "gradient_clip_norm": {"type": "choice", "values": [0.0, 1.0, 5.0]},
    }


def resolve_budget(budget: str | None) -> str:
    name = str(budget or "standard").strip().lower()
    if name not in BUDGET_PRESETS:
        allowed = ", ".join(sorted(BUDGET_PRESETS))
        raise ConfigError(f"Unsupported goal.budget={name!r}; expected one of: {allowed}")
    return name


def build_search_plan(
    *,
    model_type: str,
    budget: str,
    profile: Mapping[str, Any],
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    budget = resolve_budget(budget)
    ensure_builtin_extensions()
    model_type = REGISTRY.canonical_model_name(model_type)
    feature = profile.get("feature") or {}
    missing_rate = float(feature.get("sample_missing_rate") or 0.0)
    if model_type == "lgbm":
        space = _lgbm_space(budget, missing_rate)
    elif model_type == "mlp":
        space = _mlp_space(budget)
    else:
        space = REGISTRY.get_model_plugin(model_type).default_search_space()
    plan = dict(BUDGET_PRESETS[budget])
    plan.update({
        "model_type": model_type,
        "method": "adaptive_tpe",
        "top_fraction": 0.30,
        "seed": 42,
        "normalize_method": None,
        "allow_overlapping_validation": False,
        "fixed_params": {},
        "space": space,
    })
    if overrides:
        plan = _merge_search_overrides(plan, overrides)
    validate_search_space(plan["space"])
    return plan


def _merge_search_overrides(plan: dict[str, Any], overrides: Mapping[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(plan)
    for key, value in overrides.items():
        if key == "model_type":
            # AutoPlanner resolves the model family before search-space construction.
            # Keeping this here would let search.model_type=auto leak into SearchRunner.
            continue
        if key == "space" and value:
            if not isinstance(value, Mapping):
                raise ConfigError("search.space override must be a mapping")
            out["space"] = copy.deepcopy(dict(value))
        else:
            out[key] = value
    return out
