"""``risk_return_metrics`` skill — single-symbol risk/return dossier.

Cross-market (A 股 / 港股 / 美股) daily closes via our own ``panda_data`` /
``tqx_data`` endpoints, folded into the standard allocator ratios (annualized
return, volatility, Sharpe, Sortino, max drawdown, Calmar, win-rate).

Self-contained on purpose (same principle as ``fx_rates``): the symbol/market
routing and the metric math live here, no cross-skill import — so the package
stays independently valid and easy to reason about.
"""
from __future__ import annotations

import json
import logging
import math
import re
from datetime import date, timedelta

logger = logging.getLogger(__name__)

_SYMBOL_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_TRADING_DAYS = 252
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
    """tqx_data 美股后端只认 .NB；把 .US / .NY 归一化成 .NB。"""
    u = code.upper()
    for suf in (".US", ".NY"):
        if u.endswith(suf):
            return code[: -len(suf)] + ".NB"
    return code


def _fetch_daily(code: str, market: str, start_date: str, end_date: str):
    """Return a DataFrame (date/close/…) or raise. Import is lazy per market."""
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
    """Sorted-ascending float close Series (index = date str), NaN dropped."""
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


def _finite(x):
    """Round to 6dp when finite, else None (keeps JSON free of NaN/Inf)."""
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(xf):
        return None
    return round(xf, 6)


def _safe_div(num, den):
    if den in (0, 0.0) or den is None:
        return None
    try:
        return num / den
    except ZeroDivisionError:
        return None


def _compute(close, rf: float) -> dict:
    ret = close.pct_change().dropna()
    n = int(ret.shape[0])
    first_close = float(close.iloc[0])
    last_close = float(close.iloc[-1])

    total_return = _safe_div(last_close, first_close)
    total_return = (total_return - 1.0) if total_return is not None else None

    cagr = None
    if first_close > 0 and n > 0:
        cagr = (last_close / first_close) ** (_TRADING_DAYS / n) - 1.0

    mean_daily = float(ret.mean()) if n else 0.0
    ann_return_mean = mean_daily * _TRADING_DAYS
    std_daily = float(ret.std(ddof=1)) if n > 1 else 0.0
    ann_vol = std_daily * math.sqrt(_TRADING_DAYS)

    sharpe = _safe_div(ann_return_mean - rf, ann_vol)

    downside = ret[ret < 0]
    downside_std = float(downside.std(ddof=1)) if downside.shape[0] > 1 else 0.0
    sortino = _safe_div(ann_return_mean - rf, downside_std * math.sqrt(_TRADING_DAYS))

    cum = (1.0 + ret).cumprod()
    running_max = cum.cummax()
    dd = cum / running_max - 1.0
    max_dd = float(dd.min()) if n else 0.0
    current_dd = float(dd.iloc[-1]) if n else 0.0
    calmar = _safe_div(cagr, abs(max_dd)) if (cagr is not None and max_dd != 0) else None

    win_rate = float((ret > 0).mean()) if n else None
    best_day = float(ret.max()) if n else None
    worst_day = float(ret.min()) if n else None

    return {
        "observations": n,
        "trading_days_per_year": _TRADING_DAYS,
        "first_close": _finite(first_close),
        "last_close": _finite(last_close),
        "total_return": _finite(total_return),
        "annualized_return_cagr": _finite(cagr),
        "annualized_return_mean": _finite(ann_return_mean),
        "annualized_volatility": _finite(ann_vol),
        "sharpe": _finite(sharpe),
        "sortino": _finite(sortino),
        "max_drawdown": _finite(max_dd),
        "current_drawdown": _finite(current_dd),
        "calmar": _finite(calmar),
        "win_rate": _finite(win_rate),
        "avg_daily_return": _finite(mean_daily),
        "downside_deviation": _finite(downside_std),
        "best_day": _finite(best_day),
        "worst_day": _finite(worst_day),
    }


def _default_window(lookback_days: int, end_date: str) -> tuple[str, str]:
    end = end_date.strip() if end_date else date.today().strftime("%Y%m%d")
    try:
        end_dt = date(int(end[0:4]), int(end[4:6]), int(end[6:8]))
    except (ValueError, IndexError):
        end_dt = date.today()
        end = end_dt.strftime("%Y%m%d")
    # Calendar buffer so weekends/holidays still leave ~lookback_days trading rows.
    buffer_days = int(max(lookback_days, 5) * 1.6) + 15
    start = (end_dt - timedelta(days=buffer_days)).strftime("%Y%m%d")
    return start, end


async def run(
    stock_code: str,
    market: str = "auto",
    start_date: str = "",
    end_date: str = "",
    lookback_days: int = 250,
    risk_free_rate: float = 0.0,
) -> str:
    try:
        code = (stock_code or "").strip()
        if not code:
            return "Error: stock_code 不能为空"
        if not _SYMBOL_RE.match(code):
            return (
                f"Error: 非法 stock_code={code!r}: 只允许字母/数字/`.`/`_`/`-`，"
                "不能含中文/空格/其它特殊字符。示例: A 股 `600519` / `600519.SH`；"
                "港股 `0700.HK`；美股 `AAPL.NB`。"
            )

        resolved = _resolve_market(code, market)
        if resolved not in ("cn", "hk", "us"):
            return (
                f"Error: market={market!r} 不合法且无法从 stock_code 推断市场。"
                "请显式传 `cn`/`hk`/`us`，或给 stock_code 加 .HK / .NB 后缀。"
            )

        try:
            lookback = max(int(lookback_days), 5)
        except (TypeError, ValueError):
            lookback = 250
        try:
            rf = float(risk_free_rate)
        except (TypeError, ValueError):
            rf = 0.0

        start = start_date.strip() if start_date else ""
        end = end_date.strip() if end_date else ""
        if not start:
            start, end = _default_window(lookback, end)
        elif not end:
            end = date.today().strftime("%Y%m%d")

        try:
            df = _fetch_daily(code, resolved, start, end)
        except ImportError as exc:
            pkg = "panda_data" if resolved == "cn" else "tqx_data"
            return f"Error: 数据源 {pkg} 未安装/不可用: {exc}"
        except Exception as exc:
            return f"Error: 获取日线失败 (market={resolved}, symbol={code}): {exc}"

        close = _clean_close_series(df)
        if close is None or close.shape[0] < 3:
            got = 0 if close is None else int(close.shape[0])
            return (
                f"Error: {code} 在 {start}~{end} 内可用收盘价样本不足（得到 {got} 条，"
                "至少需要 3 条）。请放宽日期区间或确认代码/市场。"
            )

        result = {
            "stock_code": code,
            "market": resolved,
            "start_date": start,
            "end_date": end,
        }
        result.update(_compute(close, rf))
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:  # 兜底：任何未预期异常都吞成 Error 字符串，绝不抛
        logger.error("[skill risk_return_metrics] error=%s", exc, exc_info=True)
        return f"Error: {type(exc).__name__}: {exc}"


if __name__ == "__main__":
    # Standalone runner (satisfies the community "Runnable" check). Without
    # panda_data / tqx_data installed the skill returns a structured Error
    # string rather than crashing.
    import argparse
    import asyncio

    ap = argparse.ArgumentParser(description="risk_return_metrics skill — standalone runner")
    ap.add_argument("stock_code", help="e.g. 600519.SH / 0700.HK / AAPL.NB")
    ap.add_argument("--market", default="auto", choices=["auto", "cn", "hk", "us"])
    ap.add_argument("--start-date", default="")
    ap.add_argument("--end-date", default="")
    ap.add_argument("--lookback-days", type=int, default=250)
    ap.add_argument("--risk-free-rate", type=float, default=0.0)
    a = ap.parse_args()
    print(asyncio.run(run(a.stock_code, a.market, a.start_date, a.end_date,
                          a.lookback_days, a.risk_free_rate)))
