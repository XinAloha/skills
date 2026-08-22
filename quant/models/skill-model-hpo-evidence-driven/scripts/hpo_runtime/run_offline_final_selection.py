"""Offline Codex-external final selection for an existing search run.

This script reuses an existing search run's validation trials and config, runs
local neighborhood checks around top candidates, requests a Codex-external
selection when configured, and writes frozen selected parameters without
accessing holdout labels. It does not rerun the original search rounds.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from config_utils import json_default, load_config, write_json, write_resolved_config
from data_adapter import build_panel, build_windows
from decision_provider import ExternalDecisionRequired, request_final_selection_with_provider, resolve_decision_provider_config
from final_selector import (
    build_final_selection_evidence,
    build_neighbor_plan,
    fallback_final_selection,
    resolve_final_selector_config,
    select_center_candidates,
    validate_final_selection,
)
from plugin_loader import configure_extensions
from search_runner import (
    _leaderboard_from_history,
    _mapping,
    _resolve_core_config,
    _run_one_trial,
    _run_seed_confirmation,
)
from search_space import resolve_model_type, resolve_search_space


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_trials_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {path}:{line_no}: {exc}") from exc
        if isinstance(row, dict):
            rows.append(row)
    if not rows:
        raise ValueError(f"No trial rows found in {path}")
    return rows


def _make_run_id(source_run_dir: Path, prefix: str) -> str:
    source_name = source_run_dir.name
    return f"{prefix}_{source_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"


def _resolve_output_dir(args: argparse.Namespace, source_run_dir: Path) -> Path:
    if args.output_dir:
        return Path(args.output_dir).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve()
    return output_root / _make_run_id(source_run_dir, args.run_prefix)


def _final_space(source_run_dir: Path, cfg: Mapping[str, Any], model_type: str) -> dict[str, Any]:
    versions_path = source_run_dir / "search_space_versions.json"
    if versions_path.exists():
        versions = _read_json(versions_path)
        if isinstance(versions, list) and versions:
            space = versions[-1].get("space")
            if isinstance(space, dict) and space:
                return space
    return resolve_search_space(cfg, model_type)


def _apply_selector_overrides(selector_cfg: dict[str, Any], args: argparse.Namespace, model_type: str) -> dict[str, Any]:
    selector_cfg = dict(selector_cfg)
    selector_cfg["enabled"] = True
    overrides = {
        "top_k": args.top_k,
        "neighbors_per_candidate": args.neighbors_per_candidate,
        "max_extra_trials": args.max_extra_trials,
        "numeric_radius": args.numeric_radius,
        "log_numeric_radius": args.log_numeric_radius,
        "choice_neighbor_steps": args.choice_neighbor_steps,
        "min_neighbor_success": args.min_neighbor_success,
        "max_score_drop": args.max_score_drop,
        "max_all_trials_in_prompt": args.max_all_trials_in_prompt,
    }
    for key, value in overrides.items():
        if value is not None:
            selector_cfg[key] = value
    return resolve_final_selector_config(selector_cfg, model_type=model_type)


def _source_metadata(source_run_dir: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"source_run_dir": str(source_run_dir)}
    for name, key in [
        ("run_summary.json", "source_run_summary"),
        ("best_params.json", "source_best_params"),
    ]:
        path = source_run_dir / name
        if path.exists():
            out[key] = _read_json(path)
    best = out.get("source_best_params") if isinstance(out.get("source_best_params"), dict) else {}
    out.update(
        {
            "source_best_trial_id": best.get("trial_id"),
            "source_best_score": best.get("score"),
        }
    )
    return out


def run_offline_final_selection(
    *,
    source_run_dir: Path,
    output_dir: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    source_run_dir = source_run_dir.expanduser().resolve()
    if not source_run_dir.exists():
        raise FileNotFoundError(f"source run dir does not exist: {source_run_dir}")
    config_path = source_run_dir / "resolved_config.yaml"
    trials_path = source_run_dir / "trials.jsonl"
    if not config_path.exists():
        raise FileNotFoundError(f"source run is missing resolved_config.yaml: {config_path}")
    if not trials_path.exists():
        raise FileNotFoundError(f"source run is missing trials.jsonl: {trials_path}")

    raw_cfg = load_config(config_path)
    cfg = _resolve_core_config(raw_cfg)
    configure_extensions(cfg)
    model_type = resolve_model_type(cfg)
    seed = int(cfg.get("task", {}).get("seed", 42))
    search_cfg = _mapping(cfg.get("search"))
    normalize_method = search_cfg.get("normalize_method")
    selector_cfg = _apply_selector_overrides(dict(_mapping(cfg.get("final_selector"))), args, model_type)
    cfg["final_selector"] = selector_cfg

    output_dir.mkdir(parents=True, exist_ok=True)
    decision_provider_config = resolve_decision_provider_config(cfg, run_dir=output_dir)
    cfg["decision_provider"] = decision_provider_config
    write_resolved_config(cfg, output_dir / "resolved_config.yaml")

    source_meta = _source_metadata(source_run_dir)
    write_json(source_meta, output_dir / "source_run.json")

    trial_history = _read_trials_jsonl(trials_path)
    leaderboard = _leaderboard_from_history(trial_history)
    leaderboard.to_csv(output_dir / "source_trial_leaderboard.csv", index=False)

    score_best_candidates = select_center_candidates(trial_history, top_k=1)
    if not score_best_candidates:
        raise ValueError("source run has no successful trial candidates")
    score_best_trial = score_best_candidates[0]
    score_best_params = {
        "model_type": model_type,
        "trial_id": score_best_trial["trial_id"],
        "objective": score_best_trial.get("objective"),
        "score": score_best_trial["score"],
        "loss": score_best_trial.get("loss"),
        "valid_rmse": score_best_trial.get("valid_rmse"),
        "valid_mae": score_best_trial.get("valid_mae"),
        "valid_r2": score_best_trial.get("valid_r2"),
        "fast_score": score_best_trial.get("fast_score"),
        "params": score_best_trial["params"],
    }
    write_json(score_best_params, output_dir / "score_best_params.json")

    panel_data = build_panel(cfg)
    windows = build_windows(panel_data.panel, cfg)
    space = _final_space(source_run_dir, cfg, model_type)

    center_candidates = select_center_candidates(trial_history, top_k=int(selector_cfg["top_k"]))
    final_rng = np.random.default_rng(seed + int(args.seed_offset))
    neighbor_plan = build_neighbor_plan(
        center_candidates,
        search_space=space,
        model_type=model_type,
        selector_cfg=selector_cfg,
        rng=final_rng,
    )

    final_neighbor_rows: list[dict[str, Any]] = []
    final_neighbor_window_metric_frames: list[pd.DataFrame] = []
    for final_index, item in enumerate(neighbor_plan):
        row, _, window_metrics = _run_one_trial(
            trial_id=str(item["neighbor_trial_id"]),
            trial_index=len(trial_history) + final_index,
            model_type=model_type,
            params=item["params"],
            panel_data=panel_data,
            windows=windows,
            cfg=cfg,
            seed=seed + 8_000_003,
            normalize_method=normalize_method,
        )
        row["center_trial_id"] = item["center_trial_id"]
        row["center_rank"] = item["center_rank"]
        row["center_score"] = item["center_score"]
        row["neighbor_index"] = item["neighbor_index"]
        row["sampler"] = "offline_final_selector"
        row["probe_type"] = "neighborhood"
        row["probe_applied"] = True
        row["sample_meta"] = {
            "sampler": "offline_final_selector",
            "probe_type": "neighborhood",
            "center_trial_id": item["center_trial_id"],
            "center_rank": item["center_rank"],
            "neighbor_index": item["neighbor_index"],
        }
        final_neighbor_rows.append(row)
        if window_metrics is not None:
            window_metrics = window_metrics.copy()
            window_metrics.insert(1, "center_trial_id", item["center_trial_id"])
            window_metrics.insert(2, "neighbor_index", item["neighbor_index"])
            final_neighbor_window_metric_frames.append(window_metrics)

    final_neighbor_leaderboard = _leaderboard_from_history(final_neighbor_rows)
    final_neighbor_leaderboard.to_csv(output_dir / "final_neighbor_trials.csv", index=False)
    if final_neighbor_window_metric_frames:
        pd.concat(final_neighbor_window_metric_frames, ignore_index=True).to_csv(
            output_dir / "final_neighbor_window_metrics.csv",
            index=False,
        )
    else:
        pd.DataFrame().to_csv(output_dir / "final_neighbor_window_metrics.csv", index=False)

    final_selection_evidence = build_final_selection_evidence(
        model_type=model_type,
        objective=str(cfg.get("evaluation", {}).get("objective", "fast_score")),
        candidates=center_candidates,
        all_trials=trial_history,
        neighbor_rows=final_neighbor_rows,
        selector_cfg=selector_cfg,
    )
    write_json(final_selection_evidence, output_dir / "final_selection_evidence.json")

    try:
        raw_final_decision, final_source, final_error, final_external_paths = request_final_selection_with_provider(
            cfg=cfg,
            provider_config=decision_provider_config,
            evidence=final_selection_evidence,
        )
        if raw_final_decision is None:
            final_selection = fallback_final_selection(
                evidence=final_selection_evidence,
                candidates=center_candidates,
                selector_cfg=selector_cfg,
                source=final_source,
                error=final_error or "final_selection_provider_returned_no_decision",
            )
        else:
            final_selection = validate_final_selection(
                raw_final_decision,
                evidence=final_selection_evidence,
                candidates=center_candidates,
                selector_cfg=selector_cfg,
                source=final_source,
            )
        if final_external_paths:
            final_selection["external_paths"] = final_external_paths
    except ExternalDecisionRequired as exc:
        requirement = exc.to_dict()
        write_json(requirement, output_dir / "external_decision_required.json")
        final_selection = {
            "enabled": True,
            "status": "external_decision_required",
            "external_decision_required": requirement,
            "validated_selection": {},
            "config": dict(selector_cfg),
        }
        write_json(final_selection, output_dir / "final_selection.json")
        offline_summary = {
            "run_id": output_dir.name,
            "source_run_dir": str(source_run_dir),
            "output_dir": str(output_dir),
            "model_type": model_type,
            "status": "external_decision_required",
            "external_decision_required": requirement,
            "num_source_trials": len(trial_history),
            "num_center_candidates": len(center_candidates),
            "num_final_neighbor_trials": len(final_neighbor_rows),
            "decision_provider_type": decision_provider_config.get("type"),
            "decision_provider": dict(decision_provider_config),
        }
        write_json(offline_summary, output_dir / "offline_summary.json")
        return offline_summary
    except Exception as exc:
        final_selection = fallback_final_selection(
            evidence=final_selection_evidence,
            candidates=center_candidates,
            selector_cfg=selector_cfg,
            source="fallback",
            error=f"{type(exc).__name__}: {exc}",
        )
    write_json(final_selection, output_dir / "final_selection.json")

    candidate_by_id = {str(row.get("trial_id")): row for row in center_candidates}
    selected_trial_id = str(final_selection.get("validated_selection", {}).get("selected_trial_id") or score_best_trial["trial_id"])
    selected_trial = dict(candidate_by_id.get(selected_trial_id, score_best_trial))
    selected_trial, confirmation_summary = _run_seed_confirmation(
        trial_history=trial_history,
        initially_selected=selected_trial,
        model_type=model_type,
        panel_data=panel_data,
        windows=windows,
        cfg=cfg,
        normalize_method=normalize_method,
        run_dir=output_dir,
    )
    best_params = {
        "model_type": model_type,
        "selected_by": (
            "multi_seed_confirmation"
            if confirmation_summary.get("enabled")
            else final_selection.get("validated_selection", {}).get("selected_by", "score_best")
        ),
        "trial_id": selected_trial["trial_id"],
        "score_best_trial_id": score_best_trial["trial_id"],
        "score_best_score": score_best_trial["score"],
        "objective": selected_trial.get("objective"),
        "score": selected_trial["score"],
        "search_score": selected_trial.get("search_score", selected_trial["score"]),
        "confirmation_score": selected_trial.get("confirmation_score"),
        "confirmation": confirmation_summary,
        "loss": selected_trial.get("loss"),
        "valid_rmse": selected_trial.get("valid_rmse"),
        "valid_mae": selected_trial.get("valid_mae"),
        "valid_r2": selected_trial.get("valid_r2"),
        "fast_score": selected_trial.get("fast_score"),
        "final_selection": final_selection,
        "params": selected_trial["params"],
    }
    write_json(best_params, output_dir / "best_params.json")

    offline_summary = {
        "run_id": output_dir.name,
        "source_run_dir": str(source_run_dir),
        "output_dir": str(output_dir),
        "model_type": model_type,
        "status": "selected_not_tested",
        "num_source_trials": len(trial_history),
        "num_center_candidates": len(center_candidates),
        "num_final_neighbor_trials": len(final_neighbor_rows),
        "selected_by": best_params["selected_by"],
        "selected_trial_id": best_params["trial_id"],
        "selected_score": best_params["score"],
        "score_best_trial_id": score_best_trial["trial_id"],
        "score_best_score": score_best_trial["score"],
        "score_drop_from_best": float(score_best_trial["score"] - best_params["score"]),
        "final_selection_accepted": bool(final_selection.get("accepted")),
        "final_selection_source": final_selection.get("source"),
        "final_selection_errors": final_selection.get("validation_errors", []),
        "holdout_status": "sealed_not_loaded",
        "decision_provider_type": decision_provider_config.get("type"),
        "decision_provider": dict(decision_provider_config),
    }
    write_json(offline_summary, output_dir / "offline_summary.json")
    return offline_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run offline Codex-external final selection for an existing evidence-driven HPO search run")
    parser.add_argument("--source-run-dir", required=True, help="Existing search run directory")
    parser.add_argument("--output-root", default="auto_outputs", help="Root directory for offline outputs")
    parser.add_argument("--output-dir", default=None, help="Explicit offline output directory")
    parser.add_argument("--run-prefix", default="offline_final_selection", help="Prefix for generated run id")
    parser.add_argument("--top-k", type=int, default=None, help="Number of source top trials exposed as center candidates")
    parser.add_argument("--neighbors-per-candidate", type=int, default=None, help="Neighborhood trials per center candidate")
    parser.add_argument("--max-extra-trials", type=int, default=None, help="Maximum total neighborhood trials")
    parser.add_argument("--numeric-radius", type=float, default=None, help="Local perturbation radius for linear numeric params")
    parser.add_argument("--log-numeric-radius", type=float, default=None, help="Local perturbation radius for log numeric params")
    parser.add_argument("--choice-neighbor-steps", type=int, default=None, help="Neighbor step width for choice params")
    parser.add_argument("--min-neighbor-success", type=int, default=None, help="Minimum successful neighbors expected in evidence")
    parser.add_argument("--max-score-drop", type=float, default=None, help="Maximum validation score drop allowed for LLM-selected candidate")
    parser.add_argument("--max-all-trials-in-prompt", type=int, default=None, help="Maximum historical successful trials included in LLM evidence")
    parser.add_argument("--seed-offset", type=int, default=8_888_881, help="RNG offset for neighborhood generation")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    source_run_dir = Path(args.source_run_dir).expanduser().resolve()
    output_dir = _resolve_output_dir(args, source_run_dir)
    summary = run_offline_final_selection(
        source_run_dir=source_run_dir,
        output_dir=output_dir,
        args=args,
    )
    print(f"run_id: {summary['run_id']}")
    print(f"output_dir: {summary['output_dir']}")
    print(f"source_run_dir: {summary['source_run_dir']}")
    print(f"model_type: {summary['model_type']}")
    print(f"status: {summary['status']}")
    print(f"num_source_trials: {summary['num_source_trials']}")
    print(f"num_final_neighbor_trials: {summary['num_final_neighbor_trials']}")
    for key in [
        "selected_by",
        "selected_trial_id",
        "score_best_trial_id",
        "score_drop_from_best",
        "final_selection_accepted",
    ]:
        if key in summary:
            print(f"{key}: {summary[key]}")
    return 0 if summary.get("status") == "selected_not_tested" else 1


if __name__ == "__main__":
    raise SystemExit(main())
