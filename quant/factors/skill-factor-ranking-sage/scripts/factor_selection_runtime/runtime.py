"""Run either upstream mRMR or upstream SAGE factor selection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config_utils import load_config
from .data_adapter import build_panel
from .mrmr_method import run_mrmr
from .reporter import create_run_dir, write_artifacts
from .sage_method import run_sage
from .window_builder import build_windows


def run_factor_selection(config_path: str | Path) -> dict[str, Any]:
    cfg = load_config(config_path)
    data = build_panel(cfg)
    windows = build_windows(data.panel, cfg)
    if len(windows) != 1:
        raise ValueError("Exactly one fixed train/validation split is required")
    window = windows[0]
    train = data.panel[data.panel["date"].isin(window.train_dates)].reset_index(drop=True)
    valid = data.panel[data.panel["date"].isin(window.valid_dates)].reset_index(drop=True)

    count = min(int(cfg["selection_count"]), len(data.feature_columns))
    mode = str(cfg["mode"])
    frames = {}
    method_metadata: dict[str, Any] = {}
    if mode == "mrmr":
        selected, ranking, redundancy = run_mrmr(
            train, data.feature_columns, count, cfg
        )
        frames["mrmr_ranking.csv"] = ranking
        frames["mrmr_redundancy_matrix.csv"] = redundancy
    else:
        selected, ranking, method_metadata = run_sage(
            train, valid, data.feature_columns, count, cfg
        )
        frames["sage_values.csv"] = ranking

    selected_set = set(selected)
    result = {
        "mode": mode,
        "selected_factors": selected,
        "rejected_factors": [
            {"factor": factor, "reason": f"not_in_top_{count}_{mode}"}
            for factor in data.feature_columns
            if factor not in selected_set
        ],
        "selection_count": count,
        "selection_basis": "local-standard-mrmr" if mode == "mrmr" else "local-marginal-sage",
    }
    run_id, run_dir = create_run_dir(cfg)
    manifest = write_artifacts(
        run_id,
        run_dir,
        cfg,
        data.metadata,
        window,
        data.warnings,
        frames,
        result,
        method_metadata,
    )
    return {
        **manifest,
        "run_dir": str(run_dir),
        "mode": mode,
        "selected_factors": selected,
    }
