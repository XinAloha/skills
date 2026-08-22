"""
data_source.py — Pandadata 适配层（跨市场资金面/拥挤监测）

三层回退：
  1) 生产：import panda_data SDK 直连（组织标准）。
  2) 无 SDK：回退 examples/sample_data/*.json 内置样本，保证离线可跑。
  3) --prefer sample 强制样本。

接口日期格式 YYYYMMDD；symbol 传 "" 或省略表示全市场。
SDK 返回可能是 DataFrame / list[dict] / {"result":[...]} / gateway dataframe，统一成 list[dict]。
"""
from __future__ import annotations
import json
from pathlib import Path

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "examples" / "sample_data"


def _sdk_available() -> bool:
    try:
        import panda_data  # noqa: F401
        return True
    except Exception:
        return False


def _call_sdk(method: str, **params) -> list[dict]:
    import panda_data
    fn = getattr(panda_data, method)
    res = fn(**params)
    try:
        import pandas as pd
        if isinstance(res, pd.DataFrame):
            return res.to_dict("records")
    except Exception:
        pass
    if isinstance(res, list):
        return res
    if isinstance(res, dict):
        # gateway dataframe 形态: {"type":"dataframe","columns":[...],"rows":[[...]]}
        r = res.get("result", res)
        if isinstance(r, dict) and r.get("type") == "dataframe":
            cols = r.get("columns", [])
            return [dict(zip(cols, row)) for row in r.get("rows", [])]
        if isinstance(r, list):
            return r
    return []


def _call_sample(method: str, **params) -> list[dict]:
    f = SAMPLE_DIR / f"{method}.json"
    if not f.exists():
        return []
    rows = json.loads(f.read_text(encoding="utf-8"))
    symbol = params.get("symbol")
    if symbol and rows and "symbol" in rows[0]:
        syms = [symbol] if isinstance(symbol, str) else list(symbol)
        rows = [r for r in rows if r.get("symbol") in syms]
    return rows


class DataSource:
    def __init__(self, prefer: str | None = None):
        if prefer == "sample":
            self.backend = "sample"
        elif prefer == "sdk" or _sdk_available():
            self.backend = "sdk"
        elif SAMPLE_DIR.exists():
            self.backend = "sample"
        else:
            self.backend = "none"

    def fetch(self, method: str, **params) -> list[dict]:
        if self.backend == "sdk":
            try:
                return _call_sdk(method, **params)
            except Exception as e:  # noqa: BLE001
                print(f"[data_source] SDK {method} failed: {e}")
                return []
        if self.backend == "sample":
            return _call_sample(method, **params)
        return []

    # --- 资金面语义化封装 ---
    def margin(self, symbol, start, end):
        """融资融券：融资余额/融券余额/总余额（杠杆情绪，用余额变化衡量强度）。"""
        return self.fetch("get_margin", symbol=symbol, start_date=start, end_date=end)

    def hsgt_hold(self, symbol, start, end):
        """北向持股：holding_ratio/shares_num（外资/聪明钱，用持股变化衡量加减仓）。"""
        return self.fetch("get_hsgt_hold", symbol=symbol, start_date=start, end_date=end)

    def block_trade(self, symbol, start, end):
        """大宗交易：price/volume/amount/buyer/seller（机构/大股东，折溢价须自算）。"""
        return self.fetch("get_block_trade", symbol=symbol, start_date=start, end_date=end)

    def stock_daily(self, symbol, start, end):
        """个股日线：close（大宗折溢价分母 = 当日收盘价；symbol 可为列表）。"""
        return self.fetch("get_stock_daily", symbol=symbol, start_date=start, end_date=end)

    def industry_constituents(self, industry, start=None, end=None):
        """行业成分股展开。接口参数为 industry_code（不接受 start/end；start/end 仅为调用方兼容保留）。"""
        return self.fetch("get_industry_constituents", industry_code=industry)

    def concept_constituents(self, concept, start=None, end=None):
        """概念成分股展开。接口参数为 concept + 可选 date（不接受 start/end）。"""
        params = {"concept": concept}
        if end:
            params["date"] = end
        return self.fetch("get_concept_constituents", **params)
