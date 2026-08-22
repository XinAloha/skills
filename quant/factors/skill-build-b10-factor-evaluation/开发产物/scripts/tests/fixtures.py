"""共享样本数据生成器。"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# 让 tests/ 子目录里的脚本能直接 import 顶层 scripts/* 模块
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def make_sample() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range("2026-01-01", periods=24, freq="B")
    assets = [f"{i:06d}.SZ" for i in range(1, 41)]
    rows = []
    for date in dates:
        factor = rng.normal(size=len(assets))
        forward_return = 0.006 * factor + rng.normal(scale=0.015, size=len(assets))
        for asset, f, r in zip(assets, factor, forward_return):
            rows.append(
                {
                    "trade_date": date,
                    "ts_code": asset,
                    "factor_value": f,
                    "forward_return": r,
                }
            )
    return pd.DataFrame(rows)


def make_pool_sample() -> pd.DataFrame:
    df = make_sample()
    numeric = df["ts_code"].str.slice(0, 6).astype(int)
    df["is_pool_all_a"] = True
    df["is_pool_hs300"] = numeric <= 10
    df["is_pool_zz500"] = numeric.between(11, 20)
    df["is_pool_zz1000"] = numeric.between(21, 30)
    df["is_pool_zz2000"] = numeric.between(31, 40)
    df["stock_pool_memberships"] = "全A股"
    df.loc[df["is_pool_hs300"], "stock_pool_memberships"] = "全A股|沪深300"
    df.loc[df["is_pool_zz500"], "stock_pool_memberships"] = "全A股|中证500"
    df.loc[df["is_pool_zz1000"], "stock_pool_memberships"] = "全A股|中证1000"
    df.loc[df["is_pool_zz2000"], "stock_pool_memberships"] = "全A股|中证2000"
    return df


def make_research_sample() -> pd.DataFrame:
    df = make_pool_sample()
    ranks = df.groupby("trade_date")["factor_value"].rank(pct=True, method="average")
    df["factor_component_same_day"] = df["factor_value"]
    df["factor_component_repeat"] = df["factor_value"] * 0.7
    df["factor_component_quality"] = df["factor_value"] * 0.4
    df["factor_component_money"] = df["factor_value"] * 0.3
    df["factor_component_sell_pressure"] = -df["factor_value"] * 0.2
    df["factor_reverse"] = -df["factor_value"]
    df["recent_repeat_agency_count"] = (ranks > 0.65).astype(int)
    df["net_buy_to_amount"] = df["factor_value"] / 100
    df["sell_pressure"] = np.maximum(0, -df["factor_value"] / 100)
    states = np.where(ranks <= 0.33, "low_position", np.where(ranks < 0.67, "mid_position", "high_position"))
    df["position_state"] = states
    df["high_position_risk"] = ranks > 0.92
    df["signal"] = np.where(ranks >= 0.80, "buy", np.where(ranks >= 0.60, "watch", "hold"))
    df["ret_oc_t1"] = df["forward_return"] * 0.8
    df["ret_oo_t1_t2"] = df["forward_return"] * 0.9
    df["ret_open_t1_close_t2"] = df["forward_return"] * 1.1
    df["ret_cc_t1_t2"] = df["forward_return"]
    df["ret_vwap_t1_t2"] = df["forward_return"] * 0.95
    return df
