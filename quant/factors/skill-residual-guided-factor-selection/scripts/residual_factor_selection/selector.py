from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import FactorStore
from .metrics import daily_correlation, prediction_metrics
from .preprocess import preprocess_factor, preprocess_factor_wide
from .ridge import RidgeModel, fit_ridge


@dataclass
class SelectionResult:
    history: pd.DataFrame
    rankings: pd.DataFrame
    best_iteration: int
    selected_factors: list[str]
    model: object


@dataclass(frozen=True)
class PreparedFeatures:
    train: pd.DataFrame
    valid: pd.DataFrame
    oos: pd.DataFrame | None = None


def residual_score(factor: pd.Series, residual: pd.Series, method: str, min_count: int) -> tuple[float, float, int]:
    daily_ic = daily_correlation(factor, residual, method=method, min_count=min_count)
    if daily_ic.empty:
        return np.nan, np.nan, 0
    mean_ic = float(daily_ic.mean())
    return abs(mean_ic), mean_ic, int(len(daily_ic))


def vectorized_residual_scores(
    features: pd.DataFrame,
    residual: pd.Series,
    min_count: int,
) -> pd.DataFrame:
    aligned_residual = residual.reindex(features.index).to_numpy(dtype=float)
    values = features.to_numpy(dtype=float, copy=False)
    dates = features.index.get_level_values("datetime").to_numpy()
    boundaries = np.r_[0, np.flatnonzero(dates[1:] != dates[:-1]) + 1, len(dates)]
    correlation_sums = np.zeros(values.shape[1], dtype=float)
    valid_counts = np.zeros(values.shape[1], dtype=np.int64)

    for start, end in zip(boundaries[:-1], boundaries[1:]):
        if end - start < min_count:
            continue
        daily_x = values[start:end]
        daily_residual = aligned_residual[start:end]
        finite = np.isfinite(daily_residual)
        if finite.sum() < min_count:
            continue
        daily_x = daily_x[finite]
        daily_residual = daily_residual[finite]
        centered_x = daily_x - daily_x.mean(axis=0)
        centered_residual = daily_residual - daily_residual.mean()
        residual_ss = np.dot(centered_residual, centered_residual)
        factor_ss = np.einsum("ij,ij->j", centered_x, centered_x)
        denominator = np.sqrt(factor_ss * residual_ss)
        valid = denominator > 0
        correlations = np.zeros(values.shape[1], dtype=float)
        correlations[valid] = centered_residual @ centered_x[:, valid] / denominator[valid]
        correlation_sums[valid] += correlations[valid]
        valid_counts[valid] += 1

    signed_mean_ic = np.divide(
        correlation_sums,
        valid_counts,
        out=np.full(values.shape[1], np.nan),
        where=valid_counts > 0,
    )
    return pd.DataFrame(
        {
            "candidate": features.columns,
            "score": np.abs(signed_mean_ic),
            "signed_mean_ic": signed_mean_ic,
            "dates": valid_counts,
        }
    )


def vectorized_residual_scores_batch(
    features: pd.DataFrame,
    residuals: np.ndarray,
    min_count: int,
) -> tuple[np.ndarray, np.ndarray]:
    values = features.to_numpy(dtype=float, copy=False)
    residual_values = np.asarray(residuals, dtype=float)
    if residual_values.ndim != 2 or residual_values.shape[0] != len(features):
        raise ValueError("residuals must have shape (rows, paths)")
    dates = features.index.get_level_values("datetime").to_numpy()
    boundaries = np.r_[0, np.flatnonzero(dates[1:] != dates[:-1]) + 1, len(dates)]
    correlation_sums = np.zeros((residual_values.shape[1], values.shape[1]), dtype=float)
    valid_counts = np.zeros((residual_values.shape[1], values.shape[1]), dtype=np.int64)

    for start, end in zip(boundaries[:-1], boundaries[1:]):
        if end - start < min_count:
            continue
        daily_x = values[start:end]
        daily_residuals = residual_values[start:end]
        if np.isfinite(daily_residuals).all():
            centered_x = daily_x - daily_x.mean(axis=0)
            centered_residuals = daily_residuals - daily_residuals.mean(axis=0)
            factor_ss = np.einsum("ij,ij->j", centered_x, centered_x)
            residual_ss = np.einsum("ij,ij->j", centered_residuals, centered_residuals)
            denominator = np.sqrt(residual_ss[:, None] * factor_ss[None, :])
            valid = denominator > 0
            numerators = centered_residuals.T @ centered_x
            correlations = np.divide(
                numerators,
                denominator,
                out=np.zeros_like(numerators),
                where=valid,
            )
            correlation_sums += correlations
            valid_counts += valid
            continue

        for path in range(residual_values.shape[1]):
            daily_residual = daily_residuals[:, path]
            finite = np.isfinite(daily_residual)
            if finite.sum() < min_count:
                continue
            path_x = daily_x[finite]
            path_residual = daily_residual[finite]
            centered_x = path_x - path_x.mean(axis=0)
            centered_residual = path_residual - path_residual.mean()
            factor_ss = np.einsum("ij,ij->j", centered_x, centered_x)
            residual_ss = np.dot(centered_residual, centered_residual)
            denominator = np.sqrt(factor_ss * residual_ss)
            valid = denominator > 0
            correlation_sums[path, valid] += centered_residual @ centered_x[:, valid] / denominator[valid]
            valid_counts[path, valid] += 1

    signed_mean_ic = np.divide(
        correlation_sums,
        valid_counts,
        out=np.full_like(correlation_sums, np.nan),
        where=valid_counts > 0,
    )
    return signed_mean_ic, valid_counts


class ResidualForwardSelector:
    def __init__(self, store: FactorStore, preprocess_config: dict, model_config: dict, selection_config: dict):
        self.store = store
        self.preprocess_config = preprocess_config
        self.model_config = model_config
        self.selection_config = selection_config
        self._processed: dict[str, pd.Series] = {}

    def factor(self, name: str) -> pd.Series:
        if name not in self._processed:
            self._processed[name] = preprocess_factor(self.store.load(name), self.preprocess_config)
        return self._processed[name]

    def feature_frame(self, names: list[str], index: pd.MultiIndex) -> pd.DataFrame:
        return pd.concat([self.factor(name).reindex(index) for name in names], axis=1).fillna(0.0)

    def prepare_features(
        self,
        train_index: pd.MultiIndex,
        valid_index: pd.MultiIndex,
        oos_index: pd.MultiIndex | None = None,
    ) -> PreparedFeatures:
        names = self.store.factor_names
        train_values = np.empty((len(train_index), len(names)), dtype=np.float64)
        valid_values = np.empty((len(valid_index), len(names)), dtype=np.float64)
        oos_values = None if oos_index is None else np.empty((len(oos_index), len(names)), dtype=np.float64)
        for column, name in enumerate(names):
            processed = preprocess_factor_wide(self.store.load_wide(name), self.preprocess_config)
            stacked = processed.stack(future_stack=True)
            stacked.index = stacked.index.set_names(["datetime", "symbol"])
            train_values[:, column] = stacked.reindex(train_index).fillna(0.0).to_numpy()
            valid_values[:, column] = stacked.reindex(valid_index).fillna(0.0).to_numpy()
            if oos_values is not None and oos_index is not None:
                oos_values[:, column] = stacked.reindex(oos_index).fillna(0.0).to_numpy()
        self._processed.clear()
        self.store.clear_cache()
        return PreparedFeatures(
            train=pd.DataFrame(train_values, index=train_index, columns=names),
            valid=pd.DataFrame(valid_values, index=valid_index, columns=names),
            oos=None if oos_values is None else pd.DataFrame(oos_values, index=oos_index, columns=names),
        )

    def fit(
        self,
        train_target: pd.Series,
        valid_target: pd.Series,
        prepared: PreparedFeatures | None = None,
        random_seed: int | None = None,
        initial_factor: str | None = None,
    ) -> SelectionResult:
        config = self.selection_config
        rng = np.random.default_rng(int(config["random_seed"] if random_seed is None else random_seed))
        initial = initial_factor or config.get("initial_factor") or str(rng.choice(self.store.factor_names))
        if initial not in self.store.factor_names:
            raise ValueError(f"Unknown initial factor: {initial}")
        selected = [initial]
        history: list[dict] = []
        rankings: list[dict] = []
        checkpoints: dict[int, tuple[list[str], RidgeModel]] = {}
        best_score = -np.inf
        best_iteration = 0
        stale = 0

        for iteration in range(1, int(config["max_factors"]) + 1):
            train_x = (
                self.feature_frame(selected, train_target.index)
                if prepared is None
                else prepared.train.loc[:, selected]
            )
            valid_x = (
                self.feature_frame(selected, valid_target.index)
                if prepared is None
                else prepared.valid.loc[:, selected]
            )
            model = fit_ridge(
                train_x,
                train_target,
                alpha=float(self.model_config["ridge_alpha"]),
                equal_date_weight=bool(self.model_config["equal_date_weight"]),
            )
            checkpoints[iteration] = (selected.copy(), model)
            train_prediction = model.predict(train_x)
            valid_prediction = model.predict(valid_x)
            train_metrics = prediction_metrics(
                train_prediction,
                train_target,
                method=config["score_method"],
                min_count=int(self.preprocess_config["min_cross_section"]),
            )
            valid_metrics = prediction_metrics(
                valid_prediction,
                valid_target,
                method=config["score_method"],
                min_count=int(self.preprocess_config["min_cross_section"]),
            )
            valid_score = valid_metrics["mean_ic"]
            improved = np.isfinite(valid_score) and valid_score > best_score + float(config["min_delta"])
            if improved:
                best_score = valid_score
                best_iteration = iteration
                stale = 0
            else:
                stale += 1
            history.append(
                {
                    "iteration": iteration,
                    "added_factor": selected[-1],
                    "factor_count": len(selected),
                    "selected_factors": json_list(selected),
                    "train_mean_ic": train_metrics["mean_ic"],
                    "train_icir": train_metrics["icir"],
                    "valid_mean_ic": valid_metrics["mean_ic"],
                    "valid_icir": valid_metrics["icir"],
                    "valid_mse": valid_metrics["mse"],
                    "is_best": improved,
                }
            )
            min_factors = int(config.get("min_factors_before_stopping", 1))
            patience_exhausted = len(selected) >= min_factors and stale >= int(config["patience"])
            if patience_exhausted or len(selected) >= int(config["max_factors"]):
                break

            residual = train_target - train_prediction.reindex(train_target.index)
            remaining = [name for name in self.store.factor_names if name not in selected]
            if prepared is not None and config["score_method"] == "pearson":
                candidate_scores = vectorized_residual_scores(
                    prepared.train.loc[:, remaining],
                    residual,
                    min_count=int(self.preprocess_config["min_cross_section"]),
                )
            else:
                candidate_rows: list[dict] = []
                for candidate in remaining:
                    score, signed_ic, dates = residual_score(
                        self.factor(candidate).reindex(train_target.index),
                        residual,
                        method=config["score_method"],
                        min_count=int(self.preprocess_config["min_cross_section"]),
                    )
                    candidate_rows.append(
                        {"candidate": candidate, "score": score, "signed_mean_ic": signed_ic, "dates": dates}
                    )
                candidate_scores = pd.DataFrame(candidate_rows)
            ranked = candidate_scores.dropna(subset=["score"]).sort_values(
                ["score", "candidate"], ascending=[False, True]
            )
            if ranked.empty or float(ranked.iloc[0]["score"]) < float(config["min_residual_score"]):
                break
            for rank, row in enumerate(ranked.head(int(config["top_n_log"])).itertuples(index=False), start=1):
                rankings.append(
                    {
                        "iteration": iteration,
                        "rank": rank,
                        "candidate": row.candidate,
                        "score": row.score,
                        "signed_mean_ic": row.signed_mean_ic,
                        "dates": row.dates,
                    }
                )
            selected.append(str(ranked.iloc[0]["candidate"]))

        if best_iteration == 0:
            valid_scores = pd.DataFrame(history)["valid_mean_ic"].astype(float)
            best_iteration = 1 if valid_scores.isna().all() else int(valid_scores.idxmax()) + 1
        best_factors, best_model = checkpoints[best_iteration]
        return SelectionResult(
            history=pd.DataFrame(history),
            rankings=pd.DataFrame(rankings),
            best_iteration=best_iteration,
            selected_factors=best_factors,
            model=best_model,
        )


def json_list(values: list[str]) -> str:
    import json

    return json.dumps(values, ensure_ascii=False)
