"""Smoke tests for the ML factor ensemble skeleton.

Run: python scripts/test_ml_ensemble.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import subprocess
import sys
import tempfile
from pathlib import Path

from ml_ensemble import (
    EnsembleConfig,
    _fit_predict,
    icir,
    make_toy,
    make_walkforward_folds,
    rank_ic_series,
    walk_forward_predict,
)


def test_folds_are_purged():
    cfg = EnsembleConfig(horizon=5, train_window=50, step=10, embargo=5)
    dates = np.arange(200)
    for train_dates, test_dates in make_walkforward_folds(dates, cfg):
        # no train date may sit inside the horizon-overlap zone before the test block
        assert train_dates.max() < test_dates.min() - cfg.horizon + 1, "purge violated"


def test_oos_predictions_are_out_of_sample():
    # n_days must exceed train_window or no walk-forward fold can be formed
    panel, factors = make_toy(n_sym=20, n_days=300, k=4)
    cfg = EnsembleConfig(model="ridge", horizon=5, train_window=150, step=20)
    oos, imp = walk_forward_predict(panel, factors, cfg)
    assert not oos.empty
    # OOS dates must be a strict subset and never the earliest training dates
    assert oos["date"].min() > panel["date"].min()
    assert set(oos.columns) == {"date", "symbol", "score"}


def test_empty_oos_evaluation_is_well_typed_and_safe():
    merged = pd.DataFrame(columns=["date", "symbol", "score", "fwd_ret"])
    daily_ic = rank_ic_series(merged)
    assert isinstance(daily_ic, pd.Series)
    assert daily_ic.empty
    assert np.isnan(icir(daily_ic))


def test_elasticnet_default_does_not_collapse_small_return_predictions():
    rng = np.random.default_rng(7)
    x_train = pd.DataFrame(rng.normal(size=(500, 3)), columns=["f0", "f1", "f2"])
    y_train = 0.004 * x_train["f0"] - 0.002 * x_train["f1"]
    x_test = pd.DataFrame(rng.normal(size=(50, 3)), columns=x_train.columns)
    score, _ = _fit_predict(x_train, y_train, x_test, EnsembleConfig(model="elasticnet"))
    assert np.std(score) > 1e-5


def test_short_history_cli_exits_cleanly_and_writes_report():
    panel, factors = make_toy(n_sym=5, n_days=20, k=2)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        panel_path = tmp_path / "panel.csv"
        out_path = tmp_path / "signal.csv"
        report_path = tmp_path / "ensemble_report.md"
        panel.to_csv(panel_path, index=False)
        run = subprocess.run(
            [
                sys.executable, str(Path(__file__).with_name("ml_ensemble.py")),
                "--panel-csv", str(panel_path),
                "--factors", ",".join(factors),
                "--out", str(out_path),
                "--report", str(report_path),
            ],
            capture_output=True, text=True, check=False,
        )
        assert run.returncode == 0, run.stderr
        assert out_path.exists() and report_path.exists()
        assert "no OOS folds" in report_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    test_folds_are_purged()
    test_oos_predictions_are_out_of_sample()
    test_empty_oos_evaluation_is_well_typed_and_safe()
    test_elasticnet_default_does_not_collapse_small_return_predictions()
    test_short_history_cli_exits_cleanly_and_writes_report()
    print("all smoke tests passed")
