from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from factor_selection_runtime.mrmr_method import select_mrmr
from factor_selection_runtime.sage_method import MarginalImputer, PermutationSAGEEstimator


def test_local_mrmr_matches_reference_package() -> None:
    pytest.importorskip("mrmr")
    from mrmr import mrmr_regression

    rng = np.random.default_rng(21)
    X = pd.DataFrame(rng.normal(size=(300, 6)), columns=[f"f{i}" for i in range(6)])
    y = pd.Series(1.5 * X["f0"] - 0.8 * X["f2"] + 0.1 * rng.normal(size=len(X)))
    local_selected, local_relevance, local_redundancy = select_mrmr(X, y, K=4)
    reference_selected, reference_relevance, reference_redundancy = mrmr_regression(
        X,
        y,
        K=4,
        relevance="f",
        redundancy="c",
        denominator="mean",
        return_scores=True,
        n_jobs=1,
        show_progress=False,
    )
    assert local_selected == reference_selected
    np.testing.assert_allclose(
        local_relevance.loc[reference_relevance.index], reference_relevance, rtol=1e-12, atol=1e-12
    )
    np.testing.assert_allclose(local_redundancy, reference_redundancy, rtol=1e-12, atol=1e-12)


def test_local_sage_matches_reference_package() -> None:
    sage = pytest.importorskip("sage")
    rng = np.random.default_rng(22)
    background = rng.normal(size=(8, 3))
    X = rng.normal(size=(40, 3))
    y = 1.2 * X[:, 0] - 0.4 * X[:, 2]
    model = lambda values: 1.2 * values[:, 0] - 0.4 * values[:, 2]

    local = PermutationSAGEEstimator(MarginalImputer(model, background), random_state=5)
    local_result = local.estimate(
        X,
        y,
        batch_size=8,
        detect_convergence=False,
        n_permutations=24,
    )
    reference_imputer = sage.MarginalImputer(model, background)
    reference_estimator = sage.PermutationEstimator(
        reference_imputer, loss="mse", n_jobs=1, random_state=5
    )
    reference_result = reference_estimator(
        X,
        y,
        batch_size=8,
        detect_convergence=False,
        n_permutations=24,
        bar=False,
        verbose=False,
    )
    np.testing.assert_allclose(local_result.values, reference_result.values, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(local_result.std, reference_result.std, rtol=1e-12, atol=1e-12)
