---
name: risk_return_metrics
license: GPL-3.0-only
description: |
  Risk/return dossier for ONE symbol over a window: annualized return, volatility, Sharpe, Sortino, max drawdown, Calmar, win-rate. Auto-routes A-share / HK / US by suffix.
  Use when the user asks "how risky / how good is X", or wants 夏普 / 最大回撤 / 年化 over a window.

  **Why:** backed by our own `panda_data` (A-share) / `tqx_data` (HK/US) daily closes — no scraping, no external stats service. It turns a raw close series into the ratios an allocator actually reasons over in one call, instead of the agent hand-writing pandas each time. Metrics are computed on daily log-of-simple returns with 252 trading days/year; a 0-vol or 0-drawdown series yields `null` for the ratio that would divide by zero, never a crash. NOT a multi-stock screener (→ `factor_standardize`) and NOT a signal generator (→ `ma_crossover_signal`).
parameters:
  - {name: stock_code, type: str, required: true, description: "Ticker. A 股 `600519` / `600519.SH` / `000001.SZ`; 港股 `0700.HK`; 美股 `AAPL.NB`. Must match `[A-Za-z0-9._-]+` — Chinese / spaces / punctuation are rejected before any network call."}
  - {name: market, type: str, required: false, default: "auto", enum: ["auto", "cn", "hk", "us"], description: "Market routing. `auto` infers from suffix (`.HK`→hk, `.NB`/`.US`/`.NY`→us, `.SH`/`.SZ`/`.BJ` or bare 6-digit→cn). Pass `cn`/`hk`/`us` to force it."}
  - {name: start_date, type: str, required: false, default: "", description: "Window start, `YYYYMMDD`. Empty → derived from `lookback_days` back from `end_date`."}
  - {name: end_date, type: str, required: false, default: "", description: "Window end, `YYYYMMDD`. Empty → today."}
  - {name: lookback_days, type: int, required: false, default: 250, description: "Trailing trading-day target used ONLY when `start_date` is empty. Calendar buffer is added for weekends/holidays, so the realized sample may differ slightly."}
  - {name: risk_free_rate, type: float, required: false, default: 0.0, description: "Annualized risk-free rate (decimal, e.g. `0.02` = 2%) used in Sharpe / Sortino. Default 0."}
---

# risk_return_metrics

Single-symbol risk/return snapshot across A-share / HK / US. All prices come from our own `panda_data` (A 股) and `tqx_data` (HK / US) daily endpoints. Give it a ticker and a window; get back the standard allocator ratios.

## Output shape (JSON string)

```json
{
  "stock_code": "0700.HK",
  "market": "hk",
  "start_date": "20260101",
  "end_date": "20260526",
  "observations": 98,
  "trading_days_per_year": 252,
  "first_close": 371.2,
  "last_close": 402.0,
  "total_return": 0.0829,
  "annualized_return_cagr": 0.2431,
  "annualized_return_mean": 0.2510,
  "annualized_volatility": 0.2874,
  "sharpe": 0.874,
  "sortino": 1.201,
  "max_drawdown": -0.1532,
  "current_drawdown": -0.0210,
  "calmar": 1.587,
  "win_rate": 0.541,
  "avg_daily_return": 0.00099,
  "downside_deviation": 0.0121,
  "best_day": 0.061,
  "worst_day": -0.058
}
```

## Metric definitions

| Field | Formula |
|-------|---------|
| `total_return` | `last_close / first_close - 1` |
| `annualized_return_cagr` | `(last_close / first_close) ** (252 / observations) - 1` |
| `annualized_return_mean` | `mean(daily_return) * 252` |
| `annualized_volatility` | `std(daily_return, ddof=1) * sqrt(252)` |
| `sharpe` | `(annualized_return_mean - risk_free_rate) / annualized_volatility` |
| `sortino` | `(annualized_return_mean - risk_free_rate) / (downside_std * sqrt(252))` |
| `max_drawdown` | `min(cum / cummax(cum) - 1)`, `cum = cumprod(1 + daily_return)` |
| `current_drawdown` | last value of the drawdown series |
| `calmar` | `annualized_return_cagr / abs(max_drawdown)` |
| `win_rate` | `mean(daily_return > 0)` |

Ratios whose denominator is 0 (flat series, no drawdown, no down-days) return `null`.

## When NOT to use

- Rank / screen many stocks → `factor_standardize`.
- Trend / crossover signal on one stock → `ma_crossover_signal`.
- Relationship between two stocks (相关性 / 对冲 / 配对) → `pair_correlation`.
- Raw OHLCV / minute bars only → `analysis_technical`.

## Why

"How risky is X, and was the return worth it?" is a recurring question that otherwise
means re-deriving Sharpe / max-drawdown / Calmar by hand every time. Folding them into
one panda_data / tqx_data-backed call gives the agent a consistent, cross-market risk
dossier with explicit `null`s for undefined ratios instead of silent NaNs.
