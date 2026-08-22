"""Guarded LLM search-space decision layer."""

from __future__ import annotations

import copy
import json
import math
from typing import Any, Mapping

from config_utils import ConfigError, json_default
from llm_controller import request_space_update
from search_space import validate_search_space
from space_controller import decide_next_space


ALLOWED_ACTIONS = {"keep", "narrow", "expand", "shift", "stop"}
NUMERIC_TYPES = {"uniform", "loguniform", "quniform", "qloguniform"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=json_default)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _space_equal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return _canonical(left) == _canonical(right)


def _changed_params(current_space: Mapping[str, Any], next_space: Mapping[str, Any], action: str) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for name, next_spec in next_space.items():
        current_spec = current_space.get(name)
        if current_spec is None or not _space_equal(current_spec, next_spec):
            changes.append({"param": name, "action": action, "reason": "llm_space_update", "next_spec": copy.deepcopy(dict(next_spec))})
    return changes


def _numeric_span(spec: Mapping[str, Any]) -> float:
    kind = str(spec.get("type"))
    low = float(spec["low"])
    high = float(spec["high"])
    if "log" in kind:
        return math.log(high) - math.log(low)
    return high - low


def _numeric_inside(child: Mapping[str, Any], parent: Mapping[str, Any], *, tolerance: float = 1e-12) -> bool:
    child_low = float(child["low"])
    child_high = float(child["high"])
    parent_low = float(parent["low"])
    parent_high = float(parent["high"])
    return child_low >= parent_low - tolerance and child_high <= parent_high + tolerance


def _validate_param_set(current_space: Mapping[str, Any], next_space: Mapping[str, Any]) -> list[str]:
    current_keys = set(current_space)
    next_keys = set(next_space)
    errors: list[str] = []
    missing = sorted(current_keys - next_keys)
    extra = sorted(next_keys - current_keys)
    if missing:
        errors.append(f"next_search_space_missing_params:{missing}")
    if extra:
        errors.append(f"next_search_space_extra_params:{extra}")
    return errors


def _validate_choice_update(
    name: str,
    action: str,
    current_spec: Mapping[str, Any],
    next_spec: Mapping[str, Any],
    base_spec: Mapping[str, Any],
    *,
    allow_expand_beyond_initial: bool,
) -> list[str]:
    errors: list[str] = []
    current_values = list(current_spec.get("values", []))
    next_values = list(next_spec.get("values", []))
    base_values = list(base_spec.get("values", current_values))
    current_set = {_canonical(value) for value in current_values}
    next_set = {_canonical(value) for value in next_values}
    base_set = {_canonical(value) for value in base_values}
    if not next_values:
        errors.append(f"{name}:choice_empty")
    if not allow_expand_beyond_initial and not next_set.issubset(base_set):
        errors.append(f"{name}:choice_values_must_be_subset_of_initial_space")
    if action == "narrow" and not next_set.issubset(current_set):
        errors.append(f"{name}:choice_narrow_must_be_subset_of_current")
    if action == "expand" and not current_set.issubset(next_set):
        errors.append(f"{name}:choice_expand_must_include_current_values")
    return errors


def _validate_numeric_update(
    name: str,
    action: str,
    current_spec: Mapping[str, Any],
    next_spec: Mapping[str, Any],
    base_spec: Mapping[str, Any],
    *,
    allow_expand_beyond_initial: bool,
    max_shrink_ratio: float,
    max_expand_ratio: float,
) -> list[str]:
    errors: list[str] = []
    current_span = _numeric_span(current_spec)
    next_span = _numeric_span(next_spec)
    if current_span <= 0 or next_span <= 0:
        errors.append(f"{name}:non_positive_numeric_span")
        return errors
    if "log" in str(next_spec.get("type")) and float(next_spec.get("low", 0.0)) <= 0:
        errors.append(f"{name}:log_space_requires_positive_low")
    if not allow_expand_beyond_initial and not _numeric_inside(next_spec, base_spec):
        errors.append(f"{name}:numeric_bounds_outside_initial_space")
    shrink_ratio = next_span / current_span
    expand_ratio = next_span / current_span
    if action in {"narrow", "shift"} and shrink_ratio < max_shrink_ratio:
        errors.append(f"{name}:numeric_shrink_too_aggressive:{shrink_ratio:.4g}")
    if action in {"expand", "shift"} and expand_ratio > max_expand_ratio:
        errors.append(f"{name}:numeric_expand_too_aggressive:{expand_ratio:.4g}")
    return errors


def _decision_phase(round_id: int, controller_config: Mapping[str, Any]) -> tuple[str, list[str], list[str]]:
    exploration_rounds = int(controller_config.get("exploration_rounds", 2))
    relocation_rounds = int(controller_config.get("relocation_rounds", 2))
    if round_id < exploration_rounds:
        return (
            "exploration",
            list(controller_config.get("exploration_preferred_actions") or ["expand", "shift"]),
            list(controller_config.get("exploration_forbidden_actions") or ["narrow", "stop"]),
        )
    if round_id < exploration_rounds + relocation_rounds:
        return (
            "relocation",
            list(controller_config.get("relocation_preferred_actions") or ["shift", "expand", "narrow"]),
            list(controller_config.get("relocation_forbidden_actions") or ["stop"]),
        )
    return (
        "exploitation",
        list(controller_config.get("exploitation_preferred_actions") or ["narrow", "shift", "keep", "stop"]),
        list(controller_config.get("exploitation_forbidden_actions") or []),
    )



def _validate_model_specific_space(
    *,
    model_type: str,
    next_space: Mapping[str, Any],
    controller_config: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if model_type != "mlp":
        return errors
    hidden_spec = next_space.get("hidden_layers")
    if not isinstance(hidden_spec, Mapping) or hidden_spec.get("type") != "choice":
        return errors
    max_layers = int(controller_config.get("mlp_max_hidden_layers", 4))
    max_units = int(controller_config.get("mlp_max_hidden_units", 512))
    for idx, raw_value in enumerate(list(hidden_spec.get("values", []))):
        if not isinstance(raw_value, list) or not raw_value:
            errors.append(f"hidden_layers:value_{idx}_must_be_non_empty_list")
            continue
        if len(raw_value) > max_layers:
            errors.append(f"hidden_layers:value_{idx}_too_many_layers:{len(raw_value)}>{max_layers}")
        for unit in raw_value:
            try:
                unit_int = int(unit)
            except (TypeError, ValueError):
                errors.append(f"hidden_layers:value_{idx}_unit_not_int:{unit}")
                continue
            if unit_int <= 0:
                errors.append(f"hidden_layers:value_{idx}_unit_not_positive:{unit_int}")
            if unit_int > max_units:
                errors.append(f"hidden_layers:value_{idx}_unit_too_large:{unit_int}>{max_units}")
    return errors

def validate_guarded_decision(
    decision: Mapping[str, Any],
    *,
    current_space: Mapping[str, Any],
    base_space: Mapping[str, Any],
    controller_config: Mapping[str, Any],
    trial_evidence: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    round_id = int((trial_evidence or {}).get("round_id", 0))
    phase, preferred_actions, forbidden_actions = _decision_phase(round_id, controller_config)
    action = str(decision.get("action", "")).lower()
    if action not in ALLOWED_ACTIONS:
        return None, [f"unsupported_action:{decision.get('action')}"]
    if action in forbidden_actions:
        failed_trials = int((trial_evidence or {}).get("num_failed_trials_total", 0))
        total_trials = int((trial_evidence or {}).get("num_trials_total", 0))
        all_failed = total_trials > 0 and failed_trials == total_trials
        if not all_failed:
            return None, [f"phase_forbidden_action:{phase}:{action}"]
    if action in {"keep", "stop"}:
        return {
            "action": action,
            "reason": str(decision.get("reason") or f"llm_requested_{action}"),
            "next_search_space": None,
            "changed_params": [],
            "next_round_trials": decision.get("next_round_trials"),
            "decision_phase": phase,
            "preferred_actions": preferred_actions,
            "forbidden_actions": forbidden_actions,
            "hypothesis": decision.get("hypothesis"),
            "risk_flags": list(decision.get("risk_flags") or []),
        }, []

    raw_space = decision.get("next_search_space")
    if not isinstance(raw_space, Mapping):
        return None, ["next_search_space_required"]
    next_space = copy.deepcopy(dict(raw_space))
    errors.extend(_validate_param_set(current_space, next_space))
    if errors:
        return None, errors
    try:
        validate_search_space(next_space)
    except ConfigError as exc:
        errors.append(f"invalid_search_space:{exc}")
        return None, errors
    model_type = str((trial_evidence or {}).get("model_type") or "").lower()
    errors.extend(
        _validate_model_specific_space(
            model_type=model_type,
            next_space=next_space,
            controller_config=controller_config,
        )
    )
    if errors:
        return None, errors

    allow_expand_beyond_initial = bool(controller_config.get("allow_expand_beyond_initial", False))
    max_shrink_ratio = float(controller_config.get("llm_min_numeric_width_ratio", controller_config.get("numeric_min_width_ratio", 0.20)))
    max_expand_ratio = float(controller_config.get("llm_max_numeric_expand_ratio", 2.0))
    for name, current_spec in current_space.items():
        next_spec = next_space[name]
        if str(current_spec.get("type")) != str(next_spec.get("type")):
            errors.append(f"{name}:space_type_changed")
            continue
        kind = str(current_spec.get("type"))
        base_spec = _as_mapping(base_space.get(name)) or current_spec
        if kind == "choice":
            errors.extend(
                _validate_choice_update(
                    name,
                    action,
                    current_spec,
                    next_spec,
                    base_spec,
                    allow_expand_beyond_initial=allow_expand_beyond_initial,
                )
            )
        elif kind in NUMERIC_TYPES:
            errors.extend(
                _validate_numeric_update(
                    name,
                    action,
                    current_spec,
                    next_spec,
                    base_spec,
                    allow_expand_beyond_initial=allow_expand_beyond_initial,
                    max_shrink_ratio=max_shrink_ratio,
                    max_expand_ratio=max_expand_ratio,
                )
            )
    if errors:
        return None, errors
    changed = _changed_params(current_space, next_space, action)
    if action != "keep" and not changed:
        errors.append("non_keep_action_without_space_change")
        return None, errors
    if action == "keep":
        next_space = None
        changed = []
    validated = {
        "action": action,
        "reason": str(decision.get("reason") or "llm_guarded_decision"),
        "next_search_space": next_space,
        "changed_params": changed,
        "next_round_trials": decision.get("next_round_trials"),
        "decision_phase": phase,
        "preferred_actions": preferred_actions,
        "forbidden_actions": forbidden_actions,
        "hypothesis": decision.get("hypothesis"),
        "risk_flags": list(decision.get("risk_flags") or []),
    }
    return validated, []


def build_llm_guarded_evidence(
    *,
    trial_evidence: Mapping[str, Any],
    current_space: Mapping[str, Any],
    base_space: Mapping[str, Any],
    decision_memory: list[Mapping[str, Any]],
    controller_config: Mapping[str, Any],
) -> dict[str, Any]:
    max_memory = int(controller_config.get("llm_memory_items", 5))
    round_id = int(trial_evidence.get("round_id", 0))
    model_type = str(trial_evidence.get("model_type") or "").lower()
    phase, preferred_actions, forbidden_actions = _decision_phase(round_id, controller_config)
    max_next_round_trials = int(controller_config.get("max_next_round_trials", controller_config.get("trials_per_round", 0)) or 0)
    evidence_reading_guide = [
        "Use boundary_param_summary to decide whether top trials pressure the current space edge.",
        "Use top_score_diagnostics to distinguish stable regions from isolated best trials.",
        "Use probe_evidence to compare center, capacity, regularization, and learning-rate tradeoff probes before shifting or narrowing.",
        "Use round_best_history and score_improvement_over_previous_round to judge whether the last action improved search quality.",
        "Prefer shift or expand when top trials repeatedly hit boundaries or when the current best region remains under-explored.",
        "Avoid narrow when best_trial_isolated is true or top trials are dispersed.",
    ]
    hard_constraints = [
        "Return strict JSON only.",
        "Do not change model family, training data, label definition, or evaluation metric.",
        "Do not add or remove hyperparameter names.",
        "For choice parameters, next values must be valid choices under the guarded action semantics.",
        "For numeric parameters, keep valid low/high bounds and respect configured expansion limits.",
        "Use validation evidence only; holdout test metrics are unavailable during search.",
        "Prefer the listed preferred_actions for the current decision_phase unless evidence strongly contradicts them.",
        "Do not use forbidden_actions for the current decision_phase unless every trial failed.",
    ]
    if model_type == "mlp":
        max_layers = int(controller_config.get("mlp_max_hidden_layers", 4))
        max_units = int(controller_config.get("mlp_max_hidden_units", 512))
        hard_constraints.append(f"For mlp hidden_layers choices, do not exceed {max_layers} hidden layers or {max_units} units per layer.")
    if max_next_round_trials > 0:
        hard_constraints.append(f"Do not set next_round_trials above {max_next_round_trials}.")
    return {
        "task": "Decide the next hyperparameter search space for quantitative walk-forward validation.",
        "decision_mode": "llm_guarded",
        "allowed_actions": sorted(ALLOWED_ACTIONS),
        "decision_phase": phase,
        "preferred_actions": preferred_actions,
        "forbidden_actions": forbidden_actions,
        "max_next_round_trials": max_next_round_trials if max_next_round_trials > 0 else None,
        "hard_constraints": hard_constraints,
        "evidence_reading_guide": evidence_reading_guide,
        "required_schema": {
            "action": "keep | narrow | expand | shift | stop",
            "reason": "short evidence-grounded explanation",
            "next_search_space": "full search-space mapping unless action=keep or stop",
            "next_round_trials": "optional positive integer",
            "hypothesis": "optional testable hypothesis for the next round",
            "risk_flags": "optional list of risks",
        },
        "current_space": current_space,
        "initial_space": base_space,
        "controller_config": {
            "allow_expand_beyond_initial": bool(controller_config.get("allow_expand_beyond_initial", False)),
            "llm_min_numeric_width_ratio": float(controller_config.get("llm_min_numeric_width_ratio", controller_config.get("numeric_min_width_ratio", 0.20))),
            "llm_max_numeric_expand_ratio": float(controller_config.get("llm_max_numeric_expand_ratio", 2.0)),
            "decision_phase": phase,
            "preferred_actions": preferred_actions,
            "forbidden_actions": forbidden_actions,
            "max_next_round_trials": max_next_round_trials if max_next_round_trials > 0 else None,
        },
        "trial_evidence": trial_evidence,
        "decision_memory": list(decision_memory[-max_memory:]) if max_memory > 0 else [],
    }


def decide_next_space_guarded(
    *,
    cfg: Mapping[str, Any],
    trial_evidence: Mapping[str, Any],
    current_space: Mapping[str, Any],
    base_space: Mapping[str, Any],
    controller_config: Mapping[str, Any],
    model_type: str,
    decision_memory: list[Mapping[str, Any]],
) -> dict[str, Any]:
    def _phase_guard_decision(decision: Mapping[str, Any], source: str, errors: list[str] | None = None) -> dict[str, Any]:
        validated, guard_errors = validate_guarded_decision(
            decision,
            current_space=current_space,
            base_space=base_space,
            controller_config=controller_config,
            trial_evidence=trial_evidence,
        )
        if validated is not None and not guard_errors:
            return {
                "source": source,
                "accepted": False,
                "validation_errors": list(errors or []),
                "raw_llm_decision": None,
                "validated_decision": validated,
            }
        phase, preferred_actions, forbidden_actions = _decision_phase(int(trial_evidence.get("round_id", 0)), controller_config)
        return {
            "source": source,
            "accepted": False,
            "validation_errors": list(errors or []) + guard_errors,
            "raw_llm_decision": None,
            "validated_decision": {
                "action": "keep",
                "reason": "fallback_blocked_by_decision_phase_guard",
                "next_search_space": None,
                "changed_params": [],
                "next_round_trials": controller_config.get("max_next_round_trials"),
                "decision_phase": phase,
                "preferred_actions": preferred_actions,
                "forbidden_actions": forbidden_actions,
                "hypothesis": None,
                "risk_flags": ["phase_guard_fallback"],
            },
        }

    mode = str(controller_config.get("mode", "rule")).lower()
    llm_cfg = cfg.get("llm", {}) if isinstance(cfg.get("llm", {}), Mapping) else {}
    if mode in {"llm_guarded", "llm_suggest"} and not bool(llm_cfg.get("enabled", False)):
        fallback = decide_next_space(
            evidence=trial_evidence,
            current_space=current_space,
            base_space=base_space,
            controller_config=controller_config,
            model_type=model_type,
        )
        record = _phase_guard_decision(fallback, "rule_fallback", ["llm_disabled"])
        record["llm_evidence"] = build_llm_guarded_evidence(
            trial_evidence=trial_evidence,
            current_space=current_space,
            base_space=base_space,
            decision_memory=decision_memory,
            controller_config=controller_config,
        )
        return record
    if mode not in {"llm_guarded", "llm_suggest"}:
        rule = decide_next_space(
            evidence=trial_evidence,
            current_space=current_space,
            base_space=base_space,
            controller_config=controller_config,
            model_type=model_type,
        )
        return {"source": "rule", "accepted": True, "validation_errors": [], "raw_llm_decision": None, "validated_decision": rule}

    llm_evidence = build_llm_guarded_evidence(
        trial_evidence=trial_evidence,
        current_space=current_space,
        base_space=base_space,
        decision_memory=decision_memory,
        controller_config=controller_config,
    )
    try:
        raw_decision = request_space_update(cfg, llm_evidence)
    except Exception as exc:
        fallback = decide_next_space(
            evidence=trial_evidence,
            current_space=current_space,
            base_space=base_space,
            controller_config=controller_config,
            model_type=model_type,
        )
        record = _phase_guard_decision(fallback, "rule_fallback", [f"llm_request_failed:{type(exc).__name__}: {exc}"])
        record["llm_evidence"] = llm_evidence
        return record

    validated, errors = validate_guarded_decision(
        raw_decision,
        current_space=current_space,
        base_space=base_space,
        controller_config=controller_config,
        trial_evidence=trial_evidence,
    )
    if mode == "llm_suggest":
        rule = decide_next_space(
            evidence=trial_evidence,
            current_space=current_space,
            base_space=base_space,
            controller_config=controller_config,
            model_type=model_type,
        )
        return {
            "source": "rule_with_llm_suggestion",
            "accepted": bool(validated and not errors),
            "validation_errors": errors,
            "raw_llm_decision": raw_decision,
            "validated_decision": rule,
            "llm_suggestion": validated,
            "llm_evidence": llm_evidence,
        }
    if validated is None or errors:
        fallback = decide_next_space(
            evidence=trial_evidence,
            current_space=current_space,
            base_space=base_space,
            controller_config=controller_config,
            model_type=model_type,
        )
        record = _phase_guard_decision(fallback, "rule_fallback", errors)
        record["raw_llm_decision"] = raw_decision
        record["llm_evidence"] = llm_evidence
        return record
    return {
        "source": "llm",
        "accepted": True,
        "validation_errors": [],
        "raw_llm_decision": raw_decision,
        "validated_decision": validated,
        "llm_evidence": llm_evidence,
    }


def build_decision_memory_item(
    *,
    round_id: int,
    decision_record: Mapping[str, Any],
    evidence_before: Mapping[str, Any],
    evidence_after: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    decision = decision_record.get("validated_decision") or {}
    item = {
        "round_id": int(round_id),
        "source": decision_record.get("source"),
        "accepted": bool(decision_record.get("accepted")),
        "action": decision.get("action"),
        "reason": decision.get("reason"),
        "hypothesis": decision.get("hypothesis"),
        "changed_params": [change.get("param") for change in decision.get("changed_params", [])],
        "score_before": evidence_before.get("best_score"),
    }
    if evidence_after is not None:
        before = evidence_before.get("best_score")
        after = evidence_after.get("best_score")
        item["score_after"] = after
        item["score_delta"] = (float(after) - float(before)) if before is not None and after is not None else None
    return item
