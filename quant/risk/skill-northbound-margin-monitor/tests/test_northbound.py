"""Tests for northbound signal detectors."""

import numpy as np
import pandas as pd
import pytest

from core._types import apply_signal_decay, neutral_signal, SignalResult
from core.northbound import (
    _resolve_net_column,
    detect_flow_trend,
    detect_single_day_anomaly,
    detect_sector_preference,
    detect_holdings_change,
    detect_cumulative_trend,
    detect_market_flow_direction,
    detect_flow_direction_trend,
    run_all_detectors,
    get_triggered_signals,
    get_bullish_signals,
    get_bearish_signals,
    compute_composite_score,
    NORTHBOUND_REGISTRY,
)


def _make_summary(net_values: list[float]) -> pd.DataFrame:
    """Helper: make northbound summary with given net_buy_amount series."""
    dates = pd.date_range("2026-01-01", periods=len(net_values), freq="B")
    df = pd.DataFrame({
        "date": [d.strftime("%Y%m%d") for d in dates],
        "net_buy_amount": net_values,
    })
    df.attrs["source"] = "eastmoney"
    return df


def _make_summary_with_mv(mv_values: list[float]) -> pd.DataFrame:
    """Helper: make northbound summary with market_value (no net_buy)."""
    dates = pd.date_range("2026-01-01", periods=len(mv_values), freq="B")
    df = pd.DataFrame({
        "date": [d.strftime("%Y%m%d") for d in dates],
        "market_value": mv_values,
    })
    df.attrs["source"] = "eastmoney"
    return df


class TestFlowTrend:
    def test_consecutive_inflow_triggers(self, sample_config):
        # 5 consecutive days of net inflow
        values = [10.0] * 80 + [20, 30, 40, 50, 60]  # last 5 are inflow
        df = _make_summary(values)
        result = detect_flow_trend(df, sample_config)
        assert result.triggered
        assert result.direction == "bullish"
        assert result.strength > 0

    def test_consecutive_outflow_triggers(self, sample_config):
        values = [-10.0] * 80 + [-20, -30, -40, -50, -60]
        df = _make_summary(values)
        result = detect_flow_trend(df, sample_config)
        assert result.triggered
        assert result.direction == "bearish"
        assert result.strength < 0

    def test_below_threshold_no_trigger(self, sample_config):
        # Only 2 consecutive days, threshold is 3
        values = [0.0] * 80 + [10, 20]
        df = _make_summary(values)
        result = detect_flow_trend(df, sample_config)
        assert not result.triggered

    def test_mixed_direction_no_trigger(self, sample_config):
        values = [0.0] * 78 + [10, -5, 10, -5, 10]
        df = _make_summary(values)
        result = detect_flow_trend(df, sample_config)
        assert not result.triggered  # Last 2 alternate

    def test_zero_last_day(self, sample_config):
        values = [10.0] * 79 + [0.0]
        df = _make_summary(values)
        result = detect_flow_trend(df, sample_config)
        assert not result.triggered

    def test_empty_dataframe(self, sample_config):
        result = detect_flow_trend(pd.DataFrame(), sample_config)
        assert not result.triggered
        assert result.direction == "neutral"

    def test_single_row(self, sample_config):
        df = _make_summary([10.0])
        result = detect_flow_trend(df, sample_config)
        assert not result.triggered  # data insufficient

    def test_fallback_to_market_value(self, sample_config):
        # No net_buy column, must use market_value diff
        values = [20000] + [20000 + i * 10 for i in range(1, 90)]
        df = _make_summary_with_mv(values)
        result = detect_flow_trend(df, sample_config)
        # Last many days should all be positive diff
        assert result.triggered
        assert result.direction == "bullish"


class TestSingleDayAnomaly:
    def test_large_positive_zscore_triggers(self, sample_config):
        # Normal values for 60 days, then a massive spike
        base = np.random.RandomState(0).normal(10, 20, 80)
        base = list(base) + [200.0]  # huge spike
        df = _make_summary(base)
        result = detect_single_day_anomaly(df, sample_config)
        assert result.triggered
        assert result.direction == "bullish"

    def test_large_negative_zscore_triggers(self, sample_config):
        base = np.random.RandomState(0).normal(-10, 20, 80)
        base = list(base) + [-200.0]
        df = _make_summary(base)
        result = detect_single_day_anomaly(df, sample_config)
        assert result.triggered
        assert result.direction == "bearish"

    def test_normal_value_no_trigger(self, sample_config):
        base = np.random.RandomState(0).normal(10, 5, 81).tolist()
        df = _make_summary(base)
        result = detect_single_day_anomaly(df, sample_config)
        assert not result.triggered

    def test_insufficient_data(self, sample_config):
        base = [10.0] * 15  # only 15 rows
        df = _make_summary(base)
        result = detect_single_day_anomaly(df, sample_config)
        assert not result.triggered

    def test_zero_std(self, sample_config):
        # All values same → std=0
        base = [10.0] * 81
        df = _make_summary(base)
        result = detect_single_day_anomaly(df, sample_config)
        assert not result.triggered

    def test_all_nan_net_buy(self, sample_config):
        dates = pd.date_range("2026-01-01", periods=80, freq="B")
        df = pd.DataFrame({
            "date": [d.strftime("%Y%m%d") for d in dates],
            "net_buy_amount": [np.nan] * 80,
        })
        result = detect_single_day_anomaly(df, sample_config)
        assert not result.triggered


class TestSectorPreference:
    def test_with_industry_data(self, sample_config, sample_stock_info):
        net_vals = [10.0] * 80 + [20, 30, 40, 50, 60]
        df = _make_summary(net_vals)
        result = detect_sector_preference(df, sample_stock_info, sample_config)
        assert result.triggered
        assert "detail" in result.__dict__

    def test_no_stock_info(self, sample_config):
        net_vals = [10.0] * 85
        df = _make_summary(net_vals)
        result = detect_sector_preference(df, pd.DataFrame(), sample_config)
        assert not result.triggered

    def test_no_industry_column(self, sample_config):
        net_vals = [10.0] * 85
        df = _make_summary(net_vals)
        info = pd.DataFrame({"symbol": ["000001.SZ"], "name": ["测试"]})
        result = detect_sector_preference(df, info, sample_config)
        assert not result.triggered


class TestHoldingsChange:
    def test_increasing_market_value(self, sample_config):
        # Steady ~1.5% increase over 100 days to trigger 0.5% 5d threshold
        mv = [20000 + i * 50 for i in range(100)]  # ~25% increase total
        df = _make_summary_with_mv(mv)
        result = detect_holdings_change(df, pd.DataFrame(), sample_config)
        assert result.triggered
        assert result.direction == "bullish"

    def test_decreasing_market_value(self, sample_config):
        mv = [20000 - i * 50 for i in range(100)]  # steady ~25% decrease
        df = _make_summary_with_mv(mv)
        result = detect_holdings_change(df, pd.DataFrame(), sample_config)
        assert result.triggered
        assert result.direction == "bearish"

    def test_no_market_value(self, sample_config):
        dates = pd.date_range("2026-01-01", periods=30, freq="B")
        df = pd.DataFrame({
            "date": [d.strftime("%Y%m%d") for d in dates],
        })
        result = detect_holdings_change(df, pd.DataFrame(), sample_config)
        assert not result.triggered

    def test_insufficient_data(self, sample_config):
        df = _make_summary_with_mv([20000, 20001, 20002])
        result = detect_holdings_change(df, pd.DataFrame(), sample_config)
        assert not result.triggered


class TestCumulativeTrend:
    def test_bullish_accelerating(self, sample_config):
        # Steadily increasing net buy → cumulative rises
        net = [5.0] * 80 + [10.0, 15.0, 20.0, 25.0, 30.0]
        df = _make_summary(net)
        result = detect_cumulative_trend(df, sample_config)
        assert result.triggered
        assert result.direction == "bullish"

    def test_bearish_accelerating(self, sample_config):
        net = [-5.0] * 80 + [-10.0, -15.0, -20.0, -25.0, -30.0]
        df = _make_summary(net)
        result = detect_cumulative_trend(df, sample_config)
        assert result.triggered
        assert result.direction == "bearish"

    def test_insufficient_data(self, sample_config):
        df = _make_summary([10.0] * 30)
        result = detect_cumulative_trend(df, sample_config)
        assert not result.triggered

    def test_no_net_col_uses_mv(self, sample_config):
        mv = [20000 + i * 10 for i in range(90)]
        df = _make_summary_with_mv(mv)
        result = detect_cumulative_trend(df, sample_config)
        assert result.triggered


class TestMarketFlowDirection:
    def test_both_inflow(self, sample_config, sample_nb_flow):
        result = detect_market_flow_direction(sample_nb_flow, sample_config)
        assert result.triggered
        assert result.direction == "bullish"
        assert result.strength > 0

    def test_diverged(self, sample_config, sample_nb_flow_diverged):
        result = detect_market_flow_direction(sample_nb_flow_diverged, sample_config)
        assert not result.triggered
        assert result.direction == "neutral"

    def test_empty_dataframe(self, sample_config):
        result = detect_market_flow_direction(pd.DataFrame(), sample_config)
        assert not result.triggered


class TestFlowDirectionTrend:
    def test_consecutive_inflow_triggers(self, sample_config, sample_nb_flow_history):
        """10 days of bullish direction → should trigger."""
        result = detect_flow_direction_trend(sample_nb_flow_history, sample_config)
        assert result.triggered
        assert result.direction == "bullish"
        assert result.strength > 0
        assert result.key == "flow_direction_trend"

    def test_consecutive_outflow_triggers(self, sample_config, sample_nb_flow_history_bearish):
        """10 days of bearish direction → should trigger."""
        result = detect_flow_direction_trend(sample_nb_flow_history_bearish, sample_config)
        assert result.triggered
        assert result.direction == "bearish"
        assert result.strength < 0

    def test_below_threshold_no_trigger(self, sample_config, sample_nb_flow_history):
        """Only 2 consecutive days → threshold is 3 → no trigger."""
        # Take only the last 2 rows (both have direction_sum > 0)
        short = sample_nb_flow_history.tail(2).copy()
        result = detect_flow_direction_trend(short, sample_config)
        assert not result.triggered

    def test_insufficient_history(self, sample_config, sample_nb_flow_history_short):
        """2 days total, both same direction, but below threshold."""
        result = detect_flow_direction_trend(sample_nb_flow_history_short, sample_config)
        assert not result.triggered

    def test_empty_history(self, sample_config):
        result = detect_flow_direction_trend(pd.DataFrame(), sample_config)
        assert not result.triggered
        assert result.direction == "neutral"

    def test_none_history(self, sample_config):
        result = detect_flow_direction_trend(None, sample_config)
        assert not result.triggered
        assert result.direction == "neutral"

    def test_mixed_direction_no_trigger(self, sample_config):
        """Direction changes mid-series → consecutive count resets."""
        df = pd.DataFrame({
            "date": ["20260615", "20260616", "20260617", "20260618", "20260619"],
            "direction_sum": [1, 2, -1, 1, 1],
            "direction_days": [1, 2, 1, 1, 1],
        })
        result = detect_flow_direction_trend(df, sample_config)
        # Last 2 days are positive, consecutive=2 < threshold=3
        assert not result.triggered

    def test_strong_consensus_full_strength(self, sample_config):
        """Both markets agree every day → consensus_factor=1.0."""
        df = pd.DataFrame({
            "date": [f"2026061{i}" for i in range(5, 10)],
            "direction_sum": [2, 2, 2, 2, 2],
            "direction_days": [2, 2, 2, 2, 2],
        })
        result = detect_flow_direction_trend(df, sample_config)
        assert result.triggered
        assert result.detail["consensus"] == "strong"
        assert result.strength == 1.0  # 5/3=1.67 capped at 1.0 × 1.0

    def test_moderate_consensus_reduced_strength(self, sample_config):
        """One-market days → consensus_factor=0.7."""
        df = pd.DataFrame({
            "date": [f"2026061{i}" for i in range(5, 10)],
            "direction_sum": [1, 1, 1, 1, 1],
            "direction_days": [1, 1, 1, 1, 1],
        })
        result = detect_flow_direction_trend(df, sample_config)
        assert result.triggered
        assert result.detail["consensus"] == "moderate"
        assert result.strength == pytest.approx(0.7, abs=0.01)  # 1.0 × 0.7

    def test_zero_direction_returns_neutral(self, sample_config):
        """Last day direction_sum=0 → neutral."""
        df = pd.DataFrame({
            "date": ["20260615", "20260616", "20260617"],
            "direction_sum": [1, 0, 0],
            "direction_days": [1, 0, 0],
        })
        result = detect_flow_direction_trend(df, sample_config)
        assert not result.triggered
        assert result.direction == "neutral"

    def test_missing_direction_sum_column(self, sample_config):
        """No direction_sum column → neutral."""
        df = pd.DataFrame({
            "date": ["20260615", "20260616"],
            "some_other_col": [1, 2],
        })
        result = detect_flow_direction_trend(df, sample_config)
        assert not result.triggered


class TestRegistry:
    def test_all_7_detectors_registered(self):
        assert len(NORTHBOUND_REGISTRY) == 7
        expected = {
            "flow_trend", "single_day_anomaly", "sector_preference",
            "holdings_change", "cumulative_trend", "market_flow_direction",
            "flow_direction_trend",
        }
        assert set(NORTHBOUND_REGISTRY.keys()) == expected

    def test_all_have_func_weight_label(self):
        for key, entry in NORTHBOUND_REGISTRY.items():
            assert "func" in entry, f"{key} missing func"
            assert "weight" in entry, f"{key} missing weight"
            assert "label" in entry, f"{key} missing label"
            assert callable(entry["func"]), f"{key} func not callable"


class TestRunAllDetectors:
    def test_returns_7_results(self, sample_nb_summary, sample_nb_flow, sample_stock_info, sample_config):
        results = run_all_detectors(sample_nb_summary, sample_nb_flow, sample_stock_info, sample_config)
        assert len(results) == 7

    def test_active_detectors_filter(self, sample_nb_summary, sample_nb_flow, sample_stock_info, sample_config):
        results = run_all_detectors(
            sample_nb_summary, sample_nb_flow, sample_stock_info, sample_config,
            active_detectors={"flow_trend"},
        )
        assert len(results) == 1
        assert results[0].key == "flow_trend"

    def test_run_with_flow_history(self, sample_nb_summary, sample_nb_flow, sample_stock_info, sample_config, sample_nb_flow_history):
        results = run_all_detectors(
            sample_nb_summary, sample_nb_flow, sample_stock_info, sample_config,
            nb_flow_history=sample_nb_flow_history,
        )
        assert len(results) == 7
        flow_trend_results = [r for r in results if r.key == "flow_direction_trend"]
        assert len(flow_trend_results) == 1
        assert flow_trend_results[0].triggered

    def test_empty_data(self, sample_config):
        empty = pd.DataFrame()
        results = run_all_detectors(empty, empty, empty, sample_config)
        assert len(results) == 7
        for r in results:
            assert not r.triggered

    def test_detector_exception_returns_neutral(self, sample_nb_summary, sample_nb_flow, sample_stock_info, sample_config, monkeypatch):
        def _raise(*args, **kwargs):
            raise RuntimeError("simulated failure")
        monkeypatch.setattr("core.northbound.detect_flow_trend", _raise)
        results = run_all_detectors(
            sample_nb_summary, sample_nb_flow, sample_stock_info, sample_config,
            active_detectors={"flow_trend"},
        )
        assert len(results) == 1
        assert not results[0].triggered


class TestHelpers:
    def test_get_triggered_signals(self, sample_nb_summary, sample_nb_flow, sample_stock_info, sample_config):
        results = run_all_detectors(sample_nb_summary, sample_nb_flow, sample_stock_info, sample_config)
        triggered = get_triggered_signals(results)
        assert len(triggered) <= len(results)

    def test_get_bullish_signals(self, sample_nb_summary, sample_nb_flow, sample_stock_info, sample_config):
        results = run_all_detectors(sample_nb_summary, sample_nb_flow, sample_stock_info, sample_config)
        bullish = get_bullish_signals(results)
        for s in bullish:
            assert s.direction == "bullish"

    def test_get_bearish_signals(self, sample_nb_summary, sample_nb_flow, sample_stock_info, sample_config):
        results = run_all_detectors(sample_nb_summary, sample_nb_flow, sample_stock_info, sample_config)
        bearish = get_bearish_signals(results)
        for s in bearish:
            assert s.direction == "bearish"

    def test_composite_score_range(self, sample_nb_summary, sample_nb_flow, sample_stock_info, sample_config):
        results = run_all_detectors(sample_nb_summary, sample_nb_flow, sample_stock_info, sample_config)
        score = compute_composite_score(results)
        assert -1.0 <= score <= 1.0

    def test_signal_decay_fresh_signal(self):
        """Fresh signal (consecutive_days=1) should have no decay."""
        sig = SignalResult("test", "测试", True, 0.8, "bullish", "test", {"consecutive_days": 1})
        decayed = apply_signal_decay(sig, half_life_days=10)
        assert abs(decayed) > 0.7  # Near original

    def test_signal_decay_at_half_life(self):
        """At half_life_days, strength should be ~50%."""
        sig = SignalResult("test", "测试", True, 0.8, "bullish", "test", {"consecutive_days": 10})
        decayed = apply_signal_decay(sig, half_life_days=10)
        assert 0.35 < abs(decayed) < 0.45  # ~0.4 = 0.8 * 0.5

    def test_signal_decay_stale_signal(self):
        """Stale signal (3x half-life) should be heavily decayed."""
        sig = SignalResult("test", "测试", True, 0.8, "bullish", "test", {"consecutive_days": 30})
        decayed = apply_signal_decay(sig, half_life_days=10)
        assert abs(decayed) < 0.15  # ~0.1

    def test_signal_decay_not_triggered(self):
        """Non-triggered signal should not be affected."""
        sig = SignalResult("test", "测试", False, 0.0, "neutral", "test", {"consecutive_days": 100})
        decayed = apply_signal_decay(sig, half_life_days=10)
        assert decayed == 0.0

    def test_signal_decay_preserves_sign(self):
        """Decay should preserve the sign of the original strength."""
        sig = SignalResult("test", "测试", True, -0.6, "bearish", "test", {"consecutive_days": 10})
        decayed = apply_signal_decay(sig, half_life_days=10)
        assert decayed < 0

    def test_neutral_signal_direct(self):
        """neutral_signal() should return SignalResult with neutral defaults."""
        result = neutral_signal("my_key", "我的标签", "没有数据")
        assert isinstance(result, SignalResult)
        assert result.key == "my_key"
        assert result.label == "我的标签"
        assert not result.triggered
        assert result.strength == 0.0
        assert result.direction == "neutral"
        assert result.summary == "没有数据"


# ── _resolve_net_column tests ──


class TestResolveNetColumn:
    """Direct tests for the 3-tier net column resolution fallback chain."""

    def test_direct_net_buy_amount(self):
        """Tier 1: net_buy_amount column with valid recent data."""
        df = pd.DataFrame({
            "date": [f"20260{i:03d}" for i in range(1, 31)],
            "net_buy_amount": list(range(30)),
        })
        col, out_df, source = _resolve_net_column(df)
        assert col == "net_buy_amount"
        assert source == "direct"

    def test_direct_chinese_column(self):
        """Tier 1: Chinese column name 资金净流入 with valid data."""
        df = pd.DataFrame({
            "date": [f"20260{i:03d}" for i in range(1, 31)],
            "资金净流入": list(range(30)),
        })
        col, out_df, source = _resolve_net_column(df)
        assert col == "资金净流入"
        assert source == "direct"

    def test_direct_skips_column_with_nan_recent(self):
        """Tier 1: column exists but recent values are NaN → skip to next tier."""
        data = list(range(30))
        # Last 10 values are NaN → quality check fails
        data[-10:] = [np.nan] * 10
        df = pd.DataFrame({
            "date": [f"20260{i:03d}" for i in range(1, 31)],
            "net_buy_amount": data,
            "market_value": list(range(100, 130)),
        })
        col, out_df, source = _resolve_net_column(df)
        # Should fall back to market_value diff
        assert col == "_net"
        assert source == "market_value"

    def test_market_value_fallback(self):
        """Tier 2: no net column → use market_value diff."""
        df = pd.DataFrame({
            "date": [f"20260{i:03d}" for i in range(1, 31)],
            "market_value": list(range(100, 130)),
        })
        col, out_df, source = _resolve_net_column(df)
        assert col == "_net"
        assert source == "market_value"
        assert "_net" in out_df.columns

    def test_market_value_chinese_column(self):
        """Tier 2: Chinese market value column 持股市值."""
        df = pd.DataFrame({
            "date": [f"20260{i:03d}" for i in range(1, 31)],
            "持股市值": list(range(100, 130)),
        })
        col, out_df, source = _resolve_net_column(df)
        assert col == "_net"
        assert source == "market_value"

    def test_csi300_fallback(self):
        """Tier 3: no net or market_value → use CSI300 diff."""
        df = pd.DataFrame({
            "date": [f"20260{i:03d}" for i in range(1, 31)],
            "CSI300": list(range(3500, 3530)),
        })
        col, out_df, source = _resolve_net_column(df)
        assert col == "_net"
        assert source == "csi300"

    def test_csi300_chinese_column(self):
        """Tier 3: Chinese CSI300 column 沪深300."""
        df = pd.DataFrame({
            "date": [f"20260{i:03d}" for i in range(1, 31)],
            "沪深300": list(range(3500, 3530)),
        })
        col, out_df, source = _resolve_net_column(df)
        assert col == "_net"
        assert source == "csi300"

    def test_all_tiers_fail(self):
        """No usable columns → returns None, None."""
        df = pd.DataFrame({
            "date": [f"20260{i:03d}" for i in range(1, 31)],
            "some_other_column": list(range(30)),
        })
        col, out_df, source = _resolve_net_column(df)
        assert col is None
        assert source is None

    def test_market_value_recent_all_zero(self):
        """Market value column exists but all recent values are ≤0 → skip to CSI300 or None."""
        data = [0] * 30
        df = pd.DataFrame({
            "date": [f"20260{i:03d}" for i in range(1, 31)],
            "market_value": data,
        })
        col, out_df, source = _resolve_net_column(df)
        # Should fail all tiers since no CSI300 column either
        assert col is None
        assert source is None

    def test_net_buy_all_nan(self):
        """net_buy_amount exists but ALL values are NaN."""
        df = pd.DataFrame({
            "date": [f"20260{i:03d}" for i in range(1, 31)],
            "net_buy_amount": [np.nan] * 30,
        })
        col, out_df, source = _resolve_net_column(df)
        # No usable data → falls through all tiers
        assert col is None
        assert source is None

    def test_sorts_by_date_for_diff(self):
        """Market value fallback should sort df by date before diff."""
        # Create data in reverse date order
        df = pd.DataFrame({
            "date": [f"20260{30 - i:03d}" for i in range(30)],
            "market_value": list(range(100, 130)),
        })
        col, out_df, source = _resolve_net_column(df)
        assert source == "market_value"
        # After sort, first row should be the earliest date
        assert out_df["date"].iloc[0] == "20260001"

    def test_csi300_recent_zero_quality_fails(self):
        """CSI300 with all-zero recent values should fail quality check."""
        data = [0] * 30
        df = pd.DataFrame({
            "date": [f"20260{i:03d}" for i in range(1, 31)],
            "csi300": data,
        })
        col, out_df, source = _resolve_net_column(df)
        assert col is None
        assert source is None

    def test_short_data_still_works(self):
        """Less than recent_check_days total rows but enough valid values."""
        df = pd.DataFrame({
            "date": ["20260601", "20260602", "20260603", "20260604", "20260605"],
            "net_buy_amount": [1.0, 2.0, 3.0, 4.0, 5.0],
        })
        col, out_df, source = _resolve_net_column(df)
        assert col == "net_buy_amount"
        assert source == "direct"
