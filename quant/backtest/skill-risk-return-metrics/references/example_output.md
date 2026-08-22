# Example output — risk_return_metrics

Call:

```bash
python scripts/risk_return_metrics.py 0700.HK --start-date 20260101 --end-date 20260526
```

Representative JSON result (values illustrative):

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

Edge cases (return a string, never raise):

- Illegal `stock_code` (Chinese / spaces) → `"Error: 非法 stock_code=… "` before any network call.
- Flat / zero-volatility series → `sharpe`, `sortino`, `calmar` are `null` (denominator 0), no crash.
- Fewer than 3 usable closes → `"Error: … 可用收盘价样本不足 …"`.
