# Methodology

## Families tested

- Weekday
- Calendar month
- Month-start / month-end
- Turn-of-month window (month-end + first 3 sessions)

## Statistics

- Bucket-vs-complement mean contrast
- Classical and **Newey–West HAC t** for the same dummy-regression contrast
- Moving-block residual Bootstrap p, reported separately
- **Benjamini–Hochberg q-values** based only on HAC p-values across all buckets
- Chronological half-sample same-sign contrast robustness

## Verdict ladder

1. `ROBUST_ANOMALY` — BH significant **and** half-sample robust
2. `ANOMALY_AFTER_FDR` — BH significant only
3. `RAW_ONLY_ANOMALY` — raw |t|≥2 but fails FDR
4. `NO_CLEAR_ANOMALY`

## Limits

- Calendar effects are heavily mined historically; FDR is necessary but not sufficient.
- Does not prove exploitability after costs.
