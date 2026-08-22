"""Prediction metrics and fast scoring for model structure experiments."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd

from config_utils import ConfigError, optional_value, require_mapping


def safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0 or not np.isfinite(denominator):
        return 0.0
    return float(numerator / denominator)


def daily_corr(frame: pd.DataFrame, pred_col: str, y_col: str, method: str, min_assets: int) -> pd.Series:
    values: dict[int, float] = {}
    for date_value, group in frame[["date", pred_col, y_col]].groupby("date", sort=True):
        data = group[[pred_col, y_col]].dropna()
        if len(data) < min_assets:
            values[int(date_value)] = np.nan
            continue
        corr = data[pred_col].corr(data[y_col], method=method)
        values[int(date_value)] = float(corr) if pd.notna(corr) and np.isfinite(corr) else np.nan
    return pd.Series(values, dtype="float64")


def top_bottom_spread(frame: pd.DataFrame, pred_col: str, y_col: str, top_q: float, bottom_q: float, min_assets: int) -> pd.Series:
    values: dict[int, float] = {}
    for date_value, group in frame[["date", pred_col, y_col]].groupby("date", sort=True):
        data = group[[pred_col, y_col]].dropna()
        if len(data) < min_assets:
            values[int(date_value)] = np.nan
            continue
        high = data[pred_col].quantile(1.0 - top_q)
        low = data[pred_col].quantile(bottom_q)
        top = data.loc[data[pred_col] >= high, y_col]
        bottom = data.loc[data[pred_col] <= low, y_col]
        values[int(date_value)] = float(top.mean() - bottom.mean()) if not top.empty and not bottom.empty else np.nan
    return pd.Series(values, dtype="float64")


def turnover_proxy(
    frame: pd.DataFrame,
    pred_col: str,
    top_q: float,
    min_assets: int,
    *,
    reset_at_window: bool = True,
) -> float:
    turnovers: list[float] = []
    window_groups = (
        frame.groupby("window_id", sort=True)
        if reset_at_window and "window_id" in frame
        else [(0, frame)]
    )
    for _, window_frame in window_groups:
        previous: set[Any] | None = None
        for _, group in window_frame[["date", "ticker", pred_col]].groupby("date", sort=True):
            data = group[["ticker", pred_col]].dropna()
            if len(data) < min_assets:
                continue
            high = data[pred_col].quantile(1.0 - top_q)
            current = set(data.loc[data[pred_col] >= high, "ticker"].tolist())
            if previous is not None and current:
                turnovers.append(1.0 - len(previous & current) / max(len(current), 1))
            previous = current
    return float(np.nanmean(turnovers)) if turnovers else 0.0


def window_level_mean(group: pd.DataFrame, col: str) -> float:
    if col not in group:
        return 0.0
    if "window_id" in group:
        values = group[["window_id", col]].drop_duplicates("window_id")[col]
    else:
        values = group[col]
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return float(numeric.mean()) if not numeric.empty else 0.0


SUPPORTED_OBJECTIVES = {
    "fast_score",
    "rmse",
    "mean_ic",
    "icir",
    "mean_rankic",
    "rankic_ir",
    "top_bottom_spread",
    "positive_window_ratio",
    "robust_rankic",
}


def finite_or_zero(value: float) -> float:
    return float(value) if np.isfinite(value) else 0.0


def _rankic_blocks(
    group: pd.DataFrame,
    rankic: pd.Series,
    block_method: str,
) -> pd.Series:
    if rankic.empty:
        return pd.Series(dtype="float64")
    dates = pd.Series(rankic.index.astype("int64"), index=rankic.index)
    if block_method == "month":
        labels = dates // 100
    elif block_method == "year":
        labels = dates // 10_000
    elif block_method == "window":
        if "window_id" not in group:
            labels = pd.Series(0, index=rankic.index)
        else:
            date_to_window = (
                group[["date", "window_id"]]
                .drop_duplicates("date")
                .set_index("date")["window_id"]
            )
            labels = pd.Series(rankic.index.map(date_to_window), index=rankic.index)
    else:
        raise ConfigError("evaluation.robust_rankic.block must be one of: month, year, window")
    return rankic.groupby(labels).mean().dropna()


def _robust_rankic_score(
    group: pd.DataFrame,
    rankic: pd.Series,
    cfg: Mapping[str, Any],
) -> tuple[float, dict[str, Any]]:
    robust_cfg = optional_value(cfg, ["evaluation", "robust_rankic"], {})
    if not isinstance(robust_cfg, Mapping):
        raise ConfigError("evaluation.robust_rankic must be a mapping")
    min_valid_dates = int(robust_cfg.get("min_valid_dates", 60))
    min_blocks = int(robust_cfg.get("min_blocks", 3))
    block_method = str(robust_cfg.get("block", "month")).lower()
    se_multiplier = float(robust_cfg.get("se_multiplier", 1.0))
    blocks = _rankic_blocks(group, rankic, block_method)
    enough = len(rankic) >= min_valid_dates and len(blocks) >= min_blocks
    block_mean = float(blocks.mean()) if not blocks.empty else float("nan")
    block_std = float(blocks.std(ddof=1)) if len(blocks) > 1 else 0.0
    block_se = block_std / float(np.sqrt(len(blocks))) if len(blocks) else float("nan")
    robust_score = block_mean - se_multiplier * block_se if enough else float("nan")
    return robust_score, {
        "num_valid_dates": int(len(rankic)),
        "num_rankic_blocks": int(len(blocks)),
        "rankic_block_method": block_method,
        "block_rankic_mean": block_mean,
        "block_rankic_std": block_std,
        "block_rankic_se": block_se,
        "positive_block_ratio": float((blocks > 0).mean()) if not blocks.empty else 0.0,
        "robust_rankic": robust_score,
    }


def regression_summary(frame: pd.DataFrame, pred_col: str, y_col: str) -> dict[str, float]:
    data = frame[[pred_col, y_col]].dropna()
    if data.empty:
        return {"rmse": float("nan"), "mae": float("nan"), "r2": float("nan")}
    y = data[y_col].to_numpy(dtype="float64")
    pred = data[pred_col].to_numpy(dtype="float64")
    residuals = y - pred
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    mae = float(np.mean(np.abs(residuals)))
    ss_res = float(np.dot(residuals, residuals))
    centered = y - float(np.mean(y))
    ss_tot = float(np.dot(centered, centered))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return {"rmse": rmse, "mae": mae, "r2": float(r2)}


def score_predictions(predictions: pd.DataFrame, cfg: Mapping[str, Any]) -> tuple[dict[str, Any], pd.DataFrame]:
    pred_col = "prediction"
    min_assets = int(optional_value(cfg, ["validation", "min_assets_per_date"], 2))
    top_q = float(optional_value(cfg, ["fast_evaluator", "top_quantile"], 0.2))
    bottom_q = float(optional_value(cfg, ["fast_evaluator", "bottom_quantile"], 0.2))
    if not (0 < top_q < 1 and 0 < bottom_q < 1):
        raise ConfigError("fast_evaluator quantiles must be in (0, 1)")
    objective = str(optional_value(cfg, ["evaluation", "objective"], "fast_score")).lower()
    weights = require_mapping(cfg, ["evaluation", "fast_score_weights"])
    required = ["rankic_ir", "top_bottom_spread", "positive_window_ratio", "turnover_proxy", "complexity_penalty", "overfit_penalty"]
    missing = [k for k in required if k not in weights]
    if missing:
        raise ConfigError(f"evaluation.fast_score_weights missing keys: {missing}")
    if objective not in SUPPORTED_OBJECTIVES:
        allowed = ", ".join(sorted(SUPPORTED_OBJECTIVES))
        raise ConfigError(f"evaluation.objective must be one of: {allowed}")

    rows: list[dict[str, Any]] = []
    for model_name, group in predictions.groupby("model_name", sort=True):
        rankic = daily_corr(group, pred_col, "y", "spearman", min_assets).dropna()
        ic = daily_corr(group, pred_col, "y", "pearson", min_assets).dropna()
        spread = top_bottom_spread(group, pred_col, "y", top_q, bottom_q, min_assets).dropna()
        mean_rankic = float(rankic.mean()) if not rankic.empty else np.nan
        rankic_std = float(rankic.std(ddof=1)) if len(rankic) > 1 else 0.0
        mean_ic = float(ic.mean()) if not ic.empty else np.nan
        ic_std = float(ic.std(ddof=1)) if len(ic) > 1 else 0.0
        spread_mean = float(spread.mean()) if not spread.empty else np.nan
        positive_ratio = float((rankic > 0).mean()) if not rankic.empty else 0.0
        metric_policy = str(
            optional_value(
                cfg,
                ["evaluation", "metric_policy"],
                "legacy_pooled",
            )
        ).lower()
        turnover = turnover_proxy(
            group,
            pred_col,
            top_q,
            min_assets,
            reset_at_window=metric_policy != "legacy_pooled",
        )
        instability = float(rankic.std(ddof=1)) if len(rankic) > 1 else 0.0
        complexity_penalty = window_level_mean(group, "complexity_penalty")
        overfit_penalty = window_level_mean(group, "overfit_penalty")
        robust_rankic, robust_metrics = _robust_rankic_score(group, rankic, cfg)
        rankic_ir = safe_ratio(mean_rankic, rankic_std)
        rankic_ir_score = float(np.clip(finite_or_zero(rankic_ir), -5.0, 5.0))
        spread_score = float(np.clip(0.0 if np.isnan(spread_mean) else spread_mean, -0.05, 0.05))
        turnover_score = float(np.clip(turnover, 0.0, 1.0))
        complexity_score = float(np.clip(complexity_penalty, 0.0, 1.0))
        overfit_score = float(np.clip(overfit_penalty, 0.0, 1.0))
        loss_metrics = regression_summary(group, pred_col, "y")
        valid_rmse = float(loss_metrics["rmse"])
        valid_mae = float(loss_metrics["mae"])
        valid_r2 = float(loss_metrics["r2"])
        fast_score = (
            float(weights["rankic_ir"]) * rankic_ir_score
            + float(weights["top_bottom_spread"]) * spread_score
            + float(weights["positive_window_ratio"]) * positive_ratio
            - float(weights["turnover_proxy"]) * turnover_score
            - float(weights["complexity_penalty"]) * complexity_score
            - float(weights["overfit_penalty"]) * overfit_score
        )
        icir = safe_ratio(mean_ic, ic_std)
        objective_values = {
            "fast_score": float(fast_score),
            "rmse": -valid_rmse,
            "mean_ic": finite_or_zero(mean_ic),
            "icir": finite_or_zero(icir),
            "mean_rankic": finite_or_zero(mean_rankic),
            "rankic_ir": finite_or_zero(rankic_ir),
            "top_bottom_spread": finite_or_zero(spread_mean),
            "positive_window_ratio": finite_or_zero(positive_ratio),
            "robust_rankic": robust_rankic,
        }
        objective_score = objective_values[objective]
        rows.append(
            {
                "model_name": model_name,
                "model_type": group["model_type"].iloc[0],
                "mean_ic": mean_ic,
                "mean_rankic": mean_rankic,
                "icir": icir,
                "rankic_ir": rankic_ir,
                "top_bottom_spread": spread_mean,
                "positive_window_ratio": positive_ratio,
                "turnover_proxy": turnover,
                "instability_penalty": instability,
                "complexity_penalty": complexity_penalty,
                "overfit_penalty": overfit_penalty,
                "valid_rmse": valid_rmse,
                "valid_mae": valid_mae,
                "valid_r2": valid_r2,
                "window_train_rmse": window_level_mean(group, "train_rmse"),
                "window_valid_rmse": window_level_mean(group, "valid_rmse"),
                "window_train_r2": window_level_mean(group, "train_r2"),
                "window_valid_r2": window_level_mean(group, "valid_r2"),
                "fast_score": float(fast_score),
                "objective": objective,
                "objective_score": float(objective_score),
                "num_prediction_rows": int(len(group)),
                **robust_metrics,
            }
        )
    scores = pd.DataFrame(rows).sort_values("objective_score", ascending=False).reset_index(drop=True)
    summary = scores.iloc[0].to_dict() if not scores.empty else {}
    return summary, scores
