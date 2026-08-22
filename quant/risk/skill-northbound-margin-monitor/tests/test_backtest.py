"""Tests for core/backtest.py — historical IC backtesting."""

import numpy as np
import pandas as pd
import pytest

from core.backtest import (
    BacktestResult,
    DetectorICResult,
    RollingICResult,
    _spearmanr,
    analyse_detector_weights,
    backtest_summary_table,
    detector_weight_summary_table,
    rolling_ic_analysis,
    run_ic_backtest,
)


class TestSpearmanR:
    def test_perfect_positive(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        r = _spearmanr(x, y)
        assert 0.99 <= r <= 1.01

    def test_perfect_negative(self):
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([50.0, 40.0, 30.0, 20.0, 10.0])
        r = _spearmanr(x, y)
        assert -1.01 <= r <= -0.99

    def test_no_correlation(self):
        np.random.seed(99)
        x = np.random.randn(50)
        y = np.random.randn(50)
        r = _spearmanr(x, y)
        assert -0.5 < r < 0.5

    def test_too_few_points(self):
        assert _spearmanr(np.array([1.0, 2.0]), np.array([3.0, 4.0])) == 0.0

    def test_constant_array(self):
        r = _spearmanr(np.array([1.0, 1.0, 1.0, 1.0]), np.array([2.0, 3.0, 4.0, 5.0]))
        assert r == 0.0


class TestICBacktest:
    @pytest.fixture
    def backtest_nb(self):
        """Build a northbound summary with a predictable score-return relationship."""
        dates = pd.date_range("2025-01-02", periods=150, freq="B")
        np.random.seed(123)
        # Trend up with noise
        trend = np.linspace(3500, 4200, 150)
        noise = np.random.randn(150) * 30
        csi300 = trend + noise
        market_value = 18000 + np.cumsum(np.random.randn(150) * 40)
        net_buy = np.diff(market_value, prepend=market_value[0])

        return pd.DataFrame({
            "date": [d.strftime("%Y%m%d") for d in dates],
            "market_value": market_value,
            "net_buy_amount": net_buy,
            "CSI300": csi300,
        })

    @pytest.fixture
    def backtest_margin(self):
        """Build margin macro data."""
        dates = pd.date_range("2025-01-02", periods=150, freq="B")
        np.random.seed(124)
        margin_bal = 14000 + np.cumsum(np.random.randn(150) * 25)
        short_bal = 700 + np.cumsum(np.random.randn(150) * 4)
        buy = np.random.uniform(350, 700, 150)
        rows = []
        for i, d in enumerate(dates):
            for mkt in ["sh", "sz"]:
                rows.append({
                    "date": d.strftime("%Y%m%d"),
                    "market": mkt,
                    "margin_balance": margin_bal[i] * 0.55,
                    "short_balance": short_bal[i] * 0.6,
                    "buy_on_margin_value": buy[i] * 0.5,
                })
        return pd.DataFrame(rows)

    def test_backtest_returns_result(self, backtest_nb, backtest_margin):
        result = run_ic_backtest(
            backtest_nb, backtest_margin,
            min_window=60, step_days=5,
        )
        assert isinstance(result, BacktestResult)
        assert result.n_periods > 0
        assert len(result.score_series) == result.n_periods
        assert len(result.score_series) == len(result.return_series)

    def test_backtest_ic_range(self, backtest_nb, backtest_margin):
        result = run_ic_backtest(
            backtest_nb, backtest_margin,
            min_window=60, step_days=5,
        )
        assert -1.0 <= result.mean_ic <= 1.0
        if result.n_periods >= 5:
            assert result.icir == result.mean_ic / result.ic_std if result.ic_std > 0 else 0.0

    def test_backtest_hit_rate_range(self, backtest_nb, backtest_margin):
        result = run_ic_backtest(
            backtest_nb, backtest_margin,
            min_window=60, step_days=5,
        )
        assert 0.0 <= result.hit_rate <= 1.0

    def test_backtest_insufficient_data(self):
        """Too few rows should raise ValueError with clear message."""
        nb = pd.DataFrame({
            "date": ["20250101", "20250102"],
            "market_value": [20000, 20100],
            "net_buy_amount": [0, 100],
            "CSI300": [4000, 4010],
        })
        mg = pd.DataFrame({
            "date": ["20250101", "20250102"],
            "market": ["sh", "sz"],
            "margin_balance": [15000, 15000],
            "short_balance": [500, 500],
            "buy_on_margin_value": [300, 300],
        })
        with pytest.raises(ValueError, match="Need at least"):
            run_ic_backtest(nb, mg, min_window=60)

    def test_backtest_summary_table(self, backtest_nb, backtest_margin):
        result = run_ic_backtest(backtest_nb, backtest_margin, min_window=60, step_days=5)
        table = backtest_summary_table(result)
        assert "Mean IC" in table
        assert "ICIR" in table
        assert "Hit Rate" in table
        assert f"{result.mean_ic:.4f}" in table

    def test_backtest_with_config(self, backtest_nb, backtest_margin):
        config = {"scoring": {"northbound_weight": 0.6, "margin_weight": 0.4}}
        result = run_ic_backtest(backtest_nb, backtest_margin, config=config, min_window=60, step_days=5)
        assert isinstance(result, BacktestResult)

    def test_dense_step(self, backtest_nb, backtest_margin):
        """step_days=1 should produce more evaluation periods."""
        result = run_ic_backtest(backtest_nb, backtest_margin, min_window=60, step_days=1)
        assert result.n_periods > 5


# ── Rolling IC tests ──


class TestRollingIC:
    """Rolling window IC stability analysis."""

    def test_rolling_ic_basic(self):
        """Positive-trend scores + noisy returns = moderate positive IC."""
        np.random.seed(42)
        n = 100
        scores = list(np.arange(n) * 0.01 + np.random.randn(n) * 0.1)
        returns = list(np.arange(n) * 0.005 + np.random.randn(n) * 0.05)
        dates = [f"2025-{i:03d}" for i in range(n)]

        result = rolling_ic_analysis(scores, returns, dates, window_size=30, step_size=10)
        assert isinstance(result, RollingICResult)
        assert result.n_windows > 0
        assert len(result.ic_series) == result.n_windows
        assert 0.0 <= result.stability_ratio <= 1.0

    def test_rolling_ic_insufficient_data(self):
        """Too few data points should return empty result."""
        result = rolling_ic_analysis(
            [1.0, 2.0], [0.01, -0.01], ["d1", "d2"],
            window_size=60, step_size=20,
        )
        assert result.n_windows == 0
        assert "数据不足" in result.summary

    def test_rolling_ic_positive_signal(self):
        """Well-correlated signal should have high stability ratio."""
        np.random.seed(7)
        n = 80
        base = np.arange(n) * 0.1
        scores = list(base + np.random.randn(n) * 0.02)
        returns = list(base * 0.1 + np.random.randn(n) * 0.01)
        dates = [f"d{i}" for i in range(n)]

        result = rolling_ic_analysis(scores, returns, dates, window_size=20, step_size=10)
        # Most windows should have positive IC
        assert result.stability_ratio > 0.5


# ── Detector weight analysis tests ──


class TestDetectorWeightAnalysis:
    """Per-detector IC analysis and weight suggestion."""

    def _make_signals(self, keys, strengths):
        """Create mock SignalResult objects."""
        from core._types import SignalResult
        return [
            SignalResult(key=k, label=k, triggered=True, strength=s,
                         direction="bullish" if s > 0 else "bearish", summary="")
            for k, s in zip(keys, strengths)
        ]

    def test_analyse_basic(self):
        """Basic detector IC analysis runs without error."""
        np.random.seed(123)
        n = 60
        # Generate per-period signal lists
        nb_signals_list = []
        margin_signals_list = []
        futures_signals_list = []
        returns = []

        for i in range(n):
            nb_signals_list.append(self._make_signals(
                ["flow_trend", "single_day_anomaly", "sector_preference",
                 "holdings_change", "cumulative_trend", "market_flow_direction",
                 "flow_direction_trend"],
                [np.random.randn() * 0.3 for _ in range(7)],
            ))
            margin_signals_list.append(self._make_signals(
                ["margin_balance_trend", "margin_buy_ratio", "short_trend",
                 "margin_heavy_stocks", "margin_short_ratio", "margin_type_distribution"],
                [np.random.randn() * 0.3 for _ in range(6)],
            ))
            futures_signals_list.append(self._make_signals(
                ["futures_basis", "open_interest_trend", "basis_oi_convergence"],
                [np.random.randn() * 0.3 for _ in range(3)],
            ))
            returns.append(np.random.randn() * 0.02)

        results = analyse_detector_weights(
            nb_signals_list, margin_signals_list, futures_signals_list, returns,
        )
        assert len(results) == 17  # 7 NB + 7 margin + 3 futures
        assert all(isinstance(r, DetectorICResult) for r in results)

    def test_each_result_has_required_fields(self):
        """Every DetectorICResult should have all expected fields."""
        signals = [self._make_signals(["flow_trend"], [0.5]) for _ in range(10)]
        returns = [0.01 + i * 0.001 for i in range(10)]

        results = analyse_detector_weights(signals, signals, signals, returns)
        for r in results:
            assert isinstance(r.key, str)
            assert isinstance(r.label, str)
            assert r.dimension in ("northbound", "margin", "futures")
            assert r.current_weight >= 0
            assert -1.0 <= r.mean_ic <= 1.0
            assert r.suggested_weight >= 0
            assert isinstance(r.suggestion_reason, str)

    def test_detector_weight_summary_table(self):
        """Summary table should contain all detectors."""
        results = [
            DetectorICResult(
                key="flow_trend", label="净流向趋势", dimension="northbound",
                current_weight=3, mean_ic=0.045, ic_ir=0.6, hit_rate=0.55,
                n_observations=50, suggested_weight=3,
                suggestion_reason="IC=0.045, ICIR=0.60 — 维持权重",
            ),
            DetectorICResult(
                key="margin_buy_ratio", label="融资买入比", dimension="margin",
                current_weight=3, mean_ic=-0.008, ic_ir=0.08, hit_rate=0.48,
                n_observations=50, suggested_weight=2,
                suggestion_reason="预测能力弱，建议减权重",
            ),
        ]
        table = detector_weight_summary_table(results)
        assert "净流向趋势" in table
        assert "融资买入比" in table
        assert "0.045" in table or "+0.045" in table or "0.0450" in table
        assert "维持权重" in table


# ── Rolling IC stability label tests ──


class TestRollingICStability:
    """Stability assessment labels for rolling IC analysis."""

    def test_highly_stable(self):
        """≥80% positive windows + low std → 高度稳定."""
        np.random.seed(1)
        n = 100
        # Scores that produce consistently positive IC
        base = np.arange(n) * 0.1
        scores = list(base + np.random.randn(n) * 0.01)
        returns = list(base * 0.05 + np.random.randn(n) * 0.005)
        dates = [f"d{i}" for i in range(n)]
        result = rolling_ic_analysis(scores, returns, dates, window_size=20, step_size=10)
        assert result.n_windows > 0
        assert "高度稳定" in result.summary or "基本稳定" in result.summary

    def test_unstable_signal(self):
        """Random uncorrelated scores → IC unstable."""
        np.random.seed(99)
        n = 80
        scores = list(np.random.randn(n))
        returns = list(np.random.randn(n))
        dates = [f"d{i}" for i in range(n)]
        result = rolling_ic_analysis(scores, returns, dates, window_size=20, step_size=10)
        # Uncorrelated random data should have low stability
        assert result.stability_ratio < 0.8 or "不可靠" in result.summary or "不稳定" in result.summary

    def test_summary_includes_metrics(self):
        """Summary should include key metrics."""
        np.random.seed(42)
        n = 100
        scores = list(np.arange(n) * 0.01 + np.random.randn(n) * 0.1)
        returns = list(np.arange(n) * 0.005 + np.random.randn(n) * 0.05)
        dates = [f"2025-{i:03d}" for i in range(n)]
        result = rolling_ic_analysis(scores, returns, dates, window_size=30, step_size=10)
        assert "IC" in result.summary or "ic" in result.summary.lower()
        assert isinstance(result.stability_ratio, float)


# ── Backtest with futures data tests ──


class TestBacktestWithFutures:
    """run_ic_backtest with futures data included."""

    @pytest.fixture
    def backtest_futures(self):
        """Futures data for backtesting."""
        dates = pd.date_range("2025-01-02", periods=150, freq="B")
        np.random.seed(200)
        rows = []
        for idx_name in ["CSI300", "SSE50", "CSI500"]:
            oi = 50000 + np.cumsum(np.random.randn(150) * 300)
            for i, d in enumerate(dates):
                rows.append({
                    "date": d.strftime("%Y%m%d"),
                    "index_name": idx_name,
                    "close": 4000 + i * 5 + np.random.randn() * 30,
                    "spot_close": 4000 + i * 5 + np.random.randn() * 20,
                    "open_interest": max(500, oi[i]),
                    "volume": np.random.uniform(10000, 50000),
                })
        return pd.DataFrame(rows)

    def _make_nb(self):
        dates = pd.date_range("2025-01-02", periods=150, freq="B")
        np.random.seed(123)
        trend = np.linspace(3500, 4200, 150)
        noise = np.random.randn(150) * 30
        csi300 = trend + noise
        market_value = 18000 + np.cumsum(np.random.randn(150) * 40)
        net_buy = np.diff(market_value, prepend=market_value[0])
        return pd.DataFrame({
            "date": [d.strftime("%Y%m%d") for d in dates],
            "market_value": market_value,
            "net_buy_amount": net_buy,
            "CSI300": csi300,
        })

    def _make_margin(self):
        dates = pd.date_range("2025-01-02", periods=150, freq="B")
        np.random.seed(124)
        margin_bal = 14000 + np.cumsum(np.random.randn(150) * 25)
        short_bal = 700 + np.cumsum(np.random.randn(150) * 4)
        buy = np.random.uniform(350, 700, 150)
        rows = []
        for i, d in enumerate(dates):
            for mkt in ["sh", "sz"]:
                rows.append({
                    "date": d.strftime("%Y%m%d"),
                    "market": mkt,
                    "margin_balance": margin_bal[i] * 0.55,
                    "short_balance": short_bal[i] * 0.6,
                    "buy_on_margin_value": buy[i] * 0.5,
                })
        return pd.DataFrame(rows)

    def test_backtest_with_futures(self, backtest_futures):
        """Backtest should accept and process futures data."""
        result = run_ic_backtest(
            self._make_nb(), self._make_margin(),
            futures_data=backtest_futures,
            min_window=60, step_days=5,
        )
        assert isinstance(result, BacktestResult)
        assert result.n_periods > 0

    def test_summary_table_has_required_fields(self):
        """Summary table should contain all key metrics."""
        result = run_ic_backtest(
            self._make_nb(), self._make_margin(),
            min_window=60, step_days=5,
        )
        table = backtest_summary_table(result)
        assert "Mean IC" in table
        assert "ICIR" in table
        assert "Hit Rate" in table
        assert "评估周期数" in table
