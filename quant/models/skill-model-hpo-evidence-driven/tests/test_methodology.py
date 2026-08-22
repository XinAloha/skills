from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "scripts" / "hpo_runtime"
sys.path.insert(0, str(RUNTIME))

from config_utils import ConfigError
from data_adapter import (
    Window,
    _check_label_window,
    _effective_data_end,
    build_windows,
)
from extension_registry import REGISTRY
from fast_evaluator import score_predictions
from model_registry import ModelSpec
from plugin_loader import configure_extensions
from search_runner import _resolve_core_config, _run_one_trial
from trainer import _purge_training_rows, train_and_predict


class TargetIsolationPipeline:
    def __init__(self, params):
        self.params = dict(params)

    def fit(self, features, target, context, feature_columns, cfg, *, normalize_method, preserve_nan):
        assert "y" not in features
        assert "y" not in context
        assert isinstance(target, pd.Series)
        return self

    def transform(self, features, context, feature_columns, cfg, *, normalize_method, preserve_nan):
        assert "y" not in features
        assert "y" not in context
        return features[feature_columns].copy()


def _training_cfg() -> dict:
    return {
        "_config_dir": str(ROOT),
        "compatibility": {"profile": "research_v2"},
        "extensions": {},
        "features": {"pipeline": {"name": "target_isolation", "params": {}}},
        "training": {
            "label_transform": {"method": "none"},
            "sample_weight": {"method": "equal_date"},
        },
        "model_missing": {"mlp_fill_value": 0.0},
        "validation": {"min_assets_per_date": 3},
        "fast_evaluator": {"top_quantile": 0.34, "bottom_quantile": 0.34},
        "evaluation": {
            "objective": "robust_rankic",
            "robust_rankic": {
                "block": "month",
                "min_valid_dates": 1,
                "min_blocks": 1,
                "se_multiplier": 1.0,
            },
            "fast_score_weights": {
                "rankic_ir": 0.4,
                "top_bottom_spread": 0.2,
                "positive_window_ratio": 0.1,
                "turnover_proxy": 0.1,
                "complexity_penalty": 0.1,
                "overfit_penalty": 0.1,
            },
        },
        "reproducibility": {
            "trial_seed_policy": "common",
            "confirmation": {"enabled": False},
        },
    }


def test_compatibility_profiles_resolve_expected_methodology_defaults():
    legacy = _resolve_core_config({})
    research = _resolve_core_config({"compatibility": {"profile": "research_v2"}})

    assert legacy["evaluation"]["objective"] == "rankic_ir"
    assert legacy["evaluation"]["metric_policy"] == "legacy_pooled"
    assert legacy["training"]["sample_weight"]["method"] == "none"
    assert legacy["reproducibility"]["trial_seed_policy"] == "legacy_trial_index"
    assert legacy["reproducibility"]["confirmation"]["enabled"] is False
    assert legacy["data"]["strict_point_in_time"] is False
    assert legacy["holdout"]["mode"] == "automatic"

    assert research["evaluation"]["objective"] == "robust_rankic"
    assert research["evaluation"]["metric_policy"] == "cross_sectional"
    assert research["training"]["sample_weight"]["method"] == "equal_date"
    assert research["reproducibility"]["trial_seed_policy"] == "common"
    assert research["reproducibility"]["confirmation"]["enabled"] is True
    assert research["data"]["strict_point_in_time"] is True
    assert research["holdout"]["mode"] == "sealed"


def test_feature_extensions_never_receive_validation_target():
    cfg = _training_cfg()
    configure_extensions(cfg)
    REGISTRY.register_feature_pipeline("target_isolation", TargetIsolationPipeline)
    rows = []
    for date in (20200102, 20200103, 20200106):
        for ticker, value in zip(("A", "B", "C"), (1.0, 2.0, 3.0)):
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "y": value * 0.01,
                    "factor": value,
                }
            )
    panel = pd.DataFrame(rows)
    window = Window(
        window_id=0,
        train_start=20200102,
        train_end=20200103,
        valid_start=20200106,
        valid_end=20200106,
        train_dates=(20200102, 20200103),
        valid_dates=(20200106,),
    )
    predictions, _ = train_and_predict(
        panel,
        ["factor"],
        [window],
        [ModelSpec(name="ridge", type="ridge", params={"alpha": 1.0})],
        cfg,
        seed=42,
    )
    assert len(predictions) == 3


def test_actual_label_end_date_purges_crossing_training_rows():
    frame = pd.DataFrame(
        {
            "date": [20200102, 20200103],
            "ticker": ["A", "B"],
            "y": [0.1, 0.2],
            "label_end_date": [20200105, 20200106],
        }
    )
    window = Window(
        window_id=0,
        train_start=20200102,
        train_end=20200103,
        valid_start=20200106,
        valid_end=20200110,
        train_dates=(20200102, 20200103),
        valid_dates=(20200106,),
    )
    purged = _purge_training_rows(frame, window)
    assert purged["ticker"].tolist() == ["A"]


def test_trial_index_does_not_change_common_model_seed():
    cfg = _training_cfg()
    configure_extensions(cfg)
    REGISTRY.register_feature_pipeline("target_isolation", TargetIsolationPipeline)
    rows = []
    for date in (20200102, 20200103, 20200203):
        for ticker, value in zip(("A", "B", "C"), (1.0, 2.0, 3.0)):
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "y": value * 0.01,
                    "factor": value,
                }
            )
    panel_data = SimpleNamespace(
        panel=pd.DataFrame(rows),
        feature_columns=["factor"],
    )
    window = Window(
        window_id=0,
        train_start=20200102,
        train_end=20200103,
        valid_start=20200203,
        valid_end=20200203,
        train_dates=(20200102, 20200103),
        valid_dates=(20200203,),
    )
    first, _, _ = _run_one_trial(
        trial_id="first",
        trial_index=0,
        model_type="ridge",
        params={"alpha": 1.0},
        panel_data=panel_data,
        windows=[window],
        cfg=cfg,
        seed=42,
        normalize_method=None,
    )
    second, _, _ = _run_one_trial(
        trial_id="second",
        trial_index=99,
        model_type="ridge",
        params={"alpha": 1.0},
        panel_data=panel_data,
        windows=[window],
        cfg=cfg,
        seed=42,
        normalize_method=None,
    )
    assert first["model_seed"] == second["model_seed"] == 42
    assert first["score"] == pytest.approx(second["score"])


def test_legacy_trial_index_changes_model_seed():
    cfg = _training_cfg()
    cfg["compatibility"] = {"profile": "legacy_v1"}
    cfg["reproducibility"]["trial_seed_policy"] = "legacy_trial_index"
    configure_extensions(cfg)
    REGISTRY.register_feature_pipeline("target_isolation", TargetIsolationPipeline)
    rows = []
    for date in (20200102, 20200103, 20200203):
        for ticker, value in zip(("A", "B", "C"), (1.0, 2.0, 3.0)):
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "y": value * 0.01,
                    "factor": value,
                }
            )
    panel_data = SimpleNamespace(
        panel=pd.DataFrame(rows),
        feature_columns=["factor"],
    )
    window = Window(
        window_id=0,
        train_start=20200102,
        train_end=20200103,
        valid_start=20200203,
        valid_end=20200203,
        train_dates=(20200102, 20200103),
        valid_dates=(20200203,),
    )
    first, _, _ = _run_one_trial(
        trial_id="first",
        trial_index=0,
        model_type="ridge",
        params={"alpha": 1.0},
        panel_data=panel_data,
        windows=[window],
        cfg=cfg,
        seed=42,
        normalize_method=None,
    )
    second, _, _ = _run_one_trial(
        trial_id="second",
        trial_index=99,
        model_type="ridge",
        params={"alpha": 1.0},
        panel_data=panel_data,
        windows=[window],
        cfg=cfg,
        seed=42,
        normalize_method=None,
    )
    assert first["model_seed"] == 42
    assert second["model_seed"] == 42 + 99 * 997


def test_search_data_boundary_stops_at_validation_end():
    cfg = {
        "_run_phase": "search",
        "compatibility": {"profile": "research_v2"},
        "data": {"end_date": 20201231},
        "holdout": {"mode": "sealed"},
        "validation": {
            "method": "fixed_train_valid_test",
            "valid_end": 20200930,
        },
    }
    assert _effective_data_end(cfg) == 20200930


def test_strict_point_in_time_rejects_missing_label_window():
    labels = pd.DataFrame({"date": [20200102], "y": [0.1]})
    with pytest.raises(ConfigError, match="label_start_date"):
        _check_label_window(labels, [], 1, strict=True)


def test_robust_rankic_stays_bounded_when_daily_rankic_variance_is_zero():
    rows = []
    for date in (20200102, 20200103, 20200203, 20200204):
        for ticker, value in zip(("A", "B", "C"), (1.0, 2.0, 3.0)):
            rows.append(
                {
                    "date": date,
                    "ticker": ticker,
                    "y": value,
                    "prediction": value,
                    "model_name": "perfect",
                    "model_type": "ridge",
                    "window_id": 0,
                    "complexity_penalty": 0.0,
                    "overfit_penalty": 0.0,
                }
            )
    cfg = {
        "validation": {"min_assets_per_date": 3},
        "fast_evaluator": {"top_quantile": 0.34, "bottom_quantile": 0.34},
        "evaluation": {
            "objective": "robust_rankic",
            "robust_rankic": {
                "block": "month",
                "min_valid_dates": 4,
                "min_blocks": 2,
                "se_multiplier": 1.0,
            },
            "fast_score_weights": {
                "rankic_ir": 0.4,
                "top_bottom_spread": 0.2,
                "positive_window_ratio": 0.1,
                "turnover_proxy": 0.1,
                "complexity_penalty": 0.1,
                "overfit_penalty": 0.1,
            },
        },
    }
    summary, _ = score_predictions(pd.DataFrame(rows), cfg)
    assert np.isfinite(summary["objective_score"])
    assert summary["objective_score"] == pytest.approx(1.0)


def test_explicit_expanding_folds_keep_anchor_and_grow_training_period():
    dates = pd.Series(
        [
            20180102,
            20180103,
            20180104,
            20180105,
            20180108,
            20180109,
            20180110,
            20180111,
        ]
    )
    panel = pd.DataFrame({"date": dates, "ticker": "A", "y": 0.0})
    cfg = {
        "training": {"label_window": 0},
        "time": {"trade_lag_days": 0},
        "validation": {
            "method": "expanding_walk_forward",
            "embargo_days": 0,
            "folds": [
                {
                    "train_start": 20180102,
                    "train_end": 20180104,
                    "valid_start": 20180105,
                    "valid_end": 20180105,
                },
                {
                    "train_start": 20180102,
                    "train_end": 20180108,
                    "valid_start": 20180109,
                    "valid_end": 20180110,
                },
            ],
        },
    }
    windows = build_windows(panel, cfg)
    assert windows[0].train_start == windows[1].train_start
    assert len(windows[1].train_dates) > len(windows[0].train_dates)
