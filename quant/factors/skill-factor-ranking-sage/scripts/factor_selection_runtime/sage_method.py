"""Reference-compatible local Marginal-SAGE implementation for regression MSE."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd

from .model_registry import create_model
from .preprocess import FeatureTransformer


ArrayModel = Callable[[np.ndarray], np.ndarray]


@dataclass(frozen=True)
class SAGEExplanation:
    values: np.ndarray
    std: np.ndarray
    explanation_type: str
    sample_count: int
    iteration_count: int
    converged: bool
    convergence_ratio: float


class MarginalImputer:
    """Marginalize held-out factors using an empirical background distribution."""

    def __init__(self, model: ArrayModel, background: np.ndarray):
        data = np.asarray(background, dtype="float64")
        if data.ndim != 2 or len(data) == 0:
            raise ValueError("background must be a non-empty 2D array")
        self.model = model
        self.background = data
        self.num_groups = data.shape[1]

    def __call__(self, x: np.ndarray, observed: np.ndarray) -> np.ndarray:
        values = np.asarray(x, dtype="float64")
        mask = np.asarray(observed, dtype=bool)
        if values.ndim != 2 or mask.shape != values.shape:
            raise ValueError("x and observed must be equally shaped 2D arrays")
        if values.shape[1] != self.num_groups:
            raise ValueError("x has a different number of factors than background")

        sample_count = len(self.background)
        repeated_values = values.repeat(sample_count, axis=0)
        repeated_mask = mask.repeat(sample_count, axis=0)
        repeated_background = np.tile(self.background, (len(values), 1))
        combined = repeated_values.copy()
        combined[~repeated_mask] = repeated_background[~repeated_mask]

        predictions = np.asarray(self.model(combined), dtype="float64")
        predictions = predictions.reshape(
            len(values), sample_count, *predictions.shape[1:]
        )
        return predictions.mean(axis=1)


class ImportanceTracker:
    """Track means and standard errors with Welford's online algorithm."""

    def __init__(self) -> None:
        self.mean: float | np.ndarray = 0.0
        self.sum_squares: float | np.ndarray = 0.0
        self.sample_count = 0

    def update(self, scores: np.ndarray) -> None:
        values = np.asarray(scores, dtype="float64")
        if values.ndim != 2 or len(values) == 0:
            raise ValueError("scores must be a non-empty 2D array")
        self.sample_count += len(values)
        difference = values - self.mean
        self.mean = self.mean + difference.sum(axis=0) / self.sample_count
        difference_after = values - self.mean
        self.sum_squares = self.sum_squares + (difference * difference_after).sum(axis=0)

    @property
    def values(self) -> np.ndarray:
        return np.asarray(self.mean, dtype="float64")

    @property
    def std(self) -> np.ndarray:
        denominator = max(self.sample_count, 1) ** 2
        variance = np.asarray(self.sum_squares, dtype="float64") / denominator
        return np.sqrt(np.maximum(variance, 0.0))


def mse_per_sample(prediction: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Return MSE summed across non-batch output dimensions."""
    pred = np.asarray(prediction, dtype="float64")
    truth = np.asarray(target, dtype="float64")
    if truth.ndim > 0 and truth.shape[-1] == 1 and truth.ndim - pred.ndim == 1:
        pred = np.expand_dims(pred, -1)
    elif pred.ndim > 0 and pred.shape[-1] == 1 and pred.ndim - truth.ndim == 1:
        truth = np.expand_dims(truth, -1)
    elif pred.shape != truth.shape:
        raise ValueError(f"prediction shape {pred.shape} does not match target shape {truth.shape}")
    return np.square(pred - truth).reshape(len(pred), -1).sum(axis=1)


class PermutationSAGEEstimator:
    """Estimate SAGE values by unrolling random factor permutations."""

    def __init__(self, imputer: MarginalImputer, random_state: int | None = None):
        self.imputer = imputer
        self.random_state = random_state
        self.rng = np.random.default_rng(seed=random_state)

    def _process_batch(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        batch_size = len(x)
        factor_count = self.imputer.num_groups
        rows = np.arange(batch_size)
        scores = np.zeros((batch_size, factor_count), dtype="float64")
        observed = np.zeros((batch_size, factor_count), dtype=bool)
        permutations = np.tile(np.arange(factor_count), (batch_size, 1))
        for row in range(batch_size):
            self.rng.shuffle(permutations[row])

        previous_loss = mse_per_sample(self.imputer(x, observed), y)
        for position in range(factor_count):
            added = permutations[:, position]
            observed[rows, added] = True
            current_loss = mse_per_sample(self.imputer(x, observed), y)
            scores[rows, added] = previous_loss - current_loss
            previous_loss = current_loss
        return scores

    def estimate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        batch_size: int = 512,
        detect_convergence: bool = True,
        threshold: float = 0.025,
        n_permutations: int | None = None,
    ) -> SAGEExplanation:
        values = np.asarray(X, dtype="float64")
        target = np.asarray(y, dtype="float64")
        if values.ndim != 2 or len(values) == 0:
            raise ValueError("X must be a non-empty 2D array")
        if len(target) != len(values):
            raise ValueError("X and y must contain the same number of rows")
        if values.shape[1] != self.imputer.num_groups:
            raise ValueError("X has a different number of factors than the imputer")
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        if not 0 < threshold < 1:
            raise ValueError("threshold must be in (0, 1)")
        if n_permutations is not None and n_permutations < 1:
            raise ValueError("n_permutations must be null or at least 1")
        if n_permutations is None:
            detect_convergence = True
            iteration_limit: int | None = None
        else:
            iteration_limit = int(np.ceil(n_permutations / batch_size))

        self.rng = np.random.default_rng(seed=self.random_state)
        tracker = ImportanceTracker()
        iteration_count = 0
        converged = False
        ratio = float("inf")
        while iteration_limit is None or iteration_count < iteration_limit:
            indices = self.rng.choice(len(values), batch_size)
            scores = self._process_batch(values[indices], target[indices])
            tracker.update(scores)
            iteration_count += 1
            gap = max(float(tracker.values.max() - tracker.values.min()), 1e-12)
            ratio = float(np.max(tracker.std) / gap)
            if detect_convergence and ratio < threshold:
                converged = True
                break

        return SAGEExplanation(
            values=tracker.values,
            std=tracker.std,
            explanation_type="SAGE",
            sample_count=tracker.sample_count,
            iteration_count=iteration_count,
            converged=converged,
            convergence_ratio=ratio,
        )


def _sample(frame: pd.DataFrame, size: int, seed: int) -> pd.DataFrame:
    if len(frame) <= size:
        return frame.reset_index(drop=True)
    return frame.sample(n=size, random_state=seed).reset_index(drop=True)


def run_sage(
    train: pd.DataFrame,
    valid: pd.DataFrame,
    factors: list[str],
    selection_count: int,
    config: Mapping[str, Any],
) -> tuple[list[str], pd.DataFrame, dict[str, Any]]:
    seed = int(config["random_seed"])
    model_type = str(config["model"]["type"])
    transformer = FeatureTransformer(model_type).fit(train[factors])
    train_x = transformer.transform(train[factors])
    valid_x = transformer.transform(valid[factors])
    model = create_model(config["model"], seed)
    model.fit(train_x, train["y"])

    sage_cfg = config["sage"]
    background = _sample(train_x, int(sage_cfg["background_size"]), seed)
    evaluation = _sample(
        pd.concat([valid_x.reset_index(drop=True), valid[["y"]].reset_index(drop=True)], axis=1),
        int(sage_cfg["evaluation_size"]),
        seed,
    )
    evaluation_x = evaluation[factors]
    evaluation_y = evaluation["y"]

    def predict(values: np.ndarray) -> np.ndarray:
        return model.predict(pd.DataFrame(values, columns=factors))

    imputer = MarginalImputer(predict, background.to_numpy(dtype="float64"))
    estimator = PermutationSAGEEstimator(imputer, random_state=seed)
    explanation = estimator.estimate(
        evaluation_x.to_numpy(dtype="float64"),
        evaluation_y.to_numpy(dtype="float64"),
        batch_size=int(sage_cfg["batch_size"]),
        detect_convergence=bool(sage_cfg["detect_convergence"]),
        threshold=float(sage_cfg["convergence_threshold"]),
        n_permutations=sage_cfg.get("n_permutations"),
    )
    ranking = pd.DataFrame(
        {
            "factor": factors,
            "sage_value": explanation.values,
            "sage_std": explanation.std,
        }
    ).sort_values(["sage_value", "factor"], ascending=[False, True], ignore_index=True)
    ranking.insert(0, "rank", np.arange(1, len(ranking) + 1))
    selected = ranking.head(min(selection_count, len(ranking)))["factor"].astype(str).tolist()
    metadata = {
        "implementation": "local-marginal-mse-v1",
        "explanation_type": explanation.explanation_type,
        "loss": "mse",
        "background_rows": int(len(background)),
        "evaluation_rows": int(len(evaluation)),
        "sage_sample_count": explanation.sample_count,
        "sage_iteration_count": explanation.iteration_count,
        "converged": explanation.converged,
        "convergence_ratio": explanation.convergence_ratio,
    }
    return selected, ranking, metadata
