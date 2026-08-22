"""Explicit, auditable holdout evaluation for one frozen HPO result."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config_utils import file_sha256, load_config, write_json
from data_adapter import build_holdout_test_window, build_panel
from holdout_evaluator import evaluate_holdout
from plugin_loader import configure_extensions
from search_runner import _resolve_core_config


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _append_access_log(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def run_holdout_evaluation(
    *,
    source_run_dir: Path,
    output_dir: Path,
    seed: int | None,
) -> dict[str, Any]:
    source_run_dir = source_run_dir.expanduser().resolve()
    config_path = source_run_dir / "resolved_config.yaml"
    params_path = source_run_dir / "best_params.json"
    if not config_path.exists() or not params_path.exists():
        raise FileNotFoundError(
            "Source run must contain resolved_config.yaml and best_params.json"
        )
    cfg = _resolve_core_config(load_config(config_path))
    cfg["_run_phase"] = "holdout"
    configure_extensions(cfg)
    best_params = _read_json(params_path)
    model_type = str(best_params["model_type"])
    params = dict(best_params["params"])
    evaluation_seed = int(
        seed if seed is not None else cfg.get("task", {}).get("seed", 42)
    )
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    access_time = datetime.now(timezone.utc).isoformat()
    access_manifest = {
        "source_run_dir": str(source_run_dir),
        "output_dir": str(output_dir),
        "access_time_utc": access_time,
        "selected_trial_id": best_params.get("trial_id"),
        "selected_params_sha256": file_sha256(params_path),
        "resolved_config_sha256": file_sha256(config_path),
        "model_type": model_type,
        "seed": evaluation_seed,
        "status": "holdout_access_started",
    }
    write_json(access_manifest, output_dir / "holdout_access_manifest.json")
    _append_access_log(source_run_dir / "holdout_access_log.jsonl", access_manifest)

    panel_data = build_panel(cfg)
    holdout_window = build_holdout_test_window(panel_data.panel, cfg)
    if holdout_window is None:
        raise ValueError(
            "Holdout evaluation requires validation.method=fixed_train_valid_test"
        )
    normalize_method = cfg.get("search", {}).get("normalize_method")
    summary, predictions, window_metrics = evaluate_holdout(
        panel_data=panel_data,
        holdout_window=holdout_window,
        model_type=model_type,
        params=params,
        cfg=cfg,
        seed=evaluation_seed,
        normalize_method=str(normalize_method) if normalize_method else None,
    )
    write_json(summary, output_dir / "final_holdout_metrics.json")
    predictions.to_csv(output_dir / "final_holdout_predictions.csv", index=False)
    window_metrics.to_csv(
        output_dir / "final_holdout_window_metrics.csv",
        index=False,
    )
    completed = dict(access_manifest)
    completed["status"] = "holdout_evaluated"
    completed["metrics_path"] = "final_holdout_metrics.json"
    write_json(completed, output_dir / "holdout_access_manifest.json")
    _append_access_log(source_run_dir / "holdout_access_log.jsonl", completed)
    return completed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate one frozen HPO result on the configured holdout"
    )
    parser.add_argument("--source-run-dir", required=True)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--confirm-holdout-access",
        action="store_true",
        help="Required acknowledgement that test labels will be accessed",
    )
    args = parser.parse_args(argv)
    if not args.confirm_holdout_access:
        parser.error("--confirm-holdout-access is required")
    source_run_dir = Path(args.source_run_dir).expanduser().resolve()
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_dir = source_run_dir / "holdout_evaluations" / stamp
    result = run_holdout_evaluation(
        source_run_dir=source_run_dir,
        output_dir=output_dir,
        seed=args.seed,
    )
    print(f"source_run_dir: {result['source_run_dir']}")
    print(f"output_dir: {result['output_dir']}")
    print(f"status: {result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
