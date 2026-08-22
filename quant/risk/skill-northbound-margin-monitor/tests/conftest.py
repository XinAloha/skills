"""Shared pytest fixtures for the panorama monitor test suite."""

import numpy as np
import pandas as pd
import pytest


# ── Northbound fixtures ──

@pytest.fixture
def sample_nb_summary() -> pd.DataFrame:
    """Mock northbound daily summary (like stock_hsgt_hist_em output)."""
    dates = pd.date_range("2026-01-02", periods=100, freq="B")
    np.random.seed(42)
    market_value = 20000 + np.cumsum(np.random.randn(100) * 50)
    net_buy = np.diff(market_value, prepend=market_value[0])
    # Make recent net_buy NaN for last ~10 rows (simulating API issue)
    net_buy[-10:] = np.nan

    df = pd.DataFrame({
        "date": [d.strftime("%Y%m%d") for d in dates],
        "market_value": market_value,
        "net_buy_amount": net_buy,
        "CSI300": 4000 + np.cumsum(np.random.randn(100) * 10),
    })
    df.attrs["source"] = "eastmoney"
    return df


@pytest.fixture
def sample_nb_flow() -> pd.DataFrame:
    """Mock northbound flow direction — both markets northbound (inflow)."""
    return pd.DataFrame({
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


@pytest.fixture
def sample_nb_flow_diverged() -> pd.DataFrame:
    """Mock northbound flow with SH/SZ divergence."""
    return pd.DataFrame({
        "日期": ["20260630", "20260630"],
        "类型": ["沪港通", "深港通"],
        "板块": ["沪股通", "深股通"],
        "资金方向": ["北向", "南向"],
        "交易状态": ["4", "4"],
        "成交净买额": [20.0, -10.0],
        "资金净流入": [50.0, -20.0],
        "当日资金余额": [0.0, 0.0],
        "上涨数": [1000, 500],
        "持平数": [50, 30],
        "下跌数": [300, 800],
        "相关指数": ["上证指数", "深证成指"],
        "指数涨跌幅": [0.59, -0.31],
    })


# ── Margin fixtures ──

@pytest.fixture
def sample_margin_macro() -> pd.DataFrame:
    """Mock margin macro data (SH+SZ aggregate)."""
    dates = pd.date_range("2026-01-02", periods=60, freq="B")
    np.random.seed(43)
    margin_bal = 15000 + np.cumsum(np.random.randn(60) * 30)
    short_bal = 800 + np.cumsum(np.random.randn(60) * 5)
    buy_amount = np.random.uniform(400, 800, 60)

    rows = []
    for i, d in enumerate(dates):
        for mkt in ["sh", "sz"]:
            rows.append({
                "date": d.strftime("%Y%m%d"),
                "market": mkt,
                "margin_balance": margin_bal[i] * (0.55 if mkt == "sh" else 0.45),
                "short_balance": short_bal[i] * (0.6 if mkt == "sh" else 0.4),
                "buy_on_margin_value": buy_amount[i] * (0.5 if mkt == "sh" else 0.5),
            })

    df = pd.DataFrame(rows)
    df.attrs["source"] = "eastmoney"
    return df


@pytest.fixture
def sample_margin_detail() -> pd.DataFrame:
    """Mock per-stock margin detail data."""
    np.random.seed(44)
    symbols = [f"{code:06d}.{'SH' if code > 500000 else 'SZ'}" for code in range(1, 101)]
    return pd.DataFrame({
        "symbol": symbols,
        "date": "20260630",
        "margin_balance": np.random.uniform(0.1e8, 50e8, 100),
        "buy_on_margin_value": np.random.uniform(0.01e8, 5e8, 100),
        "margin_repayment": np.random.uniform(0.01e8, 4e8, 100),
        "short_balance": np.random.uniform(0, 2e8, 100),
        "short_sell_quantity": np.random.uniform(0, 100000, 100),
        "total_balance": np.random.uniform(0.2e8, 55e8, 100),
        "margin_type": np.random.choice(["现金", "股票"], 100, p=[0.7, 0.3]),
    })


@pytest.fixture
def sample_stock_info() -> pd.DataFrame:
    """Mock stock detail info."""
    symbols = [f"{code:06d}.{'SH' if code > 500000 else 'SZ'}" for code in range(1, 101)]
    industries = ["电子", "医药生物", "计算机", "食品饮料", "银行", "非银金融",
                  "汽车", "电力设备", "机械设备", "化工"]
    return pd.DataFrame({
        "symbol": symbols,
        "name": [f"测试股票{code}" for code in range(1, 101)],
        "industry": np.random.choice(industries, 100),
        "list_status": "正常",
    })


# ── Futures fixtures ──

@pytest.fixture
def sample_futures_data() -> pd.DataFrame:
    """Mock index futures daily data for CSI 300, SSE 50, CSI 500."""
    dates = pd.date_range("2026-01-02", periods=80, freq="B")
    np.random.seed(45)

    rows = []
    for idx_name, spot_base in [("CSI300", 4000), ("SSE50", 2800), ("CSI500", 5500)]:
        spot = spot_base + np.cumsum(np.random.randn(80) * 15)
        # Futures: spot + basis (-30 to +30 range)
        basis = np.random.randn(80) * 20 + 5  # slight positive bias
        futures_close = spot + basis
        oi = 50000 + np.cumsum(np.random.randn(80) * 500)
        volume = np.random.uniform(10000, 50000, 80)

        for i, d in enumerate(dates):
            rows.append({
                "date": d.strftime("%Y%m%d"),
                "index_name": idx_name,
                "contract": f"{idx_name}",
                "close": futures_close[i],
                "spot_close": spot[i],
                "open_interest": max(1000, oi[i]),
                "volume": volume[i],
            })

    df = pd.DataFrame(rows)
    df.attrs["source"] = "eastmoney"
    return df


@pytest.fixture
def sample_futures_data_bearish() -> pd.DataFrame:
    """Mock index futures with consistently negative basis."""
    dates = pd.date_range("2026-01-02", periods=80, freq="B")
    np.random.seed(46)

    rows = []
    for idx_name, spot_base in [("CSI300", 4000), ("SSE50", 2800), ("CSI500", 5500)]:
        spot = spot_base + np.cumsum(np.random.randn(80) * 15)
        # Consistently negative basis (backwardation)
        basis = np.random.randn(80) * 15 - 15
        futures_close = spot + basis
        oi = 50000 + np.cumsum(np.random.randn(80) * 500)
        volume = np.random.uniform(10000, 50000, 80)

        for i, d in enumerate(dates):
            rows.append({
                "date": d.strftime("%Y%m%d"),
                "index_name": idx_name,
                "contract": f"{idx_name}",
                "close": futures_close[i],
                "spot_close": spot[i],
                "open_interest": max(1000, oi[i]),
                "volume": volume[i],
            })

    df = pd.DataFrame(rows)
    df.attrs["source"] = "eastmoney"
    return df


# ── Flow history fixtures ──

@pytest.fixture
def sample_nb_flow_history() -> pd.DataFrame:
    """Mock accumulated flow direction history (10 trading days)."""
    dates = ["20260615", "20260616", "20260617", "20260618", "20260619",
             "20260622", "20260623", "20260624", "20260625", "20260626"]
    return pd.DataFrame({
        "date": dates,
        "direction_sum": [1, 2, 1, 1, -1, 2, 1, 2, 1, 2],
        "direction_days": [1, 2, 1, 1, 0.5, 2, 1, 2, 1, 2],
        "adv_sum": [1800, 2000, 1700, 1600, 800, 2100, 1900, 2200, 2000, 2100],
        "dec_sum": [500, 400, 600, 700, 1500, 400, 500, 300, 400, 300],
        "flat_sum": [100, 80, 90, 70, 120, 80, 100, 60, 80, 70],
        "index_chg_avg": [0.3, 0.5, 0.1, -0.1, -0.4, 0.8, 0.4, 0.6, 0.3, 0.7],
    })


@pytest.fixture
def sample_nb_flow_history_bearish() -> pd.DataFrame:
    """Mock flow history with persistent bearish direction (last 5 days outflow)."""
    dates = ["20260615", "20260616", "20260617", "20260618", "20260619",
             "20260622", "20260623", "20260624", "20260625", "20260626"]
    return pd.DataFrame({
        "date": dates,
        "direction_sum": [1, 0, -1, -1, -2, -1, -2, -1, -2, -2],
        "direction_days": [1, 0, 1, 1, 2, 1, 2, 1, 2, 2],
        "adv_sum": [1500, 1000, 500, 400, 300, 600, 400, 500, 300, 400],
        "dec_sum": [800, 1300, 1800, 1900, 2000, 1700, 1900, 1800, 2000, 1900],
        "flat_sum": [100, 100, 90, 80, 70, 80, 90, 60, 70, 80],
        "index_chg_avg": [0.1, -0.2, -0.5, -0.4, -0.8, -0.3, -0.6, -0.4, -0.7, -0.9],
    })


@pytest.fixture
def sample_nb_flow_history_short() -> pd.DataFrame:
    """Mock flow history with only 2 days (insufficient for trend)."""
    return pd.DataFrame({
        "date": ["20260625", "20260626"],
        "direction_sum": [1, 2],
        "direction_days": [1, 2],
        "adv_sum": [2000, 2100],
        "dec_sum": [400, 300],
        "flat_sum": [80, 70],
        "index_chg_avg": [0.3, 0.7],
    })


@pytest.fixture
def sample_hkex_data() -> pd.DataFrame:
    """Mock HKEX northbound turnover data."""
    np.random.seed(99)
    dates = ["20260615", "20260616", "20260617", "20260618", "20260619"]
    return pd.DataFrame({
        "date": dates,
        "nb_buy_rmb": np.random.uniform(50, 100, 5) * 1e8,
        "nb_sell_rmb": np.random.uniform(40, 90, 5) * 1e8,
        "nb_net_rmb": np.random.uniform(-20, 30, 5) * 1e8,
    })


# ── Config fixture ──

@pytest.fixture
def sample_config() -> dict:
    """Minimal config for testing."""
    return {
        "northbound": {
            "consecutive_days_threshold": 3,
            "anomaly_zscore_threshold": 2.0,
            "ma_short_window": 20,
            "ma_long_window": 60,
            "top_n_holdings": 20,
            "holding_change_top_n": 10,
        },
        "margin": {
            "buy_ratio_hot": 0.10,
            "buy_ratio_dangerous": 0.15,
            "trend_short_window": 5,
            "trend_long_window": 20,
            "short_change_days": 5,
            "top_n_margin_stocks": 20,
        },
        "resonance": {
            "enable_resonance": True,
            "enable_divergence": True,
        },
        "futures": {
            "basis_threshold": 0.3,
            "oi_change_threshold": 2.0,
            "oi_lookback_days": 5,
        },
        "scoring": {
            "northbound_weight": 0.4,
            "margin_weight": 0.4,
            "futures_weight": 0.2,
            "risk_overheat_threshold": 0.7,
        },
        "output": {"dir": "output"},
    }
