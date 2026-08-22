"""Final-selection evidence and validation with neighborhood checks."""

from __future__ import annotations

import copy
import json
import math
from typing import Any, Mapping

import numpy as np

from config_utils import ConfigError
from search_space import normalize_model_params


DEFAULT_FINAL_SELECTOR: dict[str, Any] = {
    "enabled": False,
    "mode": "llm_guarded",
    "top_k": 5,
    "neighbors_per_candidate": 2,
    "max_extra_trials": 10,
    "numeric_radius": 0.05,
    "log_numeric_radius": 0.10,
    "choice_neighbor_steps": 1,
    "choice_perturb_probability": 0.50,
    "numeric_perturb_probability": 0.75,
    "min_neighbor_success": 1,
    "max_score_drop": 0.03,
    "fallback": "score_best",
    "freeze_params": [],
    "max_all_trials_in_prompt": 80,
}

TRIAL_METRIC_KEYS = [
    "trial_id",
    "round_id",
    "sampler",
    "probe_type",
    "score",
    "objective",
    "fast_score",
    "valid_rmse",
    "valid_mae",
    "valid_r2",
    "window_train_rmse",
    "window_valid_rmse",
    "window_train_r2",
    "window_valid_r2",
    "mean_ic",
    "mean_rankic",
    "icir",
    "rankic_ir",
    "robust_rankic",
    "num_valid_dates",
    "num_rankic_blocks",
    "block_rankic_mean",
    "block_rankic_std",
    "block_rankic_se",
    "positive_block_ratio",
    "top_bottom_spread",
    "positive_window_ratio",
    "turnover_proxy",
    "instability_penalty",
    "complexity_penalty",
    "overfit_penalty",
]


class FinalSelectionError(ConfigError):
    """Raised when an LLM final-selection response cannot be accepted."""


def resolve_final_selector_config(raw: Mapping[str, Any] | None, *, model_type: str) -> dict[str, Any]:
    cfg = copy.deepcopy(DEFAULT_FINAL_SELECTOR)
    raw_cfg = dict(raw or {})
    cfg.update(raw_cfg)

    if model_type == "mlp" and "freeze_params" not in raw_cfg:
        cfg["freeze_params"] = ["activation"]

    cfg["enabled"] = bool(cfg.get("enabled", False))
    cfg["mode"] = str(cfg.get("mode") or "llm_guarded")
    if cfg["mode"] != "llm_guarded":
        raise ConfigError("final_selector.mode currently supports only llm_guarded")
    cfg["top_k"] = _positive_int(cfg.get("top_k"), "final_selector.top_k")
    cfg["neighbors_per_candidate"] = _positive_int(
        cfg.get("neighbors_per_candidate"), "final_selector.neighbors_per_candidate"
    )
    cfg["max_extra_trials"] = _positive_int(cfg.get("max_extra_trials"), "final_selector.max_extra_trials")
    cfg["min_neighbor_success"] = _positive_int(
        cfg.get("min_neighbor_success"), "final_selector.min_neighbor_success"
    )
    cfg["numeric_radius"] = _positive_float(cfg.get("numeric_radius"), "final_selector.numeric_radius")
    cfg["log_numeric_radius"] = _positive_float(cfg.get("log_numeric_radius"), "final_selector.log_numeric_radius")
    cfg["choice_neighbor_steps"] = _positive_int(
        cfg.get("choice_neighbor_steps"), "final_selector.choice_neighbor_steps"
    )
    cfg["choice_perturb_probability"] = _probability(
        cfg.get("choice_perturb_probability"), "final_selector.choice_perturb_probability"
    )
    cfg["numeric_perturb_probability"] = _probability(
        cfg.get("numeric_perturb_probability"), "final_selector.numeric_perturb_probability"
    )
    cfg["max_score_drop"] = _non_negative_float(cfg.get("max_score_drop"), "final_selector.max_score_drop")
    cfg["fallback"] = str(cfg.get("fallback") or "score_best")
    if cfg["fallback"] != "score_best":
        raise ConfigError("final_selector.fallback currently supports only score_best")
    cfg["freeze_params"] = [str(item) for item in list(cfg.get("freeze_params") or [])]
    cfg["max_all_trials_in_prompt"] = _positive_int(
        cfg.get("max_all_trials_in_prompt"), "final_selector.max_all_trials_in_prompt"
    )
    return cfg


def select_center_candidates(trial_history: list[dict[str, Any]], *, top_k: int) -> list[dict[str, Any]]:
    ok_rows: list[dict[str, Any]] = []
    for row in trial_history:
        if row.get("status") != "ok":
            continue
        score = _safe_float(row.get("score"))
        if score is None:
            continue
        copied = dict(row)
        copied["score"] = score
        ok_rows.append(copied)
    ok_rows.sort(key=lambda item: float(item["score"]), reverse=True)
    return ok_rows[: max(1, int(top_k))]


def build_neighbor_plan(
    candidates: list[dict[str, Any]],
    *,
    search_space: Mapping[str, Mapping[str, Any]],
    model_type: str,
    selector_cfg: Mapping[str, Any],
    rng: np.random.Generator,
) -> list[dict[str, Any]]:
    if not candidates:
        return []

    neighbors_per_candidate = int(selector_cfg["neighbors_per_candidate"])
    max_extra_trials = int(selector_cfg["max_extra_trials"])
    freeze_params = set(str(item) for item in selector_cfg.get("freeze_params", []))
    seen = {_params_key(row.get("params", {})) for row in candidates}
    plan: list[dict[str, Any]] = []

    for center_rank, center in enumerate(candidates, start=1):
        center_id = str(center.get("trial_id"))
        center_params = dict(center.get("params") or {})
        generated_for_center = 0
        attempts = 0
        while generated_for_center < neighbors_per_candidate and len(plan) < max_extra_trials:
            attempts += 1
            if attempts > neighbors_per_candidate * 30:
                break
            params = _make_neighbor_params(
                center_params,
                search_space=search_space,
                model_type=model_type,
                selector_cfg=selector_cfg,
                freeze_params=freeze_params,
                rng=rng,
            )
            key = _params_key(params)
            if key in seen:
                continue
            seen.add(key)
            neighbor_index = generated_for_center
            plan.append(
                {
                    "center_trial_id": center_id,
                    "center_rank": center_rank,
                    "center_score": float(center["score"]),
                    "neighbor_index": neighbor_index,
                    "neighbor_trial_id": f"final_neighbor_{center_id}_n{neighbor_index:02d}",
                    "params": params,
                }
            )
            generated_for_center += 1
        if len(plan) >= max_extra_trials:
            break
    return plan


def build_final_selection_evidence(
    *,
    model_type: str,
    objective: str,
    candidates: list[dict[str, Any]],
    all_trials: list[dict[str, Any]],
    neighbor_rows: list[dict[str, Any]],
    selector_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    if not candidates:
        raise FinalSelectionError("final selector requires at least one successful candidate")

    score_best = candidates[0]
    score_best_score = float(score_best["score"])
    candidate_ids = [str(row.get("trial_id")) for row in candidates]
    neighbor_summary = _summarize_neighbors(neighbor_rows)
    max_rows = int(selector_cfg.get("max_all_trials_in_prompt", 80))
    ok_trials = [row for row in all_trials if row.get("status") == "ok" and _safe_float(row.get("score")) is not None]
    ok_trials = sorted(ok_trials, key=lambda row: float(row.get("score", -math.inf)), reverse=True)[:max_rows]

    candidate_evidence = []
    for rank, row in enumerate(candidates, start=1):
        trial_id = str(row.get("trial_id"))
        summary = neighbor_summary.get(trial_id, _empty_neighbor_summary())
        compact = _compact_trial(row)
        compact.update(
            {
                "candidate_rank": rank,
                "score_drop_from_best": float(score_best_score - float(row["score"])),
                "neighborhood": summary,
            }
        )
        candidate_evidence.append(compact)

    evidence = {
        "model_type": model_type,
        "objective": objective,
        "score_direction": "higher_is_better",
        "selection_policy": {
            "allowed_selected_trial_ids": candidate_ids,
            "score_best_trial_id": str(score_best.get("trial_id")),
            "score_best_score": score_best_score,
            "max_score_drop": float(selector_cfg["max_score_drop"]),
            "must_select_existing_center_trial": True,
            "must_not_select_neighbor_trial": True,
            "must_not_modify_parameters": True,
            "holdout_metrics_available": False,
        },
        "instructions": {
            "primary_goal": "Select the final hyperparameter trial for holdout evaluation.",
            "use_evidence": [
                "validation objective score",
                "rank/IC metrics",
                "top-bottom spread",
                "positive window ratio",
                "RMSE/R2 as auxiliary risk checks",
                "turnover, complexity, instability, and overfit penalties",
                "local neighborhood stability around each candidate",
            ],
            "avoid": [
                "choosing a validation spike with poor neighborhood stability",
                "choosing a materially lower-score candidate without clear risk reduction",
                "using holdout/test information",
                "inventing a new parameter set",
            ],
            "response_schema": {
                "selected_trial_id": "one id from allowed_selected_trial_ids",
                "reason": "short evidence-grounded reason",
                "risk_flags": ["list of risks considered"],
                "confidence": "low|medium|high",
            },
        },
        "candidates": candidate_evidence,
        "all_successful_trials_compact": [_compact_trial(row) for row in ok_trials],
    }
    return _clean_json_value(evidence)


def validate_final_selection(
    raw_decision: Mapping[str, Any] | None,
    *,
    evidence: Mapping[str, Any],
    candidates: list[dict[str, Any]],
    selector_cfg: Mapping[str, Any],
    source: str,
    error: str | None = None,
) -> dict[str, Any]:
    score_best = candidates[0]
    score_best_id = str(score_best.get("trial_id"))
    score_best_score = float(score_best["score"])
    candidate_by_id = {str(row.get("trial_id")): row for row in candidates}
    allowed_ids = set(candidate_by_id)
    validation_errors: list[str] = []
    selected_id = None
    if raw_decision is None:
        validation_errors.append(error or "missing_llm_decision")
    else:
        selected_id = str(raw_decision.get("selected_trial_id") or "")
        if selected_id not in allowed_ids:
            validation_errors.append(f"selected_trial_id_not_allowed:{selected_id}")
        else:
            selected_score = float(candidate_by_id[selected_id]["score"])
            max_drop = float(selector_cfg["max_score_drop"])
            if score_best_score - selected_score > max_drop:
                validation_errors.append(
                    f"selected_score_drop_too_large:{score_best_score - selected_score:.6g}>{max_drop:.6g}"
                )

    accepted = not validation_errors and selected_id is not None
    if accepted:
        selected = candidate_by_id[str(selected_id)]
        reason = str(raw_decision.get("reason") or "llm_selected_candidate") if raw_decision else ""
        confidence = str(raw_decision.get("confidence") or "medium") if raw_decision else "medium"
        risk_flags = list(raw_decision.get("risk_flags") or []) if raw_decision else []
    else:
        selected = score_best
        reason = "fallback_to_score_best"
        confidence = "low" if validation_errors else "medium"
        risk_flags = ["llm_selection_rejected"] if raw_decision is not None else ["llm_selection_unavailable"]

    selected_id = str(selected.get("trial_id"))
    selected_score = float(selected["score"])
    return {
        "enabled": True,
        "source": source,
        "accepted": accepted,
        "validation_errors": validation_errors,
        "raw_llm_decision": dict(raw_decision or {}),
        "validated_selection": {
            "selected_by": "llm_final_selector" if accepted else "score_best_fallback",
            "selected_trial_id": selected_id,
            "selected_score": selected_score,
            "score_best_trial_id": score_best_id,
            "score_best_score": score_best_score,
            "score_drop_from_best": float(score_best_score - selected_score),
            "reason": reason,
            "risk_flags": risk_flags,
            "confidence": confidence,
            "selected_params": dict(selected.get("params") or {}),
        },
        "evidence_summary": {
            "objective": evidence.get("objective"),
            "num_candidates": len(candidates),
            "num_all_trials_in_prompt": len(evidence.get("all_successful_trials_compact") or []),
            "max_score_drop": float(selector_cfg["max_score_drop"]),
        },
        "config": dict(selector_cfg),
    }


def fallback_final_selection(
    *,
    evidence: Mapping[str, Any],
    candidates: list[dict[str, Any]],
    selector_cfg: Mapping[str, Any],
    source: str,
    error: str,
) -> dict[str, Any]:
    return validate_final_selection(None, evidence=evidence, candidates=candidates, selector_cfg=selector_cfg, source=source, error=error)


def _summarize_neighbors(neighbor_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_center: dict[str, list[dict[str, Any]]] = {}
    for row in neighbor_rows:
        by_center.setdefault(str(row.get("center_trial_id")), []).append(row)
    return {center_id: _neighbor_stats(rows) for center_id, rows in by_center.items()}


def _neighbor_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [row for row in rows if row.get("status") == "ok" and _safe_float(row.get("score")) is not None]
    scores = np.array([float(row["score"]) for row in ok], dtype="float64")
    out = {
        "num_neighbors": int(len(rows)),
        "num_successful_neighbors": int(len(ok)),
        "neighbor_scores": [float(x) for x in scores.tolist()],
        "score_mean": math.nan,
        "score_std": math.nan,
        "score_min": math.nan,
        "score_p25": math.nan,
        "score_max": math.nan,
    }
    if scores.size:
        out.update(
            {
                "score_mean": float(scores.mean()),
                "score_std": float(scores.std(ddof=1)) if scores.size > 1 else 0.0,
                "score_min": float(scores.min()),
                "score_p25": float(np.quantile(scores, 0.25)),
                "score_max": float(scores.max()),
            }
        )
    for key in ["valid_rmse", "mean_rankic", "rankic_ir", "positive_window_ratio", "top_bottom_spread", "overfit_penalty", "complexity_penalty"]:
        values = np.array([float(row[key]) for row in ok if _safe_float(row.get(key)) is not None], dtype="float64")
        if values.size:
            out[f"{key}_mean"] = float(values.mean())
    return out


def _empty_neighbor_summary() -> dict[str, Any]:
    return {
        "num_neighbors": 0,
        "num_successful_neighbors": 0,
        "neighbor_scores": [],
        "score_mean": math.nan,
        "score_std": math.nan,
        "score_min": math.nan,
        "score_p25": math.nan,
        "score_max": math.nan,
    }


def _compact_trial(row: Mapping[str, Any]) -> dict[str, Any]:
    out = {key: row.get(key) for key in TRIAL_METRIC_KEYS if key in row}
    params = row.get("params")
    if params is None and row.get("params_json"):
        try:
            params = json.loads(str(row.get("params_json")))
        except Exception:
            params = None
    if params is not None:
        out["params"] = dict(params)
    return out


def _clean_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _clean_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_clean_json_value(item) for item in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    return value


def _make_neighbor_params(
    center_params: Mapping[str, Any],
    *,
    search_space: Mapping[str, Mapping[str, Any]],
    model_type: str,
    selector_cfg: Mapping[str, Any],
    freeze_params: set[str],
    rng: np.random.Generator,
) -> dict[str, Any]:
    params = copy.deepcopy(dict(center_params))
    changed = False
    mutable_names = [name for name in search_space if name in params and name not in freeze_params]
    rng.shuffle(mutable_names)
    for name in mutable_names:
        spec = search_space[name]
        kind = str(spec.get("type"))
        current = params.get(name)
        if kind == "choice":
            if rng.random() > float(selector_cfg["choice_perturb_probability"]):
                continue
            new_value = _neighbor_choice(current, spec, int(selector_cfg["choice_neighbor_steps"]), rng)
        elif kind in {"uniform", "quniform", "loguniform", "qloguniform"}:
            if rng.random() > float(selector_cfg["numeric_perturb_probability"]):
                continue
            new_value = _neighbor_numeric(current, spec, selector_cfg, rng)
        else:
            continue
        if new_value != current:
            params[name] = new_value
            changed = True

    if not changed and mutable_names:
        name = mutable_names[0]
        spec = search_space[name]
        current = params.get(name)
        kind = str(spec.get("type"))
        if kind == "choice":
            params[name] = _neighbor_choice(current, spec, int(selector_cfg["choice_neighbor_steps"]), rng)
        elif kind in {"uniform", "quniform", "loguniform", "qloguniform"}:
            params[name] = _neighbor_numeric(current, spec, selector_cfg, rng)
    return normalize_model_params(model_type, params)


def _neighbor_choice(current: Any, spec: Mapping[str, Any], steps: int, rng: np.random.Generator) -> Any:
    values = list(spec.get("values") or [])
    if len(values) <= 1:
        return copy.deepcopy(current)
    idx = _choice_index(values, current)
    if idx is None:
        return copy.deepcopy(current)
    low = max(0, idx - steps)
    high = min(len(values) - 1, idx + steps)
    candidates = [pos for pos in range(low, high + 1) if pos != idx]
    if not candidates:
        return copy.deepcopy(current)
    return copy.deepcopy(values[int(rng.choice(candidates))])


def _neighbor_numeric(current: Any, spec: Mapping[str, Any], selector_cfg: Mapping[str, Any], rng: np.random.Generator) -> float:
    kind = str(spec.get("type"))
    low = float(spec["low"])
    high = float(spec["high"])
    value = _safe_float(current)
    if value is None:
        value = (low + high) / 2.0
    value = min(max(value, low), high)
    if "log" in kind:
        log_low = math.log(low)
        log_high = math.log(high)
        log_value = min(max(math.log(max(value, low)), log_low), log_high)
        proposal = math.exp(log_value + float(rng.uniform(-float(selector_cfg["log_numeric_radius"]), float(selector_cfg["log_numeric_radius"]))))
    else:
        width = high - low
        proposal = value + float(rng.uniform(-width * float(selector_cfg["numeric_radius"]), width * float(selector_cfg["numeric_radius"])))
    proposal = min(max(float(proposal), low), high)
    if kind in {"quniform", "qloguniform"}:
        proposal = _quantize(proposal, spec)
    return proposal


def _choice_index(values: list[Any], current: Any) -> int | None:
    for idx, value in enumerate(values):
        if value == current:
            return idx
    return None


def _quantize(value: float, spec: Mapping[str, Any]) -> float:
    q = float(spec.get("q", 1.0))
    low = float(spec["low"])
    high = float(spec["high"])
    if q <= 0:
        raise ConfigError("quantized search space requires q > 0")
    quantized = low + round((float(value) - low) / q) * q
    return float(min(max(quantized, low), high))


def _params_key(params: Mapping[str, Any]) -> str:
    return json.dumps(params, ensure_ascii=False, sort_keys=True, default=str)


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if np.isfinite(out) else None


def _positive_int(value: Any, name: str) -> int:
    try:
        out = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a positive integer") from exc
    if out <= 0:
        raise ConfigError(f"{name} must be a positive integer")
    return out


def _positive_float(value: Any, name: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a positive number") from exc
    if out <= 0 or not np.isfinite(out):
        raise ConfigError(f"{name} must be a positive number")
    return out


def _non_negative_float(value: Any, name: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be non-negative") from exc
    if out < 0 or not np.isfinite(out):
        raise ConfigError(f"{name} must be non-negative")
    return out


def _probability(value: Any, name: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be in [0, 1]") from exc
    if not 0.0 <= out <= 1.0:
        raise ConfigError(f"{name} must be in [0, 1]")
    return out
