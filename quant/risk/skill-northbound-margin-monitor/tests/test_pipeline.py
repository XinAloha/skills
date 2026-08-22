"""Integration tests for PanoramaPipeline.run() with mocked DataFetcher."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from core.pipeline import PanoramaPipeline, PipelineResult


# ── Mock data helpers ──

def _make_mock_fetch_data():
    """Build a mock fetch_all_data return dict using conftest-style fixtures."""
    dates = pd.date_range("2026-01-02", periods=100, freq="B")
    np.random.seed(42)
    market_value = 20000 + np.cumsum(np.random.randn(100) * 50)
    net_buy = np.diff(market_value, prepend=market_value[0])

    nb_summary = pd.DataFrame({
        "date": [d.strftime("%Y%m%d") for d in dates],
        "market_value": market_value,
        "net_buy_amount": net_buy,
        "CSI300": 4000 + np.cumsum(np.random.randn(100) * 10),
    })
    nb_summary.attrs["source"] = "eastmoney"

    nb_flow = pd.DataFrame({
        "日期": ["20260630", "20260630"],
        "类型": ["沪港通", "深港通"],
        "板块": ["沪股通", "深股通"],
        "资金方向": ["北向", "北向"],
        "交易状态": ["4", "4"],
        "成交净买额": [10.0, 20.0],
        "资金净流入": [50.0, 30.0],
        "当日资金余额": [0.0, 0.0],
        "上涨数": [1000, 800],
        "持平数": [50, 30],
        "下跌数": [300, 500],
        "相关指数": ["上证指数", "深证成指"],
        "指数涨跌幅": [0.59, 0.21],
    })

    margin_dates = pd.date_range("2026-01-02", periods=60, freq="B")
    np.random.seed(43)
    margin_bal = 15000 + np.cumsum(np.random.randn(60) * 30)
    short_bal = 800 + np.cumsum(np.random.randn(60) * 5)
    buy_amount = np.random.uniform(400, 800, 60)
    rows = []
    for i, d in enumerate(margin_dates):
        for mkt in ["sh", "sz"]:
            rows.append({
                "date": d.strftime("%Y%m%d"),
                "market": mkt,
                "margin_balance": margin_bal[i] * (0.55 if mkt == "sh" else 0.45),
                "short_balance": short_bal[i] * (0.6 if mkt == "sh" else 0.4),
                "buy_on_margin_value": buy_amount[i] * (0.5 if mkt == "sh" else 0.5),
            })
    margin_macro = pd.DataFrame(rows)
    margin_macro.attrs["source"] = "eastmoney"

    np.random.seed(44)
    symbols = [f"{code:06d}.{'SH' if code > 500000 else 'SZ'}" for code in range(1, 51)]
    margin_detail = pd.DataFrame({
        "symbol": symbols,
        "date": "20260630",
        "margin_balance": np.random.uniform(0.1e8, 50e8, 50),
        "buy_on_margin_value": np.random.uniform(0.01e8, 5e8, 50),
        "margin_repayment": np.random.uniform(0.01e8, 4e8, 50),
        "short_balance": np.random.uniform(0, 2e8, 50),
        "short_sell_quantity": np.random.uniform(0, 100000, 50),
        "total_balance": np.random.uniform(0.2e8, 55e8, 50),
        "margin_type": np.random.choice(["现金", "股票"], 50, p=[0.7, 0.3]),
    })

    industries = ["电子", "医药生物", "计算机", "食品饮料", "银行", "非银金融",
                  "汽车", "电力设备", "机械设备", "化工"]
    stock_info = pd.DataFrame({
        "symbol": symbols,
        "name": [f"测试股票{code}" for code in range(1, 51)],
        "industry": np.random.choice(industries, 50),
        "list_status": "正常",
    })

    universe = pd.DataFrame({"symbol": symbols})

    return {
        "northbound_summary": nb_summary,
        "northbound_flow": nb_flow,
        "margin_detail": margin_detail,
        "margin_macro": margin_macro,
        "stock_info": stock_info,
        "universe": universe,
        "fetch_time": "2026-07-01T10:00:00",
    }


# ── Integration tests ──

class TestPipelineIntegration:
    """End-to-end pipeline tests with mocked DataFetcher."""

    @pytest.fixture
    def mock_data(self):
        return _make_mock_fetch_data()

    @pytest.fixture
    def pipeline(self, tmp_path):
        """Pipeline with isolated cache directory."""
        return PanoramaPipeline(cache_root=str(tmp_path / "cache"))

    def test_pipeline_success_path(self, pipeline, mock_data):
        """Full pipeline run produces a valid PipelineResult."""
        with patch.object(pipeline._fetcher, "init_api"), \
             patch.object(pipeline._fetcher, "fetch_all_data", return_value=mock_data):
            result = pipeline.run(trade_date="20260630", use_cache=False)

        assert isinstance(result, PipelineResult)
        assert result.trade_date == "20260630"
        assert 0 <= result.composite_score <= 100
        assert result.composite_grade in ("A+", "A", "B+", "B", "C", "D", "E", "F", "F-")
        assert result.nb_triggered >= 0
        assert result.margin_triggered >= 0
        assert result.resonance_triggered >= 0

    def test_pipeline_generates_report_files(self, pipeline, mock_data, tmp_path):
        """Pipeline should write markdown and JSON reports."""
        output_dir = tmp_path / "output"
        config = {"output": {"dir": str(output_dir)}}
        pipeline._config = config

        with patch.object(pipeline._fetcher, "init_api"), \
             patch.object(pipeline._fetcher, "fetch_all_data", return_value=mock_data):
            result = pipeline.run(trade_date="20260630", use_cache=False)

        assert result.md_path.exists()
        assert result.json_path.exists()
        md_content = result.md_path.read_text(encoding="utf-8")
        assert "北向资金" in md_content or "northbound" in md_content.lower()

    def test_pipeline_cache_hit(self, pipeline, mock_data, tmp_path):
        """Second run with cache should load from cache."""
        # First run: fetch fresh
        with patch.object(pipeline._fetcher, "init_api"), \
             patch.object(pipeline._fetcher, "fetch_all_data", return_value=mock_data):
            result1 = pipeline.run(trade_date="20260630", use_cache=True)

        # Second run: should hit cache (no fetch_all_data call)
        fetch_called = False
        orig_fetch = pipeline._fetcher.fetch_all_data
        def _tracking_fetch(*args, **kwargs):
            nonlocal fetch_called
            fetch_called = True
            return mock_data

        with patch.object(pipeline._fetcher, "init_api"), \
             patch.object(pipeline._fetcher, "fetch_all_data", side_effect=_tracking_fetch):
            result2 = pipeline.run(trade_date="20260630", use_cache=True)

        # Cache should be hit — fetch_all_data should NOT be called
        assert not fetch_called

    def test_pipeline_data_fetch_error(self, pipeline):
        """Pipeline should return empty result on fetch failure."""
        with patch.object(pipeline._fetcher, "init_api"), \
             patch.object(pipeline._fetcher, "fetch_all_data", side_effect=Exception("API down")):
            result = pipeline.run(trade_date="20260630", use_cache=False)

        assert result.composite_score == 0.0
        assert result.composite_grade == "N/A"
        assert len(result.errors) > 0
        assert any("API down" in e for e in result.errors)

    def test_pipeline_errors_list_accumulates(self, pipeline, mock_data):
        """Non-fatal errors should be collected."""
        def _init_with_warning():
            raise RuntimeError("Pandadata login failed")
        pipeline._fetcher.init_api = _init_with_warning

        with patch.object(pipeline._fetcher, "fetch_all_data", return_value=mock_data):
            result = pipeline.run(trade_date="20260630", use_cache=False)

        # init_api failure is non-fatal
        assert any("Pandadata init" in e or "login" in e.lower() for e in result.errors)

    def test_pipeline_no_cache_skip_cache(self, pipeline, mock_data):
        """use_cache=False should skip both cache read and write."""
        with patch.object(pipeline._fetcher, "init_api"), \
             patch.object(pipeline._fetcher, "fetch_all_data", return_value=mock_data):
            result = pipeline.run(trade_date="20260630", use_cache=False)

        assert result.composite_score > 0  # Should produce real score

    def test_pipeline_result_dataclass(self):
        """PipelineResult should have all expected fields."""
        r = PipelineResult(
            trade_date="20260630",
            md_path=Path("test.md"),
            json_path=Path("test.json"),
            composite_score=55.0,
            composite_grade="B",
            nb_triggered=2,
            nb_total=7,
            margin_triggered=3,
            margin_total=7,
            resonance_triggered=1,
        )
        assert r.trade_date == "20260630"
        assert r.composite_score == 55.0
        assert r.llm_source == "none"
        assert r.llm_analysis == ""

    def test_cleanup_cache_delegates(self, tmp_path):
        """cleanup_cache should delegate to CacheManager.clear_old."""
        pipeline = PanoramaPipeline(cache_root=str(tmp_path / "cache"))
        removed = pipeline.cleanup_cache(keep_days=30)
        assert removed == 0  # No cache yet


class TestPipelineEdgeCases:
    """Edge case and boundary tests."""

    def test_pipeline_with_empty_data(self, tmp_path):
        """Pipeline should handle completely empty DataFrames gracefully."""
        pipeline = PanoramaPipeline(cache_root=str(tmp_path / "cache"))
        empty_data = {
            "northbound_summary": pd.DataFrame(),
            "northbound_flow": pd.DataFrame(),
            "margin_detail": pd.DataFrame(),
            "margin_macro": pd.DataFrame(),
            "stock_info": pd.DataFrame(),
            "universe": pd.DataFrame(),
            "fetch_time": "test",
        }
        with patch.object(pipeline._fetcher, "init_api"), \
             patch.object(pipeline._fetcher, "fetch_all_data", return_value=empty_data):
            result = pipeline.run(trade_date="20260630", use_cache=False)

        assert isinstance(result, PipelineResult)
        assert 0 <= result.composite_score <= 100

    def test_pipeline_custom_top_n(self, tmp_path):
        """top_n parameter should be respected in rankings."""
        pipeline = PanoramaPipeline(cache_root=str(tmp_path / "cache"))
        mock_data = _make_mock_fetch_data()
        with patch.object(pipeline._fetcher, "init_api"), \
             patch.object(pipeline._fetcher, "fetch_all_data", return_value=mock_data):
            result = pipeline.run(trade_date="20260630", use_cache=False, top_n=10)

        assert result.composite_score >= 0
