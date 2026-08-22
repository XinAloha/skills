"""Pyramid-organized time-series analysis API."""

from __future__ import annotations

import logging
import os
import warnings
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from skill_time_series_analysis.types import (
    CointegrationAnalysis,
    DistributionDiagnostics,
    MeanReversionAnalysis,
    TimeSeriesAnalysis,
)

logger = logging.getLogger(__name__)


def _import_matplotlib():
    import matplotlib.pyplot as plt

    return plt


def _import_seaborn():
    import seaborn as sns

    return sns


def _import_signal_stats():
    from scipy import signal, stats

    return signal, stats


def _import_statsmodels():
    from scipy.stats import linregress
    from statsmodels.tools.sm_exceptions import InterpolationWarning
    from statsmodels.tsa.stattools import adfuller, kpss

    return adfuller, kpss, linregress, InterpolationWarning


def _import_sm_api():
    import statsmodels.api as sm

    return sm


def _import_joblib():
    from joblib import Parallel, delayed

    return Parallel, delayed


def _clean_series(series: pd.Series, name: str = "series") -> pd.Series:
    s = pd.Series(series).dropna().astype(float)
    if s.empty:
        raise ValueError(f"{name} must contain at least one numeric observation")
    return s


def _default_lags(lags: Sequence[int] | None = None) -> list[int]:
    if lags is None:
        return [1, 2, 3, 4, 5, 7, 9, 13, 21, 34]
    cleaned = sorted({int(lag) for lag in lags})
    if not cleaned or min(cleaned) < 1:
        raise ValueError("lags must contain positive integers")
    return cleaned


def _default_windows(windows: Sequence[int] | None = None) -> list[int]:
    if windows is None:
        return [20, 40, 60]
    cleaned = [int(window) for window in windows]
    if not cleaned or min(cleaned) < 10:
        raise ValueError("windows must contain integers >= 10")
    return cleaned


def ensure_dir_and_get_path(base_path: str | Path, suffix: str = "") -> str:
    """Return ``base_path`` with ``suffix`` inserted before extension and create parents."""

    full_path = f"{os.path.splitext(str(base_path))[0]}{suffix}"
    dir_path = os.path.dirname(full_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    return full_path


def _standard_log_returns(price: pd.Series, lag: int) -> pd.Series:
    if (price <= 0).any():
        returns = price.diff(lag).replace([np.inf, -np.inf], np.nan).dropna()
    else:
        returns = np.log(price).diff(lag).replace([np.inf, -np.inf], np.nan).dropna()
    std = returns.std(ddof=0)
    if len(returns) == 0 or not np.isfinite(std) or std == 0:
        return pd.Series(dtype=float)
    return (returns - returns.mean()) / std


def _standardized_numeric_values(series: pd.Series) -> pd.Series:
    values = _clean_series(series).replace([np.inf, -np.inf], np.nan).dropna()
    std = values.std(ddof=0)
    if len(values) == 0 or not np.isfinite(std) or std == 0:
        return pd.Series(dtype=float)
    return (values - values.mean()) / std


def _kde_features_for_values(series: pd.Series) -> dict[str, Any]:
    signal, stats = _import_signal_stats()
    standardized = _standardized_numeric_values(series)
    if len(standardized) < 3:
        return {
            "peak_height": np.nan,
            "peak_position": np.nan,
            "num_peaks": 0,
            "tail_feature": "insufficient",
            "skew_feature": "insufficient",
            "statistical_kurtosis": np.nan,
            "statistical_skewness": np.nan,
        }

    kde = stats.gaussian_kde(standardized)
    x_grid = np.linspace(-5, 5, 1000)
    density = kde(x_grid)
    peak_index = int(np.argmax(density))
    peaks, _ = signal.find_peaks(density, height=0.01)
    stat_kurtosis = float(stats.kurtosis(standardized))
    stat_skewness = float(stats.skew(standardized))
    return {
        "peak_height": float(density[peak_index]),
        "peak_position": float(x_grid[peak_index]),
        "num_peaks": int(len(peaks)),
        "tail_feature": "fat_tail" if stat_kurtosis > 1 else "near_normal",
        "skew_feature": (
            "right_skew" if stat_skewness > 0.2 else "left_skew" if stat_skewness < -0.2 else "symmetric"
        ),
        "statistical_kurtosis": stat_kurtosis,
        "statistical_skewness": stat_skewness,
    }


def _qq_features_for_values(series: pd.Series) -> dict[str, float]:
    _, stats = _import_signal_stats()
    standardized = _standardized_numeric_values(series)
    if len(standardized) < 3:
        return {
            "kurtosis": np.nan,
            "skewness": np.nan,
            "qq_deviation": np.nan,
        }
    ordered_vals = np.sort(standardized.to_numpy())
    probabilities = (np.arange(1, len(ordered_vals) + 1) - 0.5) / len(ordered_vals)
    theoretical_quantiles = stats.norm.ppf(probabilities)
    return {
        "kurtosis": float(stats.kurtosis(standardized)),
        "skewness": float(stats.skew(standardized)),
        "qq_deviation": float(np.sqrt(np.mean((theoretical_quantiles - ordered_vals) ** 2))),
    }


def _simple_distribution_features(series: pd.Series) -> dict[str, Any]:
    kde = _kde_features_for_values(series)
    qq = _qq_features_for_values(series)
    return {
        "tail_feature": kde["tail_feature"],
        "skew_feature": kde["skew_feature"],
        "kurtosis": qq["kurtosis"],
        "skewness": qq["skewness"],
        "qq_deviation": qq["qq_deviation"],
    }


def kde_analysis(
    price: pd.Series,
    plot_title: str = "",
    plot_path: str | Path | None = None,
    ax=None,
    show: bool = True,
    lags: Sequence[int] | None = None,
):
    """KDE analysis of standardized log-return distributions across lags."""

    price = _clean_series(price, "price")
    signal, stats = _import_signal_stats()
    lag_values = _default_lags(lags)
    analysis_results: dict[int, dict[str, Any]] = {}

    is_new_figure = ax is None
    if show or plot_path or ax is not None:
        plt = _import_matplotlib()
        sns = _import_seaborn()
        if is_new_figure:
            _, ax = plt.subplots(figsize=(12, 6))
    else:
        plt = None
        sns = None

    for lag in lag_values:
        standard_returns = _standard_log_returns(price, lag)
        if len(standard_returns) < 3:
            analysis_results[lag] = {
                "peak_height": np.nan,
                "peak_position": np.nan,
                "num_peaks": 0,
                "tail_feature": "insufficient",
                "skew_feature": "insufficient",
                "statistical_kurtosis": np.nan,
                "statistical_skewness": np.nan,
            }
            continue

        kde = stats.gaussian_kde(standard_returns)
        x_grid = np.linspace(-5, 5, 1000)
        density = kde(x_grid)
        peak_index = int(np.argmax(density))
        peak_x = float(x_grid[peak_index])
        peak_height = float(density[peak_index])
        peaks, _ = signal.find_peaks(density, height=0.01)
        stat_kurtosis = float(stats.kurtosis(standard_returns))
        stat_skewness = float(stats.skew(standard_returns))

        analysis_results[lag] = {
            "peak_height": peak_height,
            "peak_position": peak_x,
            "num_peaks": int(len(peaks)),
            "tail_feature": "fat_tail" if stat_kurtosis > 1 else "near_normal",
            "skew_feature": (
                "right_skew" if stat_skewness > 0.2 else "left_skew" if stat_skewness < -0.2 else "symmetric"
            ),
            "statistical_kurtosis": stat_kurtosis,
            "statistical_skewness": stat_skewness,
        }

        if sns is not None and ax is not None:
            sns.kdeplot(standard_returns, label=f"lag={lag}", alpha=0.7, ax=ax)

    if ax is not None:
        ax.set_title(f"{plot_title} return distribution (KDE)".strip())
        ax.set_xlim(-5, 5)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize="small")
        if plot_path and is_new_figure:
            plt.savefig(ensure_dir_and_get_path(plot_path, "_kde_dist.png"), bbox_inches="tight")
        if show and is_new_figure:
            plt.show()

    return analysis_results, ax


def qq_analysis(
    price: pd.Series,
    plot_title: str = "",
    plot_path: str | Path | None = None,
    ax=None,
    show: bool = True,
    lags: Sequence[int] | None = None,
):
    """QQ diagnostics of standardized log returns versus normal quantiles."""

    price = _clean_series(price, "price")
    _, stats = _import_signal_stats()
    lag_values = _default_lags(lags)
    analysis_results: dict[int, dict[str, float]] = {}

    is_new_figure = ax is None
    if show or plot_path or ax is not None:
        plt = _import_matplotlib()
        if is_new_figure:
            _, ax = plt.subplots(figsize=(8, 8))
        ax.plot(np.linspace(-3, 3, 100), np.linspace(-3, 3, 100), "k-", linewidth=1)
    else:
        plt = None

    for lag in lag_values:
        standard_returns = _standard_log_returns(price, lag)
        if len(standard_returns) < 3:
            analysis_results[lag] = {
                "kurtosis": np.nan,
                "skewness": np.nan,
                "qq_deviation": np.nan,
            }
            continue

        ordered_vals = np.sort(standard_returns.to_numpy())
        probabilities = (np.arange(1, len(ordered_vals) + 1) - 0.5) / len(ordered_vals)
        theoretical_quantiles = stats.norm.ppf(probabilities)
        qq_deviation = float(np.sqrt(np.mean((theoretical_quantiles - ordered_vals) ** 2)))
        analysis_results[lag] = {
            "kurtosis": float(stats.kurtosis(standard_returns)),
            "skewness": float(stats.skew(standard_returns)),
            "qq_deviation": qq_deviation,
        }
        if ax is not None:
            ax.scatter(theoretical_quantiles, ordered_vals, s=3, alpha=0.5, label=f"lag={lag}")

    if ax is not None:
        ax.grid(True, alpha=0.3)
        ax.set_title(f"{plot_title} QQ plot".strip())
        ax.set_xlabel("theoretical normal quantiles")
        ax.set_ylabel("sample quantiles")
        ax.legend(fontsize="small")
        if plot_path and is_new_figure:
            plt.savefig(ensure_dir_and_get_path(plot_path, "_qq_plot.png"), bbox_inches="tight")
        if show and is_new_figure:
            plt.show()

    return analysis_results, ax


def analysis_results_to_df(analysis_results: dict) -> pd.DataFrame:
    """Flatten nested lag diagnostics into a lag-indexed DataFrame."""

    all_lags = sorted(analysis_results["kde"].keys())
    rows = []
    for lag in all_lags:
        row = {"lag": lag}
        for key, value in analysis_results["kde"].get(lag, {}).items():
            row[f"kde_{key}"] = value
        row["price_length"] = analysis_results["price_length"]
        rows.append(row)
    return pd.DataFrame(rows).set_index("lag")


def ts_analysis(
    price: pd.Series,
    plot_title: str = "",
    plot_path: str | Path | None = None,
    show: bool = True,
    save_csv: bool = False,
):
    """Run a single KDE summary plot and optional CSV export."""

    plt = _import_matplotlib()
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    analysis_results = {"price_length": len(price)}
    kde_results, _ = kde_analysis(price, plot_title, ax=ax, show=False)
    analysis_results["kde"] = kde_results
    if plot_title:
        fig.suptitle(f"{plot_title} time-series summary, bars={len(price)}", fontsize=16)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    if plot_path:
        plt.savefig(ensure_dir_and_get_path(plot_path, "_kde.png"), bbox_inches="tight", dpi=150)
        if save_csv:
            analysis_results_to_df(analysis_results).to_csv(
                ensure_dir_and_get_path(plot_path, "_kde.csv")
            )
    if show:
        plt.show()
    return fig, ax


def distribution_diagnostics(
    price: pd.Series,
    *,
    lags: Sequence[int] | None = None,
    plot: bool = False,
    output_dir: str | Path | None = None,
) -> DistributionDiagnostics:
    """Run distribution diagnostics and return a conclusion-first result object."""

    price = _clean_series(price, "price")
    lag_values = _default_lags(lags)
    plot_paths: dict[str, str] = {}
    plot_base = None
    if output_dir is not None:
        plot_base = Path(output_dir) / "distribution.png"

    kde_results, _ = kde_analysis(price, plot_path=plot_base, show=plot, lags=lag_values)
    qq_results, _ = qq_analysis(price, plot_path=plot_base, show=plot, lags=lag_values)
    kde_df = pd.DataFrame.from_dict(kde_results, orient="index")
    kde_df.index.name = "lag"
    qq_df = pd.DataFrame.from_dict(qq_results, orient="index")
    qq_df.index.name = "lag"

    if output_dir is not None:
        plot_paths["kde"] = ensure_dir_and_get_path(plot_base, "_kde_dist.png")
        plot_paths["qq"] = ensure_dir_and_get_path(plot_base, "_qq_plot.png")

    tail = str(kde_df["tail_feature"].dropna().iloc[0]) if not kde_df.empty else "unknown"
    skew = str(kde_df["skew_feature"].dropna().iloc[0]) if not kde_df.empty else "unknown"
    summary = {
        "n_obs": int(len(price)),
        "lags": ",".join(str(lag) for lag in lag_values),
        "primary_tail_feature": tail,
        "primary_skew_feature": skew,
        "max_abs_skewness": float(qq_df["skewness"].abs().max(skipna=True)),
        "max_qq_deviation": float(qq_df["qq_deviation"].max(skipna=True)),
    }
    return DistributionDiagnostics(summary=summary, kde=kde_df, qq=qq_df, plot_paths=plot_paths)


class TimeSeriesAnalyzer:
    """Analyze a series with Hurst, ADF, KPSS, and trend classification."""

    def __init__(self, series: pd.Series):
        self.series = _clean_series(series)
        self.data = self.series.to_frame()
        self.results: dict[int, dict[str, Any]] = {}

    def calculate_hurst(
        self,
        min_lag: int = 10,
        max_lag: int = 100,
        series: pd.Series | None = None,
    ) -> float:
        _, _, linregress, _ = _import_statsmodels()
        s = self.series if series is None else _clean_series(series)
        max_lag = min(max_lag, len(s) // 2)
        if max_lag < min_lag:
            return np.nan

        if (s > 0).all():
            hurst_values = np.log(s).diff().dropna()
        else:
            hurst_values = s.replace([np.inf, -np.inf], np.nan).dropna()
        if len(hurst_values) <= max_lag:
            return np.nan

        lag_used: list[int] = []
        rs_values: list[float] = []
        for lag in range(min_lag, max_lag + 1):
            rs = []
            for i in range(len(hurst_values) - lag + 1):
                segment = hurst_values.iloc[i : i + lag]
                deviations = segment - segment.mean()
                cumulative = deviations.cumsum()
                range_ = cumulative.max() - cumulative.min()
                std_ = segment.std()
                if std_ != 0:
                    rs.append(float(range_ / std_))
            if rs:
                lag_used.append(lag)
                rs_values.append(float(np.mean(rs)))
        if len(rs_values) < 3:
            return np.nan
        try:
            slope, _, _, _, _ = linregress(np.log(lag_used), np.log(rs_values))
            return float(slope)
        except Exception:
            logger.exception("hurst regression failed")
            return np.nan

    def run_adf_test(self, series: pd.Series | None = None) -> dict[str, Any]:
        adfuller, _, _, _ = _import_statsmodels()
        s = self.series if series is None else _clean_series(series)
        if s.nunique(dropna=True) <= 1:
            return {
                "statistic": np.nan,
                "pvalue": 1.0,
                "lags": 0,
                "critical_values": {},
            }
        result = adfuller(s, autolag="AIC")
        return {
            "statistic": float(result[0]),
            "pvalue": float(result[1]),
            "lags": int(result[2]),
            "critical_values": {k: float(v) for k, v in result[4].items()},
        }

    def run_kpss_test(
        self,
        regression: str = "ct",
        suppress_warnings: bool = True,
        series: pd.Series | None = None,
    ) -> dict[str, Any]:
        _, kpss, _, InterpolationWarning = _import_statsmodels()
        s = self.series if series is None else _clean_series(series)
        if s.nunique(dropna=True) <= 1:
            return {
                "statistic": np.nan,
                "pvalue": 0.0,
                "critical_values": {},
                "warning": "constant series",
            }
        if suppress_warnings:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                result = kpss(s, regression=regression)
            warning_msg = None
            for warning in caught:
                if isinstance(warning.message, InterpolationWarning):
                    warning_msg = str(warning.message)
        else:
            result = kpss(s, regression=regression)
            warning_msg = None
        return {
            "statistic": float(result[0]),
            "pvalue": float(result[1]),
            "critical_values": {k: float(v) for k, v in result[3].items()},
            "warning": warning_msg,
        }

    def analyze_windows(
        self,
        windows: list[int],
        min_lag_func: Callable[[int], int] = lambda w: max(5, w // 6),
        max_lag_func: Callable[[int], int] = lambda w: max(10, w // 3),
        drop_na: bool = True,
        suppress_warnings: bool = True,
    ) -> None:
        _ = drop_na
        for window in windows:
            min_lag = min_lag_func(window)
            max_lag = max_lag_func(window)
            window_data = self.series.iloc[-window:]
            window_max_lag = min(max_lag, len(window_data) // 2)
            if window_max_lag < min_lag:
                continue
            hurst = self.calculate_hurst(min_lag, window_max_lag, series=window_data)
            self.results[window] = {
                "hurst": hurst,
                "adf": self.run_adf_test(series=window_data),
                "kpss": self.run_kpss_test(
                    regression="ct",
                    suppress_warnings=suppress_warnings,
                    series=window_data,
                ),
                "min_lag": min_lag,
                "window_max_lag": window_max_lag,
            }

    def _classify_trend_type(self, res: dict[str, Any]) -> str:
        if np.isnan(res["hurst"]):
            return "undetermined (hurst failed)"
        hurst = res["hurst"]
        adf_p = res["adf"]["pvalue"]
        kpss_p = res["kpss"]["pvalue"]
        if hurst > 0.55 and adf_p > 0.05 and kpss_p < 0.05:
            return "strong trend, non-stationary (trend strategies)"
        if hurst > 0.55 and adf_p < 0.05 and kpss_p > 0.05:
            return "trending but stationary (short-term trend possible)"
        if hurst < 0.5 and adf_p < 0.05 and kpss_p > 0.05:
            return "mean-reverting stationary (weak for trend)"
        if hurst > 0.55 and adf_p > 0.05 and kpss_p > 0.05:
            return "conflicting signals (verify further)"
        return "weak trend or counter-trend"

    def get_results_dataframe(self) -> pd.DataFrame:
        rows = []
        for window, res in self.results.items():
            warning = res["kpss"].get("warning") or ""
            rows.append(
                {
                    "window_size": window,
                    "hurst": res["hurst"],
                    "adf_pvalue": res["adf"]["pvalue"],
                    "kpss_pvalue": res["kpss"]["pvalue"],
                    "trend_type": self._classify_trend_type(res),
                    "min_lag": res["min_lag"],
                    "effective_max_lag": res["window_max_lag"],
                    "kpss_warning": warning,
                }
            )
        return pd.DataFrame(rows)


def stationarity_diagnostics(series: pd.Series, *, windows: Sequence[int] | None = None) -> pd.DataFrame:
    """Run windowed Hurst/ADF/KPSS diagnostics."""

    analyzer = TimeSeriesAnalyzer(series)
    analyzer.analyze_windows(_default_windows(windows))
    return analyzer.get_results_dataframe()


def analyze_time_series(
    series: pd.Series,
    windows: list[int] | None = None,
    min_lag_func: Callable[[int], int] = lambda w: max(5, w // 6),
    max_lag_func: Callable[[int], int] = lambda w: max(10, w // 3),
    drop_na: bool = True,
    suppress_warnings: bool = True,
    display_results: bool = False,
) -> pd.DataFrame:
    """Compatibility wrapper for windowed stationarity analysis."""

    analyzer = TimeSeriesAnalyzer(series)
    analyzer.analyze_windows(
        _default_windows(windows), min_lag_func, max_lag_func, drop_na, suppress_warnings
    )
    results_df = analyzer.get_results_dataframe()
    if display_results:
        logger.info("summary:\n%s", results_df.to_csv(sep="\t", index=False, na_rep="nan"))
    return results_df


def analyze_time_series_yearly(
    file_path: str,
    dt_column: str = "datetime",
    close_column: str = "close",
    windows: list[int] | None = None,
    min_lag_func: Callable[[int], int] = lambda w: max(5, w // 6),
    max_lag_func: Callable[[int], int] = lambda w: max(10, w // 3),
    drop_na: bool = True,
    suppress_warnings: bool = True,
    display_results: bool = False,
) -> pd.DataFrame:
    """Run per-year windowed analysis on a CSV with datetime and close columns."""

    data = pd.read_csv(file_path)
    data[dt_column] = pd.to_datetime(data[dt_column])
    data["year"] = data[dt_column].dt.year
    all_results = []
    for year in sorted(data["year"].unique()):
        year_data = data[data["year"] == year]
        valid_windows = [w for w in _default_windows(windows or [10, 30, 60]) if w <= len(year_data)]
        if not valid_windows:
            continue
        result = analyze_time_series(
            year_data[close_column].reset_index(drop=True),
            valid_windows,
            min_lag_func,
            max_lag_func,
            drop_na,
            suppress_warnings,
            display_results,
        )
        if not result.empty:
            result["year"] = year
            all_results.append(result)
    if not all_results:
        raise ValueError("insufficient data for yearly analysis")
    return pd.concat(all_results, ignore_index=True)


def _default_log_diff_lags(lags: Sequence[int] | None = None) -> list[int]:
    if lags is None:
        return [1, 5, 10]
    cleaned = sorted({int(lag) for lag in lags})
    if not cleaned or min(cleaned) < 1:
        raise ValueError("log_diff_lags must contain positive integers")
    return cleaned


def _valid_stationarity_windows(windows: Sequence[int] | None, length: int) -> list[int]:
    valid = [window for window in _default_windows(windows) if window <= length]
    if valid:
        return valid
    if length >= 10:
        return [length]
    return []


def _log_diff(price: pd.Series, lag: int) -> pd.Series:
    price = _clean_series(price, "price")
    if (price <= 0).any():
        raise ValueError("log diff diagnostics require strictly positive price values")
    return np.log(price).diff(lag).replace([np.inf, -np.inf], np.nan).dropna()


def _log_diff_distribution_diagnostics(
    price: pd.Series,
    *,
    lags: Sequence[int] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    kde_rows: list[dict[str, Any]] = []
    qq_rows: list[dict[str, Any]] = []
    for lag in _default_log_diff_lags(lags):
        transformed = _log_diff(price, lag)
        base = {
            "lag": lag,
            "label": f"Log diff {lag}",
            "n_obs": int(len(transformed)),
        }
        kde_rows.append({**base, **_kde_features_for_values(transformed)})
        qq_rows.append({**base, **_qq_features_for_values(transformed)})
    return pd.DataFrame(kde_rows), pd.DataFrame(qq_rows)


def log_diff_diagnostics(
    price: pd.Series,
    *,
    lags: Sequence[int] | None = None,
    windows: Sequence[int] | None = None,
) -> pd.DataFrame:
    """Analyze ``log(price).diff(lag)`` series for the requested lags."""

    price = _clean_series(price, "price")
    log_diff_kde, log_diff_qq = _log_diff_distribution_diagnostics(price, lags=lags)
    rows: list[dict[str, Any]] = []
    for lag in _default_log_diff_lags(lags):
        transformed = _log_diff(price, lag)
        kde = log_diff_kde.loc[log_diff_kde["lag"] == lag].iloc[0].to_dict()
        qq = log_diff_qq.loc[log_diff_qq["lag"] == lag].iloc[0].to_dict()
        valid_windows = _valid_stationarity_windows(windows, len(transformed))
        stationarity = (
            stationarity_diagnostics(transformed, windows=valid_windows)
            if valid_windows
            else pd.DataFrame()
        )
        latest = stationarity.iloc[-1].to_dict() if not stationarity.empty else {}
        rows.append(
            {
                "lag": lag,
                "label": f"Log diff {lag}",
                "n_obs": int(len(transformed)),
                "hurst": latest.get("hurst", np.nan),
                "adf_pvalue": latest.get("adf_pvalue", np.nan),
                "kpss_pvalue": latest.get("kpss_pvalue", np.nan),
                "trend_type": latest.get("trend_type", "insufficient data"),
                "tail_feature": kde["tail_feature"],
                "skew_feature": kde["skew_feature"],
                "kurtosis": qq["kurtosis"],
                "skewness": qq["skewness"],
                "qq_deviation": qq["qq_deviation"],
            }
        )
    return pd.DataFrame(rows)


def analyze_price_series(
    price: pd.Series,
    *,
    windows: Sequence[int] | None = None,
    lags: Sequence[int] | None = None,
    log_diff_lags: Sequence[int] | None = None,
    plot: bool = False,
    output_dir: str | Path | None = None,
) -> TimeSeriesAnalysis:
    """One-shot price-series analysis with conclusion-first summary."""

    price = _clean_series(price, "price")
    distribution = distribution_diagnostics(price, lags=lags, plot=plot, output_dir=output_dir)
    stationarity = stationarity_diagnostics(price, windows=windows)
    log_diff = log_diff_diagnostics(price, lags=log_diff_lags, windows=windows)
    log_diff_kde, log_diff_qq = _log_diff_distribution_diagnostics(price, lags=log_diff_lags)
    latest = stationarity.iloc[-1].to_dict() if not stationarity.empty else {}
    summary = {
        "n_obs": int(len(price)),
        "start": str(price.index.min()) if hasattr(price, "index") else "",
        "end": str(price.index.max()) if hasattr(price, "index") else "",
        "trend_type": latest.get("trend_type", "unknown"),
        "primary_tail_feature": distribution.summary["primary_tail_feature"],
        "primary_skew_feature": distribution.summary["primary_skew_feature"],
    }
    return TimeSeriesAnalysis(
        summary=summary,
        distribution=distribution,
        stationarity=stationarity,
        log_diff=log_diff,
        log_diff_kde=log_diff_kde,
        log_diff_qq=log_diff_qq,
    )


def engle_granger_cointegration(
    y: pd.Series,
    x: pd.Series,
    significance: float = 0.05,
) -> dict[str, Any]:
    """Engle-Granger two-step cointegration test."""

    sm = _import_sm_api()
    adfuller, _, _, _ = _import_statsmodels()
    aligned = pd.concat([pd.Series(y), pd.Series(x)], axis=1, join="inner").dropna()
    if aligned.shape[0] < 20:
        raise ValueError(f"need at least 20 aligned observations, got {aligned.shape[0]}")
    y_aligned = aligned.iloc[:, 0].astype(float)
    x_aligned = aligned.iloc[:, 1].astype(float)
    X = sm.add_constant(x_aligned.values)
    ols = sm.OLS(y_aligned.values, X).fit()
    alpha = float(ols.params[0])
    beta = float(ols.params[1])
    residuals = pd.Series(ols.resid, index=aligned.index, name="residual")
    if residuals.std(ddof=0) < 1e-12:
        adf_stat = float("-inf")
        adf_pvalue = 0.0
        adf_lags = 0
        adf_crit = {}
    else:
        adf = adfuller(residuals.values, autolag="AIC")
        adf_stat = float(adf[0])
        adf_pvalue = float(adf[1])
        adf_lags = int(adf[2])
        adf_crit = {k: float(v) for k, v in adf[4].items()}
    return {
        "alpha": alpha,
        "beta": beta,
        "residuals": residuals,
        "adf_statistic": adf_stat,
        "adf_pvalue": adf_pvalue,
        "adf_lags": adf_lags,
        "adf_critical_values": adf_crit,
        "is_cointegrated": adf_pvalue < significance,
        "n_obs": int(aligned.shape[0]),
        "r_squared": float(ols.rsquared),
    }


def cointegration_diagnostics(
    y: pd.Series,
    x: pd.Series,
    *,
    significance: float = 0.05,
) -> dict[str, Any]:
    """Composable Engle-Granger diagnostics without dataclass wrapping."""

    return engle_granger_cointegration(y, x, significance=significance)


def analyze_pair_cointegration(
    y: pd.Series,
    x: pd.Series,
    *,
    significance: float = 0.05,
) -> CointegrationAnalysis:
    """Top-level pair cointegration analysis."""

    result = cointegration_diagnostics(y, x, significance=significance)
    residuals = result.pop("residuals")
    summary = {
        "n_obs": result["n_obs"],
        "alpha": result["alpha"],
        "beta": result["beta"],
        "adf_pvalue": result["adf_pvalue"],
        "is_cointegrated": result["is_cointegrated"],
        "r_squared": result["r_squared"],
    }
    return CointegrationAnalysis(summary=summary, residuals=residuals, evidence=result)


def half_life_of_mean_reversion(spread: pd.Series) -> dict[str, Any]:
    """Half-life of mean reversion via AR(1) on first differences."""

    sm = _import_sm_api()
    s = _clean_series(spread, "spread")
    if len(s) < 10:
        raise ValueError(f"need at least 10 observations, got {len(s)}")
    s_lag = s.shift(1).dropna()
    delta_s = s.diff().dropna()
    aligned = pd.concat([delta_s, s_lag], axis=1, join="inner").dropna()
    aligned.columns = ["delta_s", "s_lag"]
    X = sm.add_constant(aligned["s_lag"].values)
    ols = sm.OLS(aligned["delta_s"].values, X).fit()
    constant = float(ols.params[0])
    lam = float(ols.params[1])
    lam_pvalue = float(ols.pvalues[1])
    if lam < 0:
        half_life_bars = float(-np.log(2) / lam)
        is_mean_reverting = True
    else:
        half_life_bars = float("inf")
        is_mean_reverting = False
    return {
        "lambda": lam,
        "constant": constant,
        "lambda_pvalue": lam_pvalue,
        "half_life_bars": half_life_bars,
        "is_mean_reverting": is_mean_reverting,
        "r_squared": float(ols.rsquared),
        "n_obs": int(aligned.shape[0]),
    }


def mean_reversion_diagnostics(spread: pd.Series) -> dict[str, Any]:
    """Composable mean-reversion diagnostics."""

    return half_life_of_mean_reversion(spread)


def analyze_spread(
    spread: pd.Series,
    *,
    windows: Sequence[int] | None = None,
    plot: bool = False,
    output_dir: str | Path | None = None,
) -> MeanReversionAnalysis:
    """Top-level spread analysis for stationarity and mean reversion."""

    spread = _clean_series(spread, "spread")
    stationarity = stationarity_diagnostics(spread, windows=windows)
    half_life = mean_reversion_diagnostics(spread)
    distribution = distribution_diagnostics(spread, plot=plot, output_dir=output_dir)
    latest = stationarity.iloc[-1].to_dict() if not stationarity.empty else {}
    summary = {
        "n_obs": int(len(spread)),
        "is_mean_reverting": half_life["is_mean_reverting"],
        "half_life_bars": half_life["half_life_bars"],
        "lambda": half_life["lambda"],
        "trend_type": latest.get("trend_type", "unknown"),
    }
    return MeanReversionAnalysis(
        summary=summary,
        stationarity=stationarity,
        half_life=half_life,
        distribution=distribution,
    )


def _period_ts_analysis(price: pd.Series, period: str, period_index: int) -> dict[str, Any]:
    try:
        period_price = price if period == "1min" else price.resample(period).last().dropna()
        diagnostics = distribution_diagnostics(period_price)
        return {
            "period": period,
            "index": period_index,
            "success": True,
            "error": None,
            "data": diagnostics,
        }
    except Exception as exc:
        return {
            "period": period,
            "index": period_index,
            "success": False,
            "error": str(exc),
            "data": None,
        }


def ts_groupby_period(
    price: pd.Series,
    periods: Sequence[str] | None = None,
    save_path: str | Path | None = None,
    show: bool = True,
):
    """Multi-frequency KDE analysis with optional aggregate CSV export."""

    if periods is None:
        periods = ["1min", "5min", "15min", "1h", "4h", "1d"]
    plt = _import_matplotlib()
    Parallel, delayed = _import_joblib()
    results = Parallel(n_jobs=-1)(
        delayed(_period_ts_analysis)(price, period, i) for i, period in enumerate(periods)
    )
    results.sort(key=lambda item: item["index"])
    fig, axes = plt.subplots(len(results), 1, figsize=(12, max(4, 4 * len(results))))
    axes = np.atleast_1d(axes)
    combined = []
    for ax, result in zip(axes, results, strict=False):
        period = result["period"]
        if not result["success"]:
            ax.text(0.5, 0.5, f"{period} failed: {result['error']}", ha="center", va="center")
            ax.axis("off")
            continue
        diagnostics: DistributionDiagnostics = result["data"]
        kde = diagnostics.kde.copy()
        kde["period"] = period
        combined.append(kde.reset_index())
        ax.set_title(f"{period} KDE diagnostics")
        ax.plot(kde.index, kde["statistical_kurtosis"], marker="o")
        ax.set_ylabel("kurtosis")
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    plot_path = None
    csv_path = None
    if save_path:
        base = os.path.splitext(str(save_path))[0]
        plot_path = f"{base}_groupby_period_ts.png"
        csv_path = f"{base}_groupby_period_ts.csv"
        fig.savefig(plot_path, bbox_inches="tight", dpi=150)
        if combined:
            pd.concat(combined, ignore_index=True).to_csv(csv_path, index=False)
    if show:
        plt.show()
    return fig, plot_path, csv_path


__all__ = [
    "TimeSeriesAnalyzer",
    "analysis_results_to_df",
    "analyze_pair_cointegration",
    "analyze_price_series",
    "analyze_spread",
    "analyze_time_series",
    "analyze_time_series_yearly",
    "cointegration_diagnostics",
    "distribution_diagnostics",
    "engle_granger_cointegration",
    "ensure_dir_and_get_path",
    "half_life_of_mean_reversion",
    "kde_analysis",
    "log_diff_diagnostics",
    "mean_reversion_diagnostics",
    "qq_analysis",
    "stationarity_diagnostics",
    "ts_analysis",
    "ts_groupby_period",
]
