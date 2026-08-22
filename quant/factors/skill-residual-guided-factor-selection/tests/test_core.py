from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from residual_factor_selection.data import FactorStore, purge_tail, select_universe, stack_wide
from residual_factor_selection.pool import ExhaustivePoolSelector, select_smallest_weight_factor
from residual_factor_selection.beam import (
    BeamResidualSelector,
    BeamState,
    aggregate_cv_score,
    beam_priority,
    factor_jaccard,
    select_diverse_states,
)
from residual_factor_selection.metrics import daily_correlation
from residual_factor_selection.materialize import _read_bar
from residual_factor_selection.preprocess import preprocess_factor, preprocess_factor_wide, preprocess_label
from residual_factor_selection.ridge import fit_ridge
from residual_factor_selection.selector import (
    PreparedFeatures,
    vectorized_residual_scores,
    vectorized_residual_scores_batch,
)


class CoreTests(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range("2020-01-01", periods=8, freq="D")
        symbols = ["A", "B", "C", "D"]
        self.index = pd.MultiIndex.from_product([dates, symbols], names=["datetime", "symbol"])

    def test_ridge_recovers_linear_signal(self):
        x = pd.DataFrame({"x1": np.tile([-1.5, -0.5, 0.5, 1.5], 8)}, index=self.index)
        target = pd.Series(2.0 * x["x1"], index=self.index, name="target")
        model = fit_ridge(x, target, alpha=1e-8)
        self.assertAlmostEqual(model.coefficients["x1"], 2.0, places=5)

    def test_factor_store_accepts_prepared_cache_columns_without_factor_dir(self):
        store = FactorStore(None, ["A", "B"], factor_names=["alpha_001", "factor_mad_001"])
        self.assertEqual(store.factor_names, ["alpha_001", "factor_mad_001"])
        with self.assertRaisesRegex(FileNotFoundError, "cache-only"):
            store.load_wide("alpha_001")

    def test_beam_diversity_prefers_distinct_paths(self):
        states = [
            BeamState(("A", "B", "C"), 3.0, 3.0, 0.0, 3.0, 0.0, 10.0, (), "", "one"),
            BeamState(("A", "B", "D"), 2.0, 2.0, 0.0, 2.0, 0.0, 10.0, (), "", "two"),
            BeamState(("A", "E", "F"), 1.0, 1.0, 0.0, 1.0, 0.0, 10.0, (), "", "three"),
        ]
        selected = select_diverse_states(states, width=2, max_jaccard=0.4)
        self.assertEqual([state.path_id for state in selected], ["one", "three"])
        self.assertAlmostEqual(factor_jaccard(states[0].factors, states[1].factors), 0.5)

    def test_pool_prunes_smallest_absolute_weight(self):
        removed = select_smallest_weight_factor(("A", "B", "C"), np.array([0.4, -0.05, 0.2]))
        self.assertEqual(removed, "B")

    def test_pool_capacity_prunes_augmented_pool(self):
        selector = ExhaustivePoolSelector(
            {"min_cross_section": 4},
            {"ridge_alpha": 0.0, "equal_date_weight": True},
            {"score_method": "pearson", "max_factors": 3, "top_n_log": 2},
            {"ridge_alphas": [0.0], "cv_folds": []},
            {"pool_capacity": 2},
        )
        features = pd.DataFrame(
            {
                "A": np.tile([-1.5, -0.5, 0.5, 1.5], 8),
                "B": np.tile([0.5, -1.5, 1.5, -0.5], 8),
                "C": np.tile([-0.5, 1.5, -1.5, 0.5], 8),
            },
            index=self.index,
        )
        target = pd.Series(2.0 * features["A"] + 0.01 * features["B"] + features["C"], index=self.index)
        selector._prepare_cv(PreparedFeatures(train=features, valid=features), target)
        pool, removed = selector._candidate_pool(("A", "B"), "C", 2, 0.0)
        self.assertEqual(removed, "B")
        self.assertEqual(pool, ("A", "C"))

    def test_beam_selection_uses_search_priority(self):
        current_best = BeamState(("A",), 3.0, 3.0, 0.0, 3.0, 0.0, 10.0, (), "", "one")
        deeper_potential = BeamState(
            ("B",), 2.0, 2.0, 0.0, 2.0, 0.0, 10.0, (), "", "two", priority_score=4.0
        )
        selected = select_diverse_states([current_best, deeper_potential], width=1, max_jaccard=1.0)
        self.assertEqual(selected[0].path_id, "two")
        self.assertEqual(beam_priority(current_best), 3.0)

    def test_resume_frontier_restores_paths_and_recent_improvements(self):
        selector = BeamResidualSelector(
            {"min_cross_section": 4},
            {"ridge_alpha": 10.0, "equal_date_weight": True},
            {"score_method": "pearson"},
            {
                "resume_history": "unused.csv",
                "trend_window": 2,
                "cv_folds": [{"score_start": "2020-01-01"}],
            },
        )
        history = pd.DataFrame(
            [
                {"depth": 1, "path_id": "b01p01", "parent_id": "root", "factors": '["A"]', "cv_score": 0.1, "cv_mean_ic": 0.1, "cv_std_ic": 0.0, "cv_min_ic": 0.1, "cv_se": 0.0, "ridge_alpha": 1.0, "priority_score": 0.1, "residual_score": np.nan, "continuation_score": 0.0, "ic_2020": 0.1, "kept": True},
                {"depth": 2, "path_id": "b02p01", "parent_id": "b01p01", "factors": '["A", "B"]', "cv_score": 0.12, "cv_mean_ic": 0.12, "cv_std_ic": 0.0, "cv_min_ic": 0.12, "cv_se": 0.0, "ridge_alpha": 1.0, "priority_score": 0.12, "residual_score": np.nan, "continuation_score": 0.0, "ic_2020": 0.12, "kept": True},
            ]
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "beam_history.csv"
            history.to_csv(path, index=False)
            selector.beam_config["resume_history"] = str(path)
            beam, rows, depth = selector._resume_frontier()
        self.assertEqual(depth, 2)
        self.assertEqual(len(rows), 2)
        self.assertEqual(beam[0].factors, ("A", "B"))
        self.assertAlmostEqual(beam[0].recent_improvements[0], 0.02)

    def test_residual_objective_matches_fitted_ridge(self):
        features = pd.DataFrame(
            {
                "x1": np.tile([-1.5, -0.5, 0.5, 1.5], 8),
                "x2": np.tile([0.5, -1.5, 1.5, -0.5], 8),
            },
            index=self.index,
        )
        target = pd.Series(2.0 * features["x1"] - features["x2"], index=self.index, name="target")
        selector = BeamResidualSelector(
            {"min_cross_section": 4},
            {"ridge_alpha": 10.0, "equal_date_weight": True},
            {"score_method": "pearson"},
            {"residual_ridge_alpha": 10.0, "cv_folds": []},
        )
        prepared = PreparedFeatures(train=features, valid=features)
        selector._prepare_cv(prepared, target)
        actual = selector._residual_score(("x1", "x2"))
        model = fit_ridge(features, target, alpha=10.0, equal_date_weight=True)
        weights = np.full(len(target), 0.25)
        residual_ss = float(weights @ np.square(target - model.predict(features)))
        baseline_ss = float(weights @ np.square(target - np.average(target, weights=weights)))
        self.assertAlmostEqual(actual, 1.0 - residual_ss / baseline_ss, places=12)

    def test_cv_score_penalizes_instability_and_complexity(self):
        score, mean_ic, std_ic, min_ic, standard_error = aggregate_cv_score(
            [0.01, 0.03], 0.5, 4, 0.00005, min_year_weight=0.25
        )
        self.assertAlmostEqual(mean_ic, 0.02)
        self.assertAlmostEqual(std_ic, 0.01)
        self.assertAlmostEqual(min_ic, 0.01)
        self.assertAlmostEqual(standard_error, 0.01 / np.sqrt(2))
        self.assertAlmostEqual(score, 0.0173)

    def test_daily_correlation(self):
        left = pd.Series(np.tile([1.0, 2.0, 3.0, 4.0], 8), index=self.index)
        right = left * 3.0
        correlations = daily_correlation(left, right, min_count=4)
        self.assertTrue(np.allclose(correlations, 1.0))

    def test_cross_sectional_rank_label(self):
        raw = pd.Series(np.tile([40.0, 10.0, 30.0, 20.0], 8), index=self.index)
        transformed = preprocess_label(
            raw,
            {"label_transform": "cross_sectional_rank", "demean_label": True, "min_cross_section": 4},
        )
        expected = np.tile([0.375, -0.375, 0.125, -0.125], 8)
        self.assertTrue(np.allclose(transformed, expected))

    def test_cross_sectional_preprocess(self):
        raw = pd.Series(np.tile([1.0, 2.0, 3.0, 100.0], 8), index=self.index, name="factor")
        processed = preprocess_factor(
            raw,
            {
                "winsor_lower": 0.0,
                "winsor_upper": 0.75,
                "cross_sectional_zscore": True,
                "min_cross_section": 4,
            },
        )
        means = processed.groupby(level="datetime").mean()
        self.assertTrue(np.allclose(means, 0.0))

    def test_wide_preprocess_handles_extreme_finite_values(self):
        wide = pd.DataFrame(
            [[-1e300, -1e200, 1e200, 1e300]],
            index=[pd.Timestamp("2020-01-01")],
            columns=["A", "B", "C", "D"],
        )
        processed = preprocess_factor_wide(
            wide,
            {
                "winsor_lower": 0.0,
                "winsor_upper": 1.0,
                "cross_sectional_zscore": True,
                "min_cross_section": 4,
            },
        )
        self.assertTrue(np.isfinite(processed.to_numpy()).all())
        self.assertAlmostEqual(float(processed.std(axis=1, ddof=0).iloc[0]), 1.0)

    def test_wide_preprocess_matches_stacked_preprocess(self):
        wide = pd.DataFrame(
            np.arange(32, dtype=float).reshape(8, 4),
            index=pd.date_range("2020-01-01", periods=8, freq="D"),
            columns=["A", "B", "C", "D"],
        )
        wide.iloc[2, 1] = np.nan
        config = {
            "winsor_lower": 0.01,
            "winsor_upper": 0.99,
            "cross_sectional_zscore": True,
            "min_cross_section": 3,
        }
        expected = preprocess_factor(stack_wide(wide, wide.columns).rename("factor"), config)
        actual = stack_wide(preprocess_factor_wide(wide, config), wide.columns).rename("factor")
        self.assertTrue(np.allclose(actual, expected, atol=1e-12))

    def test_rolling_preprocess_matches_stacked_and_is_causal(self):
        wide = pd.DataFrame(
            {
                "A": [1.0, 2.0, 3.0, 4.0, 100.0, 6.0, 7.0, 8.0],
                "B": [8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0],
            },
            index=pd.date_range("2020-01-01", periods=8, freq="D"),
        )
        config = {
            "factor_transform": "rolling_median_zscore",
            "rolling_window": 4,
            "rolling_min_periods": 2,
            "rolling_clip": 3.0,
        }
        expected = preprocess_factor(stack_wide(wide, wide.columns).rename("factor"), config)
        actual_wide = preprocess_factor_wide(wide, config)
        actual = stack_wide(actual_wide, wide.columns).rename("factor")
        self.assertTrue(np.allclose(actual, expected, atol=1e-12))
        self.assertLessEqual(float(actual_wide.abs().max().max()), 3.0)

        changed = wide.copy()
        changed.iloc[-1, 0] = -1e6
        changed_processed = preprocess_factor_wide(changed, config)
        self.assertTrue(np.allclose(actual_wide.iloc[:-1], changed_processed.iloc[:-1]))

    def test_vectorized_residual_scores_match_scalar_correlations(self):
        rng = np.random.default_rng(42)
        features = pd.DataFrame(rng.normal(size=(len(self.index), 3)), index=self.index, columns=list("xyz"))
        residual = pd.Series(rng.normal(size=len(self.index)), index=self.index)
        scores = vectorized_residual_scores(features, residual, min_count=4).set_index("candidate")
        for name in features:
            expected = daily_correlation(features[name], residual, min_count=4)
            self.assertAlmostEqual(scores.loc[name, "signed_mean_ic"], expected.mean(), places=12)
            self.assertEqual(scores.loc[name, "dates"], len(expected))

    def test_batch_residual_scores_match_individual_scores(self):
        rng = np.random.default_rng(43)
        features = pd.DataFrame(rng.normal(size=(len(self.index), 5)), index=self.index)
        residuals = rng.normal(size=(len(self.index), 3))
        batch_scores, batch_counts = vectorized_residual_scores_batch(features, residuals, min_count=4)
        for path in range(residuals.shape[1]):
            expected = vectorized_residual_scores(
                features,
                pd.Series(residuals[:, path], index=self.index),
                min_count=4,
            )
            self.assertTrue(np.allclose(batch_scores[path], expected["signed_mean_ic"], atol=1e-12))
            self.assertTrue(np.array_equal(batch_counts[path], expected["dates"]))

    def test_universe_and_embargo(self):
        label = pd.DataFrame(
            {"A": [1.0] * 8, "B": [1.0, np.nan] * 4},
            index=pd.date_range("2020-01-01", periods=8, freq="D"),
        )
        self.assertEqual(select_universe(label, "2020-01-01", "2020-01-08", 0.75), ["A"])
        panel = pd.DataFrame({"value": 1.0}, index=self.index)
        purged = purge_tail(panel, 2)
        self.assertEqual(purged.index.get_level_values("datetime").nunique(), 6)

    def test_stack_wide_preserves_missing_rows(self):
        wide = pd.DataFrame(
            {"A": [1.0, np.nan], "B": [2.0, 3.0]},
            index=pd.date_range("2020-01-01", periods=2, freq="D"),
        )
        stacked = stack_wide(wide, ["A", "B"])
        self.assertEqual(len(stacked), 4)
        self.assertTrue(np.isnan(stacked.loc[(pd.Timestamp("2020-01-02"), "A")]))

    def test_stock_bar_uses_trade_date_column(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "1.parquet"
            pd.DataFrame(
                {"trade_date": ["2020-01-02", "2020-01-03"], "close": [10.0, 11.0]}
            ).to_parquet(path, index=False)
            frame = _read_bar(path)
        self.assertEqual(frame.index.min(), pd.Timestamp("2020-01-02"))
        self.assertNotIn("trade_date", frame.columns)


if __name__ == "__main__":
    unittest.main()
