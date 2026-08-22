"""Tests for flow accumulator."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from core.flow_accumulator import FlowAccumulator


class TestFlowAccumulatorInit:
    def test_default_cache_root(self):
        fa = FlowAccumulator()
        assert fa._root == Path("cache")
        assert fa._history_path == Path("cache") / "nb_flow_history.parquet"

    def test_custom_cache_root(self):
        fa = FlowAccumulator(cache_root="/tmp/my_cache")
        assert fa._root == Path("/tmp/my_cache")


class TestParseDirection:
    def test_north_inflow(self):
        assert FlowAccumulator._parse_direction("北向") == 1
        assert FlowAccumulator._parse_direction("资金流入") == 1
        assert FlowAccumulator._parse_direction("北向资金") == 1

    def test_south_outflow(self):
        assert FlowAccumulator._parse_direction("南向") == -1
        assert FlowAccumulator._parse_direction("资金流出") == -1

    def test_empty_returns_zero(self):
        assert FlowAccumulator._parse_direction("") == 0
        assert FlowAccumulator._parse_direction("未知") == 0


class TestNormalizeMarket:
    def test_shanghai(self):
        assert FlowAccumulator._normalize_market("沪股通") == "SH"

    def test_shenzhen(self):
        assert FlowAccumulator._normalize_market("深股通") == "SZ"


class TestParseFlow:
    def test_parse_valid_flow(self):
        """Northbound rows should be parsed, southbound filtered out."""
        nb_flow = pd.DataFrame({
            "日期": ["20260630", "20260630", "20260630", "20260630"],
            "板块": ["沪股通", "港股通(沪)", "深股通", "港股通(深)"],
            "资金方向": ["北向", "南向", "北向", "南向"],
            "上涨数": [1000, 0, 800, 0],
            "下跌数": [300, 0, 500, 0],
            "持平数": [50, 0, 30, 0],
            "指数涨跌幅": [0.59, 0.0, 0.21, 0.0],
        })
        fa = FlowAccumulator()
        rows = fa._parse_flow("20260630", nb_flow)
        assert len(rows) == 2  # only northbound SH + SZ
        markets = {r["market"] for r in rows}
        assert markets == {"SH", "SZ"}

    def test_empty_flow(self):
        fa = FlowAccumulator()
        rows = fa._parse_flow("20260630", pd.DataFrame())
        assert rows == []

    def test_none_flow(self):
        fa = FlowAccumulator()
        rows = fa._parse_flow("20260630", None)
        assert rows == []

    def test_flow_with_positional_fallback(self):
        """Test column resolution falls back to positional indices."""
        # Intentionally use odd column names to force positional fallback
        nb_flow = pd.DataFrame({
            "col0": ["20260630", "20260630"],
            "col1": ["x", "y"],
            "col2": ["沪股通", "深股通"],    # position 2 → sector
            "col3": ["北向", "北向"],         # position 3 → direction
            "col4": [1, 1],
            "col5": [10.0, 20.0],
            "col6": [50.0, 30.0],
            "col7": [0.0, 0.0],
            "col8": [1000, 800],             # position 8 → advancing
            "col9": [50, 30],                # position 9 → flat
            "col10": [300, 500],             # position 10 → declining
            "col11": ["上证", "深证"],
            "col12": [0.59, 0.21],           # position 12 → index change
        })
        fa = FlowAccumulator()
        rows = fa._parse_flow("20260630", nb_flow)
        assert len(rows) == 2
        assert rows[0]["market"] == "SH"
        assert rows[0]["direction"] == 1
        assert rows[0]["adv_count"] == 1000

    def test_southbound_filtered(self):
        """港股通 rows should be excluded."""
        nb_flow = pd.DataFrame({
            "板块": ["沪股通", "港股通(沪)", "深股通", "港股通(深)"],
            "资金方向": ["北向", "南向", "北向", "南向"],
            "上涨数": [1000, 200, 800, 300],
            "下跌数": [300, 100, 500, 200],
            "持平数": [50, 30, 30, 40],
            "指数涨跌幅": [0.5, 0.2, 0.3, 0.1],
        })
        fa = FlowAccumulator()
        rows = fa._parse_flow("20260630", nb_flow)
        assert len(rows) == 2
        assert all(r["market"] in ("SH", "SZ") for r in rows)


class TestAccumulate:
    def test_first_accumulation_creates_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fa = FlowAccumulator(cache_root=tmpdir)
            nb_flow = pd.DataFrame({
                "板块": ["沪股通", "深股通"],
                "资金方向": ["北向", "北向"],
                "上涨数": [1000, 800],
                "下跌数": [300, 500],
                "持平数": [50, 30],
                "指数涨跌幅": [0.59, 0.21],
            })
            history = fa.accumulate("20260630", nb_flow)
            assert len(history) == 2
            assert history["date"].nunique() == 1
            assert fa._history_path.exists()

    def test_accumulate_dedup_same_date(self):
        """Re-accumulating same date should not create duplicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fa = FlowAccumulator(cache_root=tmpdir)
            nb_flow = pd.DataFrame({
                "板块": ["沪股通", "深股通"],
                "资金方向": ["北向", "北向"],
                "上涨数": [1000, 800],
                "下跌数": [300, 500],
                "持平数": [50, 30],
                "指数涨跌幅": [0.59, 0.21],
            })
            fa.accumulate("20260630", nb_flow)
            # Same date, slightly different values
            nb_flow2 = nb_flow.copy()
            nb_flow2["上涨数"] = [1100, 900]
            history = fa.accumulate("20260630", nb_flow2)
            assert len(history) == 2  # still 2, not 4
            assert history["adv_count"].iloc[0] == 1100  # latest value kept

    def test_accumulate_incremental_new_date(self):
        """Adding a new date should append to history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fa = FlowAccumulator(cache_root=tmpdir)
            nb_flow1 = pd.DataFrame({
                "板块": ["沪股通", "深股通"],
                "资金方向": ["北向", "北向"],
                "上涨数": [1000, 800],
                "下跌数": [300, 500],
                "持平数": [50, 30],
                "指数涨跌幅": [0.59, 0.21],
            })
            fa.accumulate("20260630", nb_flow1)
            history = fa.accumulate("20260701", nb_flow1)
            assert len(history) == 4  # 2 dates * 2 markets
            assert history["date"].nunique() == 2

    def test_empty_flow_returns_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fa = FlowAccumulator(cache_root=tmpdir)
            nb_flow = pd.DataFrame({
                "板块": ["沪股通", "深股通"],
                "资金方向": ["北向", "北向"],
                "上涨数": [1000, 800],
                "下跌数": [300, 500],
                "持平数": [50, 30],
                "指数涨跌幅": [0.59, 0.21],
            })
            fa.accumulate("20260630", nb_flow)
            history = fa.accumulate("20260701", pd.DataFrame())
            assert len(history) == 2  # unchanged


class TestGetDirectionSeries:
    def test_daily_aggregate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fa = FlowAccumulator(cache_root=tmpdir)
            nb_flow = pd.DataFrame({
                "板块": ["沪股通", "深股通"],
                "资金方向": ["北向", "北向"],
                "上涨数": [1000, 800],
                "下跌数": [300, 500],
                "持平数": [50, 30],
                "指数涨跌幅": [0.59, 0.21],
            })
            fa.accumulate("20260630", nb_flow)
            ds = fa.get_direction_series("daily")
            assert len(ds) == 1
            assert ds["direction_sum"].iloc[0] == 2
            assert ds["direction_days"].iloc[0] == 2
            assert ds["adv_sum"].iloc[0] == 1800
            assert ds["dec_sum"].iloc[0] == 800

    def test_market_separate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fa = FlowAccumulator(cache_root=tmpdir)
            nb_flow = pd.DataFrame({
                "板块": ["沪股通", "深股通"],
                "资金方向": ["北向", "南向"],
                "上涨数": [1000, 800],
                "下跌数": [300, 500],
                "持平数": [50, 30],
                "指数涨跌幅": [0.59, 0.21],
            })
            fa.accumulate("20260630", nb_flow)
            ds = fa.get_direction_series("daily")
            assert ds["direction_sum"].iloc[0] == 0  # SH inflow + SZ outflow

    def test_empty_history_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fa = FlowAccumulator(cache_root=tmpdir)
            ds = fa.get_direction_series("daily")
            assert ds.empty


class TestLoadHistory:
    def test_load_empty_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fa = FlowAccumulator(cache_root=tmpdir)
            history = fa.load_history()
            assert history.empty


class TestRebuildFromCache:
    def test_rebuild_from_cache(self):
        """Rebuild should scan per-date cache files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            # Create a per-date directory with northbound_flow.parquet
            date_dir = tmp / "20260630"
            date_dir.mkdir(parents=True)
            nb_flow = pd.DataFrame({
                "板块": ["沪股通", "深股通"],
                "资金方向": ["北向", "北向"],
                "上涨数": [1000, 800],
                "下跌数": [300, 500],
                "持平数": [50, 30],
                "指数涨跌幅": [0.59, 0.21],
            })
            nb_flow.to_parquet(date_dir / "northbound_flow.parquet", index=False)

            fa = FlowAccumulator(cache_root=tmpdir)
            history = fa.rebuild_from_cache()
            assert len(history) == 2
            assert history["date"].iloc[0] == "20260630"

    def test_rebuild_empty_when_no_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fa = FlowAccumulator(cache_root=tmpdir)
            history = fa.rebuild_from_cache()
            assert history.empty
