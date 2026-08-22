from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .beam import BeamResidualSelector, CVResult
from .metrics import prediction_metrics
from .selector import PreparedFeatures, SelectionResult, json_list


@dataclass(frozen=True)
class PoolCandidate:
    candidate: str
    factors: tuple[str, ...]
    removed_factor: str | None
    cv_result: CVResult


def select_smallest_weight_factor(factors: tuple[str, ...], coefficients: np.ndarray) -> str:
    if len(factors) != len(coefficients):
        raise ValueError("factors and coefficients must have the same length")
    return min(zip(factors, np.abs(coefficients)), key=lambda item: (item[1], item[0]))[0]


class ExhaustivePoolSelector(BeamResidualSelector):
    """Exhaustive greedy joint-CV selection over a fixed factor bank."""

    def __init__(
        self,
        preprocess_config: dict,
        model_config: dict,
        selection_config: dict,
        beam_config: dict,
        pool_config: dict,
        embargo_bars: int = 0,
    ):
        super().__init__(preprocess_config, model_config, selection_config, beam_config, embargo_bars)
        self.pool_config = pool_config

    def _full_sample_coefficients(self, factors: tuple[str, ...], alpha: float) -> np.ndarray:
        if self._residual_objective is None:
            raise RuntimeError("Pool-search objective has not been prepared")
        positions = np.asarray([self._factor_positions[name] for name in factors], dtype=int)
        design_positions = np.r_[0, positions + 1]
        lhs = self._residual_objective.gram[np.ix_(design_positions, design_positions)].copy()
        lhs.flat[:: len(lhs) + 1] += alpha
        lhs[0, 0] -= alpha
        solution = np.linalg.pinv(lhs) @ self._residual_objective.rhs[design_positions]
        return solution[1:]

    def _candidate_pool(
        self,
        selected: tuple[str, ...],
        candidate: str,
        pool_capacity: int | None,
        pruning_alpha: float,
    ) -> tuple[tuple[str, ...], str | None]:
        augmented = selected + (candidate,)
        if pool_capacity is None or len(augmented) <= pool_capacity:
            return augmented, None
        coefficients = self._full_sample_coefficients(augmented, pruning_alpha)
        removed = select_smallest_weight_factor(augmented, coefficients)
        return tuple(factor for factor in augmented if factor != removed), removed

    def fit(
        self,
        train_target: pd.Series,
        valid_target: pd.Series,
        prepared: PreparedFeatures,
    ) -> SelectionResult:
        del valid_target
        factor_positions = {name: position for position, name in enumerate(prepared.train.columns)}
        if not self._cv_folds or self._factor_positions != factor_positions:
            self._prepare_cv(prepared, train_target)

        config = self.pool_config
        max_steps = int(config.get("max_steps", self.selection_config["max_factors"]))
        pool_capacity_value = config.get("pool_capacity")
        pool_capacity = None if pool_capacity_value is None else int(pool_capacity_value)
        if pool_capacity is not None and pool_capacity < 1:
            raise ValueError("pool.pool_capacity must be positive or null")
        patience = int(config.get("patience", 0))
        min_delta = float(config.get("min_delta", 0.0))
        top_n_log = int(config.get("top_n_log", self.selection_config.get("top_n_log", 10)))
        progress = bool(config.get("progress", False))
        pruning_alpha = float(config.get("pruning_alpha", self.model_config["ridge_alpha"]))

        selected: tuple[str, ...] = ()
        proposed: set[str] = set()
        current_score = -np.inf
        stale_steps = 0
        candidate_evaluations = 0
        history_rows: list[dict] = []
        ranking_rows: list[dict] = []
        checkpoints: list[tuple[dict, tuple[str, ...]]] = []

        for step in range(1, max_steps + 1):
            remaining = [name for name in prepared.train.columns if name not in proposed and name not in selected]
            if not remaining:
                break

            candidate_pools: dict[str, tuple[tuple[str, ...], str | None]] = {}
            unique_pools: list[tuple[str, ...]] = []
            seen_pools: set[tuple[str, ...]] = set()
            for candidate in remaining:
                factors, removed = self._candidate_pool(selected, candidate, pool_capacity, pruning_alpha)
                candidate_pools[candidate] = (factors, removed)
                cache_key = tuple(sorted(factors))
                if cache_key not in seen_pools:
                    seen_pools.add(cache_key)
                    unique_pools.append(factors)

            cv_results = self._cv_scores_batch(prepared, train_target, unique_pools)
            candidates: list[PoolCandidate] = []
            for candidate in remaining:
                factors, removed = candidate_pools[candidate]
                result = cv_results[factors]
                candidates.append(PoolCandidate(candidate, factors, removed, result))
            candidates.sort(
                key=lambda item: (
                    -item.cv_result.score,
                    item.removed_factor == item.candidate,
                    item.candidate,
                )
            )
            candidate_evaluations += len(candidates)
            best = candidates[0]
            previous_score = current_score
            improvement = np.inf if not np.isfinite(previous_score) else best.cv_result.score - previous_score
            for rank, item in enumerate(candidates[:top_n_log], start=1):
                ranking_rows.append(
                    {
                        "step": step,
                        "rank": rank,
                        "candidate": item.candidate,
                        "removed_factor": item.removed_factor,
                        "factor_count": len(item.factors),
                        "cv_score": item.cv_result.score,
                        "cv_mean_ic": item.cv_result.mean_ic,
                        "cv_std_ic": item.cv_result.std_ic,
                        "cv_min_ic": item.cv_result.min_ic,
                        "ridge_alpha": item.cv_result.ridge_alpha,
                        "increment": np.nan if not np.isfinite(previous_score) else item.cv_result.score - previous_score,
                    }
                )

            if np.isfinite(previous_score) and improvement <= min_delta:
                stale_steps += 1
            else:
                stale_steps = 0
            if np.isfinite(previous_score) and patience == 0 and improvement <= min_delta:
                break
            if np.isfinite(previous_score) and patience > 0 and stale_steps >= patience:
                break

            proposed.add(best.candidate)
            selected = best.factors
            current_score = best.cv_result.score
            model = self._fit(prepared.train, train_target, selected, best.cv_result.ridge_alpha)
            train_metrics = prediction_metrics(
                model.predict(prepared.train.loc[:, list(selected)]),
                train_target,
                method=self.selection_config["score_method"],
                min_count=int(self.preprocess_config["min_cross_section"]),
            )
            row = {
                "path_id": f"pool_{step:03d}",
                "iteration": step,
                "added_factor": best.candidate,
                "removed_factor": best.removed_factor,
                "factor_count": len(selected),
                "selected_factors": json_list(list(selected)),
                "train_mean_ic": train_metrics["mean_ic"],
                "train_icir": train_metrics["icir"],
                "cv_score": best.cv_result.score,
                "cv_mean_ic": best.cv_result.mean_ic,
                "cv_std_ic": best.cv_result.std_ic,
                "cv_min_ic": best.cv_result.min_ic,
                "cv_se": best.cv_result.standard_error,
                "ridge_alpha": best.cv_result.ridge_alpha,
                "increment": np.nan if not np.isfinite(previous_score) else improvement,
                "valid_mean_ic": best.cv_result.mean_ic,
                "valid_icir": (
                    best.cv_result.mean_ic / best.cv_result.std_ic if best.cv_result.std_ic > 0 else np.nan
                ),
                "valid_mse": np.nan,
                "is_best": False,
            }
            for fold, fold_ic in zip(self.beam_config["cv_folds"], best.cv_result.fold_ics):
                row[f"ic_{pd.Timestamp(fold['score_start']).year}"] = fold_ic
            history_rows.append(row)
            checkpoints.append((row, selected))
            if progress:
                action = f" remove={best.removed_factor}" if best.removed_factor is not None else ""
                print(
                    f"step={step}/{max_steps} factors={len(selected)} add={best.candidate}{action} "
                    f"cv={best.cv_result.score:.6f} increment={improvement:.6f}",
                    flush=True,
                )

        if not checkpoints:
            raise RuntimeError("Pool selection produced no checkpoint")
        best_index = max(
            range(len(checkpoints)),
            key=lambda index: (float(checkpoints[index][0]["cv_score"]), -index),
        )
        checkpoints[best_index][0]["is_best"] = True
        best_row, best_factors = checkpoints[best_index]
        best_model = self._fit(
            prepared.train,
            train_target,
            best_factors,
            float(best_row["ridge_alpha"]),
        )
        history = pd.DataFrame(history_rows)
        history.attrs["candidate_evaluations"] = candidate_evaluations
        history.attrs["searched_steps"] = len(history_rows)
        history.attrs["pool_capacity"] = pool_capacity
        return SelectionResult(
            history=history,
            rankings=pd.DataFrame(ranking_rows),
            best_iteration=int(best_row["iteration"]),
            selected_factors=list(best_factors),
            model=best_model,
        )
