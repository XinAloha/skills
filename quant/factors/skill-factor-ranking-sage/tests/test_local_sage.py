from __future__ import annotations

import numpy as np

from factor_selection_runtime.sage_method import (
    ImportanceTracker,
    MarginalImputer,
    PermutationSAGEEstimator,
)


def test_marginal_imputer_uses_empirical_background() -> None:
    background = np.array([[0.0, 10.0], [2.0, 20.0]])
    imputer = MarginalImputer(lambda values: values.sum(axis=1), background)
    x = np.array([[5.0, 7.0]])
    only_first = imputer(x, np.array([[True, False]]))
    all_factors = imputer(x, np.array([[True, True]]))
    no_factors = imputer(x, np.array([[False, False]]))
    np.testing.assert_allclose(only_first, [20.0])
    np.testing.assert_allclose(all_factors, [12.0])
    np.testing.assert_allclose(no_factors, [16.0])


def test_importance_tracker_matches_direct_mean_and_standard_error() -> None:
    scores = np.array([[1.0, 2.0], [3.0, 2.0], [5.0, 8.0]])
    tracker = ImportanceTracker()
    tracker.update(scores[:2])
    tracker.update(scores[2:])
    expected_mean = scores.mean(axis=0)
    expected_std = np.sqrt(np.square(scores - expected_mean).sum(axis=0) / len(scores) ** 2)
    np.testing.assert_allclose(tracker.values, expected_mean)
    np.testing.assert_allclose(tracker.std, expected_std)


def test_permutation_sage_is_reproducible_and_ignores_unused_factor() -> None:
    rng = np.random.default_rng(12)
    X = rng.normal(size=(80, 2))
    y = X[:, 0]
    background = rng.normal(size=(12, 2))
    model = lambda values: values[:, 0]

    first = PermutationSAGEEstimator(MarginalImputer(model, background), random_state=9)
    second = PermutationSAGEEstimator(MarginalImputer(model, background), random_state=9)
    result_a = first.estimate(X, y, batch_size=16, detect_convergence=False, n_permutations=32)
    result_b = second.estimate(X, y, batch_size=16, detect_convergence=False, n_permutations=32)

    np.testing.assert_allclose(result_a.values, result_b.values)
    np.testing.assert_allclose(result_a.std, result_b.std)
    assert result_a.values[0] > 0
    assert result_a.values[1] == 0.0
    assert result_a.sample_count == 32


def test_permutation_sage_detects_zero_width_convergence() -> None:
    X = np.ones((10, 2))
    y = np.zeros(10)
    model = lambda values: np.zeros(len(values))
    estimator = PermutationSAGEEstimator(MarginalImputer(model, X[:2]), random_state=3)
    result = estimator.estimate(X, y, batch_size=8, detect_convergence=True, n_permutations=None)
    assert result.converged
    assert result.iteration_count == 1
    assert result.sample_count == 8
    np.testing.assert_array_equal(result.values, np.zeros(2))
