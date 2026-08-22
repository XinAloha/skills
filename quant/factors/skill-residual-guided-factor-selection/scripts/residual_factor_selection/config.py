from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


PATH_KEYS = {
    "panel_path",
    "bar_dir",
    "label_path",
    "alpha158_source_dir",
    "alpha_formula_source_repo",
    "formula_source_repo",
    "factor_dir",
    "factor_manifest",
    "feature_store_path",
    "prepared_feature_cache",
    "checkpoint_path",
    "resume_history",
    "root",
}


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Configuration root must be a mapping")
    resolved = deepcopy(config)
    for section in resolved.values():
        if not isinstance(section, dict):
            continue
        for key, value in list(section.items()):
            if key in PATH_KEYS and value is not None:
                candidate = Path(value).expanduser()
                section[key] = str(candidate if candidate.is_absolute() else (config_path.parent / candidate).resolve())
    return resolved


def validate_config(config: dict[str, Any], command: str) -> None:
    if "data" not in config:
        raise ValueError("Missing required configuration section: data")
    if command == "materialize":
        return
    required_sections = ("split", "universe", "preprocess", "model", "selection", "beam", "output")
    missing = [name for name in required_sections if name not in config]
    if missing:
        raise ValueError(f"Missing required configuration sections: {missing}")

    split = config["split"]
    required_split = ("train_start", "train_end", "valid_start", "valid_end", "oos_start", "embargo_bars")
    missing_split = [name for name in required_split if name not in split]
    if missing_split:
        raise ValueError(f"Missing required split fields: {missing_split}")
    train_start = pd.Timestamp(split["train_start"])
    train_end = pd.Timestamp(split["train_end"])
    valid_start = pd.Timestamp(split["valid_start"])
    valid_end = pd.Timestamp(split["valid_end"])
    oos_start = pd.Timestamp(split["oos_start"])
    if not train_start <= train_end < valid_start <= valid_end < oos_start:
        raise ValueError("Expected Train < Valid < OOS with non-overlapping date ranges")
    if split.get("oos_end") is not None and pd.Timestamp(split["oos_end"]) < oos_start:
        raise ValueError("split.oos_end must not precede split.oos_start")
    if int(split["embargo_bars"]) < 0:
        raise ValueError("split.embargo_bars must be non-negative")

    coverage = float(config["universe"]["train_label_min_coverage"])
    if not 0.0 <= coverage <= 1.0:
        raise ValueError("universe.train_label_min_coverage must be between zero and one")

    model_type = config["model"].get("type", "ridge")
    if model_type not in {"ridge", "lgbm"}:
        raise ValueError(f"Unsupported model.type: {model_type}")
    if model_type == "lgbm" and command not in {
        "run-beam",
        "run-many-beam",
        "evaluate-oos",
        "validate-cache",
    }:
        raise ValueError("model.type=lgbm is supported only by Beam search and OOS evaluation")
    if command == "run-pool" and model_type != "ridge":
        raise ValueError("run-pool requires model.type=ridge")
    if command == "run-pool" and "pool" not in config:
        raise ValueError("Missing required configuration section: pool")

    development_start = train_start
    development_end = valid_end
    for fold in config["beam"].get("cv_folds", []):
        required_fold = ("fit_start", "fit_end", "score_start", "score_end")
        missing_fold = [name for name in required_fold if name not in fold]
        if missing_fold:
            raise ValueError(f"Missing temporal CV fold fields: {missing_fold}")
        fit_start = pd.Timestamp(fold["fit_start"])
        fit_end = pd.Timestamp(fold["fit_end"])
        score_start = pd.Timestamp(fold["score_start"])
        score_end = pd.Timestamp(fold["score_end"])
        if not development_start <= fit_start <= fit_end < score_start <= score_end <= development_end:
            raise ValueError(f"Temporal CV fold is outside the development period or overlaps: {fold}")

    if command in {"run-beam", "run-many-beam", "run-pool"} and not config["beam"].get("cv_folds"):
        raise ValueError(f"{command} requires at least one beam.cv_folds entry")
