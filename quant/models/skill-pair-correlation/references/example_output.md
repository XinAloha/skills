# Example output — pair_correlation

Call:

```bash
python scripts/pair_correlation.py 0700.HK 9988.HK --start-date 20260101 --end-date 20260526
```

Representative JSON result (values illustrative):

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
  "interpretation_hint": "z<-2 → A 相对 B 偏低（做多 A / 做空 B 的均值回归setup）；z>2 → 反向。"
}
```

Notes:

- The two legs are inner-joined on shared trading dates first; `aligned_observations`
  is the post-join sample size (cross-market pairs shrink here due to calendar diffs).
- A degenerate leg (`var(ret_b) = 0`, flat spread) → `beta_a_on_b` / `spread_zscore` = `null`.
- Empty / illegal ticker or `<3` aligned rows → a structured `Error: …` string.
