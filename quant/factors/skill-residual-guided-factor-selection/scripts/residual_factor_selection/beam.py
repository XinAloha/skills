from __future__ import annotations

import json
import multiprocessing as mp
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from .data import build_temporal_fold_masks
from .metrics import prediction_metrics
from .ridge import RidgeModel, fit_ridge
from .selector import (
    PreparedFeatures,
    SelectionResult,
    json_list,
    vectorized_residual_scores,
    vectorized_residual_scores_batch,
)


_BEAM_CV_SELECTOR: BeamResidualSelector | None = None


def _parallel_cv_worker(factors: tuple[str, ...]) -> tuple[tuple[str, ...], CVResult]:
    if _BEAM_CV_SELECTOR is None:
        raise RuntimeError("Parallel CV selector was not initialized")
    model_threads = int(_BEAM_CV_SELECTOR.model_config.get("model_threads", 1))
    with threadpool_limits(limits=model_threads):
        return factors, _BEAM_CV_SELECTOR._cv_score_prepared(factors)


@dataclass
class BeamState:
    factors: tuple[str, ...]
    cv_score: float
    cv_mean_ic: float
    cv_std_ic: float
    cv_min_ic: float
    cv_se: float
    ridge_alpha: float
    fold_ics: tuple[float, ...]
    parent_id: str
    path_id: str
    priority_score: float | None = None
    continuation_score: float = 0.0
    recent_improvements: tuple[float, ...] = ()
    residual_score: float = np.nan


@dataclass(frozen=True)
class CVResult:
    score: float
    mean_ic: float
    std_ic: float
    min_ic: float
    standard_error: float
    ridge_alpha: float
    fold_ics: tuple[float, ...]


@dataclass(frozen=True)
class PreparedCVFold:
    gram: np.ndarray
    rhs: np.ndarray
    score_features: np.ndarray
    score_target: np.ndarray
    score_boundaries: np.ndarray


@dataclass(frozen=True)
class PreparedResidualObjective:
    gram: np.ndarray
    rhs: np.ndarray
    target_sum_squares: float
    baseline_sum_squares: float


def aggregate_cv_score(
    fold_ics: list[float] | tuple[float, ...],
    stability_penalty: float,
    factor_count: int,
    complexity_penalty: float,
    min_year_weight: float = 0.0,
) -> tuple[float, float, float, float, float]:
    values = np.asarray(fold_ics, dtype=float)
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return -np.inf, np.nan, np.nan, np.nan, np.nan
    mean_ic = float(finite.mean())
    std_ic = float(finite.std(ddof=0))
    min_ic = float(finite.min())
    standard_error = std_ic / np.sqrt(len(finite))
    score = mean_ic - stability_penalty * std_ic + min_year_weight * min_ic - complexity_penalty * factor_count
    return score, mean_ic, std_ic, min_ic, standard_error


def _mean_daily_correlation(
    prediction: np.ndarray,
    target: np.ndarray,
    boundaries: np.ndarray,
    min_count: int,
) -> float:
    correlation_sum = 0.0
    valid_days = 0
    for start, end in zip(boundaries[:-1], boundaries[1:]):
        daily_prediction = prediction[start:end]
        daily_target = target[start:end]
        finite = np.isfinite(daily_prediction) & np.isfinite(daily_target)
        if finite.sum() < min_count:
            continue
        centered_prediction = daily_prediction[finite] - daily_prediction[finite].mean()
        centered_target = daily_target[finite] - daily_target[finite].mean()
        denominator = np.sqrt(
            np.dot(centered_prediction, centered_prediction) * np.dot(centered_target, centered_target)
        )
        if denominator > 0:
            correlation_sum += float(np.dot(centered_prediction, centered_target) / denominator)
            valid_days += 1
    return correlation_sum / valid_days if valid_days else np.nan


def factor_jaccard(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    left_set, right_set = set(left), set(right)
    return len(left_set & right_set) / len(left_set | right_set)


def beam_priority(state: BeamState) -> float:
    return state.cv_score if state.priority_score is None else state.priority_score


def select_diverse_states(states: list[BeamState], width: int, max_jaccard: float) -> list[BeamState]:
    selected: list[BeamState] = []
    ordered = sorted(states, key=lambda item: (-beam_priority(item), -item.cv_score, item.factors))
    for state in ordered:
        if all(factor_jaccard(state.factors, kept.factors) <= max_jaccard for kept in selected):
            selected.append(state)
        if len(selected) == width:
            break
    if len(selected) < width:
        selected_sets = {frozenset(state.factors) for state in selected}
        for state in ordered:
            if frozenset(state.factors) not in selected_sets:
                selected.append(state)
                selected_sets.add(frozenset(state.factors))
            if len(selected) == width:
                break
    return selected


class BeamResidualSelector:
    def __init__(
        self,
        preprocess_config: dict,
        model_config: dict,
        selection_config: dict,
        beam_config: dict,
        embargo_bars: int = 0,
    ):
        self.preprocess_config = preprocess_config
        self.model_config = model_config
        self.selection_config = selection_config
        self.beam_config = beam_config
        self.embargo_bars = int(embargo_bars)
        self._factor_positions: dict[str, int] = {}
        self._cv_folds: list[PreparedCVFold] = []
        self._cv_cache: dict[tuple[str, ...], CVResult] = {}
        self._ranking_cache: dict[tuple[str, ...], pd.DataFrame] = {}
        self._residual_objective: PreparedResidualObjective | None = None
        self._residual_cache: dict[tuple[str, ...], float] = {}

    def _fit(
        self, features: pd.DataFrame, target: pd.Series, factors: tuple[str, ...], alpha: float | None = None
    ) -> RidgeModel:
        return fit_ridge(
            features.loc[:, list(factors)],
            target,
            alpha=float(self.model_config["ridge_alpha"] if alpha is None else alpha),
            equal_date_weight=bool(self.model_config["equal_date_weight"]),
        )

    def _root_candidates(self, prepared: PreparedFeatures, target: pd.Series) -> list[str]:
        return list(prepared.train.columns)

    def _save_search_checkpoint(self, beam_history: list[dict], rankings: list[dict]) -> None:
        checkpoint_path = self.beam_config.get("checkpoint_path")
        if not checkpoint_path:
            return
        path = Path(checkpoint_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(beam_history).to_csv(path, index=False)
        pd.DataFrame(rankings).to_csv(path.with_name(f"{path.stem}_rankings.csv"), index=False)

    def _cv_score(
        self, prepared: PreparedFeatures, target: pd.Series, factors: tuple[str, ...]
    ) -> CVResult:
        cache_key = tuple(sorted(factors))
        cached = self._cv_cache.get(cache_key)
        if cached is not None:
            return cached
        if self._cv_folds and self.selection_config["score_method"] == "pearson":
            result = self._cv_score_prepared(factors)
            self._cv_cache[cache_key] = result
            return result
        dates = target.index.get_level_values("datetime")
        alphas = [float(value) for value in self.beam_config.get("ridge_alphas", [self.model_config["ridge_alpha"]])]
        results: list[CVResult] = []
        for alpha in alphas:
            fold_scores: list[float] = []
            for fold in self.beam_config["cv_folds"]:
                fit_mask, score_mask = build_temporal_fold_masks(dates, fold, self.embargo_bars)
                model = self._fit(prepared.train.loc[fit_mask], target.loc[fit_mask], factors, alpha)
                prediction = model.predict(prepared.train.loc[score_mask, list(factors)])
                metrics = prediction_metrics(
                    prediction,
                    target.loc[score_mask],
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
            results.append(CVResult(score, mean_ic, std_ic, min_ic, standard_error, alpha, tuple(fold_scores)))
        result = max(results, key=lambda result: (result.score, -result.ridge_alpha))
        self._cv_cache[cache_key] = result
        return result

    def _prepare_cv(self, prepared: PreparedFeatures, target: pd.Series) -> None:
        features = prepared.train
        aligned_target = target.reindex(features.index)
        values = features.to_numpy(dtype=float, copy=False)
        target_values = aligned_target.to_numpy(dtype=float)
        dates = features.index.get_level_values("datetime")
        self._factor_positions = {name: position for position, name in enumerate(features.columns)}
        self._cv_folds = []
        self._cv_cache.clear()
        self._ranking_cache.clear()
        self._residual_cache.clear()
        if bool(self.model_config["equal_date_weight"]):
            _, inverse, counts = np.unique(dates.to_numpy(), return_inverse=True, return_counts=True)
            full_weights = 1.0 / counts[inverse]
        else:
            full_weights = np.ones(len(values), dtype=float)
        weighted_values = values * full_weights[:, None]
        full_gram = np.empty((values.shape[1] + 1, values.shape[1] + 1), dtype=float)
        full_gram[0, 0] = full_weights.sum()
        full_gram[0, 1:] = full_weights @ values
        full_gram[1:, 0] = full_gram[0, 1:]
        full_gram[1:, 1:] = values.T @ weighted_values
        full_rhs = np.r_[full_weights @ target_values, weighted_values.T @ target_values]
        weighted_mean = float(full_rhs[0] / full_gram[0, 0])
        target_ss = float(full_weights @ np.square(target_values))
        centered_target_ss = float(full_weights @ np.square(target_values - weighted_mean))
        self._residual_objective = PreparedResidualObjective(full_gram, full_rhs, target_ss, centered_target_ss)
        for fold in self.beam_config["cv_folds"]:
            fit_mask, score_mask = build_temporal_fold_masks(dates, fold, self.embargo_bars)
            fit_values = values[fit_mask]
            fit_target = target_values[fit_mask]
            fit_dates = dates[fit_mask].to_numpy()
            if bool(self.model_config["equal_date_weight"]):
                _, inverse, counts = np.unique(fit_dates, return_inverse=True, return_counts=True)
                weights = 1.0 / counts[inverse]
            else:
                weights = np.ones(len(fit_values), dtype=float)
            weighted_values = fit_values * weights[:, None]
            gram = np.empty((fit_values.shape[1] + 1, fit_values.shape[1] + 1), dtype=float)
            gram[0, 0] = weights.sum()
            gram[0, 1:] = weights @ fit_values
            gram[1:, 0] = gram[0, 1:]
            gram[1:, 1:] = fit_values.T @ weighted_values
            rhs = np.r_[weights @ fit_target, weighted_values.T @ fit_target]
            score_dates = dates[score_mask].to_numpy()
            boundaries = np.r_[0, np.flatnonzero(score_dates[1:] != score_dates[:-1]) + 1, len(score_dates)]
            self._cv_folds.append(
                PreparedCVFold(gram, rhs, values[score_mask], target_values[score_mask], boundaries)
            )

    def _residual_score(self, factors: tuple[str, ...]) -> float:
        cache_key = tuple(sorted(factors))
        cached = self._residual_cache.get(cache_key)
        if cached is not None:
            return cached
        if self._residual_objective is None:
            raise RuntimeError("Residual objective has not been prepared")
        positions = np.asarray([self._factor_positions[name] for name in factors], dtype=int)
        design_positions = np.r_[0, positions + 1]
        gram = self._residual_objective.gram[np.ix_(design_positions, design_positions)]
        rhs = self._residual_objective.rhs[design_positions]
        alpha = float(self.beam_config.get("residual_ridge_alpha", self.model_config["ridge_alpha"]))
        lhs = gram.copy()
        lhs.flat[:: len(lhs) + 1] += alpha
        lhs[0, 0] -= alpha
        solution = np.linalg.pinv(lhs) @ rhs
        residual_ss = self._residual_objective.target_sum_squares - 2.0 * float(solution @ rhs)
        residual_ss += float(solution @ gram @ solution)
        score = 1.0 - residual_ss / self._residual_objective.baseline_sum_squares
        self._residual_cache[cache_key] = score
        return score

    def _cv_score_prepared(self, factors: tuple[str, ...]) -> CVResult:
        positions = np.asarray([self._factor_positions[name] for name in factors], dtype=int)
        design_positions = np.r_[0, positions + 1]
        results: list[CVResult] = []
        alphas = [float(value) for value in self.beam_config.get("ridge_alphas", [self.model_config["ridge_alpha"]])]
        for alpha in alphas:
            fold_scores: list[float] = []
            for fold in self._cv_folds:
                lhs = fold.gram[np.ix_(design_positions, design_positions)].copy()
                lhs.flat[:: len(lhs) + 1] += alpha
                lhs[0, 0] -= alpha
                solution = np.linalg.pinv(lhs) @ fold.rhs[design_positions]
                prediction = solution[0] + fold.score_features[:, positions] @ solution[1:]
                fold_scores.append(
                    _mean_daily_correlation(
                        prediction,
                        fold.score_target,
                        fold.score_boundaries,
                        int(self.preprocess_config["min_cross_section"]),
                    )
                )
            score, mean_ic, std_ic, min_ic, standard_error = aggregate_cv_score(
                fold_scores,
                stability_penalty=float(self.beam_config["stability_penalty"]),
                factor_count=len(factors),
                complexity_penalty=float(self.beam_config.get("complexity_penalty", 0.0)),
                min_year_weight=float(self.beam_config.get("min_year_weight", 0.0)),
            )
            results.append(CVResult(score, mean_ic, std_ic, min_ic, standard_error, alpha, tuple(fold_scores)))
        return max(results, key=lambda result: (result.score, -result.ridge_alpha))

    def _cv_scores_batch(
        self,
        prepared: PreparedFeatures,
        target: pd.Series,
        factor_sets: list[tuple[str, ...]],
    ) -> dict[tuple[str, ...], CVResult]:
        results: dict[tuple[str, ...], CVResult] = {}
        uncached: list[tuple[str, ...]] = []
        seen: set[tuple[str, ...]] = set()
        for factors in factor_sets:
            cache_key = tuple(sorted(factors))
            cached = self._cv_cache.get(cache_key)
            if cached is not None:
                results[factors] = cached
            elif cache_key not in seen:
                seen.add(cache_key)
                uncached.append(factors)
        if not uncached:
            return results

        jobs = min(int(self.beam_config.get("cv_jobs", 1)), len(uncached))
        if jobs <= 1 or not self._cv_folds or self.selection_config["score_method"] != "pearson":
            computed = [(factors, self._cv_score(prepared, target, factors)) for factors in uncached]
        else:
            global _BEAM_CV_SELECTOR
            _BEAM_CV_SELECTOR = self
            with mp.get_context("fork").Pool(processes=jobs) as pool:
                computed = pool.map(_parallel_cv_worker, uncached)
            _BEAM_CV_SELECTOR = None
        for factors, result in computed:
            cache_key = tuple(sorted(factors))
            self._cv_cache[cache_key] = result
        for factors in factor_sets:
            results[factors] = self._cv_cache[tuple(sorted(factors))]
        return results

    def _checkpoint_row(
        self,
        path_id: str,
        factors: tuple[str, ...],
        train_metrics: dict,
        cv_result: CVResult,
        ridge_alpha: float,
        residual_score: float,
    ) -> dict:
        row = {
            "path_id": path_id,
            "iteration": len(factors),
            "added_factor": factors[-1],
            "factor_count": len(factors),
            "selected_factors": json_list(list(factors)),
            "train_mean_ic": train_metrics["mean_ic"],
            "train_icir": train_metrics["icir"],
            "cv_score": cv_result.score,
            "cv_mean_ic": cv_result.mean_ic,
            "cv_std_ic": cv_result.std_ic,
            "cv_min_ic": cv_result.min_ic,
            "cv_se": cv_result.standard_error,
            "ridge_alpha": ridge_alpha,
            "residual_score": residual_score,
            "valid_mean_ic": cv_result.mean_ic,
            "valid_icir": cv_result.mean_ic / cv_result.std_ic if cv_result.std_ic > 0 else np.nan,
            "valid_mse": np.nan,
            "is_best": False,
        }
        for fold, fold_ic in zip(self.beam_config["cv_folds"], cv_result.fold_ics):
            row[f"ic_{pd.Timestamp(fold['score_start']).year}"] = fold_ic
        return row

    def _rank_candidates(
        self,
        prepared: PreparedFeatures,
        target: pd.Series,
        factors: tuple[str, ...],
        alpha: float | None = None,
    ) -> tuple[RidgeModel, pd.DataFrame]:
        model = self._fit(prepared.train, target, factors, alpha)
        cache_key = tuple(sorted(factors))
        cached = self._ranking_cache.get(cache_key)
        if cached is not None:
            return model, cached
        residual = target - model.predict(prepared.train.loc[:, list(factors)])
        remaining = [name for name in prepared.train.columns if name not in factors]
        ranked = vectorized_residual_scores(
            prepared.train.loc[:, remaining],
            residual,
            min_count=int(self.preprocess_config["min_cross_section"]),
        ).dropna(subset=["score"])
        ranked = ranked.sort_values(["score", "candidate"], ascending=[False, True])
        self._ranking_cache[cache_key] = ranked
        return model, ranked

    def _rank_candidates_batch(
        self,
        prepared: PreparedFeatures,
        target: pd.Series,
        requests: list[tuple[tuple[str, ...], float]],
    ) -> dict[tuple[str, ...], pd.DataFrame]:
        rankings: dict[tuple[str, ...], pd.DataFrame] = {}
        uncached: list[tuple[tuple[str, ...], tuple[str, ...], np.ndarray]] = []
        for factors, alpha in requests:
            cache_key = tuple(sorted(factors))
            cached = self._ranking_cache.get(cache_key)
            if cached is not None:
                rankings[factors] = cached
                continue
            model = self._fit(prepared.train, target, factors, alpha)
            residual = target - model.predict(prepared.train.loc[:, list(factors)])
            uncached.append((factors, cache_key, residual.to_numpy(dtype=float)))
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
            ranked = pd.DataFrame(
                {
                    "candidate": factor_names[remaining],
                    "score": np.abs(signed_mean_ic[path, remaining]),
                    "signed_mean_ic": signed_mean_ic[path, remaining],
                    "dates": valid_counts[path, remaining],
                }
            ).dropna(subset=["score"])
            ranked = ranked.sort_values(["score", "candidate"], ascending=[False, True])
            self._ranking_cache[cache_key] = ranked
            rankings[factors] = ranked
        return rankings

    def _resume_frontier(self) -> tuple[list[BeamState], list[dict], int]:
        history_path = self.beam_config.get("resume_history")
        if not history_path:
            return [], [], 0
        frame = pd.read_csv(Path(history_path))
        if frame.empty:
            raise ValueError(f"Empty beam resume history: {history_path}")
        start_depth = int(frame["depth"].max())
        frontier = frame.loc[(frame["depth"] == start_depth) & frame["kept"].astype(bool)].copy()
        if frontier.empty:
            raise ValueError(f"No kept frontier at depth {start_depth}: {history_path}")
        rows_by_path = {str(row.path_id): row for row in frame.itertuples(index=False)}
        trend_window = int(self.beam_config.get("trend_window", 3))
        fold_columns = [f"ic_{pd.Timestamp(fold['score_start']).year}" for fold in self.beam_config["cv_folds"]]
        beam: list[BeamState] = []
        for row in frontier.itertuples(index=False):
            improvements: list[float] = []
            current = row
            while len(improvements) < trend_window and str(current.parent_id) in rows_by_path:
                parent = rows_by_path[str(current.parent_id)]
                improvements.append(float(current.cv_score) - float(parent.cv_score))
                current = parent
            beam.append(
                BeamState(
                    tuple(json.loads(row.factors)),
                    float(row.cv_score),
                    float(row.cv_mean_ic),
                    float(row.cv_std_ic),
                    float(row.cv_min_ic),
                    float(row.cv_se),
                    float(row.ridge_alpha),
                    tuple(float(getattr(row, column)) for column in fold_columns),
                    str(row.parent_id),
                    str(row.path_id),
                    priority_score=float(row.priority_score),
                    continuation_score=float(row.continuation_score),
                    recent_improvements=tuple(reversed(improvements)),
                    residual_score=float(row.residual_score),
                )
            )
        return beam, frame.to_dict("records"), start_depth

    def fit(
        self,
        train_target: pd.Series,
        valid_target: pd.Series,
        prepared: PreparedFeatures,
        initial_factor: str | None,
    ) -> SelectionResult:
        deterministic_roots = bool(self.beam_config.get("deterministic_roots", False))
        if not deterministic_roots and initial_factor not in prepared.train.columns:
            raise ValueError(f"Unknown initial factor: {initial_factor}")
        factor_positions = {name: position for position, name in enumerate(prepared.train.columns)}
        if not self._cv_folds or self._factor_positions != factor_positions:
            self._prepare_cv(prepared, train_target)
        beam_width = int(self.beam_config["width"])
        branch_width = int(self.beam_config["branch_width"])
        final_depth = int(self.beam_config["final_depth"])
        max_jaccard = float(self.beam_config["diversity_max_jaccard"])
        rankings: list[dict] = []
        beam_history: list[dict] = []
        search_objective = str(self.beam_config.get("search_objective", "cv"))
        if search_objective not in {"cv", "residual"}:
            raise ValueError(f"Unknown beam search objective: {search_objective}")
        residual_alpha = float(self.beam_config.get("residual_ridge_alpha", self.model_config["ridge_alpha"]))

        beam, beam_history, start_depth = self._resume_frontier()
        if beam:
            missing = sorted({factor for state in beam for factor in state.factors} - set(prepared.train.columns))
            if missing:
                raise ValueError(f"Resume history contains unknown factors: {missing}")
        elif deterministic_roots:
            roots = []
            root_candidates = self._root_candidates(prepared, train_target)
            root_cv_results = (
                self._cv_scores_batch(
                    prepared,
                    train_target,
                    [(factor,) for factor in root_candidates],
                )
                if search_objective == "cv"
                else {}
            )
            for factor in root_candidates:
                if search_objective == "residual":
                    residual_score = self._residual_score((factor,))
                    cv_result = CVResult(np.nan, np.nan, np.nan, np.nan, np.nan, residual_alpha, ())
                else:
                    cv_result = root_cv_results[(factor,)]
                    residual_score = np.nan
                if np.isfinite(residual_score if search_objective == "residual" else cv_result.score):
                    roots.append(BeamState(
                        (factor,), cv_result.score, cv_result.mean_ic, cv_result.std_ic,
                        cv_result.min_ic, cv_result.standard_error, cv_result.ridge_alpha,
                        cv_result.fold_ics, "root", "", priority_score=residual_score,
                        residual_score=residual_score,
                    ))
            root_width = max(beam_width, int(self.beam_config.get("root_width", beam_width)))
            roots = sorted(roots, key=lambda state: (-beam_priority(state), state.factors))[:root_width]
            beam = select_diverse_states(roots, beam_width, max_jaccard)
        else:
            initial_cv = self._cv_score(prepared, train_target, (str(initial_factor),))
            beam = [BeamState(
                (str(initial_factor),), initial_cv.score, initial_cv.mean_ic, initial_cv.std_ic,
                initial_cv.min_ic, initial_cv.standard_error, initial_cv.ridge_alpha,
                initial_cv.fold_ics, "", ""
            )]
        if start_depth == 0:
            start_depth = 1
            for position, state in enumerate(beam, start=1):
                state.path_id = f"b01p{position:02d}"
                beam_history.append(self._beam_row(1, state, True))

        trend_window = int(self.beam_config.get("trend_window", 3))
        trend_weight = float(self.beam_config.get("trend_weight", 0.0))
        continuation_weight = float(self.beam_config.get("continuation_weight", 0.0))
        continuation_probe_width = int(self.beam_config.get("continuation_probe_width", 0))
        early_stopping_patience = int(self.beam_config.get("early_stopping_patience", 0))
        early_stopping_min_delta = float(self.beam_config.get("early_stopping_min_delta", 0.0))
        historical_scores = [float(row["cv_score"]) for row in beam_history if np.isfinite(row["cv_score"])]
        best_search_score = max(historical_scores, default=-np.inf)
        stale_depths = 0
        stopped_early = False
        for depth in range(start_depth + 1, final_depth + 1):
            candidates: dict[frozenset[str], BeamState] = {}
            parent_rankings = self._rank_candidates_batch(
                prepared,
                train_target,
                [(parent.factors, parent.ridge_alpha) for parent in beam],
            )
            expansions: list[tuple[BeamState, tuple[str, ...]]] = []
            for parent in beam:
                ranked = parent_rankings[parent.factors]
                for rank, row in enumerate(ranked.head(branch_width).itertuples(index=False), start=1):
                    factors = parent.factors + (str(row.candidate),)
                    expansions.append((parent, factors))
                    rankings.append(
                        {
                            "stage": "beam",
                            "iteration": depth - 1,
                            "path_id": parent.path_id,
                            "rank": rank,
                            "candidate": row.candidate,
                            "score": row.score,
                            "signed_mean_ic": row.signed_mean_ic,
                            "dates": row.dates,
                        }
                    )
            cv_results = (
                self._cv_scores_batch(prepared, train_target, [factors for _, factors in expansions])
                if search_objective == "cv"
                else {}
            )
            for parent, factors in expansions:
                key = frozenset(factors)
                if search_objective == "residual":
                    residual_score = self._residual_score(factors)
                    cv_result = CVResult(np.nan, np.nan, np.nan, np.nan, np.nan, residual_alpha, ())
                else:
                    cv_result = cv_results[factors]
                    residual_score = np.nan
                objective_score = residual_score if search_objective == "residual" else cv_result.score
                if not np.isfinite(objective_score):
                    continue
                state = BeamState(
                    factors, cv_result.score, cv_result.mean_ic, cv_result.std_ic,
                    cv_result.min_ic, cv_result.standard_error, cv_result.ridge_alpha,
                    cv_result.fold_ics, parent.path_id, "",
                    recent_improvements=(parent.recent_improvements + (cv_result.score - parent.cv_score,))[-trend_window:],
                    residual_score=residual_score,
                )
                if search_objective == "residual":
                    state.priority_score = residual_score
                    state.recent_improvements = ()
                else:
                    state.priority_score = state.cv_score + trend_weight * float(np.mean(state.recent_improvements))
                previous = candidates.get(key)
                if previous is None or beam_priority(state) > beam_priority(previous):
                    candidates[key] = state
            candidate_states = list(candidates.values())
            if search_objective == "cv" and continuation_weight > 0.0 and continuation_probe_width > 0:
                probed = sorted(candidate_states, key=lambda state: (-beam_priority(state), state.factors))[
                    :continuation_probe_width
                ]
                probe_rankings = self._rank_candidates_batch(
                    prepared,
                    train_target,
                    [(state.factors, state.ridge_alpha) for state in probed],
                )
                for state in probed:
                    next_ranked = probe_rankings[state.factors]
                    state.continuation_score = float(next_ranked.iloc[0]["score"]) if not next_ranked.empty else 0.0
                    state.priority_score = beam_priority(state) + continuation_weight * state.continuation_score
            beam = select_diverse_states(candidate_states, beam_width, max_jaccard)
            for position, state in enumerate(beam, start=1):
                state.path_id = f"b{depth:02d}p{position:02d}"
                beam_history.append(self._beam_row(depth, state, True))
            self._save_search_checkpoint(beam_history, rankings)
            if bool(self.beam_config.get("progress", False)) and beam:
                best = max(beam, key=beam_priority)
                if search_objective == "residual":
                    print(f"depth={depth}/{final_depth} residual_r2={best.residual_score:.6f}", flush=True)
                else:
                    print(
                        f"depth={depth}/{final_depth} best_cv={best.cv_score:.6f} "
                        f"priority={beam_priority(best):.6f} continuation={best.continuation_score:.6f}",
                        flush=True,
                    )
            current_best = max(beam_priority(state) if search_objective == "residual" else state.cv_score for state in beam)
            if current_best > best_search_score + early_stopping_min_delta:
                best_search_score = current_best
                stale_depths = 0
            else:
                stale_depths += 1
            if early_stopping_patience > 0 and stale_depths >= early_stopping_patience:
                stopped_early = True
                if bool(self.beam_config.get("progress", False)):
                    print(
                        f"early_stop depth={depth} stale_depths={stale_depths} best_cv={best_search_score:.6f}",
                        flush=True,
                    )
                break

        checkpoints: list[tuple[dict, tuple[str, ...], RidgeModel]] = []
        frontier_rows: list[dict] = []
        for depth in sorted({int(row["depth"]) for row in beam_history}):
            depth_rows = [row for row in beam_history if int(row["depth"]) == depth]
            frontier_key = "residual_score" if search_objective == "residual" else "cv_score"
            frontier_rows.append(max(depth_rows, key=lambda row: float(row[frontier_key])))
        for beam_row in frontier_rows:
            factors = tuple(json.loads(beam_row["factors"]))
            cv_result = self._cv_score(prepared, train_target, factors)
            model_alpha = residual_alpha if search_objective == "residual" else cv_result.ridge_alpha
            model = self._fit(prepared.train, train_target, factors, model_alpha)
            train_metrics = prediction_metrics(
                model.predict(prepared.train.loc[:, list(factors)]),
                train_target,
                method=self.selection_config["score_method"],
                min_count=int(self.preprocess_config["min_cross_section"]),
            )
            checkpoints.append(
                (
                    self._checkpoint_row(
                        f"beam_{beam_row['path_id']}",
                        factors,
                        train_metrics,
                        cv_result,
                        model_alpha,
                        float(beam_row["residual_score"]),
                    ),
                    factors,
                    model,
                )
            )
        peak_index = max(
            range(len(checkpoints)),
            key=lambda index: float(checkpoints[index][0]["cv_score"])
            if np.isfinite(checkpoints[index][0]["cv_score"])
            else -np.inf,
        )
        best_index = peak_index
        if search_objective == "residual":
            selection_depth = int(self.beam_config.get("residual_selection_depth", final_depth))
            best_index = next(
                index for index, (row, _, _) in enumerate(checkpoints)
                if int(row["factor_count"]) == selection_depth
            )
        else:
            deep_tolerance = self.beam_config.get("deep_selection_tolerance")
        if search_objective == "cv" and deep_tolerance is not None:
            threshold = float(checkpoints[peak_index][0]["cv_score"]) - float(deep_tolerance)
            eligible = [
                index for index, (row, _, _) in enumerate(checkpoints)
                if np.isfinite(row["cv_score"]) and float(row["cv_score"]) >= threshold
            ]
            best_index = max(
                eligible,
                key=lambda index: (
                    int(checkpoints[index][0]["factor_count"]),
                    float(checkpoints[index][0]["cv_score"]),
                ),
            )
        elif search_objective == "cv" and bool(self.beam_config.get("one_standard_error", False)):
            peak_row = checkpoints[peak_index][0]
            threshold = float(peak_row["cv_score"]) - float(peak_row["cv_se"])
            eligible = [
                index for index, (row, _, _) in enumerate(checkpoints)
                if np.isfinite(row["cv_score"]) and float(row["cv_score"]) >= threshold
            ]
            best_index = min(
                eligible,
                key=lambda index: (
                    int(checkpoints[index][0]["factor_count"]),
                    -float(checkpoints[index][0]["cv_score"]),
                ),
            )
        checkpoints[best_index][0]["is_best"] = True
        best_row, best_factors, best_model = checkpoints[best_index]
        history = pd.DataFrame([row for row, _, _ in checkpoints])
        history.attrs["beam_history"] = pd.DataFrame(beam_history)
        history.attrs["stopped_early"] = stopped_early
        history.attrs["searched_depth"] = max(int(row["depth"]) for row in beam_history)
        history.attrs["stale_depths"] = stale_depths
        return SelectionResult(
            history=history,
            rankings=pd.DataFrame(rankings),
            best_iteration=int(best_row["iteration"]),
            selected_factors=list(best_factors),
            model=best_model,
        )

    def _beam_row(self, depth: int, state: BeamState, kept: bool) -> dict:
        return {
            "depth": depth,
            "path_id": state.path_id,
            "parent_id": state.parent_id,
            "factors": json_list(list(state.factors)),
            "cv_score": state.cv_score,
            "cv_mean_ic": state.cv_mean_ic,
            "cv_std_ic": state.cv_std_ic,
            "cv_min_ic": state.cv_min_ic,
            "cv_se": state.cv_se,
            "ridge_alpha": state.ridge_alpha,
            "priority_score": beam_priority(state),
            "residual_score": state.residual_score,
            "continuation_score": state.continuation_score,
            "recent_improvement": float(np.mean(state.recent_improvements)) if state.recent_improvements else 0.0,
            **{
                f"ic_{pd.Timestamp(fold['score_start']).year}": fold_ic
                for fold, fold_ic in zip(self.beam_config["cv_folds"], state.fold_ics)
            },
            "kept": kept,
        }
