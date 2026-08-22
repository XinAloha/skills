from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor, early_stopping, log_evaluation

from .beam import BeamResidualSelector, CVResult, aggregate_cv_score
from .data import build_temporal_fold_masks
from .metrics import prediction_metrics
from .selector import PreparedFeatures, vectorized_residual_scores, vectorized_residual_scores_batch


@dataclass
class LGBMModel:
    estimator: LGBMRegressor
    factors: tuple[str, ...]
    iterations: int
    alpha: float = np.nan
    intercept: float = np.nan

    @property
    def coefficients(self) -> pd.Series:
        return pd.Series(self.estimator.feature_importances_, index=self.factors, dtype=float)

    def predict(self, features: pd.DataFrame) -> pd.Series:
        values = self.estimator.predict(features.loc[:, list(self.factors)])
        return pd.Series(values, index=features.index, name="prediction")


class LGBMBeamResidualSelector(BeamResidualSelector):
    def __init__(
        self,
        preprocess_config: dict,
        model_config: dict,
        selection_config: dict,
        beam_config: dict,
        embargo_bars: int = 0,
    ):
        super().__init__(preprocess_config, model_config, selection_config, beam_config, embargo_bars)
        self._prepared_features: pd.DataFrame | None = None
        self._prepared_target: pd.Series | None = None
        self._oof_residual_cache: dict[tuple[str, ...], np.ndarray] = {}

    def _model_params(self, n_estimators: int) -> dict:
        config = self.model_config.get("lgbm", {})
        return {
            "objective": "regression_l2",
            "learning_rate": float(config.get("learning_rate", 0.03)),
            "n_estimators": int(n_estimators),
            "num_leaves": int(config.get("num_leaves", 7)),
            "max_depth": int(config.get("max_depth", 4)),
            "min_child_samples": int(config.get("min_child_samples", 300)),
            "subsample": 1.0,
            "colsample_bytree": float(config.get("colsample_bytree", 0.8)),
            "reg_alpha": float(config.get("reg_alpha", 0.5)),
            "reg_lambda": float(config.get("reg_lambda", 20.0)),
            "random_state": int(config.get("random_state", 20260716)),
            "n_jobs": int(self.model_config.get("model_threads", 8)),
            "deterministic": True,
            "force_col_wise": True,
            "verbosity": -1,
        }

    @staticmethod
    def _date_weights(index: pd.MultiIndex) -> np.ndarray:
        dates = index.get_level_values("datetime").to_numpy()
        _, inverse, counts = np.unique(dates, return_inverse=True, return_counts=True)
        return 1.0 / counts[inverse]

    def _fit(self, features: pd.DataFrame, target: pd.Series, factors: tuple[str, ...], alpha=None) -> LGBMModel:
        selected = features.loc[:, list(factors)]
        config = self.model_config.get("lgbm", {})
        max_estimators = int(config.get("n_estimators", 1500))
        patience = int(config.get("early_stopping_rounds", 100))
        validation_days = int(config.get("validation_days", 126))
        dates = pd.DatetimeIndex(selected.index.get_level_values("datetime").unique()).sort_values()
        weights = self._date_weights(selected.index)
        if len(dates) > validation_days * 2:
            validation_dates = dates[-validation_days:]
            all_dates = selected.index.get_level_values("datetime")
            tuning_fold = {
                "fit_start": dates[0],
                "fit_end": validation_dates[0] - pd.Timedelta(nanoseconds=1),
                "score_start": validation_dates[0],
                "score_end": validation_dates[-1],
            }
            fit_mask, validation_mask = build_temporal_fold_masks(
                all_dates, tuning_fold, self.embargo_bars
            )
            tuning = LGBMRegressor(**self._model_params(max_estimators))
            tuning.fit(
                selected.loc[fit_mask],
                target.loc[fit_mask],
                sample_weight=weights[fit_mask],
                eval_set=[(selected.loc[validation_mask], target.loc[validation_mask])],
                eval_sample_weight=[weights[validation_mask]],
                callbacks=[early_stopping(patience, verbose=False), log_evaluation(0)],
            )
            iterations = int(tuning.best_iteration_ or max_estimators)
        else:
            iterations = int(config.get("fallback_estimators", 200))
        estimator = LGBMRegressor(**self._model_params(iterations))
        estimator.fit(selected, target, sample_weight=weights)
        return LGBMModel(estimator, factors, iterations)

    def _fit_search(self, features: pd.DataFrame, target: pd.Series, factors: tuple[str, ...]) -> LGBMModel:
        selected = features.loc[:, list(factors)]
        iterations = int(self.model_config.get("lgbm", {}).get("search_estimators", 200))
        estimator = LGBMRegressor(**self._model_params(iterations))
        estimator.fit(selected, target, sample_weight=self._date_weights(selected.index))
        return LGBMModel(estimator, factors, iterations)

    def _prepare_cv(self, prepared: PreparedFeatures, target: pd.Series) -> None:
        self._prepared_features = prepared.train
        self._prepared_target = target.reindex(prepared.train.index)
        self._factor_positions = {name: position for position, name in enumerate(prepared.train.columns)}
        self._cv_folds = list(self.beam_config["cv_folds"])
        self._cv_cache.clear()
        self._ranking_cache.clear()
        self._oof_residual_cache.clear()

    def _root_candidates(self, prepared: PreparedFeatures, target: pd.Series) -> list[str]:
        shortlist = int(self.beam_config.get("root_residual_shortlist", 20))
        ranked = vectorized_residual_scores(
            prepared.train,
            target,
            min_count=int(self.preprocess_config["min_cross_section"]),
        ).dropna(subset=["score"])
        ranked = ranked.sort_values(["score", "candidate"], ascending=[False, True])
        return ranked.head(shortlist)["candidate"].astype(str).tolist()

    def _cv_score_for_folds(self, factors: tuple[str, ...], folds: list[dict]) -> CVResult:
        if self._prepared_features is None or self._prepared_target is None:
            raise RuntimeError("LGBM CV data has not been prepared")
        dates = self._prepared_target.index.get_level_values("datetime")
        fold_scores = []
        for fold in folds:
            fit_mask, score_mask = build_temporal_fold_masks(dates, fold, self.embargo_bars)
            model = self._fit_search(
                self._prepared_features.loc[fit_mask], self._prepared_target.loc[fit_mask], factors
            )
            prediction = model.predict(self._prepared_features.loc[score_mask])
            metrics = prediction_metrics(
                prediction,
                self._prepared_target.loc[score_mask],
                method=self.selection_config["score_method"],
                min_count=int(self.preprocess_config["min_cross_section"]),
            )
            fold_scores.append(float(metrics["mean_ic"]))
        score, mean_ic, std_ic, min_ic, standard_error = aggregate_cv_score(
            fold_scores,
            stability_penalty=float(self.beam_config["stability_penalty"]),
            factor_count=len(factors),
            complexity_penalty=float(self.beam_config.get("complexity_penalty", 0.0)),
            min_year_weight=float(self.beam_config.get("min_year_weight", 0.0)),
        )
        return CVResult(score, mean_ic, std_ic, min_ic, standard_error, np.nan, tuple(fold_scores))

    def _cv_score_prepared(self, factors: tuple[str, ...]) -> CVResult:
        return self._cv_score_for_folds(factors, self.beam_config["cv_folds"])

    def _cv_scores_batch(self, prepared, target, factor_sets):
        results = {}
        uncached = []
        seen = set()
        for factors in factor_sets:
            cache_key = tuple(sorted(factors))
            cached = self._cv_cache.get(cache_key)
            if cached is not None:
                results[factors] = cached
            elif cache_key not in seen:
                seen.add(cache_key)
                uncached.append(factors)
        jobs = min(int(self.beam_config.get("cv_jobs", 1)), len(uncached))
        screen_fold_count = int(self.beam_config.get("screen_fold_count", 0))
        full_per_parent = int(self.beam_config.get("full_cv_candidates_per_parent", 0))
        if screen_fold_count > 0 and full_per_parent > 0 and uncached:
            screen_folds = self.beam_config["cv_folds"][-screen_fold_count:]
            with ThreadPoolExecutor(max_workers=jobs) as executor:
                screened = list(zip(uncached, executor.map(
                    lambda factors: self._cv_score_for_folds(factors, screen_folds), uncached
                )))
            keep_count = int(self.beam_config.get("root_width", full_per_parent)) if len(uncached[0]) == 1 else full_per_parent
            grouped = {}
            for factors, result in screened:
                grouped.setdefault(tuple(sorted(factors[:-1])), []).append((factors, result))
            uncached = []
            for values in grouped.values():
                values.sort(key=lambda item: (-item[1].score, item[0]))
                kept = {tuple(sorted(factors)) for factors, _ in values[:keep_count]}
                uncached.extend(factors for factors, _ in values[:keep_count])
                for factors, screen_result in values[keep_count:]:
                    self._cv_cache[tuple(sorted(factors))] = CVResult(
                        -np.inf,
                        screen_result.mean_ic,
                        screen_result.std_ic,
                        screen_result.min_ic,
                        screen_result.standard_error,
                        np.nan,
                        screen_result.fold_ics,
                    )
        if jobs <= 1:
            computed = [(factors, self._cv_score_prepared(factors)) for factors in uncached]
        else:
            with ThreadPoolExecutor(max_workers=jobs) as executor:
                computed = list(zip(uncached, executor.map(self._cv_score_prepared, uncached)))
        for factors, result in computed:
            self._cv_cache[tuple(sorted(factors))] = result
        for factors in factor_sets:
            results[factors] = self._cv_cache[tuple(sorted(factors))]
        return results

    def _oof_residual(self, factors: tuple[str, ...]) -> np.ndarray:
        cache_key = tuple(sorted(factors))
        cached = self._oof_residual_cache.get(cache_key)
        if cached is not None:
            return cached
        if self._prepared_features is None or self._prepared_target is None:
            raise RuntimeError("LGBM CV data has not been prepared")
        residual = np.full(len(self._prepared_target), np.nan, dtype=float)
        dates = self._prepared_target.index.get_level_values("datetime")
        target_values = self._prepared_target.to_numpy(dtype=float)
        for fold in self.beam_config["cv_folds"]:
            fit_mask, score_mask = build_temporal_fold_masks(dates, fold, self.embargo_bars)
            model = self._fit_search(
                self._prepared_features.loc[fit_mask], self._prepared_target.loc[fit_mask], factors
            )
            residual[score_mask] = target_values[score_mask] - model.predict(
                self._prepared_features.loc[score_mask]
            ).to_numpy()
        self._oof_residual_cache[cache_key] = residual
        return residual

    def _rank_candidates_batch(self, prepared, target, requests):
        rankings = {}
        uncached = []
        for factors, _ in requests:
            cache_key = tuple(sorted(factors))
            cached = self._ranking_cache.get(cache_key)
            if cached is not None:
                rankings[factors] = cached
            else:
                uncached.append((factors, cache_key, self._oof_residual(factors)))
        if not uncached:
            return rankings
        signed_mean_ic, valid_counts = vectorized_residual_scores_batch(
            prepared.train,
            np.column_stack([item[2] for item in uncached]),
            min_count=int(self.preprocess_config["min_cross_section"]),
        )
        factor_names = prepared.train.columns.to_numpy()
        for path, (factors, cache_key, _) in enumerate(uncached):
            remaining = ~np.isin(factor_names, factors)
            ranked = pd.DataFrame({
                "candidate": factor_names[remaining],
                "score": np.abs(signed_mean_ic[path, remaining]),
                "signed_mean_ic": signed_mean_ic[path, remaining],
                "dates": valid_counts[path, remaining],
            }).dropna(subset=["score"])
            ranked = ranked.sort_values(["score", "candidate"], ascending=[False, True])
            self._ranking_cache[cache_key] = ranked
            rankings[factors] = ranked
        return rankings
