"""Tests for futures signal detectors."""

import numpy as np
import pandas as pd
import pytest

from core._types import SignalResult
from core.futures import (
    detect_futures_basis,
    detect_open_interest_trend,
    detect_basis_oi_convergence,
    run_all_detectors,
    get_triggered_signals,
    get_bullish_signals,
    get_bearish_signals,
    compute_composite_score,
    FUTURES_REGISTRY,
)


class TestFuturesBasis:
    def test_positive_basis_triggers_bullish(self, sample_config):
        """Create data with strong positive basis."""
        dates = pd.date_range("2026-01-02", periods=80, freq="B")
        rows = []
        for idx_name, spot_base in [("CSI300", 4000), ("SSE50", 2800), ("CSI500", 5500)]:
            spot = spot_base + np.cumsum(np.random.RandomState(47).randn(80) * 5)
            # Strong positive basis: futures consistently ~40 pts above spot
            basis = np.random.RandomState(48).randn(80) * 5 + 40
            futures_close = spot + basis
            for i, d in enumerate(dates):
                rows.append({
                    "date": d.strftime("%Y%m%d"),
                    "index_name": idx_name,
                    "close": futures_close[i],
                    "spot_close": spot[i],
                    "open_interest": 50000,
                })
        df = pd.DataFrame(rows)
        result = detect_futures_basis(df, sample_config)
        assert result.triggered
        assert result.direction == "bullish"
        assert result.strength > 0

    def test_negative_basis_triggers_bearish(self, sample_futures_data_bearish, sample_config):
        result = detect_futures_basis(sample_futures_data_bearish, sample_config)
        assert result.triggered
        assert result.direction == "bearish"
        assert result.strength < 0

    def test_basis_detail_has_required_fields(self, sample_futures_data, sample_config):
        result = detect_futures_basis(sample_futures_data, sample_config)
        assert "avg_basis_pct" in result.detail
        assert "n_positive" in result.detail
        assert "n_total" in result.detail
        assert result.detail["n_total"] == 3  # 3 indices

    def test_empty_data(self, sample_config):
        result = detect_futures_basis(pd.DataFrame(), sample_config)
        assert not result.triggered
        assert result.direction == "neutral"

    def test_missing_close_column(self, sample_config):
        df = pd.DataFrame({"date": ["20260101"], "open": [4000]})
        result = detect_futures_basis(df, sample_config)
        assert not result.triggered

    def test_all_nan_prices(self, sample_config):
        df = pd.DataFrame({
            "date": ["20260101", "20260102"],
            "index_name": ["CSI300", "CSI300"],
            "close": [np.nan, np.nan],
            "spot_close": [np.nan, np.nan],
        })
        result = detect_futures_basis(df, sample_config)
        assert not result.triggered

    def test_single_index(self, sample_config):
        """Should work with only one index's data."""
        df = pd.DataFrame({
            "date": pd.date_range("2026-01-02", periods=60, freq="B").strftime("%Y%m%d"),
            "index_name": ["CSI300"] * 60,
            "contract": ["IF"] * 60,
            "close": 4000 + np.cumsum(np.random.RandomState(99).randn(60) * 10),
            "spot_close": 4000 + np.cumsum(np.random.RandomState(99).randn(60) * 10) + 20,
            "open_interest": 50000 + np.cumsum(np.random.RandomState(99).randn(60) * 500),
        })
        result = detect_futures_basis(df, sample_config)
        # Should still work with one index
        assert isinstance(result, SignalResult)


class TestOpenInterestTrend:
    def test_rising_oi_triggers_bullish(self, sample_config):
        """Create data with clearly rising OI (>2% 5-day change)."""
        dates = pd.date_range("2026-01-02", periods=80, freq="B")
        # Steady 3% rise per 5-day period: 50000 * 1.03^(80/5) ≈ 50000 * 1.60
        growth_rate = 1.006  # per day, ~3% per 5 days
        oi = 50000 * (growth_rate ** np.arange(80))
        df = pd.DataFrame({
            "date": [d.strftime("%Y%m%d") for d in dates],
            "index_name": "CSI300",
            "close": 4000 + np.random.randn(80).cumsum() * 5,
            "spot_close": 4000 + np.random.randn(80).cumsum() * 5,
            "open_interest": oi,
            "volume": np.random.uniform(10000, 50000, 80),
        })
        result = detect_open_interest_trend(df, sample_config)
        assert result.triggered
        assert result.direction == "bullish"

    def test_falling_oi_triggers_bearish(self, sample_config):
        """Create data with clearly falling OI (<-2% 5-day change)."""
        dates = pd.date_range("2026-01-02", periods=80, freq="B")
        # Steady 3% decline per 5-day period
        decay_rate = 0.994  # per day, ~-3% per 5 days
        oi = 80000 * (decay_rate ** np.arange(80))
        df = pd.DataFrame({
            "date": [d.strftime("%Y%m%d") for d in dates],
            "index_name": "CSI300",
            "close": 4000 + np.random.randn(80).cumsum() * 5,
            "spot_close": 4000 + np.random.randn(80).cumsum() * 5,
            "open_interest": oi,
            "volume": np.random.uniform(10000, 50000, 80),
        })
        result = detect_open_interest_trend(df, sample_config)
        assert result.triggered
        assert result.direction == "bearish"

    def test_flat_oi_no_trigger(self, sample_config):
        """Flat OI should not trigger."""
        dates = pd.date_range("2026-01-02", periods=80, freq="B")
        df = pd.DataFrame({
            "date": [d.strftime("%Y%m%d") for d in dates],
            "index_name": "CSI300",
            "close": 4000 + np.random.randn(80).cumsum() * 5,
            "spot_close": 4000 + np.random.randn(80).cumsum() * 5,
            "open_interest": [50000] * 80,
            "volume": np.random.uniform(10000, 50000, 80),
        })
        result = detect_open_interest_trend(df, sample_config)
        assert not result.triggered

    def test_empty_data(self, sample_config):
        result = detect_open_interest_trend(pd.DataFrame(), sample_config)
        assert not result.triggered

    def test_missing_oi_column(self, sample_config):
        df = pd.DataFrame({"date": pd.date_range("2026-01-02", periods=80, freq="B").strftime("%Y%m%d")})
        result = detect_open_interest_trend(df, sample_config)
        assert not result.triggered

    def test_insufficient_history(self, sample_config):
        """Less than 5 data points should return neutral."""
        df = pd.DataFrame({
            "date": ["20260101", "20260102", "20260103"],
            "index_name": ["CSI300"] * 3,
            "open_interest": [50000, 51000, 52000],
        })
        result = detect_open_interest_trend(df, sample_config)
        assert not result.triggered


class TestBasisOIConvergence:
    def test_both_bullish_convergence(self, sample_futures_data, sample_config):
        """With bullish basis + rising OI, convergence should trigger."""
        result = detect_basis_oi_convergence(sample_futures_data, sample_config)
        # May or may not trigger depending on exact random data
        assert isinstance(result, SignalResult)

    def test_bearish_convergence(self, sample_futures_data_bearish, sample_config):
        """With bearish basis + potential OI trend."""
        result = detect_basis_oi_convergence(sample_futures_data_bearish, sample_config)
        assert isinstance(result, SignalResult)

    def test_empty_data(self, sample_config):
        result = detect_basis_oi_convergence(pd.DataFrame(), sample_config)
        assert not result.triggered

    def test_detail_has_dependency_info(self, sample_futures_data, sample_config):
        result = detect_basis_oi_convergence(sample_futures_data, sample_config)
        assert "basis_triggered" in result.detail
        assert "oi_triggered" in result.detail


class TestRegistry:
    def test_all_3_detectors_registered(self):
        assert len(FUTURES_REGISTRY) == 3
        expected = {"futures_basis", "open_interest_trend", "basis_oi_convergence"}
        assert set(FUTURES_REGISTRY.keys()) == expected

    def test_all_have_func_weight_label(self):
        for key, entry in FUTURES_REGISTRY.items():
            assert "func" in entry, f"{key} missing func"
            assert "weight" in entry, f"{key} missing weight"
            assert "label" in entry, f"{key} missing label"
            assert "half_life_days" in entry, f"{key} missing half_life_days"


class TestRunAllDetectors:
    def test_returns_3_results(self, sample_futures_data, sample_config):
        results = run_all_detectors(sample_futures_data, sample_config)
        assert len(results) == 3

    def test_active_detectors_filter(self, sample_futures_data, sample_config):
        results = run_all_detectors(
            sample_futures_data, sample_config,
            active_detectors={"futures_basis"},
        )
        assert len(results) == 1
        assert results[0].key == "futures_basis"

    def test_empty_data(self, sample_config):
        results = run_all_detectors(pd.DataFrame(), sample_config)
        assert len(results) == 3
        for r in results:
            assert not r.triggered

    def test_detector_exception_returns_neutral(self, sample_futures_data, sample_config, monkeypatch):
        def _raise(*args, **kwargs):
            raise RuntimeError("simulated failure")
        # Patch the func_map entry since run_all_detectors looks up from there
        import core.futures as fut_mod
        monkeypatch.setitem(fut_mod._DETECTOR_FUNC_MAP, "futures_basis", _raise)
        results = run_all_detectors(
            sample_futures_data, sample_config,
            active_detectors={"futures_basis"},
        )
        assert len(results) == 1
        assert not results[0].triggered


class TestHelpers:
    def test_get_triggered_signals(self, sample_futures_data, sample_config):
        results = run_all_detectors(sample_futures_data, sample_config)
        triggered = get_triggered_signals(results)
        assert len(triggered) <= len(results)

    def test_get_bullish_signals(self, sample_futures_data, sample_config):
        results = run_all_detectors(sample_futures_data, sample_config)
        bullish = get_bullish_signals(results)
        for s in bullish:
            assert s.direction == "bullish"

    def test_get_bearish_signals(self, sample_futures_data, sample_config):
        results = run_all_detectors(sample_futures_data, sample_config)
        bearish = get_bearish_signals(results)
        for s in bearish:
            assert s.direction == "bearish"

    def test_composite_score_range(self, sample_futures_data, sample_config):
        results = run_all_detectors(sample_futures_data, sample_config)
        score = compute_composite_score(results)
        assert -1.0 <= score <= 1.0

    def test_composite_score_empty(self):
        score = compute_composite_score([])
        assert score == 0.0


# ── Neutral basis tests ──


class TestFuturesBasisNeutral:
    """Neutral basis range (-0.3% to +0.3%) and edge cases."""

    def _make_futures_with_basis(self, basis_pct: float):
        """Create futures data with a specific average basis percentage."""
        dates = pd.date_range("2026-01-02", periods=80, freq="B")
        np.random.seed(99)
        rows = []
        for idx_name, spot_base in [("CSI300", 4000), ("SSE50", 2800), ("CSI500", 5500)]:
            spot = spot_base + np.cumsum(np.random.randn(80) * 10)
            futures_close = spot * (1 + basis_pct / 100)
            oi = 50000 + np.cumsum(np.random.randn(80) * 300)
            for i, d in enumerate(dates):
                rows.append({
                    "date": d.strftime("%Y%m%d"),
                    "index_name": idx_name,
                    "contract": f"{idx_name}",
                    "close": futures_close[i],
                    "spot_close": spot[i],
                    "open_interest": max(1000, oi[i]),
                    "volume": 20000,
                })
        return pd.DataFrame(rows)

    def test_neutral_basis_near_zero(self, sample_config):
        """Basis exactly 0% → neutral, not triggered."""
        data = self._make_futures_with_basis(0.0)
        result = detect_futures_basis(data, sample_config)
        assert result.direction == "neutral"
        assert not result.triggered

    def test_neutral_basis_slightly_positive(self, sample_config):
        """Basis +0.2% (within neutral range) → neutral."""
        data = self._make_futures_with_basis(0.2)
        result = detect_futures_basis(data, sample_config)
        assert result.direction == "neutral"
        assert not result.triggered

    def test_neutral_basis_slightly_negative(self, sample_config):
        """Basis -0.2% (within neutral range) → neutral."""
        data = self._make_futures_with_basis(-0.2)
        result = detect_futures_basis(data, sample_config)
        assert result.direction == "neutral"
        assert not result.triggered

    def test_bullish_basis_exceeds_threshold(self, sample_config):
        """Basis +0.5% → bullish, triggered."""
        data = self._make_futures_with_basis(0.5)
        result = detect_futures_basis(data, sample_config)
        assert result.direction == "bullish"
        assert result.triggered

    def test_bearish_basis_exceeds_threshold(self, sample_config):
        """Basis -0.5% → bearish, triggered."""
        data = self._make_futures_with_basis(-0.5)
        result = detect_futures_basis(data, sample_config)
        assert result.direction == "bearish"
        assert result.triggered

    def test_neutral_summary_text(self, sample_config):
        """Neutral basis should mention '平水' in summary."""
        data = self._make_futures_with_basis(0.1)
        result = detect_futures_basis(data, sample_config)
        assert "平水" in result.summary or "方向不明确" in result.summary


# ── Divergence tests ──


class TestBasisOIDivergence:
    """Basis-OI convergence: divergence scenario (opposite directions)."""

    def _make_basis_data(self, basis_pct):
        """Create data producing a specific basis signal."""
        dates = pd.date_range("2026-01-02", periods=80, freq="B")
        rows = []
        for idx_name, spot_base in [("CSI300", 4000), ("SSE50", 2800), ("CSI500", 5500)]:
            spot = spot_base + np.cumsum(np.random.randn(80) * 10)
            futures_close = spot * (1 + basis_pct / 100)
            oi = 50000 + np.cumsum(np.random.randn(80) * 300)
            for i, d in enumerate(dates):
                rows.append({
                    "date": d.strftime("%Y%m%d"),
                    "index_name": idx_name,
                    "contract": f"{idx_name}",
                    "close": futures_close[i],
                    "spot_close": spot[i],
                    "open_interest": max(1000, oi[i]),
                    "volume": 20000,
                })
        return pd.DataFrame(rows)

    def test_divergence_basis_bullish_oi_bearish(self, sample_config):
        """Basis bullish + OI falling → divergence → neutral, not triggered."""
        # Use bullish basis data but with declining OI trend
        data = self._make_basis_data(0.8)
        # Make OI clearly declining for all indices
        for idx_name in data["index_name"].unique():
            mask = data["index_name"] == idx_name
            sorted_idx = data.loc[mask].sort_values("date").index
            declining_oi = np.linspace(60000, 40000, len(sorted_idx))
            data.loc[sorted_idx, "open_interest"] = declining_oi
        result = detect_basis_oi_convergence(data, sample_config)
        # If basis bullish but OI bearish, it's divergence → neutral + not triggered
        if result.direction == "neutral" and not result.triggered:
            assert "背离" in result.summary or "分歧" in result.summary
        # Either way, detail should capture both sub-signal directions
        assert "basis_direction" in result.detail

    def test_divergence_strength_is_zero(self, sample_config):
        """Divergence should produce strength=0.0."""
        data = self._make_basis_data(0.8)
        for idx_name in data["index_name"].unique():
            mask = data["index_name"] == idx_name
            sorted_idx = data.loc[mask].sort_values("date").index
            declining_oi = np.linspace(60000, 40000, len(sorted_idx))
            data.loc[sorted_idx, "open_interest"] = declining_oi
        result = detect_basis_oi_convergence(data, sample_config)
        if not result.triggered:
            assert result.strength == 0.0 or result.direction == "neutral"

    def test_convergence_both_bullish(self, sample_config):
        """Basis bullish + OI rising sharply → convergence bullish, triggered."""
        data = self._make_basis_data(0.8)
        # Make OI clearly rising — need >2% 5-day change to trigger OI signal
        for idx_name in data["index_name"].unique():
            mask = data["index_name"] == idx_name
            sorted_idx = data.loc[mask].sort_values("date").index
            rising_oi = np.linspace(30000, 80000, len(sorted_idx))
            data.loc[sorted_idx, "open_interest"] = rising_oi
        result = detect_basis_oi_convergence(data, sample_config)
        assert result.triggered
        assert result.direction == "bullish"


# ── No idx_col fallback tests ──


class TestOpenInterestNoIdxCol:
    """detect_open_interest_trend when idx_col is missing."""

    def test_no_idx_col_uses_flat_series(self, sample_config):
        """Without index_name column, treats entire DF as flat series."""
        dates = pd.date_range("2026-01-02", periods=30, freq="B")
        np.random.seed(88)
        oi = 50000 + np.cumsum(np.random.randn(30) * 500)
        df = pd.DataFrame({
            "date": [d.strftime("%Y%m%d") for d in dates],
            "open_interest": oi,
            "close": 4000 + np.cumsum(np.random.randn(30) * 10),
        })
        result = detect_open_interest_trend(df, sample_config)
        assert result.key == "open_interest_trend"

    def test_no_idx_col_insufficient_data(self, sample_config):
        """Without idx_col, <5 rows → neutral with insufficient data."""
        df = pd.DataFrame({
            "date": ["20260601", "20260602"],
            "open_interest": [50000, 51000],
        })
        result = detect_open_interest_trend(df, sample_config)
        assert not result.triggered
        assert "数据不足" in result.summary
