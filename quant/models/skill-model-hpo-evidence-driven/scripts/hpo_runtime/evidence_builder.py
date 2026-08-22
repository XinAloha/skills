"""Build structured trial evidence for adaptive search-space control."""

from __future__ import annotations

import json
import math
from collections import Counter
from typing import Any, Mapping

import numpy as np
import pandas as pd


NUMERIC_SPACE_TYPES = {"uniform", "loguniform", "quniform", "qloguniform"}


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _parse_params(raw: Any) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        return dict(raw)
    if raw in (None, ""):
        return {}
    try:
        loaded = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return dict(loaded) if isinstance(loaded, Mapping) else {}


def _top_ok_rows(leaderboard: pd.DataFrame, top_fraction: float) -> pd.DataFrame:
    ok = leaderboard[leaderboard["status"] == "ok"].copy()
    ok["score"] = pd.to_numeric(ok["score"], errors="coerce")
    ok = ok[np.isfinite(ok["score"])].sort_values("score", ascending=False)
    if ok.empty:
        return ok
    count = max(1, int(math.ceil(len(ok) * top_fraction)))
    return ok.head(min(count, len(ok)))


def _row_params(row: pd.Series) -> dict[str, Any]:
    if "params" in row and isinstance(row["params"], Mapping):
        return dict(row["params"])
    return _parse_params(row.get("params_json"))


def _metric_snapshot(row: pd.Series) -> dict[str, Any]:
    keys = [
        "score",
        "objective_score",
        "valid_rmse",
        "valid_mae",
        "valid_r2",
        "window_train_rmse",
        "window_valid_rmse",
        "fast_score",
        "objective",
        "mean_rankic",
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
        "complexity_penalty",
        "overfit_penalty",
    ]
    objective = str(row.get("objective") or "").lower()
    if objective == "rmse":
        keys = [
            "score",
            "objective_score",
            "valid_rmse",
            "valid_mae",
            "valid_r2",
            "window_train_rmse",
            "window_valid_rmse",
            "objective",
        ]
    snapshot: dict[str, Any] = {}
    for key in keys:
        if key not in row:
            continue
        if key == "objective":
            snapshot[key] = row.get(key)
        else:
            snapshot[key] = _safe_float(row.get(key))
    return snapshot


def _choice_evidence(name: str, spec: Mapping[str, Any], top_params: list[dict[str, Any]]) -> dict[str, Any]:
    allowed = list(spec.get("values", []))
    allowed_by_key = {_canonical(value): value for value in allowed}
    values = [params[name] for params in top_params if name in params]
    counts = Counter(_canonical(value) for value in values)
    sorted_counts = counts.most_common()
    top_values = [allowed_by_key.get(key, key) for key, _ in sorted_counts]
    total = sum(counts.values())
    concentration = (sorted_counts[0][1] / total) if total and sorted_counts else None
    first_key = _canonical(allowed[0]) if allowed else None
    last_key = _canonical(allowed[-1]) if allowed else None
    return {
        "type": "choice",
        "space": {"values": allowed},
        "observed_top_values": values,
        "value_counts": {key: int(count) for key, count in sorted_counts},
        "ranked_values": top_values,
        "best_value": values[0] if values else None,
        "concentration": _safe_float(concentration),
        "boundary_hit_low": bool(sorted_counts and sorted_counts[0][0] == first_key),
        "boundary_hit_high": bool(sorted_counts and sorted_counts[0][0] == last_key),
    }


def _numeric_evidence(name: str, spec: Mapping[str, Any], top_params: list[dict[str, Any]], boundary_margin: float) -> dict[str, Any]:
    low = float(spec["low"])
    high = float(spec["high"])
    values = np.array(
        [
            float(params[name])
            for params in top_params
            if name in params and _safe_float(params[name]) is not None
        ],
        dtype="float64",
    )
    if values.size == 0:
        return {
            "type": str(spec.get("type")),
            "space": {"low": low, "high": high, "q": spec.get("q")},
            "top_values": [],
            "boundary_hit_low": False,
            "boundary_hit_high": False,
        }
    q20, q50, q80 = np.quantile(values, [0.2, 0.5, 0.8])
    span = high - low
    margin = max(0.0, min(0.5, boundary_margin)) * span
    return {
        "type": str(spec.get("type")),
        "space": {"low": low, "high": high, "q": spec.get("q")},
        "top_values": [_safe_float(value) for value in values.tolist()],
        "top_min": _safe_float(np.min(values)),
        "top_max": _safe_float(np.max(values)),
        "top_q20": _safe_float(q20),
        "top_median": _safe_float(q50),
        "top_q80": _safe_float(q80),
        "top_mean": _safe_float(np.mean(values)),
        "top_std": _safe_float(np.std(values, ddof=1)) if values.size > 1 else 0.0,
        "relative_width": _safe_float((float(np.max(values)) - float(np.min(values))) / span) if span > 0 else None,
        "boundary_hit_low": bool(float(np.mean(values)) <= low + margin),
        "boundary_hit_high": bool(float(np.mean(values)) >= high - margin),
    }


def _score_stats(leaderboard: pd.DataFrame, round_id: int) -> dict[str, Any]:
    ok = leaderboard[leaderboard["status"] == "ok"].copy()
    ok["score"] = pd.to_numeric(ok["score"], errors="coerce")
    ok = ok[np.isfinite(ok["score"])]
    if ok.empty:
        return {
            "best_score": None,
            "score_mean": None,
            "score_std": None,
            "round_best_score": None,
            "previous_best_score": None,
            "score_improvement_over_previous_round": None,
        }
    previous = ok[ok.get("round_id", -1) < round_id]
    current = ok[ok.get("round_id", -1) == round_id]
    best_score = float(ok["score"].max())
    previous_best = float(previous["score"].max()) if not previous.empty else None
    round_best = float(current["score"].max()) if not current.empty else None
    improvement = None
    if previous_best is not None and round_best is not None:
        improvement = round_best - previous_best
    return {
        "best_score": _safe_float(best_score),
        "score_mean": _safe_float(ok["score"].mean()),
        "score_std": _safe_float(ok["score"].std(ddof=1)) if len(ok) > 1 else 0.0,
        "round_best_score": _safe_float(round_best),
        "previous_best_score": _safe_float(previous_best),
        "score_improvement_over_previous_round": _safe_float(improvement),
    }



def _round_best_history(leaderboard: pd.DataFrame) -> list[dict[str, Any]]:
    ok = leaderboard[leaderboard["status"] == "ok"].copy()
    if ok.empty or "round_id" not in ok:
        return []
    ok["score"] = pd.to_numeric(ok["score"], errors="coerce")
    ok = ok[np.isfinite(ok["score"])]
    if ok.empty:
        return []
    rows: list[dict[str, Any]] = []
    cumulative_best: float | None = None
    previous_cumulative: float | None = None
    for raw_round_id in sorted(ok["round_id"].dropna().unique()):
        current = ok[ok["round_id"] == raw_round_id].sort_values("score", ascending=False)
        if current.empty:
            continue
        best = current.iloc[0]
        round_best = _safe_float(best.get("score"))
        if round_best is None:
            continue
        improved = cumulative_best is None or round_best > cumulative_best
        if improved:
            cumulative_best = round_best
        improvement = None
        if previous_cumulative is not None:
            improvement = cumulative_best - previous_cumulative
        previous_cumulative = cumulative_best
        rows.append(
            {
                "round_id": int(raw_round_id),
                "num_ok_trials": int(len(current)),
                "round_best_trial_id": best.get("trial_id"),
                "round_best_score": round_best,
                "round_best_valid_rmse": _safe_float(best.get("valid_rmse")),
                "cumulative_best_score": _safe_float(cumulative_best),
                "cumulative_best_valid_rmse": _safe_float(best.get("valid_rmse")) if improved else None,
                "score_improvement_vs_previous_cumulative": _safe_float(improvement),
            }
        )
    return rows


def _top_score_diagnostics(top_rows: pd.DataFrame, ok_rows: pd.DataFrame) -> dict[str, Any]:
    if top_rows.empty:
        return {
            "top_score_gap_to_second": None,
            "top_score_gap_to_median": None,
            "top_score_range": None,
            "best_trial_isolated": False,
        }
    top_scores = pd.to_numeric(top_rows["score"], errors="coerce").dropna().to_numpy(dtype="float64")
    ok_scores = pd.to_numeric(ok_rows.get("score", pd.Series(dtype="float64")), errors="coerce").dropna().to_numpy(dtype="float64")
    if top_scores.size == 0:
        return {
            "top_score_gap_to_second": None,
            "top_score_gap_to_median": None,
            "top_score_range": None,
            "best_trial_isolated": False,
        }
    best = float(top_scores[0])
    second = float(top_scores[1]) if top_scores.size > 1 else None
    median = float(np.median(top_scores))
    gap_second = best - second if second is not None else None
    gap_median = best - median
    score_std = float(np.std(ok_scores, ddof=1)) if ok_scores.size > 1 else 0.0
    isolation_threshold = max(score_std, abs(best) * 1e-4, 1e-12)
    return {
        "top_score_gap_to_second": _safe_float(gap_second),
        "top_score_gap_to_median": _safe_float(gap_median),
        "top_score_range": _safe_float(float(np.max(top_scores)) - float(np.min(top_scores))) if top_scores.size else None,
        "all_ok_score_std": _safe_float(score_std),
        "best_trial_isolated": bool(gap_second is not None and gap_second > isolation_threshold),
        "isolation_threshold": _safe_float(isolation_threshold),
    }


def _boundary_param_summary(param_evidence: Mapping[str, Any]) -> dict[str, Any]:
    low: list[str] = []
    high: list[str] = []
    for name, item in param_evidence.items():
        if not isinstance(item, Mapping):
            continue
        if item.get("boundary_hit_low"):
            low.append(str(name))
        if item.get("boundary_hit_high"):
            high.append(str(name))
    any_params = sorted(set(low + high))
    return {
        "boundary_hit_low_params": low,
        "boundary_hit_high_params": high,
        "boundary_hit_any_params": any_params,
        "num_boundary_params": int(len(any_params)),
    }


def _probe_evidence(leaderboard: pd.DataFrame) -> dict[str, Any]:
    if leaderboard.empty or "probe_type" not in leaderboard:
        return {}
    ok = leaderboard[leaderboard["status"] == "ok"].copy()
    if ok.empty:
        return {}
    ok["score"] = pd.to_numeric(ok["score"], errors="coerce")
    ok = ok[np.isfinite(ok["score"])]
    ok = ok[ok["probe_type"].notna()]
    if ok.empty:
        return {}

    metrics = [
        "score",
        "valid_rmse",
        "mean_rankic",
        "rankic_ir",
        "top_bottom_spread",
        "positive_window_ratio",
        "turnover_proxy",
        "overfit_penalty",
    ]
    evidence: dict[str, Any] = {}
    for raw_probe_type, group in ok.groupby("probe_type", dropna=True):
        probe_type = str(raw_probe_type)
        if not probe_type:
            continue
        ordered = group.sort_values("score", ascending=False)
        best = ordered.iloc[0]
        metric_summary: dict[str, Any] = {}
        for key in metrics:
            if key not in ordered:
                continue
            values = pd.to_numeric(ordered[key], errors="coerce").dropna()
            if values.empty:
                continue
            metric_summary[key] = {
                "mean": _safe_float(values.mean()),
                "min": _safe_float(values.min()),
                "max": _safe_float(values.max()),
            }
        evidence[probe_type] = {
            "num_trials": int(len(ordered)),
            "best_trial_id": best.get("trial_id"),
            "best_round_id": int(best.get("round_id", -1)),
            "best_score": _safe_float(best.get("score")),
            "mean_score": _safe_float(ordered["score"].mean()),
            "score_std": _safe_float(ordered["score"].std(ddof=1)) if len(ordered) > 1 else 0.0,
            "best_metrics": _metric_snapshot(best),
            "metric_summary": metric_summary,
        }
    return evidence


def build_trial_evidence(
    *,
    round_id: int,
    model_type: str,
    current_space: Mapping[str, Any],
    leaderboard: pd.DataFrame,
    diagnostics: Mapping[str, Any] | None = None,
    top_fraction: float = 0.30,
    boundary_margin: float = 0.15,
) -> dict[str, Any]:
    """Summarize trial outcomes into JSON-serializable evidence.

    The evidence intentionally focuses on search-control signals: top-trial
    parameter concentration, boundary pressure, score improvement, and failure
    modes. It does not make decisions.
    """
    if leaderboard.empty:
        return {
            "round_id": int(round_id),
            "model_type": model_type,
            "num_trials_total": 0,
            "num_ok_trials_total": 0,
            "num_failed_trials_total": 0,
            "param_evidence": {},
            "probe_evidence": {},
            "diagnostics": dict(diagnostics or {}),
        }
    work = leaderboard.copy()
    if "round_id" not in work:
        work["round_id"] = -1
    ok_mask = work["status"] == "ok"
    top_rows = _top_ok_rows(work, top_fraction=top_fraction)
    top_params = [_row_params(row) for _, row in top_rows.iterrows()]
    param_evidence: dict[str, Any] = {}
    for name, spec in current_space.items():
        kind = str(spec.get("type"))
        if kind == "choice":
            param_evidence[name] = _choice_evidence(name, spec, top_params)
        elif kind in NUMERIC_SPACE_TYPES:
            param_evidence[name] = _numeric_evidence(name, spec, top_params, boundary_margin=boundary_margin)

    best_row = top_rows.iloc[0] if not top_rows.empty else None
    best_score = _safe_float(best_row.get("score")) if best_row is not None else None
    score_stats = _score_stats(work, round_id)
    top_trials = []
    for _, row in top_rows.head(10).iterrows():
        top_trials.append(
            {
                "trial_id": row.get("trial_id"),
                "round_id": int(row.get("round_id", -1)),
                "sampler": row.get("sampler"),
                "probe_type": row.get("probe_type"),
                "probe_applied": bool(row.get("probe_applied")) if "probe_applied" in row else None,
                "metrics": _metric_snapshot(row),
                "params": _row_params(row),
            }
        )
    return {
        "round_id": int(round_id),
        "model_type": model_type,
        "score_semantics": "higher_is_better; rmse objective uses negative validation RMSE; IC objectives use raw IC/IR values",
        "num_trials_total": int(len(work)),
        "num_trials_round": int((work["round_id"] == round_id).sum()),
        "num_ok_trials_total": int(ok_mask.sum()),
        "num_failed_trials_total": int((~ok_mask).sum()),
        "top_fraction": float(top_fraction),
        "best_trial_id": best_row.get("trial_id") if best_row is not None else None,
        "best_score": best_score,
        **score_stats,
        "round_best_history": _round_best_history(work),
        "top_score_diagnostics": _top_score_diagnostics(top_rows, work[ok_mask].copy()),
        "boundary_param_summary": _boundary_param_summary(param_evidence),
        "probe_evidence": _probe_evidence(work),
        "top_trials": top_trials,
        "param_evidence": param_evidence,
        "diagnostics": dict(diagnostics or {}),
    }
