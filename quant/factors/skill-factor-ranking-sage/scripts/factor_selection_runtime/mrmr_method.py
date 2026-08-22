"""Reference-compatible local mRMR regression implementation."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd
from sklearn.feature_selection import f_regression as sklearn_f_regression


REDUNDANCY_FLOOR = 0.001


def f_statistic_relevance(X: pd.DataFrame, y: pd.Series) -> pd.Series:
    """Compute the univariate regression F-statistic for every factor."""
    target = pd.to_numeric(y, errors="coerce").replace([np.inf, -np.inf], np.nan)

    def score(column: pd.Series) -> float:
        values = pd.to_numeric(column, errors="coerce").replace([np.inf, -np.inf], np.nan)
        valid = values.notna() & target.notna()
        if int(valid.sum()) < 3:
            return 0.0
        x_valid = values.loc[valid]
        y_valid = target.loc[valid]
        if x_valid.nunique(dropna=True) < 2 or y_valid.nunique(dropna=True) < 2:
            return 0.0
        result = float(
            sklearn_f_regression(
                x_valid.to_numpy(dtype="float64").reshape(-1, 1),
                y_valid.to_numpy(dtype="float64"),
            )[0][0]
        )
        return result if np.isfinite(result) and result > 0 else 0.0

    return X.apply(score).fillna(0.0).astype("float64")


def pearson_redundancy(
    X: pd.DataFrame,
    target_factor: str,
    candidate_factors: list[str],
) -> pd.Series:
    """Compute candidate Pearson correlations with one selected factor."""
    clean = X[[target_factor, *candidate_factors]].replace([np.inf, -np.inf], np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        correlations = clean[candidate_factors].corrwith(clean[target_factor])
    return correlations.fillna(REDUNDANCY_FLOOR)


def select_mrmr(
    X: pd.DataFrame,
    y: pd.Series,
    K: int,
    denominator: str = "mean",
) -> tuple[list[str], pd.Series, pd.DataFrame]:
    """Select up to K factors using the standard quotient mRMR rule."""
    if denominator not in {"mean", "max"}:
        raise ValueError("denominator must be mean or max")
    relevance = f_statistic_relevance(X, y)
    factors = relevance[relevance > 0].index.astype(str).tolist()
    relevance = relevance.loc[factors]
    redundancy = pd.DataFrame(
        REDUNDANCY_FLOOR,
        index=factors,
        columns=factors,
        dtype="float64",
    )
    selected: list[str] = []
    remaining = factors.copy()
    limit = min(int(K), len(remaining))

    for _ in range(limit):
        numerator = relevance.loc[remaining]
        if selected:
            last_selected = selected[-1]
            correlations = pearson_redundancy(X, last_selected, remaining)
            redundancy.loc[remaining, last_selected] = (
                correlations.abs().clip(lower=REDUNDANCY_FLOOR)
            )
            selected_redundancy = redundancy.loc[remaining, selected]
            if denominator == "mean":
                denominator_score = selected_redundancy.mean(axis=1)
            else:
                denominator_score = selected_redundancy.max(axis=1)
            denominator_score = denominator_score.replace(1.0, float("inf"))
        else:
            denominator_score = pd.Series(1.0, index=remaining)
        scores = numerator / denominator_score
        best = str(scores.idxmax())
        selected.append(best)
        remaining.remove(best)

    return selected, relevance, redundancy


def run_mrmr(
    train: pd.DataFrame,
    factors: list[str],
    selection_count: int,
    config: Mapping[str, Any],
) -> tuple[list[str], pd.DataFrame, pd.DataFrame]:
    mrmr_cfg = config["mrmr"]
    selected, relevance, redundancy = select_mrmr(
        X=train[factors],
        y=train["y"],
        K=min(selection_count, len(factors)),
        denominator=str(mrmr_cfg["denominator"]),
    )
    ranking = pd.DataFrame(
        {
            "rank": range(1, len(selected) + 1),
            "factor": selected,
            "relevance": [float(relevance.loc[factor]) for factor in selected],
        }
    )
    return selected, ranking, redundancy.reset_index(names="factor")
