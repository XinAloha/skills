"""Tests for core/data_fetcher.py — retry, batch, fallback, column remapping, orchestration.

Mock strategy: modules imported inside function bodies (panda_data, akshare)
must be injected via sys.modules, since they're not module-level attributes.
High-level orchestration methods are mocked via patch.object on the instance.
"""

import sys
from unittest.mock import MagicMock, patch, call

import numpy as np
import pandas as pd
import pytest

from core.data_fetcher import (
    DataFetcher,
    _load_config,
    _retry_api_call,
)


# ── Helpers ──


def _inject_mock_pandadata(get_trade_list=None, get_stock_detail=None,
                           get_margin=None, get_last_trade_date=None,
                           get_trade_cal=None, init_token=None):
    """Inject a mock ``panda_data`` module into sys.modules."""
    mock_pdd = MagicMock()
    if get_trade_list is not None:
        mock_pdd.get_trade_list.return_value = get_trade_list
    if get_stock_detail is not None:
        mock_pdd.get_stock_detail.return_value = get_stock_detail
    if get_margin is not None:
        mock_pdd.get_margin.return_value = get_margin
    if get_last_trade_date is not None:
        mock_pdd.get_last_trade_date.return_value = get_last_trade_date
    if get_trade_cal is not None:
        mock_pdd.get_trade_cal.return_value = get_trade_cal
    if init_token is not None:
        mock_pdd.init_token = init_token
    sys.modules["panda_data"] = mock_pdd
    return mock_pdd


def _inject_mock_akshare(**func_returns):
    """Inject a mock ``akshare`` module into sys.modules.

    Keyword args map function names to return values or side_effects.
    """
    mock_ak = MagicMock()
    for name, val in func_returns.items():
        if callable(val) and not isinstance(val, MagicMock):
            mock_ak.__getattr__(name).side_effect = val
        else:
            mock_ak.__getattr__(name).return_value = val
    sys.modules["akshare"] = mock_ak
    return mock_ak


def _remove_mock(mod_name):
    sys.modules.pop(mod_name, None)


# ── _retry_api_call tests ──


class TestRetryApiCall:
    """Retry logic with exponential backoff."""

    def test_success_first_attempt(self):
        func = MagicMock(return_value="ok")
        result = _retry_api_call(func, "arg1", kw="val", description="test")
        assert result == "ok"
        func.assert_called_once_with("arg1", kw="val")

    def test_retries_on_failure_then_succeeds(self):
        func = MagicMock(side_effect=[Exception("fail1"), Exception("fail2"), "ok"])
        with patch("time.sleep"):
            result = _retry_api_call(func, max_retries=2, description="test")
        assert result == "ok"
        assert func.call_count == 3

    def test_exhausts_retries_then_raises(self):
        func = MagicMock(side_effect=Exception("always fails"))
        with patch("time.sleep"):
            with pytest.raises(Exception, match="always fails"):
                _retry_api_call(func, max_retries=2, description="test")
        assert func.call_count == 3

    def test_exponential_backoff_delays(self):
        func = MagicMock(side_effect=[Exception, Exception, "ok"])
        with patch("time.sleep") as mock_sleep:
            _retry_api_call(func, max_retries=2, base_delay=1.0, backoff_factor=2.0)
        expected_calls = [call(1.0), call(2.0)]
        mock_sleep.assert_has_calls(expected_calls)

    def test_zero_max_retries_no_retry(self):
        func = MagicMock(side_effect=Exception("fail"))
        with patch("time.sleep"):
            with pytest.raises(Exception):
                _retry_api_call(func, max_retries=0, description="test")
        assert func.call_count == 1


# ── _load_config tests ──


class TestLoadConfig:
    """Config loading with in-memory caching."""

    def test_loads_config_from_file(self, tmp_path):
        import json
        import core.data_fetcher as df

        config_data = {"test_key": "test_value"}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        old_cache = df._config_cache
        df._config_cache = None
        try:
            with patch.object(df, "Path") as mock_path_cls:
                mock_path_cls.return_value.resolve.return_value.parent.parent = tmp_path
                result = df._load_config()
                assert result["test_key"] == "test_value"
        finally:
            df._config_cache = old_cache

    def test_missing_config_returns_empty_dict(self):
        import core.data_fetcher as df

        old_cache = df._config_cache
        df._config_cache = None
        try:
            with patch.object(df, "Path") as mock_path_cls:
                # Simulate: Path(__file__).resolve().parent.parent / "config.json"
                # The __truediv__ creates the final config path — make it not exist
                mock_config_path = MagicMock()
                mock_config_path.exists.return_value = False
                mock_root = MagicMock()
                mock_root.__truediv__.return_value = mock_config_path
                mock_path_cls.return_value.resolve.return_value.parent.parent = mock_root
                result = df._load_config()
                assert result == {}
        finally:
            df._config_cache = old_cache

    def test_cache_returns_same_object(self):
        import core.data_fetcher as df
        old_cache = df._config_cache
        df._config_cache = None
        try:
            r1 = df._load_config()
            r2 = df._load_config()
            assert r1 is r2
        finally:
            df._config_cache = old_cache


# ── DataFetcher __init__ tests ──


class TestDataFetcherInit:
    """DataFetcher initialization and config injection."""

    def test_default_uses_config_file(self):
        df = DataFetcher()
        assert df._config is not None
        assert isinstance(df._config, dict)

    def test_explicit_config_overrides_file(self):
        custom = {"custom": "config"}
        df = DataFetcher(config=custom)
        assert df._config is custom

    def test_initially_not_initialized(self):
        df = DataFetcher()
        assert not df._initialized


# ── init_api tests ──


class TestBedInitApi:
    """Pandadata API initialization."""

    def test_init_skips_when_already_initialized(self):
        df = DataFetcher({})
        df._initialized = True
        with patch("core.data_fetcher.logger") as mock_logger:
            df.init_api()
            mock_logger.info.assert_not_called()

    def test_missing_pandadata_sdk_raises(self):
        df = DataFetcher({
            "pandadata": {"username": "8613800000000", "password": "pass123"}
        })
        sys.modules["panda_data"] = None
        try:
            with pytest.raises(RuntimeError, match="panda_data SDK"):
                df.init_api()
        finally:
            _remove_mock("panda_data")

    def test_missing_credentials_raises(self, monkeypatch):
        monkeypatch.delenv("DEFAULT_USERNAME", raising=False)
        monkeypatch.delenv("DEFAULT_PASSWORD", raising=False)
        df = DataFetcher({"pandadata": {"username": "", "password": ""}})
        _inject_mock_pandadata()
        try:
            with pytest.raises(RuntimeError, match="credentials"):
                df.init_api()
        finally:
            _remove_mock("panda_data")

    def test_adds_86_prefix_when_missing(self, monkeypatch):
        monkeypatch.delenv("DEFAULT_USERNAME", raising=False)
        monkeypatch.delenv("DEFAULT_PASSWORD", raising=False)
        mock_pdd = _inject_mock_pandadata(
            init_token=MagicMock(),
        )
        try:
            df = DataFetcher({
                "pandadata": {"username": "18046753943", "password": "pass"}
            })
            df.init_api()
            mock_pdd.init_token.assert_called_once()
            call_kwargs = mock_pdd.init_token.call_args[1]
            assert call_kwargs["username"].startswith("86")
        finally:
            _remove_mock("panda_data")


# ── Stock universe tests ──


class TestStockUniverse:
    """Stock universe and detail fetching."""

    def test_fetch_stock_universe_sets_source(self):
        _inject_mock_pandadata(
            get_trade_list=pd.DataFrame({"symbol": ["000001.SZ"]})
        )
        try:
            df = DataFetcher({})
            result = df.fetch_stock_universe("20260701")
            assert result.attrs["source"] == "pandadata"
        finally:
            _remove_mock("panda_data")

    def test_fetch_stock_universe_empty(self):
        _inject_mock_pandadata(get_trade_list=pd.DataFrame())
        try:
            df = DataFetcher({})
            result = df.fetch_stock_universe("20260701")
            assert result.empty
        finally:
            _remove_mock("panda_data")

    def test_fetch_stock_details_empty_symbols(self):
        df = DataFetcher({})
        result = df.fetch_stock_details_batch([])
        assert result.empty

    def test_fetch_stock_details_column_remapping(self):
        _inject_mock_pandadata(
            get_stock_detail=pd.DataFrame({
                "symbol": ["000001.SZ"],
                "sector_code_name": ["金融"],
                "status": ["正常"],
            })
        )
        try:
            df = DataFetcher({})
            result = df.fetch_stock_details_batch(["000001.SZ"])
            assert "industry" in result.columns
            assert result.loc[0, "industry"] == "金融"
        finally:
            _remove_mock("panda_data")

    def test_fetch_stock_details_missing_cols_filled(self):
        _inject_mock_pandadata(
            get_stock_detail=pd.DataFrame({"symbol": ["000001.SZ"]})
        )
        try:
            df = DataFetcher({})
            result = df.fetch_stock_details_batch(["000001.SZ"])
            assert "name" in result.columns
            assert "industry" in result.columns
            assert result.loc[0, "name"] == "未知"
        finally:
            _remove_mock("panda_data")

    def test_fetch_stock_details_all_chunks_fail(self):
        mock_pdd = _inject_mock_pandadata()
        mock_pdd.get_stock_detail.side_effect = Exception("fail")
        try:
            df = DataFetcher({})
            result = df.fetch_stock_details_batch(["000001.SZ", "000002.SZ"])
            assert result.empty
        finally:
            _remove_mock("panda_data")

    def test_fetch_stock_details_chunks_multiple(self):
        """410 symbols → 3 chunks (200 + 200 + 10)."""
        mock_pdd = _inject_mock_pandadata(
            get_stock_detail=pd.DataFrame({"symbol": ["x"]})
        )
        try:
            df = DataFetcher({})
            symbols = [f"{i:06d}.SZ" for i in range(410)]
            result = df.fetch_stock_details_batch(symbols)
            assert mock_pdd.get_stock_detail.call_count == 3
        finally:
            _remove_mock("panda_data")

    def test_fetch_stock_universe_with_info_empty_universe(self):
        df = DataFetcher({})
        with patch.object(df, "fetch_stock_universe", return_value=pd.DataFrame()):
            universe, info = df.fetch_stock_universe_with_info("20260701")
            assert universe.empty
            assert info.empty


# ── Margin data tests ──


class TestMarginData:
    """Margin data fetching — Pandadata primary + AKShare fallback."""

    def test_fetch_margin_batch_empty_symbols(self):
        df = DataFetcher({})
        result = df.fetch_margin_batch([], "20260601", "20260701")
        assert result.empty

    def test_fetch_margin_batch_success(self):
        _inject_mock_pandadata(
            get_margin=pd.DataFrame({
                "symbol": ["000001.SZ", "000002.SZ"],
                "date": ["20260701", "20260701"],
                "margin_balance": [1e8, 2e8],
            })
        )
        try:
            df = DataFetcher({})
            result = df.fetch_margin_batch(
                ["000001.SZ", "000002.SZ"], "20260601", "20260701"
            )
            assert len(result) == 2
            assert result.attrs["source"] == "pandadata"
        finally:
            _remove_mock("panda_data")

    def test_fetch_margin_batch_chunks_properly(self):
        """500 symbols → 3 chunks of 200 each."""
        mock_pdd = _inject_mock_pandadata(
            get_margin=pd.DataFrame({"symbol": ["test"], "margin_balance": [1e8]})
        )
        try:
            df = DataFetcher({})
            symbols = [f"{i:06d}.SZ" for i in range(500)]
            df.fetch_margin_batch(symbols, "20260601", "20260701")
            assert mock_pdd.get_margin.call_count == 3
        finally:
            _remove_mock("panda_data")

    def test_fetch_margin_batch_partial_chunk_failure(self):
        """When one chunk fails, other chunks still succeed."""
        mock_pdd = _inject_mock_pandadata()
        call_count = [0]

        def _side_effect(symbol, start_date, end_date):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("chunk 2 failed")
            return pd.DataFrame({
                "symbol": [f"chunk{call_count[0]}"],
                "margin_balance": [1e8],
            })

        mock_pdd.get_margin.side_effect = _side_effect
        try:
            df = DataFetcher({})
            symbols = [f"{i:06d}.SZ" for i in range(400)]
            result = df.fetch_margin_batch(symbols, "20260601", "20260701")
            assert not result.empty
        finally:
            _remove_mock("panda_data")

    def test_fetch_margin_detail_em_column_renaming(self):
        _inject_mock_akshare(
            stock_margin_detail_sse=pd.DataFrame({
                "股票代码": ["600001"],
                "股票名称": ["测试"],
                "融资余额": [1e8],
                "融资买入额": [0.5e8],
                "日期": ["20260701"],
            }),
            stock_margin_detail_szse=pd.DataFrame({
                "股票代码": ["000001"],
                "股票名称": ["测试2"],
                "融资余额": [2e8],
                "融资买入额": [0.3e8],
                "日期": ["20260701"],
            }),
        )
        try:
            df = DataFetcher({})
            result = df._fetch_margin_detail_em("20260701")
            assert len(result) == 2
            assert "symbol" in result.columns
            assert "name" in result.columns
            assert "margin_balance" in result.columns
            assert "buy_on_margin_value" in result.columns
            assert result.attrs["source"] == "eastmoney"
        finally:
            _remove_mock("akshare")

    def test_fetch_margin_detail_em_both_fail(self):
        _inject_mock_akshare(
            stock_margin_detail_sse=Exception("SSE down"),
            stock_margin_detail_szse=Exception("SZSE down"),
        )
        try:
            df = DataFetcher({})
            result = df._fetch_margin_detail_em("20260701")
            assert result.empty
        finally:
            _remove_mock("akshare")

    def test_fetch_margin_macro_em(self):
        _inject_mock_akshare(
            macro_china_market_margin_sh=pd.DataFrame({
                "日期": ["20260701"],
                "融资余额": [15000],
                "融资买入额": [500],
                "融券余额": [200],
            }),
            macro_china_market_margin_sz=pd.DataFrame({
                "日期": ["20260701"],
                "融资余额": [12000],
                "融资买入额": [400],
                "融券余额": [150],
            }),
        )
        try:
            df = DataFetcher({})
            result = df._fetch_margin_macro_em()
            assert len(result) == 2
            assert result.attrs["source"] == "eastmoney"
            assert "margin_balance" in result.columns
            assert "market" in result.columns
        finally:
            _remove_mock("akshare")

    def test_fetch_margin_macro_em_partial_failure(self):
        _inject_mock_akshare(
            macro_china_market_margin_sh=Exception("SH down"),
            macro_china_market_margin_sz=pd.DataFrame({
                "日期": ["20260701"],
                "融资余额": [12000],
            }),
        )
        try:
            df = DataFetcher({})
            result = df._fetch_margin_macro_em()
            assert len(result) == 1
        finally:
            _remove_mock("akshare")

    def test_fetch_margin_data_primary_path(self):
        df = DataFetcher({})
        df._initialized = True
        mock_detail = pd.DataFrame({"symbol": ["000001.SZ"], "margin_balance": [1e8]})
        mock_macro = pd.DataFrame({"date": ["20260701"], "margin_balance": [27000]})
        with patch.object(df, "fetch_margin_batch", return_value=mock_detail), \
             patch.object(df, "_fetch_margin_macro_em", return_value=mock_macro):
            detail, macro = df.fetch_margin_data(["000001.SZ"], "20260701")
            assert not detail.empty
            assert not macro.empty

    def test_fetch_margin_data_fallback_path(self):
        df = DataFetcher({})
        df._initialized = True
        mock_detail_em = pd.DataFrame({"symbol": ["600001"], "margin_balance": [1e8]})
        mock_detail_em.attrs["source"] = "eastmoney"
        mock_macro = pd.DataFrame({"date": ["20260701"], "margin_balance": [27000]})
        with patch.object(df, "fetch_margin_batch", return_value=pd.DataFrame()), \
             patch.object(df, "_fetch_margin_detail_em", return_value=mock_detail_em), \
             patch.object(df, "_fetch_margin_macro_em", return_value=mock_macro):
            detail, macro = df.fetch_margin_data(["000001.SZ"], "20260701")
            assert detail.attrs.get("source") == "eastmoney"


# ── Northbound data tests ──


class TestNorthboundData:
    """Northbound data — East Money primary with degradation."""

    def test_fetch_northbound_summary_column_remapping(self):
        _inject_mock_akshare(
            stock_hsgt_hist_em=pd.DataFrame({
                "日期": ["20260701"],
                "当日成交净买额": [10.0],
                "持股市值": [20000],
                "沪深300": [4000],
            })
        )
        try:
            df = DataFetcher({})
            result = df._fetch_northbound_summary_em()
            assert "net_buy_amount" in result.columns
            assert "market_value" in result.columns
            assert "csi300" in result.columns
            assert "date" in result.columns
            assert result.attrs["source"] == "eastmoney"
        finally:
            _remove_mock("akshare")

    def test_fetch_northbound_summary_failure(self):
        _inject_mock_akshare(
            stock_hsgt_hist_em=Exception("API error"),
        )
        try:
            df = DataFetcher({})
            result = df._fetch_northbound_summary_em()
            assert result.empty
        finally:
            _remove_mock("akshare")

    def test_fetch_northbound_flow_direction_success(self):
        _inject_mock_akshare(
            stock_hsgt_fund_flow_summary_em=pd.DataFrame({
                "日期": ["20260701"],
                "板块": ["沪股通"],
                "资金方向": ["北向"],
            })
        )
        try:
            df = DataFetcher({})
            result = df._fetch_northbound_flow_direction_em()
            assert not result.empty
            assert result.attrs["source"] == "eastmoney"
        finally:
            _remove_mock("akshare")

    def test_fetch_northbound_flow_direction_failure(self):
        _inject_mock_akshare(
            stock_hsgt_fund_flow_summary_em=Exception("API error"),
        )
        try:
            df = DataFetcher({})
            result = df._fetch_northbound_flow_direction_em()
            assert result.empty
        finally:
            _remove_mock("akshare")

    def test_fetch_northbound_data_both_succeed(self):
        df = DataFetcher({})
        summary = pd.DataFrame({"date": ["20260701"], "market_value": [20000]})
        flow = pd.DataFrame({"板块": ["沪股通"]})
        with patch.object(df, "_fetch_northbound_summary_em", return_value=summary), \
             patch.object(df, "_fetch_northbound_flow_direction_em", return_value=flow):
            s, f = df.fetch_northbound_data()
            assert not s.empty
            assert not f.empty

    def test_fetch_northbound_data_both_fail_returns_empty_degraded(self):
        df = DataFetcher({})
        with patch.object(df, "_fetch_northbound_summary_em", return_value=pd.DataFrame()), \
             patch.object(df, "_fetch_northbound_flow_direction_em", return_value=pd.DataFrame()):
            s, f = df.fetch_northbound_data()
            assert s.empty
            assert f.empty
            assert s.attrs.get("source") == "degraded"

    def test_fetch_northbound_data_summary_only_degraded(self):
        df = DataFetcher({})
        summary = pd.DataFrame({"date": ["20260701"]})
        with patch.object(df, "_fetch_northbound_summary_em", return_value=summary), \
             patch.object(df, "_fetch_northbound_flow_direction_em", return_value=pd.DataFrame()):
            s, f = df.fetch_northbound_data()
            assert not s.empty
            assert s.attrs.get("source") == "degraded"

    def test_fetch_northbound_data_flow_only_degraded(self):
        df = DataFetcher({})
        flow = pd.DataFrame({"板块": ["沪股通"]})
        with patch.object(df, "_fetch_northbound_summary_em", return_value=pd.DataFrame()), \
             patch.object(df, "_fetch_northbound_flow_direction_em", return_value=flow):
            s, f = df.fetch_northbound_data()
            assert not f.empty
            assert f.attrs.get("source") == "degraded"


# ── Futures data tests ──


class TestFuturesData:
    """Index futures data fetching and merging."""

    def _make_futures_side_effect(self):
        def _futures(symbol):
            base = {"IF0": 4000, "IH0": 2800, "IC0": 5500}[symbol]
            return pd.DataFrame({
                "日期": ["20260701"],
                "收盘价": [base],
                "成交量": [10000],
                "持仓量": [50000],
            })
        return _futures

    def _make_spot_side_effect(self):
        def _spot(symbol):
            base = {"sh000300": 4005, "sh000016": 2810, "sh000905": 5520}[symbol]
            return pd.DataFrame({"date": ["20260701"], "close": [base]})
        return _spot

    def test_fetch_index_futures_all_three_indices(self):
        _inject_mock_akshare(
            futures_main_sina=self._make_futures_side_effect(),
            stock_zh_index_daily=self._make_spot_side_effect(),
        )
        try:
            df = DataFetcher({})
            result = df._fetch_index_futures_em()
            assert len(result) == 3
            assert "close" in result.columns
            assert "spot_close" in result.columns
            assert "open_interest" in result.columns
            assert result.attrs["source"] == "sina_eastmoney"
        finally:
            _remove_mock("akshare")

    def test_fetch_index_futures_spot_failure_skips_index(self):
        def _futures(symbol):
            return pd.DataFrame({
                "日期": ["20260701"],
                "收盘价": [4000],
                "成交量": [10000],
                "持仓量": [50000],
            })

        def _spot(symbol):
            if symbol == "sh000300":
                raise Exception("spot unavailable")
            return pd.DataFrame({"date": ["20260701"], "close": [4000]})

        _inject_mock_akshare(
            futures_main_sina=_futures,
            stock_zh_index_daily=_spot,
        )
        try:
            df = DataFetcher({})
            result = df._fetch_index_futures_em()
            assert len(result) == 2  # SSE50 + CSI500
        finally:
            _remove_mock("akshare")

    def test_fetch_futures_data_empty_degraded(self):
        df = DataFetcher({})
        with patch.object(df, "_fetch_index_futures_em", return_value=pd.DataFrame()):
            result = df.fetch_futures_data()
            assert result.empty
            assert result.attrs.get("source") == "degraded"


# ── fetch_all_data orchestration tests ──


class TestFetchAllData:
    """Orchestration of all data fetching."""

    def _make_fake_results(self):
        universe = pd.DataFrame({"symbol": ["000001.SZ", "000002.SZ"]})
        stock_info = pd.DataFrame({
            "symbol": ["000001.SZ", "000002.SZ"],
            "name": ["平安银行", "万科A"],
            "industry": ["金融", "房地产"],
        })
        nb_summary = pd.DataFrame({
            "date": ["20260701"],
            "market_value": [20000],
            "net_buy_amount": [10.0],
        })
        nb_summary.attrs["source"] = "eastmoney"
        nb_flow = pd.DataFrame({"板块": ["沪股通"]})
        margin_detail = pd.DataFrame({"symbol": ["000001.SZ"], "margin_balance": [1e8]})
        margin_detail.attrs["source"] = "pandadata"
        margin_macro = pd.DataFrame({"date": ["20260701"], "margin_balance": [27000]})
        futures_data = pd.DataFrame({
            "date": ["20260701"],
            "close": [4000],
            "spot_close": [4005],
            "open_interest": [50000],
            "index_name": ["CSI300"],
        })
        futures_data.attrs["source"] = "sina_eastmoney"
        return {
            "universe": universe,
            "stock_info": stock_info,
            "nb_summary": nb_summary,
            "nb_flow": nb_flow,
            "margin_detail": margin_detail,
            "margin_macro": margin_macro,
            "futures_data": futures_data,
        }

    def test_fetch_all_data_returns_all_keys(self):
        fakes = self._make_fake_results()
        df = DataFetcher({})
        with patch.object(df, "fetch_stock_universe_with_info",
                          return_value=(fakes["universe"], fakes["stock_info"])), \
             patch.object(df, "fetch_northbound_data",
                          return_value=(fakes["nb_summary"], fakes["nb_flow"])), \
             patch.object(df, "fetch_margin_data",
                          return_value=(fakes["margin_detail"], fakes["margin_macro"])), \
             patch.object(df, "fetch_futures_data",
                          return_value=fakes["futures_data"]):
            result = df.fetch_all_data("20260701")
        assert result["trade_date"] == "20260701"
        assert "fetch_time" in result
        assert len(result["northbound_summary"]) == 1
        assert len(result["margin_detail"]) == 1
        assert len(result["futures_data"]) == 1

    def test_fetch_all_data_empty_universe(self):
        df = DataFetcher({})
        with patch.object(df, "fetch_stock_universe_with_info",
                          return_value=(pd.DataFrame(), pd.DataFrame())), \
             patch.object(df, "fetch_northbound_data",
                          return_value=(pd.DataFrame(), pd.DataFrame())), \
             patch.object(df, "fetch_margin_data",
                          return_value=(pd.DataFrame(), pd.DataFrame())), \
             patch.object(df, "fetch_futures_data",
                          return_value=pd.DataFrame()):
            result = df.fetch_all_data("20260701")
            assert result["trade_date"] == "20260701"
            assert result["northbound_summary"].empty


# ── Date utility tests ──


class TestDateUtils:
    """get_last_trade_date() and is_trading_day() — critical for pipeline."""

    def test_get_last_trade_date(self):
        _inject_mock_pandadata(get_last_trade_date="20260630")
        try:
            df = DataFetcher({})
            result = df.get_last_trade_date()
            assert result == "20260630"
        finally:
            _remove_mock("panda_data")

    def test_get_last_trade_date_propagates_error(self):
        """If panda_data raises, it should propagate (no silent swallowing)."""
        mock_pdd = MagicMock()
        mock_pdd.get_last_trade_date.side_effect = RuntimeError("API down")
        sys.modules["panda_data"] = mock_pdd
        try:
            df = DataFetcher({})
            with pytest.raises(RuntimeError, match="API down"):
                df.get_last_trade_date()
        finally:
            _remove_mock("panda_data")

    def test_is_trading_day_true(self):
        cal_df = pd.DataFrame({"is_trade": ["1"]})
        _inject_mock_pandadata(get_trade_cal=cal_df)
        try:
            df = DataFetcher({})
            assert df.is_trading_day("20260630") is True
        finally:
            _remove_mock("panda_data")

    def test_is_trading_day_false(self):
        cal_df = pd.DataFrame({"is_trade": ["0"]})
        _inject_mock_pandadata(get_trade_cal=cal_df)
        try:
            df = DataFetcher({})
            assert df.is_trading_day("20260630") is False
        finally:
            _remove_mock("panda_data")

    def test_is_trading_day_empty_calendar(self):
        _inject_mock_pandadata(get_trade_cal=pd.DataFrame())
        try:
            df = DataFetcher({})
            assert df.is_trading_day("20260630") is False
        finally:
            _remove_mock("panda_data")

    def test_is_trading_day_fallback_column(self):
        """Should use is_trading_day column as fallback when is_trade missing."""
        cal_df = pd.DataFrame({"is_trading_day": [1]})
        _inject_mock_pandadata(get_trade_cal=cal_df)
        try:
            df = DataFetcher({})
            assert df.is_trading_day("20260630") is True
        finally:
            _remove_mock("panda_data")

    def test_is_trading_day_bool_true(self):
        cal_df = pd.DataFrame({"is_trade": [True]})
        _inject_mock_pandadata(get_trade_cal=cal_df)
        try:
            df = DataFetcher({})
            assert df.is_trading_day("20260630") is True
        finally:
            _remove_mock("panda_data")


# ── Shenwan industry mapping tests ──


class TestShenwanMapping:
    """fetch_shenwan_mapping() — AKShare Shenwan industry classification."""

    def _make_industry_list_df(self, names=None):
        if names is None:
            names = ["半导体", "银行", "食品饮料", "医药生物", "计算机"]
        return pd.DataFrame({"板块名称": names})

    def _make_cons_df(self, symbols):
        """Create constituent DataFrame for a single industry."""
        return pd.DataFrame({"代码": symbols, "名称": [f"股票{i}" for i in range(len(symbols))]})

    def test_fetch_basic(self):
        """Build mapping from 2 industries with 3+2 stocks."""
        ind_list = self._make_industry_list_df(["半导体", "银行"])
        cons_data = {
            "半导体": self._make_cons_df(["000001.SZ", "000002.SZ", "000003.SZ"]),
            "银行": self._make_cons_df(["600001.SH", "600002.SH"]),
        }
        mock_ak = _inject_mock_akshare(
            stock_board_industry_name_em=ind_list,
            stock_board_industry_cons_em=lambda symbol, **kw: cons_data.get(symbol, pd.DataFrame()),
        )
        try:
            df = DataFetcher({"shenwan": {"enabled": True, "request_delay": 0}})
            result = df.fetch_shenwan_mapping()
            assert len(result) == 5
            assert "symbol" in result.columns
            assert "sw_industry" in result.columns
            assert result.attrs["source"] == "akshare_shenwan"
            assert result[result["symbol"] == "000001.SZ"]["sw_industry"].values[0] == "半导体"
            assert result[result["symbol"] == "600001.SH"]["sw_industry"].values[0] == "银行"
        finally:
            _remove_mock("akshare")

    def test_disabled_by_config(self):
        """When shenwan.enabled=false, return empty DataFrame."""
        mock_ak = _inject_mock_akshare()
        try:
            df = DataFetcher({"shenwan": {"enabled": False}})
            result = df.fetch_shenwan_mapping()
            assert result.empty
        finally:
            _remove_mock("akshare")

    def test_empty_industry_list(self):
        """AKShare returns empty industry list → empty result."""
        mock_ak = _inject_mock_akshare(stock_board_industry_name_em=pd.DataFrame())
        try:
            df = DataFetcher({"shenwan": {"enabled": True, "request_delay": 0}})
            result = df.fetch_shenwan_mapping()
            assert result.empty
        finally:
            _remove_mock("akshare")

    def test_industry_list_none(self):
        """AKShare returns None → empty result."""
        mock_ak = _inject_mock_akshare(stock_board_industry_name_em=None)
        try:
            df = DataFetcher({"shenwan": {"enabled": True, "request_delay": 0}})
            result = df.fetch_shenwan_mapping()
            assert result.empty
        finally:
            _remove_mock("akshare")

    def test_industry_list_exception(self):
        """AKShare raises exception → return empty DataFrame."""
        mock_ak = _inject_mock_akshare(
            stock_board_industry_name_em=MagicMock(side_effect=RuntimeError("Network error")),
        )
        try:
            df = DataFetcher({"shenwan": {"enabled": True, "request_delay": 0}})
            result = df.fetch_shenwan_mapping()
            assert result.empty
        finally:
            _remove_mock("akshare")

    def test_constituents_exception_per_industry(self):
        """Individual industry constituent calls fail gracefully."""
        ind_list = self._make_industry_list_df(["半导体", "银行"])
        def _cons_side_effect(symbol, **kw):
            if symbol == "半导体":
                raise RuntimeError("timeout")
            return self._make_cons_df(["600001.SH", "600002.SH"])
        mock_ak = _inject_mock_akshare(
            stock_board_industry_name_em=ind_list,
            stock_board_industry_cons_em=_cons_side_effect,
        )
        try:
            df = DataFetcher({"shenwan": {"enabled": True, "request_delay": 0}})
            result = df.fetch_shenwan_mapping()
            assert len(result) == 2  # Only 银行 mapped
            assert result["sw_industry"].unique()[0] == "银行"
        finally:
            _remove_mock("akshare")

    def test_deduplicate_symbols(self):
        """Stock appearing in multiple industries keeps first assignment."""
        ind_list = self._make_industry_list_df(["半导体", "银行"])
        cons_data = {
            "半导体": self._make_cons_df(["000001.SZ", "000002.SZ"]),
            "银行": self._make_cons_df(["000001.SZ", "600001.SH"]),
        }
        mock_ak = _inject_mock_akshare(
            stock_board_industry_name_em=ind_list,
            stock_board_industry_cons_em=lambda symbol, **kw: cons_data.get(symbol, pd.DataFrame()),
        )
        try:
            df = DataFetcher({"shenwan": {"enabled": True, "request_delay": 0}})
            result = df.fetch_shenwan_mapping()
            assert len(result) == 3  # 000001 appears once
        finally:
            _remove_mock("akshare")
