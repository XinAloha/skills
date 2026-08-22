"""
data_source.py — Pandadata 适配层（交易成本分析 TCA）

三层回退策略（与组织样板一致）：
  1) 生产环境：`import panda_data` SDK 直连（组织标准）。
  2) 无 SDK 时：回退到 examples 内置样本，保证离线可跑 demo。
  3) 显式 `--prefer sample`：强制用样本（复现/演示）。

所有接口日期格式 YYYYMMDD；symbol 传 "" 表示全市场。

本 Skill 用到的接口：
  - get_stock_min(start_date, end_date, symbol, frequency='1m'/'5m'/'15m'/'60m')
      返回 records: {date, minute, datetime, symbol, open, close, high, low,
                     volume, amount, num_trades}
  - get_stock_daily(start_date, end_date, symbol, st=True)
      返回 {date, symbol, name, open, close, high, low, volume, amount,
            pre_close, trade_status}
  - get_hk_daily / get_us_daily —— 港美股日线，自带 vwap/bid/ask 字段。
"""
from __future__ import annotations
import json
from pathlib import Path

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "examples" / "sample_data"


# ---------------------------------------------------------------------------
# 后端探测
# ---------------------------------------------------------------------------
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
    # SDK 可能返回 DataFrame 或 list[dict]，两种都要能处理
    try:
        import pandas as pd
        if isinstance(res, pd.DataFrame):
            return res.to_dict("records")
    except Exception:
        pass
    if isinstance(res, list):
        return res
    if isinstance(res, dict) and "result" in res:
        return res["result"]
    return []


def _sample_available() -> bool:
    return SAMPLE_DIR.exists()


def _call_sample(method: str, **params) -> list[dict]:
    """从内置样本读取；按 symbol 过滤（若样本含 symbol 列且调用指定了 symbol）。"""
    f = SAMPLE_DIR / f"{method}.json"
    if not f.exists():
        return []
    rows = json.loads(f.read_text(encoding="utf-8"))
    symbol = params.get("symbol")
    if symbol and rows and "symbol" in rows[0]:
        syms = [symbol] if isinstance(symbol, str) else list(symbol)
        rows = [r for r in rows if r.get("symbol") in syms]
    return rows


# ---------------------------------------------------------------------------
# 统一取数入口
# ---------------------------------------------------------------------------
class DataSource:
    def __init__(self, prefer: str | None = None):
        # prefer: "sdk" | "sample" | None(自动)
        if prefer == "sample":
            self.backend = "sample"
        elif prefer == "sdk" or _sdk_available():
            self.backend = "sdk"
        elif _sample_available():
            self.backend = "sample"
        else:
            self.backend = "none"

    def fetch(self, method: str, **params) -> list[dict]:
        if self.backend == "sdk":
            try:
                return _call_sdk(method, **params)
            except Exception as e:  # noqa: BLE001
                # 单接口失败不应中断整轮分析，返回空并让上层记降级
                print(f"[data_source] SDK {method} failed: {e}")
                return []
        if self.backend == "sample":
            return _call_sample(method, **params)
        return []

    # --- 行情源语义化封装 ---
    def stock_min(self, symbol, start, end, frequency="5m"):
        """A 股分钟线：用于重建成交区间 VWAP/TWAP、波动率、ADV。"""
        return self.fetch("get_stock_min", start_date=start, end_date=end,
                          symbol=symbol, frequency=frequency)

    def stock_daily(self, symbol, start, end):
        """A 股日线：用于估 ADV（近 N 日均量）与决策价代理。"""
        return self.fetch("get_stock_daily", start_date=start, end_date=end,
                          symbol=symbol, st=True)

    def hk_daily(self, symbol, start, end):
        """港股日线：自带 vwap/bid/ask，可提升点差与基准精度。"""
        return self.fetch("get_hk_daily", start_date=start, end_date=end, symbol=symbol)

    def us_daily(self, symbol, start, end):
        """美股日线：自带 vwap/bid/ask。"""
        return self.fetch("get_us_daily", start_date=start, end_date=end, symbol=symbol)
