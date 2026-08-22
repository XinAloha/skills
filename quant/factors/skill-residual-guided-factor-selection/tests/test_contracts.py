from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from residual_factor_selection.cache import load_prepared_cache, write_prepared_cache
from residual_factor_selection.config import validate_config
from residual_factor_selection.data import build_temporal_fold_masks
from residual_factor_selection.experiment import (
    ExperimentContext,
    _build_beam_selector,
    _model_metadata,
    _write_selection_result,
)
from residual_factor_selection.lgbm_beam import LGBMBeamResidualSelector
from residual_factor_selection.ridge import RidgeModel
from residual_factor_selection.selector import PreparedFeatures, SelectionResult
from residual_factor_selection.serialization import write_json


def _panel() -> tuple[pd.MultiIndex, pd.DataFrame, pd.Series]:
    dates = pd.date_range("2020-01-01", periods=8, freq="D")
    symbols = ["A", "B", "C", "D"]
    index = pd.MultiIndex.from_product([dates, symbols], names=["datetime", "symbol"])
    values = np.tile([-1.5, -0.5, 0.5, 1.5], len(dates))
    features = pd.DataFrame({"x": values}, index=index)
    target = pd.Series(values, index=index, name="target")
    return index, features, target


def _config() -> dict:
    return {
        "data": {"label_path": "labels.parquet", "factor_dir": "factors"},
        "split": {
            "train_start": "2020-01-01",
            "train_end": "2020-01-03",
            "valid_start": "2020-01-04",
            "valid_end": "2020-01-06",
            "oos_start": "2020-01-07",
            "oos_end": "2020-01-08",
            "embargo_bars": 1,
        },
        "universe": {"symbols": None, "train_label_min_coverage": 0.8},
        "preprocess": {"min_cross_section": 4},
        "model": {"type": "ridge", "ridge_alpha": 10.0, "equal_date_weight": True},
        "selection": {"score_method": "pearson", "random_seed": 1},
        "beam": {
            "cv_folds": [
                {
                    "fit_start": "2020-01-01",
                    "fit_end": "2020-01-02",
                    "score_start": "2020-01-03",
                    "score_end": "2020-01-03",
                }
            ]
        },
        "output": {"root": "outputs", "experiment_name": "test"},
    }


def test_temporal_fold_masks_purge_fit_trading_dates() -> None:
    index, _, _ = _panel()
    dates = index.get_level_values("datetime")
    fold = {
        "fit_start": "2020-01-01",
        "fit_end": "2020-01-05",
        "score_start": "2020-01-06",
        "score_end": "2020-01-08",
    }
    fit_mask, score_mask = build_temporal_fold_masks(dates, fold, embargo_bars=2)
    assert pd.DatetimeIndex(dates[fit_mask]).unique().tolist() == list(pd.date_range("2020-01-01", periods=3))
    assert pd.DatetimeIndex(dates[score_mask]).unique().tolist() == list(pd.date_range("2020-01-06", periods=3))


def test_lgbm_cv_and_oof_use_embargo_masks() -> None:
    _, features, target = _panel()
    fold = {
        "fit_start": "2020-01-01",
        "fit_end": "2020-01-05",
        "score_start": "2020-01-06",
        "score_end": "2020-01-08",
    }
    selector = LGBMBeamResidualSelector(
        {"min_cross_section": 4},
        {"type": "lgbm", "model_threads": 1, "lgbm": {"search_estimators": 2}},
        {"score_method": "pearson"},
        {"cv_folds": [fold], "stability_penalty": 0.0, "min_year_weight": 0.0},
        embargo_bars=2,
    )
    selector._prepare_cv(PreparedFeatures(train=features, valid=features), target)
    fit_end_dates: list[pd.Timestamp] = []

    class DummyModel:
        def predict(self, frame: pd.DataFrame) -> pd.Series:
            return pd.Series(0.0, index=frame.index)

    def fake_fit(frame: pd.DataFrame, _: pd.Series, __: tuple[str, ...]) -> DummyModel:
        fit_end_dates.append(frame.index.get_level_values("datetime").max())
        return DummyModel()

    selector._fit_search = fake_fit
    selector._cv_score_for_folds(("x",), [fold])
    selector._oof_residual(("x",))
    assert fit_end_dates == [pd.Timestamp("2020-01-03"), pd.Timestamp("2020-01-03")]


def test_beam_factory_honors_lgbm_and_embargo() -> None:
    config = _config()
    config["model"] = {"type": "lgbm", "model_threads": 1, "lgbm": {}}
    config["split"]["embargo_bars"] = 3
    selector = _build_beam_selector(config)
    assert isinstance(selector, LGBMBeamResidualSelector)
    assert selector.embargo_bars == 3


def test_prepared_cache_manifest_rejects_preprocess_mismatch(tmp_path) -> None:
    index, features, _ = _panel()
    path = tmp_path / "features.parquet"
    preprocess = {"factor_transform": "cross_sectional"}
    split = _config()["split"]
    write_prepared_cache(path, features, index, ["A", "B", "C", "D"], preprocess, split)
    loaded = load_prepared_cache(path, index, ["A", "B", "C", "D"], preprocess, split, ["x"])
    pd.testing.assert_frame_equal(loaded, features)
    with pytest.raises(ValueError, match="manifest"):
        load_prepared_cache(
            path,
            index,
            ["A", "B", "C", "D"],
            {"factor_transform": "rolling_median_zscore"},
            split,
            ["x"],
        )


def test_json_and_lgbm_metadata_are_model_specific(tmp_path) -> None:
    output = tmp_path / "result.json"
    write_json(output, {"finite": 1.0, "missing": np.nan})
    assert json.loads(output.read_text(encoding="utf-8")) == {"finite": 1.0, "missing": None}
    model = SimpleNamespace(iterations=7, coefficients=pd.Series({"x": 3.0}))
    metadata = _model_metadata({"model": {"type": "lgbm"}}, model)
    assert metadata == {"type": "lgbm", "iterations": 7, "feature_importance": {"x": 3.0}}
    assert not any(key.startswith("ridge") for key in metadata)


def test_selection_writer_does_not_emit_oos_files(tmp_path) -> None:
    index, features, target = _panel()
    history = pd.DataFrame(
        [{"iteration": 1, "valid_mean_ic": 0.1, "valid_icir": 0.2, "is_best": True}]
    )
    model = RidgeModel(0.0, pd.Series({"x": 1.0}), 10.0)
    result = SelectionResult(history, pd.DataFrame(), 1, ["x"], model)
    context = ExperimentContext(
        ["A", "B", "C", "D"],
        target,
        target,
        target,
        SimpleNamespace(),
        PreparedFeatures(features, features, features),
    )
    output = tmp_path / "run"
    _write_selection_result(_config(), context, result, output, 1, "x")
    assert (output / "summary.json").exists()
    assert not (output / "oos_predictions.parquet").exists()
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["oos_evaluation"] == "not_run"


def test_config_validation_rejects_overlap_and_wrong_model_command() -> None:
    config = _config()
    validate_config(config, "run-beam")
    config["split"]["valid_start"] = "2020-01-03"
    with pytest.raises(ValueError, match="Train < Valid < OOS"):
        validate_config(config, "run-beam")
    config = _config()
    config["model"]["type"] = "lgbm"
    with pytest.raises(ValueError, match="supported only"):
        validate_config(config, "run")
