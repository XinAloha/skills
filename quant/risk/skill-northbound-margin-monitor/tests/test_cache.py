"""Tests for CacheManager."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from core.cache import CacheManager, META_FILENAME


@pytest.fixture
def cache() -> CacheManager:
    with tempfile.TemporaryDirectory() as d:
        yield CacheManager(cache_root=d)


def make_test_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    nb = pd.DataFrame({"date": ["20260630"], "market_value": [21000]})
    mg = pd.DataFrame({"date": ["20260630"], "margin_balance": [15000]})
    md = pd.DataFrame({"symbol": ["000001.SZ"], "margin_balance": [100]})
    info = pd.DataFrame({"symbol": ["000001.SZ"], "name": ["测试"]})
    return nb, mg, md, info


class TestCacheBasic:
    def test_has_false_when_empty(self, cache):
        assert cache.has("20260630") is False

    def test_save_and_has(self, cache):
        nb, mg, md, info = make_test_data()
        cache.save("20260630", nb, mg, md, info)
        assert cache.has("20260630") is True

    def test_save_and_load_roundtrip(self, cache):
        nb, mg, md, info = make_test_data()
        nb.attrs["source"] = "eastmoney"
        mg.attrs["source"] = "pandadata"

        cache.save("20260630", nb, mg, md, info)
        loaded_nb, loaded_mg, loaded_md, loaded_info, loaded_fut = cache.load("20260630")

        assert len(loaded_nb) == 1
        assert loaded_nb.iloc[0]["market_value"] == 21000
        assert len(loaded_mg) == 1
        assert len(loaded_md) == 1
        assert len(loaded_info) == 1
        assert loaded_fut.empty  # No futures saved

    def test_load_returns_empty_on_missing(self, cache):
        nb, mg, md, info, fut = cache.load("20990101")
        assert nb.empty
        assert mg.empty
        assert md.empty
        assert info.empty
        assert fut.empty

    def test_save_creates_meta_file(self, cache):
        nb, mg, md, info = make_test_data()
        cache.save("20260630", nb, mg, md, info)
        assert (Path(cache._root) / "20260630" / META_FILENAME).exists()

    def test_load_meta(self, cache):
        nb, mg, md, info = make_test_data()
        cache.save("20260630", nb, mg, md, info)
        meta = cache.load_meta("20260630")
        assert meta["trade_date"] == "20260630"
        assert meta["northbound_rows"] == 1
        assert meta["margin_rows"] == 1

    def test_load_meta_missing(self, cache):
        assert cache.load_meta("20990101") == {}

    def test_cached_dates(self, cache):
        nb, _, _, _ = make_test_data()
        empty = pd.DataFrame()
        cache.save("20260630", nb, empty, empty, empty)
        cache.save("20260629", nb, empty, empty, empty)
        dates = cache.cached_dates
        assert "20260629" in dates
        assert "20260630" in dates
        assert dates == sorted(dates)

    def test_clear_old(self, cache):
        nb, _, _, _ = make_test_data()
        empty = pd.DataFrame()
        # Save a date from 60 days ago
        import datetime
        old_date = (datetime.datetime.now() - datetime.timedelta(days=60)).strftime("%Y%m%d")
        cache.save(old_date, nb, empty, empty, empty)
        cache.save("20260630", nb, empty, empty, empty)

        removed = cache.clear_old(keep_days=30)
        assert removed == 1
        assert cache.has("20260630") is True
        assert cache.has(old_date) is False

    def test_clear_old_no_root(self, cache):
        assert cache.clear_old(keep_days=30) == 0

    def test_has_without_root(self, cache):
        # Should not crash when cache root doesn't exist
        assert cache.has("20260630") is False

    def test_has_with_partial_cache(self, cache):
        # Directory exists but no northbound.parquet
        date_dir = Path(cache._root) / "20260630"
        date_dir.mkdir(parents=True)
        (date_dir / "margin.parquet").write_text("")
        assert cache.has("20260630") is False


class TestCacheCorruption:
    def test_corrupt_parquet_returns_empty(self, cache):
        date_dir = Path(cache._root) / "20260630"
        date_dir.mkdir(parents=True)
        (date_dir / "northbound.parquet").write_bytes(b"not a parquet file")
        (date_dir / "margin.parquet").write_bytes(b"also corrupt")

        nb, mg, md, info, fut = cache.load("20260630")
        assert nb.empty
        assert mg.empty
        # margin_detail and stock_info don't exist → empty
        assert md.empty
        assert info.empty
        assert fut.empty

    def test_corrupt_meta_returns_empty_dict(self, cache):
        date_dir = Path(cache._root) / "20260630"
        date_dir.mkdir(parents=True)
        (date_dir / META_FILENAME).write_text("{not valid json}", encoding="utf-8")
        assert cache.load_meta("20260630") == {}

    def test_partial_cache_load(self, cache):
        # Only northbound exists, others don't
        nb = pd.DataFrame({"a": [1]})
        cache.save("20260630", nb, pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
        loaded_nb, loaded_mg, loaded_md, loaded_info, loaded_fut = cache.load("20260630")
        assert len(loaded_nb) == 1
        assert loaded_mg.empty
        assert loaded_md.empty
        assert loaded_info.empty
        assert loaded_fut.empty

    def test_load_nb_flow_success(self, cache):
        """load_nb_flow() should return the northbound flow DataFrame."""
        nb = pd.DataFrame({"date": ["20260630"], "market_value": [21000]})
        nb_flow = pd.DataFrame({"板块": ["沪股通", "深股通"], "资金方向": ["北向", "北向"]})
        cache.save("20260630", nb, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
                   northbound_flow_df=nb_flow)
        loaded_flow = cache.load_nb_flow("20260630")
        assert not loaded_flow.empty
        assert len(loaded_flow) == 2
        assert "板块" in loaded_flow.columns

    def test_load_nb_flow_saves_and_loads_futures(self, cache):
        """save() with futures_df should persist to futures.parquet."""
        nb = pd.DataFrame({"date": ["20260630"]})
        fut = pd.DataFrame({
            "date": ["20260630"],
            "index_name": ["CSI300"],
            "close": [4000],
        })
        cache.save("20260630", nb, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(),
                   futures_df=fut)
        _, _, _, _, loaded_fut = cache.load("20260630")
        assert not loaded_fut.empty
        assert len(loaded_fut) == 1
        assert "index_name" in loaded_fut.columns
