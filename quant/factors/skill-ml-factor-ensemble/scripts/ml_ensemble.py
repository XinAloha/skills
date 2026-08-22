"""Leakage-safe supervised combination of many factors into one OOS meta-signal.

Skeleton implementation for skill-ml-factor-ensemble.

Key idea: overlapping forward-return windows leak the future into CV folds. We enforce
a rolling walk-forward with **purging** (drop train samples whose label window overlaps
the test window) and **embargo** (drop a buffer right after each test window), following
Lopez de Prado, *Advances in Financial Machine Learning*.

Pure core (`walk_forward_predict`) takes a tidy panel and returns OOS predictions only.
This is a research scaffold, not investment advice. It places no orders.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class EnsembleConfig:
    model: str = "ridge"          # ridge | elasticnet | lightgbm
    horizon: int = 5              # label forward-return horizon H (trading days)
    train_window: int = 252       # rolling train length in unique dates
    step: int = 21                # how many dates each OOS block covers
    embargo: int = 5              # extra dates dropped after each test block
    label_col: str = "fwd_ret"
    elasticnet_alpha: float = 1e-5
    elasticnet_l1_ratio: float = 0.5


# --------------------------------------------------------------------------- #
# Fold construction (the leakage-control heart of the skill)
# --------------------------------------------------------------------------- #
def make_walkforward_folds(dates: np.ndarray, cfg: EnsembleConfig):
    """Yield (train_dates, test_dates) date-index blocks with purge + embargo.

    Purge: a train date is dropped if its label window [d, d+H] can overlap the test
    block. We approximate by removing the last H train dates before the test block.
    Embargo: the first ``embargo`` dates after the test block are excluded from the
    *next* train window's tail as well.
    """
    udates = np.sort(np.unique(dates))
    n = len(udates)
    start = cfg.train_window
    while start < n:
        test_idx = slice(start, min(start + cfg.step, n))
        test_dates = udates[test_idx]
        # purge: drop the last H train dates whose label overlaps the test block
        train_end = max(0, start - cfg.horizon)
        train_start = max(0, train_end - cfg.train_window)
        train_dates = udates[train_start:train_end]
        if len(train_dates) and len(test_dates):
            yield train_dates, test_dates
        start += cfg.step + cfg.embargo


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
def _fit_predict(X_tr, y_tr, X_te, cfg: EnsembleConfig):
    if cfg.model in ("ridge", "elasticnet"):
        from sklearn.linear_model import ElasticNet, Ridge

        model = (
            Ridge(alpha=1.0)
            if cfg.model == "ridge"
            else ElasticNet(
                alpha=cfg.elasticnet_alpha,
                l1_ratio=cfg.elasticnet_l1_ratio,
                max_iter=10_000,
            )
        )
        model.fit(X_tr, y_tr)
        coef = dict(zip(getattr(X_tr, "columns", range(X_tr.shape[1])), model.coef_))
        return model.predict(X_te), coef
    elif cfg.model == "lightgbm":
        import lightgbm as lgb

        model = lgb.LGBMRegressor(n_estimators=200, num_leaves=15, learning_rate=0.05,
                                  subsample=0.8, colsample_bytree=0.8, verbosity=-1)
        model.fit(X_tr, y_tr)
        imp = dict(zip(getattr(X_tr, "columns", range(X_tr.shape[1])),
                       model.feature_importances_))
        return model.predict(X_te), imp
    raise ValueError(f"unknown model: {cfg.model}")


# --------------------------------------------------------------------------- #
# Walk-forward driver
# --------------------------------------------------------------------------- #
def walk_forward_predict(panel: pd.DataFrame, factor_cols: list[str], cfg: EnsembleConfig):
    """Return (oos_predictions_df, importance_df).

    ``panel`` must have columns: date, symbol, <factor_cols>, <label_col>.
    OOS predictions contain test rows only — never in-sample.
    """
    panel = panel.sort_values("date").reset_index(drop=True)
    preds = []
    importances = []
    for train_dates, test_dates in make_walkforward_folds(panel["date"].to_numpy(), cfg):
        tr = panel[panel["date"].isin(train_dates)].dropna(subset=factor_cols + [cfg.label_col])
        te = panel[panel["date"].isin(test_dates)].dropna(subset=factor_cols)
        if tr.empty or te.empty:
            continue
        yhat, imp = _fit_predict(tr[factor_cols], tr[cfg.label_col], te[factor_cols], cfg)
        block = te[["date", "symbol"]].copy()
        block["score"] = yhat
        preds.append(block)
        importances.append(pd.Series(imp, name=str(test_dates[-1])))

    if not preds:
        import warnings
        warnings.warn(
            "no walk-forward folds were produced — train_window "
            f"({cfg.train_window}) likely exceeds the number of available dates "
            f"({panel['date'].nunique()}). Lower train_window or supply more history.",
            stacklevel=2,
        )
    oos = pd.concat(preds, ignore_index=True) if preds else pd.DataFrame(columns=["date", "symbol", "score"])
    imp_df = pd.concat(importances, axis=1).T if importances else pd.DataFrame()
    return oos, imp_df


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
def rank_ic_series(merged: pd.DataFrame) -> pd.Series:
    """Daily cross-sectional Spearman (rank) IC of score vs realized fwd_ret."""
    if merged.empty:
        return pd.Series(dtype=float, name="rank_ic")

    def _ic(g):
        return g["score"].rank().corr(g["fwd_ret"].rank())

    result = merged.groupby("date", sort=True)[["score", "fwd_ret"]].apply(_ic)
    result.name = "rank_ic"
    return result


def icir(ic: pd.Series) -> float:
    ic = ic.dropna()
    if len(ic) < 2:
        return float("nan")
    std = float(ic.std())
    if not np.isfinite(std) or std == 0:
        return float("nan")
    return float(ic.mean() / std * np.sqrt(252))


def equal_weight_baseline(panel: pd.DataFrame, factor_cols: list[str]) -> pd.DataFrame:
    """Baseline = mean of per-date z-scored factors (no learning).

    Uses groupby-transform (not apply) so it is robust across pandas 2.x / 3.x, where
    ``group_keys=False`` changed whether the grouping column is passed into the callable.
    """
    g = panel.groupby("date")
    z = pd.DataFrame(index=panel.index)
    for c in factor_cols:
        z[c] = (panel[c] - g[c].transform("mean")) / (g[c].transform("std") + 1e-12)
    out = panel[["date", "symbol"]].copy()
    out["score"] = z.mean(axis=1).to_numpy()
    return out


# --------------------------------------------------------------------------- #
# Toy data / CLI
# --------------------------------------------------------------------------- #
def make_toy(n_sym: int = 40, n_days: int = 400, k: int = 6, seed: int = 11):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2022-01-01", periods=n_days)
    rows = []
    true_w = rng.normal(0, 1, k)
    for d in dates:
        f = rng.normal(0, 1, size=(n_sym, k))
        signal = f @ true_w
        fwd = 0.3 * (signal - signal.mean()) / (signal.std() + 1e-9) * 0.01 + rng.normal(0, 0.02, n_sym)
        for i in range(n_sym):
            row = {"date": d, "symbol": f"S{i:03d}", "fwd_ret": fwd[i]}
            row.update({f"f{j}": f[i, j] for j in range(k)})
            rows.append(row)
    return pd.DataFrame(rows), [f"f{j}" for j in range(k)]


def write_report(path: str, cfg: EnsembleConfig, panel: pd.DataFrame,
                 factor_cols: list[str], oos: pd.DataFrame, imp: pd.DataFrame,
                 ml_icir: float, baseline_icir: float) -> None:
    """Write the diagnostics artifact promised by the skill output contract."""
    degraded = []
    if oos.empty:
        degraded.append(
            f"no OOS folds: {panel['date'].nunique()} dates is not enough for "
            f"train_window={cfg.train_window}"
        )
    elif oos["score"].nunique(dropna=True) <= max(1, len(factor_cols)):
        degraded.append("prediction diversity is low; inspect regularization and input scaling")
    if not np.isfinite(ml_icir):
        degraded.append("OOS ICIR is unavailable because the IC series is empty or has zero variance")

    importance = (
        imp.abs().mean().sort_values(ascending=False)
        if not imp.empty else pd.Series(dtype=float)
    )
    lines = [
        "# ML Factor Ensemble Report",
        "",
        "## Configuration",
        "",
        f"- Model: `{cfg.model}`",
        f"- Horizon / train / step / embargo: {cfg.horizon} / {cfg.train_window} / "
        f"{cfg.step} / {cfg.embargo} trading dates",
        f"- Factors: {', '.join(factor_cols)}",
        f"- Input dates / rows: {panel['date'].nunique()} / {len(panel)}",
        f"- OOS dates / rows: {oos['date'].nunique() if not oos.empty else 0} / {len(oos)}",
        "",
        "## OOS Evaluation",
        "",
        f"- ML Rank-IC IR: {ml_icir:.3f}" if np.isfinite(ml_icir) else "- ML Rank-IC IR: unavailable",
        f"- Equal-weight baseline Rank-IC IR: {baseline_icir:.3f}"
        if np.isfinite(baseline_icir) else "- Equal-weight baseline Rank-IC IR: unavailable",
        "",
        "## Mean Absolute Feature Importance",
        "",
    ]
    lines.extend(
        [f"- `{name}`: {value:.6g}" for name, value in importance.items()]
        or ["- unavailable (no fitted folds)"]
    )
    lines.extend([
        "",
        "## Degradation & Caveats",
        "",
    ])
    lines.extend([f"- {item}" for item in degraded] or ["- None detected by automated checks."])
    lines.extend([
        "- Metrics are walk-forward OOS estimates, not live-performance guarantees.",
        "- Research/education only; no orders are placed.",
        "",
    ])
    report = Path(path)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Leakage-safe ML factor ensemble (walk-forward).")
    ap.add_argument("--panel-csv", help="long panel: date,symbol,<factors>,fwd_ret (omit for toy)")
    ap.add_argument("--factors", help="comma-separated factor column names")
    ap.add_argument("--model", default="ridge", choices=["ridge", "elasticnet", "lightgbm"])
    ap.add_argument("--horizon", type=int, default=5)
    ap.add_argument("--train-window", type=int, default=252)
    ap.add_argument("--step", type=int, default=21)
    ap.add_argument("--embargo", type=int, default=5)
    ap.add_argument("--elasticnet-alpha", type=float, default=1e-5)
    ap.add_argument("--elasticnet-l1-ratio", type=float, default=0.5)
    ap.add_argument("--out", default="combined_signal.csv")
    ap.add_argument("--report", default="ensemble_report.md")
    args = ap.parse_args()

    if args.panel_csv and args.factors:
        panel = pd.read_csv(args.panel_csv, parse_dates=["date"])
        factor_cols = args.factors.split(",")
    else:
        print("[info] no inputs; running toy demo")
        panel, factor_cols = make_toy()

    cfg = EnsembleConfig(
        model=args.model,
        horizon=args.horizon,
        train_window=args.train_window,
        step=args.step,
        embargo=args.embargo,
        elasticnet_alpha=args.elasticnet_alpha,
        elasticnet_l1_ratio=args.elasticnet_l1_ratio,
    )
    oos, imp = walk_forward_predict(panel, factor_cols, cfg)
    oos.to_csv(args.out, index=False)

    merged = oos.merge(panel[["date", "symbol", "fwd_ret"]], on=["date", "symbol"], how="left")
    ml_ic = rank_ic_series(merged)
    base = equal_weight_baseline(panel, factor_cols).merge(
        panel[["date", "symbol", "fwd_ret"]], on=["date", "symbol"])
    base_ic = rank_ic_series(base)
    ml_value = icir(ml_ic)
    base_value = icir(base_ic)
    write_report(args.report, cfg, panel, factor_cols, oos, imp, ml_value, base_value)
    print(f"[ok] wrote {args.out} ({len(oos)} OOS rows)")
    print(f"[ok] wrote {args.report}")
    print(f"OOS ICIR  ml={ml_value:.3f}  equal-weight-baseline={base_value:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
