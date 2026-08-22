"""Final holdout evaluation for the selected hyperparameters."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from data_adapter import PanelData, Window
from fast_evaluator import score_predictions
from model_registry import ModelSpec
from trainer import train_and_predict


def evaluate_holdout(
    *,
    panel_data: PanelData,
    holdout_window: Window,
    model_type: str,
    params: Mapping[str, Any],
    cfg: Mapping[str, Any],
    seed: int,
    normalize_method: str | None = None,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    spec = ModelSpec(
        name=f"{model_type}_final_holdout",
        type=model_type,
        params=dict(params),
    )
    predictions, window_metrics = train_and_predict(
        panel_data.panel,
        panel_data.feature_columns,
        [holdout_window],
        [spec],
        cfg,
        seed=seed,
        normalize_method=normalize_method,
    )
    summary, metric_table = score_predictions(predictions, cfg)
    out = dict(summary)
    out.update(
        {
            "model_type": model_type,
            "train_start": holdout_window.train_start,
            "train_end": holdout_window.train_end,
            "test_start": holdout_window.valid_start,
            "test_end": holdout_window.valid_end,
            "num_train_dates": len(holdout_window.train_dates),
            "num_test_dates": len(holdout_window.valid_dates),
            "num_prediction_rows": int(len(predictions)),
            "params": dict(params),
        }
    )
    return out, predictions, window_metrics
