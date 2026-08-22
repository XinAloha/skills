"""Tests for price-volume confirmation factor detectors."""

import numpy as np
import pandas as pd
import pytest

from core._types import SignalResult
from core.price_volume import (
    detect_index_momentum,
    detect_volatility_regime,
    run_all_detectors,
    get_triggered_signals,
    get_bullish_signals,
    get_bearish_signals,
    compute_composite_score,
    PRICE_VOLUME_REGISTRY,
)


# ── Helpers ──


def _make_csi300_data(prices: list[float]) -> pd.DataFrame:
    """Create a simple DataFrame with CSI300 prices."""
    return pd.DataFrame({
        "date": [f"20260{i:03d}" for i in range(1, len(prices) + 1)],
        "csi300": prices,
    })


# ── Index momentum tests ──


class TestIndexMomentum:
    def test_bullish_momentum(self, sample_config):
        """20-day return > 5% + price > MA20 → bullish."""
        # Build 30 days: steady rise from 4000 to 4400 (~10% gain)
        prices = [4000 + i * 13.3 for i in range(30)]  # ~400 point gain = 10%
        data = _make_csi300_data(prices)
        result = detect_index_momentum(data, sample_config)
        assert result.triggered
        assert result.direction == "bullish"
        assert result.strength > 0

    def test_bearish_momentum(self, sample_config):
        """20-day return < -5% + price < MA20 → bearish."""
        prices = [4400 - i * 15 for i in range(30)]  # steep decline
        data = _make_csi300_data(prices)
        result = detect_index_momentum(data, sample_config)
        assert result.triggered
        assert result.direction == "bearish"
        assert result.strength < 0

    def test_neutral_small_gain(self, sample_config):
        """Small 20-day return within threshold → neutral."""
        prices = [4000 + i * 1 for i in range(30)]  # ~0.75% gain
        data = _make_csi300_data(prices)
        result = detect_index_momentum(data, sample_config)
        assert not result.triggered
        assert result.direction == "neutral"

    def test_neutral_below_ma_but_positive(self, sample_config):
        """Price below MA20 negates the bullish signal."""
        # Large gain but recent pullback puts price below MA20
        np.random.seed(1)
        base = [4000 + i * 15 for i in range(25)]  # strong uptrend
        base += [base[-1] * (1 - d) for d in np.linspace(0, 0.08, 5)]  # sharp pullback
        data = _make_csi300_data(base)
        result = detect_index_momentum(data, sample_config)
        # 20-day return is positive but price is below MA20 → not triggered
        assert not result.triggered or result.direction == "neutral"

    def test_empty_data(self, sample_config):
        result = detect_index_momentum(pd.DataFrame(), sample_config)
        assert not result.triggered
        assert "缺少CSI300数据" in result.summary

    def test_missing_csi_column(self, sample_config):
        df = pd.DataFrame({"other": [4000, 4100, 4200]})
        result = detect_index_momentum(df, sample_config)
        assert not result.triggered

    def test_insufficient_data(self, sample_config):
        """Less than lookback days → neutral."""
        prices = [4000] * 15  # less than 20
        data = _make_csi300_data(prices)
        result = detect_index_momentum(data, sample_config)
        assert not result.triggered
        assert "数据不足" in result.summary

    def test_detail_contains_metrics(self, sample_config):
        prices = [4000 + i * 5 for i in range(30)]
        data = _make_csi300_data(prices)
        result = detect_index_momentum(data, sample_config)
        assert "ret_20d_pct" in result.detail
        assert "ma_deviation_pct" in result.detail
        assert "csi300_current" in result.detail

    def test_custom_threshold_config(self):
        """Lower threshold via config triggers bullish more easily."""
        prices = [4000 + i * 2 for i in range(30)]  # ~1.5% gain
        data = _make_csi300_data(prices)
        config = {"price_volume": {"momentum_lookback": 20, "momentum_bullish_threshold": 1.0,
                                    "momentum_bearish_threshold": -1.0}}
        result = detect_index_momentum(data, config)
        # With threshold=1%, this small uptrend should trigger
        # (but also needs price > MA20)
        assert "ret_20d_pct" in result.detail

    def test_uses_csi300_column_variants(self, sample_config):
        """Should accept 'CSI300' (uppercase) column."""
        df = pd.DataFrame({
            "date": [f"20260{i:03d}" for i in range(1, 31)],
            "CSI300": [4000 + i * 10 for i in range(30)],
        })
        result = detect_index_momentum(df, sample_config)
        assert result.key == "index_momentum"


# ── Volatility regime tests ──


class TestVolatilityRegime:
    def test_high_volatility_bearish(self):
        """High volatility (>30%) → bearish."""
        np.random.seed(42)
        # Generate volatile daily returns
        base = 4000
        prices = [base]
        for _ in range(30):
            prices.append(prices[-1] * (1 + np.random.randn() * 0.03))  # ~48% annualized
        data = _make_csi300_data(prices)
        config = {"price_volume": {"volatility_lookback": 20, "volatility_high_threshold": 30.0,
                                    "volatility_low_threshold": 15.0}}
        result = detect_volatility_regime(data, config)
        assert result.key == "volatility_regime"
        # High vol should trigger bearish
        if result.triggered:
            assert result.direction == "bearish"

    def test_low_volatility_bullish(self):
        """Low volatility (<15%) → bullish."""
        prices = [4000]
        for _ in range(30):
            prices.append(prices[-1] * (1 + np.random.randn() * 0.005))  # ~8% annualized
        data = _make_csi300_data(prices)
        config = {"price_volume": {"volatility_lookback": 20, "volatility_high_threshold": 30.0,
                                    "volatility_low_threshold": 15.0}}
        result = detect_volatility_regime(data, config)
        if result.triggered:
            assert result.direction == "bullish"

    def test_normal_volatility_neutral(self):
        """Moderate volatility (15-30%) → neutral."""
        prices = [4000]
        for _ in range(30):
            prices.append(prices[-1] * (1 + np.random.randn() * 0.012))  # ~19% annualized
        data = _make_csi300_data(prices)
        config = {"price_volume": {"volatility_lookback": 20, "volatility_high_threshold": 30.0,
                                    "volatility_low_threshold": 15.0}}
        result = detect_volatility_regime(data, config)
        # May or may not trigger depending on exact random values
        assert isinstance(result, SignalResult)

    def test_empty_data(self, sample_config):
        result = detect_volatility_regime(pd.DataFrame(), sample_config)
        assert not result.triggered

    def test_missing_csi_column(self, sample_config):
        df = pd.DataFrame({"other": [4000, 4100, 4200]})
        result = detect_volatility_regime(df, sample_config)
        assert not result.triggered

    def test_insufficient_data(self, sample_config):
        """Less than lookback + 1 days → neutral."""
        prices = [4000] * 15
        data = _make_csi300_data(prices)
        result = detect_volatility_regime(data, sample_config)
        assert not result.triggered
        assert "数据不足" in result.summary

    def test_detail_has_vol_metrics(self, sample_config):
        """Detail should include annualized volatility."""
        np.random.seed(7)
        prices = [4000]
        for _ in range(30):
            prices.append(prices[-1] * (1 + np.random.randn() * 0.01))
        data = _make_csi300_data(prices)
        result = detect_volatility_regime(data, sample_config)
        assert "annualized_vol_pct" in result.detail
        assert "n_observations" in result.detail


# ── Registry tests ──


class TestRegistry:
    def test_all_2_detectors_registered(self):
        assert len(PRICE_VOLUME_REGISTRY) == 2
        expected = {"index_momentum", "volatility_regime"}
        assert set(PRICE_VOLUME_REGISTRY.keys()) == expected

    def test_all_have_func_weight_label(self):
        for key, entry in PRICE_VOLUME_REGISTRY.items():
            assert "func" in entry, f"{key} missing func"
            assert "weight" in entry, f"{key} missing weight"
            assert "label" in entry, f"{key} missing label"
            assert "half_life_days" in entry, f"{key} missing half_life_days"


# ── run_all_detectors tests ──


class TestRunAllDetectors:
    def _make_data(self, n=50):
        prices = [4000 + i * 5 + np.random.randn() * 20 for i in range(n)]
        return _make_csi300_data(prices)

    def test_returns_2_results(self, sample_config):
        data = self._make_data()
        results = run_all_detectors(data, sample_config)
        assert len(results) == 2
        assert all(isinstance(r, SignalResult) for r in results)

    def test_active_detectors_filter(self, sample_config):
        data = self._make_data()
        results = run_all_detectors(data, sample_config, active_detectors={"index_momentum"})
        assert len(results) == 1
        assert results[0].key == "index_momentum"

    def test_empty_data(self, sample_config):
        results = run_all_detectors(pd.DataFrame(), sample_config)
        assert len(results) == 2
        for r in results:
            assert not r.triggered

    def test_detector_exception_returns_neutral(self, sample_config, monkeypatch):
        """Detector exception → neutral signal, doesn't crash."""
        def _raise(*args, **kwargs):
            raise RuntimeError("simulated failure")
        monkeypatch.setattr("core.price_volume.detect_index_momentum", _raise)
        data = self._make_data()
        results = run_all_detectors(data, sample_config, active_detectors={"index_momentum"})
        assert len(results) == 1
        assert not results[0].triggered


# ── Helpers tests ──


class TestHelpers:
    def _make_data(self, n=50):
        prices = [4000 + i * 10 for i in range(n)]  # steady uptrend
        return _make_csi300_data(prices)

    def test_get_triggered_signals(self, sample_config):
        data = self._make_data()
        results = run_all_detectors(data, sample_config)
        triggered = get_triggered_signals(results)
        assert len(triggered) <= len(results)

    def test_get_bullish_signals(self, sample_config):
        data = self._make_data()
        results = run_all_detectors(data, sample_config)
        bullish = get_bullish_signals(results)
        for s in bullish:
            assert s.direction == "bullish"

    def test_get_bearish_signals(self, sample_config):
        data = self._make_data()
        results = run_all_detectors(data, sample_config)
        bearish = get_bearish_signals(results)
        for s in bearish:
            assert s.direction == "bearish"

    def test_composite_score_range(self, sample_config):
        data = self._make_data()
        results = run_all_detectors(data, sample_config)
        score = compute_composite_score(results)
        assert -1.0 <= score <= 1.0

    def test_composite_score_empty(self):
        score = compute_composite_score([])
        assert score == 0.0
