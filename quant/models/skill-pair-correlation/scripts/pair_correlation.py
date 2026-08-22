"""``pair_correlation`` skill — two-symbol relationship snapshot.

Return correlation (full + recent), hedge beta (A on B), and the latest
log-spread z-score for pairs / mean-reversion. Each leg is routed to our own
``panda_data`` (A 股) / ``tqx_data`` (港股 / 美股) endpoints independently, then
the two close series are inner-joined on shared trading dates before any stat.

Self-contained (same principle as ``fx_rates`` / ``risk_return_metrics``).
"""
from __future__ import annotations

import json
import logging
import math
import re
from datetime import date, timedelta

logger = logging.getLogger(__name__)

_SYMBOL_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_HK_SUFFIX = ".HK"
_US_SUFFIXES = (".NB", ".US", ".NY")
_CN_SUFFIXES = (".SH", ".SZ", ".BJ")
_FIELDS = ["open", "close", "high", "low", "volume", "pre_close"]


def _resolve_market(code: str, declared: str) -> str | None:
    m = (declared or "auto").strip().lower()
    if m in ("cn", "hk", "us"):
        return m
    if m and m != "auto":
        return None
    u = code.upper()
    if u.endswith(_HK_SUFFIX):
        return "hk"
    if u.endswith(_US_SUFFIXES):
        return "us"
    if u.endswith(_CN_SUFFIXES):
        return "cn"
    if re.fullmatch(r"\d{6}", u):
        return "cn"
    return None


def _to_us_symbol(code: str) -> str:
    u = code.upper()
    for suf in (".US", ".NY"):
        if u.endswith(suf):
            return code[: -len(suf)] + ".NB"
    return code


def _fetch_daily(code: str, market: str, start_date: str, end_date: str):
    if market == "cn":
        import panda_data  # type: ignore[import-untyped]

        return panda_data.get_market_data(
            symbol=[code],
            start_date=start_date,
            end_date=end_date,
            type="stock",
            fields=_FIELDS,
        )
    if market == "hk":
        import tqx_data  # type: ignore[import-untyped]

        return tqx_data.get_hk_daily(
            symbol=[code], start_date=start_date, end_date=end_date, fields=_FIELDS
        )
    import tqx_data  # type: ignore[import-untyped]

    return tqx_data.get_us_daily(
        symbol=[_to_us_symbol(code)],
        start_date=start_date,
        end_date=end_date,
        fields=_FIELDS + ["amount"],
    )


def _clean_close_series(df):
    import pandas as pd  # noqa: PLC0415

    if df is None or not hasattr(df, "empty") or df.empty:
        return None
    if "close" not in df.columns:
        return None
    work = df.copy()
    if "date" in work.columns:
        work = work.sort_values("date")
        idx = work["date"].astype(str).tolist()
    else:
        idx = [str(i) for i in range(len(work))]
    close = pd.to_numeric(work["close"], errors="coerce")
    close.index = idx
    return close.dropna()


def _finite(x, n: int = 6):
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(xf):
        return None
    return round(xf, n)


def _corr(a, b):
    """Pearson correlation of two aligned return Series, or None if degenerate."""
    if a is None or b is None or len(a) < 3:
        return None
    if float(a.std(ddof=1) or 0) == 0 or float(b.std(ddof=1) or 0) == 0:
        return None
    c = float(a.corr(b))
    return c if math.isfinite(c) else None


def _fetch_leg(code_raw: str, market_raw: str, start: str, end: str, label: str):
    """Return (close_series, resolved_market, None) or (None, None, error_str)."""
    code = (code_raw or "").strip()
    if not code:
        return None, None, f"Error: {label} 不能为空"
    if not _SYMBOL_RE.match(code):
        return None, None, (
            f"Error: 非法 {label}={code!r}: 只允许字母/数字/`.`/`_`/`-`。"
            "示例: A 股 `600519`；港股 `0700.HK`；美股 `AAPL.NB`。"
        )
    resolved = _resolve_market(code, market_raw)
    if resolved not in ("cn", "hk", "us"):
        return None, None, (
            f"Error: 无法为 {label}={code!r} 推断市场，请显式传 cn/hk/us 或加后缀。"
        )
    try:
        df = _fetch_daily(code, resolved, start, end)
    except ImportError as exc:
        pkg = "panda_data" if resolved == "cn" else "tqx_data"
        return None, None, f"Error: 数据源 {pkg} 未安装/不可用: {exc}"
    except Exception as exc:
        return None, None, f"Error: 获取 {label} 日线失败 (symbol={code}): {exc}"
    close = _clean_close_series(df)
    if close is None or close.shape[0] < 3:
        return None, None, (
            f"Error: {label}={code} 在 {start}~{end} 内样本不足（需 ≥3 条）。"
        )
    return close, resolved, None


def _default_window(lookback_days: int, end_date: str) -> tuple[str, str]:
    end = end_date.strip() if end_date else date.today().strftime("%Y%m%d")
    try:
        end_dt = date(int(end[0:4]), int(end[4:6]), int(end[6:8]))
    except (ValueError, IndexError):
        end_dt = date.today()
        end = end_dt.strftime("%Y%m%d")
    buffer_days = int(max(lookback_days, 5) * 1.6) + 15
    start = (end_dt - timedelta(days=buffer_days)).strftime("%Y%m%d")
    return start, end


async def run(
    stock_code_a: str,
    stock_code_b: str,
    market_a: str = "auto",
    market_b: str = "auto",
    start_date: str = "",
    end_date: str = "",
    lookback_days: int = 250,
    zscore_window: int = 60,
) -> str:
    try:
        import numpy as np  # noqa: PLC0415
        import pandas as pd  # noqa: PLC0415

        try:
            lookback = max(int(lookback_days), 5)
        except (TypeError, ValueError):
            lookback = 250
        try:
            zwin = max(int(zscore_window), 5)
        except (TypeError, ValueError):
            zwin = 60

        start = start_date.strip() if start_date else ""
        end = end_date.strip() if end_date else ""
        if not start:
            start, end = _default_window(lookback, end)
        elif not end:
            end = date.today().strftime("%Y%m%d")

        close_a, mkt_a, err_a = _fetch_leg(stock_code_a, market_a, start, end, "stock_code_a")
        if err_a:
            return err_a
        close_b, mkt_b, err_b = _fetch_leg(stock_code_b, market_b, start, end, "stock_code_b")
        if err_b:
            return err_b

        # Inner-join on shared trading dates BEFORE any statistic.
        joined = pd.concat(
            {"a": close_a, "b": close_b}, axis=1, join="inner"
        ).dropna()
        if joined.shape[0] < 3:
            return (
                f"Error: 两标的在 {start}~{end} 内的共同交易日不足（对齐后 "
                f"{int(joined.shape[0])} 条，需 ≥3）。可能是跨市场交易日历差异，请放宽区间。"
            )

        ret = joined.pct_change().dropna()
        ret_a, ret_b = ret["a"], ret["b"]

        correlation = _corr(ret_a, ret_b)
        corr_20 = _corr(ret_a.tail(20), ret_b.tail(20)) if ret_a.shape[0] >= 20 else None
        corr_60 = _corr(ret_a.tail(60), ret_b.tail(60)) if ret_a.shape[0] >= 60 else None

        var_b = float(ret_b.var(ddof=1)) if ret_b.shape[0] > 1 else 0.0
        cov_ab = float(ret_a.cov(ret_b)) if ret_a.shape[0] > 1 else 0.0
        beta = (cov_ab / var_b) if var_b != 0 else None

        # Log-spread z-score. Needs positive prices for ln; guard just in case.
        spread_z = None
        pa, pb = joined["a"], joined["b"]
        if beta is not None and float(pa.min()) > 0 and float(pb.min()) > 0:
            spread = np.log(pa) - beta * np.log(pb)
            tail = spread.tail(min(zwin, spread.shape[0]))
            s_std = float(tail.std(ddof=1)) if tail.shape[0] > 1 else 0.0
            if s_std != 0:
                spread_z = (float(spread.iloc[-1]) - float(tail.mean())) / s_std

        last_a = float(pa.iloc[-1])
        last_b = float(pb.iloc[-1])

        result = {
            "stock_code_a": (stock_code_a or "").strip(),
            "stock_code_b": (stock_code_b or "").strip(),
            "market_a": mkt_a,
            "market_b": mkt_b,
            "start_date": start,
            "end_date": end,
            "aligned_observations": int(joined.shape[0]),
            "correlation": _finite(correlation),
            "correlation_recent_20": _finite(corr_20),
            "correlation_recent_60": _finite(corr_60),
            "beta_a_on_b": _finite(beta),
            "hedge_ratio": _finite(beta),
            "spread_zscore": _finite(spread_z, 4),
            "spread_zscore_window": int(min(zwin, joined.shape[0])),
            "last_close_a": _finite(last_a),
            "last_close_b": _finite(last_b),
            "price_ratio": _finite(last_a / last_b) if last_b != 0 else None,
            "interpretation_hint": (
                "z<-2 → A 相对 B 偏低（做多 A / 做空 B 的均值回归setup）；z>2 → 反向。"
            ),
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        logger.error("[skill pair_correlation] error=%s", exc, exc_info=True)
        return f"Error: {type(exc).__name__}: {exc}"


if __name__ == "__main__":
    import argparse
    import asyncio

    ap = argparse.ArgumentParser(description="pair_correlation skill — standalone runner")
    ap.add_argument("stock_code_a")
    ap.add_argument("stock_code_b")
    ap.add_argument("--market-a", default="auto", choices=["auto", "cn", "hk", "us"])
    ap.add_argument("--market-b", default="auto", choices=["auto", "cn", "hk", "us"])
    ap.add_argument("--start-date", default="")
    ap.add_argument("--end-date", default="")
    ap.add_argument("--lookback-days", type=int, default=250)
    ap.add_argument("--zscore-window", type=int, default=60)
    a = ap.parse_args()
    print(asyncio.run(run(a.stock_code_a, a.stock_code_b, a.market_a, a.market_b,
                          a.start_date, a.end_date, a.lookback_days, a.zscore_window)))
