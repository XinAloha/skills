from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from factor_selection_runtime.mrmr_method import (
    REDUNDANCY_FLOOR,
    f_statistic_relevance,
    pearson_redundancy,
    select_mrmr,
)


def test_f_statistic_relevance_handles_signal_constant_and_missing() -> None:
    signal = np.arange(20, dtype="float64")
    X = pd.DataFrame(
        {
            "signal": signal,
            "constant": np.ones(20),
            "partly_missing": signal,
        }
    )
    X.loc[::2, "partly_missing"] = np.nan
    relevance = f_statistic_relevance(X, pd.Series(2.0 * signal + 1.0))
    assert relevance["signal"] > 0
    assert relevance["partly_missing"] > 0
    assert relevance["constant"] == 0.0


def test_pearson_redundancy_preserves_sign_before_selection_abs() -> None:
    X = pd.DataFrame(
        {
            "base": np.arange(10, dtype="float64"),
            "same": np.arange(10, dtype="float64"),
            "opposite": -np.arange(10, dtype="float64"),
            "constant": np.ones(10),
        }
    )
    values = pearson_redundancy(X, "base", ["same", "opposite", "constant"])
    assert values["same"] == pytest.approx(1.0)
    assert values["opposite"] == pytest.approx(-1.0)
    assert values["constant"] == REDUNDANCY_FLOOR


def test_mrmr_avoids_an_exact_duplicate() -> None:
    rng = np.random.default_rng(7)
    first = rng.normal(size=500)
    second = rng.normal(size=500)
    y = 2.0 * first + second + 0.05 * rng.normal(size=500)
    X = pd.DataFrame(
        {
            "first": first,
            "duplicate": first.copy(),
            "second": second,
            "noise": rng.normal(size=500),
        }
    )
    selected, relevance, redundancy = select_mrmr(X, pd.Series(y), K=2)
    assert selected == ["first", "second"]
    assert relevance.index.tolist() == X.columns.tolist()
    assert redundancy.loc["duplicate", "first"] == 1.0
