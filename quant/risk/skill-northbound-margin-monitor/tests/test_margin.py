"""Tests for margin signal detectors."""

import numpy as np
import pandas as pd
import pytest

from core.margin import (
    detect_margin_balance_trend,
    detect_margin_buy_ratio,
    detect_short_trend,
    detect_margin_heavy_stocks,
    detect_margin_short_ratio,
    detect_margin_type_distribution,
    run_all_detectors,
    get_triggered_signals,
    get_bullish_signals,
    get_bearish_signals,
    compute_composite_score,
    MARGIN_REGISTRY,
)


class TestMarginBalanceTrend:
    def test_rising_balance(self, sample_config, sample_margin_macro):
        result = detect_margin_balance_trend(sample_margin_macro, sample_config)
        # Should return a valid result (may or may not trigger depending on random data)
        assert result is not None
        assert hasattr(result, "triggered")
        assert hasattr(result, "direction")

    def test_empty_data(self, sample_config):
        result = detect_margin_balance_trend(pd.DataFrame(), sample_config)
        assert not result.triggered

    def test_no_balance_column(self, sample_config):
        df = pd.DataFrame({"date": ["20260630"], "other": [100]})
        result = detect_margin_balance_trend(df, sample_config)
        assert not result.triggered

    def test_short_history(self, sample_config):
        # Only 10 days of data, need 20 for MA20
        dates = pd.date_range("2026-06-20", periods=10, freq="B")
        df = pd.DataFrame({
            "date": [d.strftime("%Y%m%d") for d in dates],
            "market": ["sh", "sz"] * 5,
            "margin_balance": np.random.uniform(1000, 2000, 10),
        })
        result = detect_margin_balance_trend(df, sample_config)
        assert not result.triggered

    def test_overheat_detection(self, sample_config):
        # Create data where current balance is >10% above MA20
        dates = pd.date_range("2026-01-01", periods=60, freq="B")
        base = [1000] * 40 + [1000 + i * 8 for i in range(20)]  # rising
        rows = []
        for i, d in enumerate(dates):
            rows.append({
                "date": d.strftime("%Y%m%d"),
                "market": "sh",
                "margin_balance": base[i],
            })
        df = pd.DataFrame(rows)
        result = detect_margin_balance_trend(df, sample_config)
        assert result.triggered
        # Should detect heat level
        assert "detail" in result.__dict__


class TestMarginBuyRatio:
    def test_with_macro_data(self, sample_config, sample_margin_macro):
        result = detect_margin_buy_ratio(pd.DataFrame(), sample_margin_macro, sample_config)
        assert result is not None
        assert "detail" in result.__dict__

    def test_no_data(self, sample_config):
        result = detect_margin_buy_ratio(pd.DataFrame(), pd.DataFrame(), sample_config)
        assert not result.triggered

    def test_empty_dataframes(self, sample_config):
        result = detect_margin_buy_ratio(pd.DataFrame(), pd.DataFrame(), sample_config)
        assert not result.triggered

    def test_with_turnover_data(self, sample_config):
        df = pd.DataFrame({
            "date": ["20260630"],
            "market": ["sh"],
            "buy_on_margin_value": [500e8],
            "total_turnover": [5000e8],
        })
        result = detect_margin_buy_ratio(pd.DataFrame(), df, sample_config)
        assert result.triggered  # 10% ratio = hot
        assert result.direction == "bullish"

    def test_dangerous_ratio(self, sample_config):
        df = pd.DataFrame({
            "date": ["20260630"],
            "market": ["sh"],
            "buy_on_margin_value": [900e8],
            "total_turnover": [5000e8],
        })
        result = detect_margin_buy_ratio(pd.DataFrame(), df, sample_config)
        assert result.triggered
        assert result.direction == "bearish"  # 18% > 15% danger


class TestShortTrend:
    def test_rising_short_balance(self, sample_config, sample_margin_macro):
        result = detect_short_trend(sample_margin_macro, sample_config)
        assert result is not None

    def test_empty_data(self, sample_config):
        result = detect_short_trend(pd.DataFrame(), sample_config)
        assert not result.triggered

    def test_no_short_column(self, sample_config):
        df = pd.DataFrame({
            "date": ["20260630"] * 10,
            "market": ["sh"] * 10,
            "other": list(range(10)),
        })
        result = detect_short_trend(df, sample_config)
        assert not result.triggered

    def test_rapid_short_increase(self, sample_config):
        dates = pd.date_range("2026-01-01", periods=30, freq="B")
        short_vals = [100] * 20 + [100 + i * 10 for i in range(10)]  # 100% increase
        rows = []
        for i, d in enumerate(dates):
            rows.append({
                "date": d.strftime("%Y%m%d"),
                "market": "sh",
                "short_balance": short_vals[i],
            })
        df = pd.DataFrame(rows)
        result = detect_short_trend(df, sample_config)
        assert result.triggered
        assert result.direction == "bearish"

    def test_rapid_short_decrease(self, sample_config):
        dates = pd.date_range("2026-01-01", periods=30, freq="B")
        short_vals = [200] * 20 + [200 - i * 10 for i in range(10)]  # declining
        rows = []
        for i, d in enumerate(dates):
            rows.append({
                "date": d.strftime("%Y%m%d"),
                "market": "sh",
                "short_balance": short_vals[i],
            })
        df = pd.DataFrame(rows)
        result = detect_short_trend(df, sample_config)
        assert result.triggered
        assert result.direction == "bullish"


class TestMarginHeavyStocks:
    def test_with_detail(self, sample_config, sample_margin_detail, sample_stock_info):
        result = detect_margin_heavy_stocks(sample_margin_detail, sample_stock_info, sample_config)
        assert result.triggered  # Always triggered (informational)
        assert "detail" in result.__dict__

    def test_empty_data(self, sample_config):
        result = detect_margin_heavy_stocks(pd.DataFrame(), pd.DataFrame(), sample_config)
        assert not result.triggered

    def test_no_balance_column(self, sample_config):
        df = pd.DataFrame({"symbol": ["000001.SZ"], "other": [100]})
        result = detect_margin_heavy_stocks(df, pd.DataFrame(), sample_config)
        assert not result.triggered

    def test_high_concentration(self, sample_config):
        # One stock dominates
        symbols = [f"{i:06d}.SZ" for i in range(1, 101)]
        balances = [1000e8] + [1e8] * 99  # first stock = 99% of total
        df = pd.DataFrame({
            "symbol": symbols,
            "margin_balance": balances,
            "date": "20260630",
        })
        result = detect_margin_heavy_stocks(df, pd.DataFrame(), sample_config)
        assert result.triggered
        assert result.direction == "bearish"  # High concentration


class TestMarginShortRatio:
    def test_with_macro(self, sample_config, sample_margin_macro):
        result = detect_margin_short_ratio(sample_margin_macro, sample_config)
        assert result is not None

    def test_empty_data(self, sample_config):
        result = detect_margin_short_ratio(pd.DataFrame(), sample_config)
        assert not result.triggered

    def test_missing_short_column(self, sample_config):
        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=30, freq="B").strftime("%Y%m%d"),
            "margin_balance": range(1000, 1030),
        })
        result = detect_margin_short_ratio(df, sample_config)
        assert not result.triggered

    def test_zero_short_balance(self, sample_config):
        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=30, freq="B").strftime("%Y%m%d"),
            "margin_balance": range(1000, 1030),
            "short_balance": [0] * 30,
        })
        result = detect_margin_short_ratio(df, sample_config)
        assert not result.triggered

    def test_rising_ratio(self, sample_config):
        dates = pd.date_range("2026-01-01", periods=30, freq="B")
        rows = []
        for i, d in enumerate(dates):
            rows.append({
                "date": d.strftime("%Y%m%d"),
                "margin_balance": 1000 + i * 10,
                "short_balance": 100 - i * 2,  # declining short → ratio rising
            })
        df = pd.DataFrame(rows)
        result = detect_margin_short_ratio(df, sample_config)
        assert result.triggered
        assert result.direction == "bullish"


class TestMarginTypeDistribution:
    def test_with_detail(self, sample_config, sample_margin_detail):
        result = detect_margin_type_distribution(sample_margin_detail, sample_config)
        assert result.triggered
        assert "detail" in result.__dict__

    def test_empty_data(self, sample_config):
        result = detect_margin_type_distribution(pd.DataFrame(), sample_config)
        assert not result.triggered

    def test_no_type_column(self, sample_config):
        df = pd.DataFrame({"symbol": ["000001.SZ"], "margin_balance": [100]})
        result = detect_margin_type_distribution(df, sample_config)
        assert not result.triggered

    def test_single_type(self, sample_config):
        df = pd.DataFrame({
            "symbol": [f"{i:06d}.SZ" for i in range(1, 51)],
            "margin_type": ["现金"] * 50,
        })
        result = detect_margin_type_distribution(df, sample_config)
        assert not result.triggered  # single type


class TestRegistry:
    def test_all_7_detectors_registered(self):
        assert len(MARGIN_REGISTRY) == 7
        expected = {
            "margin_balance_trend", "margin_buy_ratio", "short_trend",
            "margin_heavy_stocks", "margin_short_ratio", "margin_type_distribution",
            "margin_extreme_regime",
        }
        assert set(MARGIN_REGISTRY.keys()) == expected

    def test_all_have_func_weight_label(self):
        for key, entry in MARGIN_REGISTRY.items():
            assert "func" in entry, f"{key} missing func"
            assert "weight" in entry, f"{key} missing weight"
            assert "label" in entry, f"{key} missing label"


class TestRunAllDetectors:
    def test_returns_7_results(self, sample_margin_detail, sample_margin_macro, sample_stock_info, sample_config):
        results = run_all_detectors(sample_margin_detail, sample_margin_macro, sample_stock_info, sample_config)
        assert len(results) == 7

    def test_empty_data(self, sample_config):
        empty = pd.DataFrame()
        results = run_all_detectors(empty, empty, empty, sample_config)
        assert len(results) == 7
        for r in results:
            assert not r.triggered

    def test_active_detectors_filter(self, sample_margin_detail, sample_margin_macro, sample_stock_info, sample_config):
        results = run_all_detectors(
            sample_margin_detail, sample_margin_macro, sample_stock_info, sample_config,
            active_detectors={"margin_balance_trend"},
        )
        assert len(results) == 1
        assert results[0].key == "margin_balance_trend"

    def test_detector_exception_returns_neutral(self, sample_margin_detail, sample_margin_macro, sample_stock_info, sample_config, monkeypatch):
        def _raise(*args, **kwargs):
            raise RuntimeError("simulated failure")
        monkeypatch.setattr("core.margin.detect_margin_balance_trend", _raise)
        results = run_all_detectors(
            sample_margin_detail, sample_margin_macro, sample_stock_info, sample_config,
            active_detectors={"margin_balance_trend"},
        )
        assert len(results) == 1
        assert not results[0].triggered


class TestHelpers:
    def test_composite_score_range(self, sample_margin_detail, sample_margin_macro, sample_stock_info, sample_config):
        results = run_all_detectors(sample_margin_detail, sample_margin_macro, sample_stock_info, sample_config)
        score = compute_composite_score(results)
        assert -1.0 <= score <= 1.0

    def test_get_triggered_and_bullish_bearish(self, sample_margin_detail, sample_margin_macro, sample_stock_info, sample_config):
        results = run_all_detectors(sample_margin_detail, sample_margin_macro, sample_stock_info, sample_config)
        triggered = get_triggered_signals(results)
        bullish = get_bullish_signals(results)
        bearish = get_bearish_signals(results)
        assert len(triggered) <= len(results)
        for s in bullish:
            assert s.direction == "bullish"
        for s in bearish:
            assert s.direction == "bearish"


# ── Estimation bucket tests (no turnover data) ──


class TestMarginBuyRatioEstimation:
    """detect_margin_buy_ratio when total_turnover is unavailable."""

    def test_estimation_bucket_dangerous(self, sample_config):
        """Buy amount > 1500亿 → estimated ratio 18% → danger trigger."""
        macro = pd.DataFrame({
            "date": ["20260630"] * 2,
            "market": ["sh", "sz"],
            "buy_on_margin_value": [1000e8, 800e8],  # sum > 1500亿
        })
        result = detect_margin_buy_ratio(pd.DataFrame(), macro, sample_config)
        assert result.triggered
        assert result.direction == "bearish"
        assert "估算买入比" in result.summary
        assert result.detail.get("note", "").startswith("总成交额不可用")

    def test_estimation_bucket_hot(self, sample_config):
        """Buy amount > 1000亿 < 1500亿 → estimated ratio 12% → hot trigger."""
        macro = pd.DataFrame({
            "date": ["20260630"] * 2,
            "market": ["sh", "sz"],
            "buy_on_margin_value": [600e8, 500e8],  # 1100亿 total → 12%
        })
        result = detect_margin_buy_ratio(pd.DataFrame(), macro, sample_config)
        assert result.triggered
        assert result.direction == "bullish"

    def test_estimation_bucket_neutral(self, sample_config):
        """Buy amount < 200亿 → estimated ratio 2% → neutral."""
        macro = pd.DataFrame({
            "date": ["20260630"],
            "market": ["sh"],
            "buy_on_margin_value": [100e8],
        })
        result = detect_margin_buy_ratio(pd.DataFrame(), macro, sample_config)
        assert not result.triggered
        assert result.direction == "neutral"

    def test_estimation_bucket_high_threshold(self, sample_config):
        """Buy amount > 1000亿 → estimated ratio 12% → bullish (hot)."""
        macro = pd.DataFrame({
            "date": ["20260630"] * 2,
            "market": ["sh", "sz"],
            "buy_on_margin_value": [600e8, 600e8],  # 1200亿
        })
        result = detect_margin_buy_ratio(pd.DataFrame(), macro, sample_config)
        assert result.triggered
        assert result.direction == "bullish"

    def test_estimation_with_custom_buckets(self):
        """Custom estimation buckets from config."""
        config = {
            "margin": {
                "buy_ratio_hot": 0.10,
                "buy_ratio_dangerous": 0.15,
                "buy_ratio_estimate_buckets": [
                    [300, 0.20],  # Lower threshold for testing
                ],
            },
        }
        macro = pd.DataFrame({
            "date": ["20260630"],
            "market": ["sh"],
            "buy_on_margin_value": [400e8],
        })
        result = detect_margin_buy_ratio(pd.DataFrame(), macro, config)
        assert result.triggered
        assert result.direction == "bearish"
        assert result.detail["estimated_ratio"] == 0.2


# ── No-date fallback tests ──


class TestMarginNoDateFallback:
    """Detectors when date column is missing."""

    def test_balance_trend_no_date(self, sample_config):
        """detect_margin_balance_trend without date column returns neutral."""
        macro = pd.DataFrame({
            "margin_balance": [14000, 14100, 14200, 14300, 14400] * 2,
            "market": ["sh"] * 5 + ["sz"] * 5,
        })
        result = detect_margin_balance_trend(macro, sample_config)
        assert not result.triggered
        assert "无法按日期聚合" in result.summary

    def test_balance_trend_no_date_no_market(self, sample_config):
        """No date, no market column → uses iloc[-1]."""
        macro = pd.DataFrame({
            "margin_balance": [14000, 14100, 14200],
        })
        result = detect_margin_balance_trend(macro, sample_config)
        assert not result.triggered
        assert "无法按日期聚合" in result.summary

    def test_balance_trend_no_date_empty_balance(self, sample_config):
        """No date, all-NaN balance → returns neutral with empty message."""
        macro = pd.DataFrame({
            "margin_balance": [np.nan, np.nan],
        })
        result = detect_margin_balance_trend(macro, sample_config)
        assert not result.triggered
        assert "数据为空" in result.summary

    def test_short_trend_no_date(self, sample_config):
        """detect_short_trend without date column uses positional indexing."""
        # Need large enough change to trigger: change > 10% triggers bearish
        macro = pd.DataFrame({
            "short_balance": [800, 810, 820, 830, 840, 850, 900, 1000],
        })
        result = detect_short_trend(macro, sample_config)
        # 8 rows, change_days=5, current=1000, prev=830, change ≈ 20.5%
        assert result.triggered
        assert result.direction == "bearish"

    def test_short_ratio_no_date(self, sample_config):
        """detect_margin_short_ratio without date column uses positional indexing."""
        # Create 30 rows so len(ratio) >= 21
        balances = list(range(14000, 14030))
        shorts = list(range(800, 770, -1))
        macro = pd.DataFrame({
            "margin_balance": balances,
            "short_balance": shorts,
        })
        result = detect_margin_short_ratio(macro, sample_config)
        # Should produce a valid signal (direction depends on trend)
        assert result.key == "margin_short_ratio"

    def test_buy_ratio_no_date_macro(self, sample_config):
        """detect_margin_buy_ratio without date column sums all rows."""
        macro = pd.DataFrame({
            "buy_on_margin_value": [200e8, 300e8],
        })
        result = detect_margin_buy_ratio(pd.DataFrame(), macro, sample_config)
        # Should estimate from 500亿 total
        assert result.key == "margin_buy_ratio"
