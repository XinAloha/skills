# Validation & Report Templates

Standard templates for fundamental factor validation reports. Every factor analysis should produce these diagnostics.

## Report Structure

```
┌──────────────────────────────────────────────┐
│          Factor Validation Report             │
├──────────────────────────────────────────────┤
│ 1. Factor Overview                            │
│ 2. Descriptive Statistics                      │
│ 3. IC Analysis                                 │
│ 4. Grouped Returns (Deciles)                   │
│ 5. Fama-MacBeth Regression                     │
│ 6. IC Decay / Half-Life                        │
│ 7. Sub-Sample Stability                        │
│ 8. Visualizations                              │
│ 9. Conclusion & Recommendation                 │
└──────────────────────────────────────────────┘
```

## 1. Factor Overview

```markdown
## Factor: EP (Earnings Yield)

**Formula**: net_profit_parent_ttm / market_cap  
**Category**: Value  
**Data Period**: 2024Q4 financials → Factor date: 2025-01-15  
**Universe**: All A-shares (ex-ST, ex-financial, ex-IPO < 1yr)  
**N stocks**: 4,523

**Rationale**: Stocks with higher earnings relative to price (cheaper) outperform.
```

## 2. Descriptive Statistics

```markdown
### Descriptive Statistics

| Stat | EP | EP_z |
|------|-----|------|
| Mean | 0.042 | 0.00 |
| Median | 0.038 | 0.05 |
| Std | 0.065 | 1.00 |
| Min | -0.35 | -3.00 |
| Max | 0.22 | 3.00 |
| Skew | -0.85 | 0.12 |
| Pct Positive | 72.3% | — |
| N | 4,365 | 4,365 |
```

## 3. IC Analysis

### Single-Period IC

```markdown
### IC (Rank Correlation)

| Metric | Value | Benchmark |
|--------|-------|-----------|
| Mean Rank IC (1d) | 0.032 | > 0.02 = meaningful |
| Std IC | 0.071 | |
| IC IR | 0.45 | > 0.3 = decent |
| t-stat | 2.85 | > 2.0 = significant |
| Positive IC Ratio | 58.2% | > 55% = consistent |
```

### IC Distribution (Histogram Required)

The daily IC should be roughly normally distributed around the mean. A fat left tail = crash risk.

## 4. Grouped Returns

```markdown
### Decile Returns (Equal-Weighted, 1-day Forward)

| Decile | Mean Return | Cumulative | t-stat |
|--------|-------------|------------|--------|
| Q1 (Low EP) | -0.028% | -7.1% | -1.52 |
| Q2 | -0.012% | -3.0% | -0.81 |
| Q3 | 0.001% | 0.3% | 0.07 |
| Q4 | 0.014% | 3.5% | 1.12 |
| Q5 | 0.023% | 5.8% | 1.89 |
| Q6 | 0.031% | 7.8% | 2.45 |
| Q7 | 0.042% | 10.6% | 2.98 |
| Q8 | 0.051% | 12.9% | 3.21 |
| Q9 | 0.060% | 15.2% | 3.45 |
| Q10 (High EP) | **0.075%** | **19.0%** | **3.78** |
| **LS Spread** | **0.103%** | **26.1%** | **3.52** |
```

### Monotonicity Diagnostics

| Metric | Value |
|--------|-------|
| Strictly monotonic up? | Yes |
| Q1-Q10 gap | 103 bp / day |
| Q1-Q10 Sharpe (annualized) | 1.85 |

### Visualization Check
```
Q1   Q2   Q3   Q4   Q5   Q6   Q7   Q8   Q9   Q10
▲    ▲    ▲    ▲    ▲    ▲    ▲    ▲    ▲    ▲
|    |    |    |    |    |    |    |    |    |
−2bp  0bp  2bp  4bp  6bp  8bp
(All deciles should be monotonically increasing for clean factor)
```

## 5. Fama-MacBeth Regression

```markdown
### Fama-MacBeth Cross-Sectional Regression

**Specification**: return_{t+1} ~ α + β₁·EP_z + β₂·market_cap_z + β₃·BM_z

| Variable | Coef | t-stat | Sig | Positive Pct |
|----------|------|--------|-----|-------------|
| Intercept | 0.012% | 0.85 | | 52% |
| **EP_z** | **0.042%** | **2.15** | ** | **58%** |
| market_cap_z | -0.008% | -1.12 | | 44% |
| BM_z | 0.018% | 0.92 | | 55% |

* p<0.10 | ** p<0.05 | *** p<0.01

**Interpretation**: EP has significant explanatory power for returns even after controlling for size and book-to-market. The coefficient implies 1 std increase in EP → +4.2 bp next-day return (≈10.5% annualized).
```

## 6. IC Decay

```markdown
### IC Decay / Half-Life

| Horizon | Mean IC | IR | Annualized Return | Degradation |
|---------|---------|----|--------------------|-------------|
| 1d | 0.032 | 0.45 | 8.1% | — |
| 5d | 0.028 | 0.38 | 7.1% | 12.5% |
| 10d | 0.022 | 0.29 | 5.6% | 31.3% |
| 20d (1M) | 0.015 | 0.18 | 3.8% | 53.1% |
| 60d (3M) | 0.008 | 0.09 | 2.0% | 75.0% |

**Half-Life**: ~15 trading days (3 weeks)
**Optimal Rebalance**: Weekly

**Interpretation**: Fundamental factors decay faster than price factors because the signal resets only at earnings announcements (quarterly). The decay is mostly due to information being impounded into prices over time.
```

## 7. Sub-Sample Stability

```markdown
### Sub-Sample Analysis (6-month windows)

| Period | L/S Spread | Mean IC | t-stat | Monotonic |
|--------|-----------|---------|--------|-----------|
| 2024 H1 | 0.095% | 0.030 | 2.45 | Yes |
| 2024 H2 | 0.110% | 0.035 | 3.01 | Yes |
| 2023 H1 | 0.082% | 0.025 | 1.85 | Yes |
| 2023 H2 | 0.098% | 0.031 | 2.62 | Yes |
| 2022 H1 | 0.075% | 0.022 | 1.65 | Partial |
| 2022 H2 | 0.088% | 0.028 | 2.12 | Yes |

**Stable across periods?** Yes, all periods show positive L/S spread. The factor works in both bull and bear markets (2022 was down market).
```

## 8. Visualizations Checklist

For each factor, produce:

1. **IC Time Series** — Daily IC with rolling 20-day mean
2. **IC Distribution** — Histogram with normal curve overlay
3. **Decile Bar Chart** — Average return per decile (should be monotonically increasing)
4. **Cumulative L/S** — Cumulative return of top decile minus bottom decile
5. **IC Decay Curve** — IC at each forward horizon
6. **Fama-MacBeth Coefficients** — Time series of regression coefficients
7. **Sub-Sample Heatmap** — IC by year/quarter

### Example: IC Time Series Chart

```
IC  0.15 ┤         ╱╲
    0.10 ┤       ╱╱ ╲╲      ╱╲
    0.05 ┤╱╲   ╱╱    ╲╲   ╱╱  ╲╲
    0.00 ┤╱ ╲ ╱╱       ╲╲╱╱     ╲
   -0.05 ┤    ╱╱           ╲╲
   -0.10 ┤  ╱╱               ╲╲
         └─────────────────────────
          Jan  Feb  Mar  Apr  May  Jun
```

## 9. Conclusion

```markdown
## Conclusion

### Factor: EP (Earnings Yield)

| Criterion | Verdict | Notes |
|-----------|---------|-------|
| IC positive & significant | ✅ | Mean IC 0.032, t=2.85 |
| Monotonic deciles | ✅ | Strictly monotonic |
| Stable across periods | ✅ | 6/6 periods positive |
| Controls for size/bm | ✅ | FM regression significant |
| IC decay reasonable | ✅ | Half-life ~15 days |
| No known bugs | ✅ | Clean computation |

**Recommendation**: ✅ USE as a standalone factor. Combine with BP and CP for a value composite. Address negative-EP handling for robust ranking.

**Suggested Next Step**: Test Value+Quality composite and compare to individual factors.
```

## Quick Reference: Warning Signs

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| IC on single date is extremely high (> 0.2) | Look-ahead bias | Check date alignment |
| Only top and bottom groups show spread | Non-linear relationship | Try quintiles, not deciles |
| 2022 performance breaks | Regime shift (rate hikes) | Sub-sample analysis |
| Q1 returns higher than Q10 sometimes | Inversion | Check if short-leg issue |
| Fama-MacBeth t-stat < 0.5 | Weak factor | Try more controls |
| IC positive but grouped returns don't increase | Monotonicity violation | Check for outliers in mid-groups |
