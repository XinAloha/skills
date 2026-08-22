---
name: pair_correlation
license: GPL-3.0-only
description: |
  Relationship between TWO symbols: return correlation (full + recent 20/60d), hedge beta (A on B), latest log-spread z-score for pairs / mean-reversion. Auto-routes each leg A-share / HK / US.
  Use when the user asks 相关性 / 对冲比例 / 配对交易 / 价差 between two names, or "do X and Y move together".

  **Why:** backed by our own `panda_data` (A-share) / `tqx_data` (HK/US) daily closes — each leg is routed independently, so cross-market pairs (e.g. `0700.HK` vs `BABA.NB`) work. The two series are inner-joined on common trading dates BEFORE any stat, so a mismatched calendar or a halt day can't silently misalign returns. Correlation uses daily simple returns; beta = cov(A,B)/var(B); spread = ln(Pa) − beta·ln(Pb), z-scored over `zscore_window`. A degenerate leg (0 variance) yields `null` for beta/z, never a crash. NOT single-name risk (→ `risk_return_metrics`).
parameters:
  - {name: stock_code_a, type: str, required: true, description: "First ticker (the one you'd be LONG in a spread). A 股 `600519`; 港股 `0700.HK`; 美股 `AAPL.NB`. `[A-Za-z0-9._-]+` only — rejected before any network call otherwise."}
  - {name: stock_code_b, type: str, required: true, description: "Second ticker (the hedge / SHORT leg). Same format rules as `stock_code_a`."}
  - {name: market_a, type: str, required: false, default: "auto", enum: ["auto", "cn", "hk", "us"], description: "Market routing for leg A. `auto` infers from suffix; pass `cn`/`hk`/`us` to force."}
  - {name: market_b, type: str, required: false, default: "auto", enum: ["auto", "cn", "hk", "us"], description: "Market routing for leg B. Same as `market_a`."}
  - {name: start_date, type: str, required: false, default: "", description: "Window start `YYYYMMDD`. Empty → derived from `lookback_days`."}
  - {name: end_date, type: str, required: false, default: "", description: "Window end `YYYYMMDD`. Empty → today."}
  - {name: lookback_days, type: int, required: false, default: 250, description: "Trailing trading-day target used only when `start_date` is empty (calendar buffer added)."}
  - {name: zscore_window, type: int, required: false, default: 60, description: "Trailing observations used to mean/std the log-spread for `spread_zscore`. Capped at the aligned sample length."}
---

# pair_correlation

Two-symbol relationship snapshot for pairs / hedging / 相关性 questions, across and within A-share / HK / US. Each leg's daily closes come from our own `panda_data` (A 股) / `tqx_data` (HK / US) endpoints and are **inner-joined on shared trading dates** before any statistic is computed.

## Output shape (JSON string)

```json
{
  "stock_code_a": "0700.HK",
  "stock_code_b": "9988.HK",
  "market_a": "hk",
  "market_b": "hk",
  "start_date": "20260101",
  "end_date": "20260526",
  "aligned_observations": 96,
  "correlation": 0.712,
  "correlation_recent_20": 0.664,
  "correlation_recent_60": 0.731,
  "beta_a_on_b": 0.884,
  "hedge_ratio": 0.884,
  "spread_zscore": -1.83,
  "spread_zscore_window": 60,
  "last_close_a": 402.0,
  "last_close_b": 78.5,
  "price_ratio": 5.121,
  "interpretation_hint": "z<-2 → A cheap vs B (long A / short B mean-revert setup); z>2 → reverse."
}
```

## Definitions

| Field | Formula |
|-------|---------|
| `correlation` | Pearson corr of daily simple returns over the full aligned window |
| `correlation_recent_20 / _60` | same, on the last 20 / 60 aligned rows (`null` if too few) |
| `beta_a_on_b` / `hedge_ratio` | `cov(ret_a, ret_b) / var(ret_b)` |
| `spread_zscore` | `spread = ln(Pa) − beta·ln(Pb)`; `(spread_last − mean) / std` over `zscore_window` |
| `price_ratio` | `last_close_a / last_close_b` |

Any statistic whose denominator is 0 (a flat leg, `var(ret_b)=0`, `std(spread)=0`) returns `null`.

## When NOT to use

- One stock's risk/return ratios → `risk_return_metrics`.
- Trend / MA crossover on one stock → `ma_crossover_signal`.
- Multi-name factor screening → `factor_standardize`.

## Why

Correlation and hedge beta drive every pair trade and every "are these two names
redundant in my book?" question, but they're error-prone to hand-roll — the classic bug
is comparing two return series that were never aligned on the same dates. This skill does
the inner-join first and returns the hedge ratio plus a ready-to-read spread z-score, so
the agent reasons about the relationship, not the plumbing.
