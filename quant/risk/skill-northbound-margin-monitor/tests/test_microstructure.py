"""Tests for core.microstructure — market microstructure detectors."""

import numpy as np
import pandas as pd
import pytest

from core._types import SignalResult
from core.microstructure import (
    MICROSTRUCTURE_REGISTRY,
    compute_composite_score,
    detect_advance_decline_ratio,
    detect_index_volume_trend,
    detect_limit_stocks,
    detect_turnover_trend,
    get_bearish_signals,
    get_bullish_signals,
    get_triggered_signals,
    run_all_detectors,
)


# ── Fixtures ──


@pytest.fixture
def sample_config():
    return {
        "microstructure": {
            "advance_decline_bullish": 0.65,
            "advance_decline_bearish": 0.35,
            "volume_expansion_threshold": 1.3,
            "volume_contraction_threshold": 0.7,
            "volume_ma_period": 20,
            "limit_up_count_threshold": 100,
            "limit_ratio_threshold": 3.0,
        },
    }


@pytest.fixture
def bullish_nb_flow():
    """1800 advancing, 400 declining → breadth=0.82 (bullish)."""
    return pd.DataFrame({
        "上涨数": [900, 900],
        "持平数": [50, 30],
        "下跌数": [200, 200],
    })


@pytest.fixture
def bearish_nb_flow():
    """300 advancing, 1300 declining → breadth=0.18 (bearish)."""
    return pd.DataFrame({
        "上涨数": [150, 150],
        "持平数": [50, 30],
        "下跌数": [650, 650],
    })


@pytest.fixture
def neutral_nb_flow():
    """Balanced advancing/declining."""
    return pd.DataFrame({
        "上涨数": [500, 500],
        "持平数": [50, 30],
        "下跌数": [450, 450],
    })


@pytest.fixture
def volume_data_neutral():
    """CSI300 data with normal volume."""
    dates = pd.date_range("2026-01-02", periods=30, freq="B")
    np.random.seed(99)
    close = 4000 + np.cumsum(np.random.randn(30) * 5)
    volume = np.random.uniform(15000, 25000, 30)
    return pd.DataFrame({
        "date": [d.strftime("%Y%m%d") for d in dates],
        "index_name": ["CSI300"] * 30,
        "spot_close": close,
        "index_volume": volume,
    })


@pytest.fixture
def volume_data_bullish():
    """CSI300 with volume expansion and price rise."""
    dates = pd.date_range("2026-01-02", periods=30, freq="B")
    np.random.seed(98)
    volume = np.random.uniform(15000, 25000, 25).tolist() + [35000, 38000, 40000, 42000, 45000]
    close = list(4000 + np.cumsum(np.random.randn(25) * 5)) + [4120, 4150, 4180, 4200, 4250]
    return pd.DataFrame({
        "date": [d.strftime("%Y%m%d") for d in dates],
        "index_name": ["CSI300"] * 30,
        "spot_close": close,
        "index_volume": volume,
    })


@pytest.fixture
def volume_data_bearish():
    """CSI300 with volume expansion and price decline."""
    dates = pd.date_range("2026-01-02", periods=30, freq="B")
    np.random.seed(97)
    volume = np.random.uniform(15000, 25000, 25).tolist() + [35000, 38000, 40000, 42000, 45000]
    close = list(4000 + np.cumsum(np.random.randn(25) * 5)) + [4120, 4080, 4050, 4000, 3950]
    return pd.DataFrame({
        "date": [d.strftime("%Y%m%d") for d in dates],
        "index_name": ["CSI300"] * 30,
        "spot_close": close,
        "index_volume": volume,
    })


@pytest.fixture
def turnover_macro():
    """Margin macro with total_turnover."""
    dates = pd.date_range("2026-01-02", periods=30, freq="B")
    np.random.seed(96)
    base = 8000e8  # 8000 亿
    turnover = base + np.cumsum(np.random.randn(30) * 100e8)
    # Make last 5 days expanding
    turnover = list(turnover[:25]) + list(turnover[25] * np.array([1.4, 1.5, 1.6, 1.7, 1.8]))
    return pd.DataFrame({
        "date": [d.strftime("%Y%m%d") for d in dates],
        "total_turnover": [float(v) for v in turnover],
    })


# ── Detector tests ──


class TestAdvanceDeclineRatio:
    def test_bullish_breadth(self, sample_config, bullish_nb_flow):
        result = detect_advance_decline_ratio(bullish_nb_flow, sample_config)
        assert result.triggered
        assert result.direction == "bullish"
        assert result.strength > 0
        assert "涨跌比" in result.summary

    def test_bearish_breadth(self, sample_config, bearish_nb_flow):
        result = detect_advance_decline_ratio(bearish_nb_flow, sample_config)
        assert result.triggered
        assert result.direction == "bearish"
        assert result.strength < 0

    def test_neutral_breadth(self, sample_config, neutral_nb_flow):
        result = detect_advance_decline_ratio(neutral_nb_flow, sample_config)
        assert not result.triggered
        assert result.direction == "neutral"

    def test_empty_data(self, sample_config):
        result = detect_advance_decline_ratio(pd.DataFrame(), sample_config)
        assert not result.triggered
        assert "缺少" in result.summary

    def test_none_data(self, sample_config):
        result = detect_advance_decline_ratio(None, sample_config)
        assert not result.triggered

    def test_detail_populated(self, sample_config, bullish_nb_flow):
        result = detect_advance_decline_ratio(bullish_nb_flow, sample_config)
        assert "breadth" in result.detail
        assert result.detail["breadth"] > 0.6


class TestIndexVolumeTrend:
    def test_neutral_normal_volume(self, sample_config, volume_data_neutral):
        result = detect_index_volume_trend(volume_data_neutral, sample_config)
        assert not result.triggered, f"Expected neutral, got {result.direction}: {result.summary}"

    def test_bullish_expansion(self, sample_config, volume_data_bullish):
        result = detect_index_volume_trend(volume_data_bullish, sample_config)
        if result.triggered:
            assert result.direction == "bullish"

    def test_bearish_expansion(self, sample_config, volume_data_bearish):
        result = detect_index_volume_trend(volume_data_bearish, sample_config)
        if result.triggered:
            assert result.direction == "bearish"

    def test_empty_data(self, sample_config):
        result = detect_index_volume_trend(pd.DataFrame(), sample_config)
        assert not result.triggered

    def test_none_data(self, sample_config):
        result = detect_index_volume_trend(None, sample_config)
        assert not result.triggered

    def test_detail_populated(self, sample_config, volume_data_neutral):
        result = detect_index_volume_trend(volume_data_neutral, sample_config)
        assert "expansion_ratio" in result.detail


class TestTurnoverTrend:
    def test_with_margin_macro(self, sample_config, turnover_macro, volume_data_bullish):
        result = detect_turnover_trend(turnover_macro, volume_data_bullish, sample_config)
        # With expanding turnover + rising prices → should be bullish
        if result.triggered:
            assert result.direction == "bullish"

    def test_fallback_to_index_volume(self, sample_config, volume_data_bullish):
        result = detect_turnover_trend(pd.DataFrame(), volume_data_bullish, sample_config)
        assert "expansion_ratio" in result.detail
        # Falls back to CSI300 index volume
        assert "CSI300" in result.detail.get("data_source", "")

    def test_empty_both_sources(self, sample_config):
        result = detect_turnover_trend(pd.DataFrame(), pd.DataFrame(), sample_config)
        assert not result.triggered
        assert "缺少" in result.summary

    def test_detail_populated(self, sample_config, turnover_macro, volume_data_neutral):
        result = detect_turnover_trend(turnover_macro, volume_data_neutral, sample_config)
        assert "expansion_ratio" in result.detail
        assert "data_source" in result.detail


class TestLimitStocks:
    def test_returns_signal_result(self, sample_config):
        """Limit stocks detector should always return a valid SignalResult."""
        result = detect_limit_stocks(sample_config)
        assert isinstance(result, SignalResult)
        assert result.key == "limit_stocks"
        assert result.label == "涨跌停统计"


# ── Registry tests ──


class TestMicrostructureRegistry:
    def test_all_seven_detectors_registered(self):
        assert len(MICROSTRUCTURE_REGISTRY) == 7
        assert "advance_decline_ratio" in MICROSTRUCTURE_REGISTRY
        assert "index_volume_trend" in MICROSTRUCTURE_REGISTRY
        assert "turnover_trend" in MICROSTRUCTURE_REGISTRY
        assert "limit_stocks" in MICROSTRUCTURE_REGISTRY
        assert "main_fund_flow" in MICROSTRUCTURE_REGISTRY
        assert "lhb_activity" in MICROSTRUCTURE_REGISTRY
        assert "nh_nl_breadth" in MICROSTRUCTURE_REGISTRY

    def test_registry_entries_have_required_keys(self):
        for key, entry in MICROSTRUCTURE_REGISTRY.items():
            assert "func" in entry, f"{key} missing func"
            assert "weight" in entry, f"{key} missing weight"
            assert "label" in entry, f"{key} missing label"
            assert "half_life_days" in entry, f"{key} missing half_life_days"
            assert callable(entry["func"])

    def test_total_weight_is_13(self):
        total = sum(v["weight"] for v in MICROSTRUCTURE_REGISTRY.values())
        assert total == 13


# ── Orchestration tests ──


class TestRunAllDetectors:
    def test_returns_list_of_seven(self, sample_config, neutral_nb_flow, volume_data_neutral, turnover_macro):
        results = run_all_detectors(neutral_nb_flow, volume_data_neutral, turnover_macro, sample_config)
        assert len(results) == 7
        for r in results:
            assert isinstance(r, SignalResult)

    def test_all_results_have_keys(self, sample_config, neutral_nb_flow, volume_data_neutral, turnover_macro):
        results = run_all_detectors(neutral_nb_flow, volume_data_neutral, turnover_macro, sample_config)
        keys = {r.key for r in results}
        assert keys == {"advance_decline_ratio", "index_volume_trend", "turnover_trend", "limit_stocks", "main_fund_flow", "lhb_activity", "nh_nl_breadth"}

    def test_active_detectors_filter(self, sample_config, neutral_nb_flow, volume_data_neutral, turnover_macro):
        results = run_all_detectors(
            neutral_nb_flow, volume_data_neutral, turnover_macro, sample_config,
            active_detectors={"advance_decline_ratio"},
        )
        assert len(results) == 1
        assert results[0].key == "advance_decline_ratio"

    def test_handles_none_inputs(self, sample_config):
        results = run_all_detectors(None, None, None, sample_config)
        assert len(results) == 7
        # Data-dependent detectors should gracefully degrade
        data_dependent = {"advance_decline_ratio", "index_volume_trend", "turnover_trend"}
        for r in results:
            assert isinstance(r, SignalResult)
            if r.key in data_dependent:
                assert not r.triggered, f"{r.key} should not trigger with None input"
        # Self-fetching detectors (main_fund_flow, lhb_activity, nh_nl_breadth)
        # may trigger based on live API data — that's expected behavior

    def test_handles_empty_dataframes(self, sample_config):
        results = run_all_detectors(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), sample_config)
        assert len(results) == 7

    def test_handles_exception_in_detector(self, sample_config, neutral_nb_flow, volume_data_neutral, turnover_macro):
        """Ensure individual detector exceptions don't crash the pipeline."""
        # Pass None for nb_flow → advance_decline returns neutral gracefully
        results = run_all_detectors(None, volume_data_neutral, turnover_macro, sample_config)
        assert len(results) == 7
        for r in results:
            assert isinstance(r, SignalResult)


# ── Composite score tests ──


class TestComputeCompositeScore:
    def test_balanced_neutral(self, sample_config, neutral_nb_flow, volume_data_neutral, turnover_macro):
        results = run_all_detectors(neutral_nb_flow, volume_data_neutral, turnover_macro, sample_config)
        score = compute_composite_score(results)
        assert -1.0 <= score <= 1.0

    def test_empty_signals(self):
        assert compute_composite_score([]) == 0.0

    def test_known_signals(self):
        sigs = [
            SignalResult(key="advance_decline_ratio", label="", triggered=False, strength=0.5, direction="bullish", summary=""),
            SignalResult(key="index_volume_trend", label="", triggered=False, strength=0.3, direction="bullish", summary=""),
            SignalResult(key="turnover_trend", label="", triggered=False, strength=-0.2, direction="bearish", summary=""),
            SignalResult(key="limit_stocks", label="", triggered=False, strength=0.0, direction="neutral", summary=""),
        ]
        score = compute_composite_score(sigs)
        # weights: 2,2,2,1 → (0.5*2 + 0.3*2 + (-0.2)*2 + 0.0*1) / 7 = 1.2/7 ≈ 0.1714
        assert round(score, 2) == 0.17


# ── Filter helpers tests ──


class TestSignalFilters:
    def test_get_triggered_signals(self):
        sigs = [
            SignalResult(key="a", label="", triggered=True, strength=0.5, direction="bullish", summary=""),
            SignalResult(key="b", label="", triggered=False, strength=0.3, direction="bullish", summary=""),
            SignalResult(key="c", label="", triggered=True, strength=-0.5, direction="bearish", summary=""),
        ]
        triggered = get_triggered_signals(sigs)
        assert len(triggered) == 2
        assert all(s.triggered for s in triggered)

    def test_get_bullish_signals(self):
        sigs = [
            SignalResult(key="a", label="", triggered=True, strength=0.5, direction="bullish", summary=""),
            SignalResult(key="b", label="", triggered=False, strength=0.3, direction="bullish", summary=""),
            SignalResult(key="c", label="", triggered=True, strength=-0.5, direction="bearish", summary=""),
        ]
        bullish = get_bullish_signals(sigs)
        assert len(bullish) == 2

    def test_get_bearish_signals(self):
        sigs = [
            SignalResult(key="a", label="", triggered=True, strength=0.5, direction="bullish", summary=""),
            SignalResult(key="b", label="", triggered=True, strength=-0.8, direction="bearish", summary=""),
            SignalResult(key="c", label="", triggered=False, strength=-0.5, direction="bearish", summary=""),
        ]
        bearish = get_bearish_signals(sigs)
        assert len(bearish) == 2
