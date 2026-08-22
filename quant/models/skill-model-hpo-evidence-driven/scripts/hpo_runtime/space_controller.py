"""Rule-based search-space controller driven by trial evidence."""

from __future__ import annotations

import copy
import math
from typing import Any, Mapping

from config_utils import ConfigError
from search_space import validate_search_space


NUMERIC_SPACE_TYPES = {"uniform", "loguniform", "quniform", "qloguniform"}

DEFAULT_CONTROLLER_CONFIG: dict[str, Any] = {
    "enabled": True,
    "min_trials_for_adapt": 6,
    "allow_narrow": True,
    "allow_expand": True,
    "allow_stop": True,
    "allow_expand_beyond_initial": False,
    "boundary_margin": 0.15,
    "numeric_concentration_threshold": 0.45,
    "numeric_min_width_ratio": 0.20,
    "numeric_padding_ratio": 0.50,
    "expand_ratio": 0.50,
    "choice_concentration_threshold": 0.65,
    "choice_keep_min": 2,
    "choice_keep_max_fraction": 0.50,
    "patience_rounds": 2,
    "min_round_improvement": 0.001,
}


def _config(controller_config: Mapping[str, Any] | None) -> dict[str, Any]:
    out = dict(DEFAULT_CONTROLLER_CONFIG)
    if controller_config:
        out.update(dict(controller_config))
    return out


def _is_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _canonical(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _space_changed(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return _canonical(left) != _canonical(right)


def _current_and_base_specs(
    name: str,
    current_space: Mapping[str, Any],
    base_space: Mapping[str, Any] | None,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    current = current_space[name]
    base = (base_space or {}).get(name)
    return current, base if isinstance(base, Mapping) else current


def _transform(value: float, *, log_scale: bool) -> float:
    return math.log(value) if log_scale else value


def _inverse(value: float, *, log_scale: bool) -> float:
    return math.exp(value) if log_scale else value


def _numeric_bounds(spec: Mapping[str, Any], *, log_scale: bool) -> tuple[float, float]:
    low = float(spec["low"])
    high = float(spec["high"])
    return _transform(low, log_scale=log_scale), _transform(high, log_scale=log_scale)


def _narrow_numeric_spec(
    spec: Mapping[str, Any],
    evidence: Mapping[str, Any],
    *,
    min_width_ratio: float,
    padding_ratio: float,
) -> dict[str, Any] | None:
    q20 = evidence.get("top_q20")
    q80 = evidence.get("top_q80")
    median = evidence.get("top_median")
    if not (_is_finite(q20) and _is_finite(q80) and _is_finite(median)):
        return None
    kind = str(spec["type"])
    log_scale = "log" in kind
    if log_scale and (float(q20) <= 0 or float(q80) <= 0 or float(median) <= 0):
        return None

    low_t, high_t = _numeric_bounds(spec, log_scale=log_scale)
    if not low_t < high_t:
        return None
    q20_t = _transform(float(q20), log_scale=log_scale)
    q80_t = _transform(float(q80), log_scale=log_scale)
    median_t = _transform(float(median), log_scale=log_scale)
    current_span = high_t - low_t
    raw_span = max(q80_t - q20_t, 0.0)
    target_span = max(raw_span * (1.0 + max(0.0, padding_ratio)), current_span * max(0.0, min_width_ratio))
    target_span = min(target_span, current_span)
    center = median_t
    new_low_t = max(low_t, center - 0.5 * target_span)
    new_high_t = min(high_t, center + 0.5 * target_span)
    if new_high_t - new_low_t < current_span * max(0.0, min_width_ratio) * 0.99:
        deficit = current_span * max(0.0, min_width_ratio) - (new_high_t - new_low_t)
        new_low_t = max(low_t, new_low_t - 0.5 * deficit)
        new_high_t = min(high_t, new_high_t + 0.5 * deficit)
    if not new_low_t < new_high_t:
        return None

    updated = copy.deepcopy(dict(spec))
    updated["low"] = float(_inverse(new_low_t, log_scale=log_scale))
    updated["high"] = float(_inverse(new_high_t, log_scale=log_scale))
    return updated if _space_changed(spec, updated) else None


def _expand_numeric_spec(
    spec: Mapping[str, Any],
    base_spec: Mapping[str, Any],
    *,
    direction: str,
    expand_ratio: float,
    allow_beyond_initial: bool,
) -> dict[str, Any] | None:
    kind = str(spec["type"])
    log_scale = "log" in kind
    low_t, high_t = _numeric_bounds(spec, log_scale=log_scale)
    base_low_t, base_high_t = _numeric_bounds(base_spec, log_scale=log_scale)
    span = high_t - low_t
    if span <= 0:
        return None

    step = span * max(0.0, expand_ratio)
    new_low_t = low_t
    new_high_t = high_t
    if direction == "low":
        candidate = low_t - step
        new_low_t = candidate if allow_beyond_initial else max(base_low_t, candidate)
    elif direction == "high":
        candidate = high_t + step
        new_high_t = candidate if allow_beyond_initial else min(base_high_t, candidate)
    else:
        return None
    if not new_low_t < new_high_t:
        return None

    updated = copy.deepcopy(dict(spec))
    updated["low"] = float(_inverse(new_low_t, log_scale=log_scale))
    updated["high"] = float(_inverse(new_high_t, log_scale=log_scale))
    return updated if _space_changed(spec, updated) else None


def _narrow_choice_spec(
    spec: Mapping[str, Any],
    evidence: Mapping[str, Any],
    *,
    keep_min: int,
    keep_max_fraction: float,
) -> dict[str, Any] | None:
    allowed = list(spec.get("values", []))
    if len(allowed) <= max(1, keep_min):
        return None
    counts = evidence.get("value_counts") or {}
    if not isinstance(counts, Mapping) or not counts:
        return None
    ranked_keys = [str(key) for key in counts.keys()]
    keep_count = max(int(keep_min), int(math.ceil(len(allowed) * float(keep_max_fraction))))
    keep_count = min(max(1, keep_count), len(allowed))
    ranked_allowed = [value for key in ranked_keys for value in allowed if _canonical(value) == key]
    selected: list[Any] = []
    for value in ranked_allowed:
        if value not in selected:
            selected.append(value)
        if len(selected) >= keep_count:
            break
    if len(selected) < max(1, keep_min):
        for value in allowed:
            if value not in selected:
                selected.append(value)
            if len(selected) >= max(1, keep_min):
                break
    if not selected or len(selected) >= len(allowed):
        return None
    updated = copy.deepcopy(dict(spec))
    updated["values"] = selected
    return updated


def _stop_recommended(evidence: Mapping[str, Any], cfg: Mapping[str, Any]) -> bool:
    if not bool(cfg.get("allow_stop", True)):
        return False
    round_id = int(evidence.get("round_id", 0))
    patience_rounds = int(cfg.get("patience_rounds", 2))
    if round_id + 1 < patience_rounds:
        return False
    improvement = evidence.get("score_improvement_over_previous_round")
    if not _is_finite(improvement):
        return False
    return float(improvement) < float(cfg.get("min_round_improvement", 0.001))


def _keep(reason: str, evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "action": "keep",
        "reason": reason,
        "round_id": int((evidence or {}).get("round_id", 0)),
        "next_search_space": None,
        "changed_params": [],
    }


def decide_next_space(
    *,
    evidence: Mapping[str, Any],
    current_space: Mapping[str, Any],
    base_space: Mapping[str, Any] | None = None,
    controller_config: Mapping[str, Any] | None = None,
    model_type: str | None = None,
) -> dict[str, Any]:
    """Return a conservative keep/narrow/expand/stop decision.

    The controller only consumes structured evidence. It does not inspect raw
    data or retrain models, which keeps this layer reusable as a future skill.
    """
    cfg = _config(controller_config)
    if not bool(cfg.get("enabled", True)):
        return _keep("space_controller_disabled", evidence)
    num_ok = int(evidence.get("num_ok_trials_total") or 0)
    min_trials = int(cfg.get("min_trials_for_adapt", 6))
    if num_ok < min_trials:
        return _keep(f"insufficient_successful_trials:{num_ok}<{min_trials}", evidence)

    candidate_space = copy.deepcopy(dict(current_space))
    changes: list[dict[str, Any]] = []
    param_evidence = evidence.get("param_evidence") or {}
    if not isinstance(param_evidence, Mapping):
        return _keep("missing_param_evidence", evidence)

    for name, item in param_evidence.items():
        if name not in current_space or not isinstance(item, Mapping):
            continue
        current_spec, base_spec = _current_and_base_specs(name, current_space, base_space)
        kind = str(current_spec.get("type"))
        if kind in NUMERIC_SPACE_TYPES:
            update = None
            update_reason = None
            if bool(cfg.get("allow_expand", True)) and bool(item.get("boundary_hit_low")):
                update = _expand_numeric_spec(
                    current_spec,
                    base_spec,
                    direction="low",
                    expand_ratio=float(cfg.get("expand_ratio", 0.50)),
                    allow_beyond_initial=bool(cfg.get("allow_expand_beyond_initial", False)),
                )
                update_reason = "boundary_hit_low"
            elif bool(cfg.get("allow_expand", True)) and bool(item.get("boundary_hit_high")):
                update = _expand_numeric_spec(
                    current_spec,
                    base_spec,
                    direction="high",
                    expand_ratio=float(cfg.get("expand_ratio", 0.50)),
                    allow_beyond_initial=bool(cfg.get("allow_expand_beyond_initial", False)),
                )
                update_reason = "boundary_hit_high"
            if update is None and bool(cfg.get("allow_narrow", True)):
                width = item.get("relative_width")
                if _is_finite(width) and float(width) <= float(cfg.get("numeric_concentration_threshold", 0.45)):
                    update = _narrow_numeric_spec(
                        current_spec,
                        item,
                        min_width_ratio=float(cfg.get("numeric_min_width_ratio", 0.20)),
                        padding_ratio=float(cfg.get("numeric_padding_ratio", 0.50)),
                    )
                    update_reason = f"top_trials_concentrated_width:{float(width):.4g}"
            if update is not None and _space_changed(current_spec, update):
                candidate_space[name] = update
                changes.append({"param": name, "action": "expand" if "boundary" in str(update_reason) else "narrow", "reason": update_reason, "next_spec": update})
        elif kind == "choice":
            if not bool(cfg.get("allow_narrow", True)):
                continue
            concentration = item.get("concentration")
            if _is_finite(concentration) and float(concentration) >= float(cfg.get("choice_concentration_threshold", 0.65)):
                update = _narrow_choice_spec(
                    current_spec,
                    item,
                    keep_min=int(cfg.get("choice_keep_min", 2)),
                    keep_max_fraction=float(cfg.get("choice_keep_max_fraction", 0.50)),
                )
                if update is not None and _space_changed(current_spec, update):
                    candidate_space[name] = update
                    changes.append({
                        "param": name,
                        "action": "narrow",
                        "reason": f"choice_concentration:{float(concentration):.4g}",
                        "next_spec": update,
                    })

    if changes:
        try:
            validate_search_space(candidate_space)
        except ConfigError as exc:
            return {
                "action": "keep",
                "reason": f"candidate_space_invalid:{exc}",
                "round_id": int(evidence.get("round_id", 0)),
                "next_search_space": None,
                "changed_params": [],
            }
        action = "expand" if any(change["action"] == "expand" for change in changes) else "narrow"
        return {
            "action": action,
            "reason": "trial_evidence_space_update",
            "round_id": int(evidence.get("round_id", 0)),
            "model_type": model_type,
            "next_search_space": candidate_space,
            "changed_params": changes,
        }

    if _stop_recommended(evidence, cfg):
        return {
            "action": "stop",
            "reason": "no_material_round_improvement",
            "round_id": int(evidence.get("round_id", 0)),
            "next_search_space": None,
            "changed_params": [],
        }
    return _keep("no_reliable_space_update", evidence)
