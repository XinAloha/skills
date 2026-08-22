# Composite Factors

Fundamental factors that combine multiple financial metrics into a single composite signal.

## 1. Piotroski F-Score

**Origin**: Piotroski (2000) "Value Investing: The Use of Historical Financial Statement Information"

**Logic**: Score value stocks (high B/M) on 9 binary financial signals. Higher F-Score = stronger fundamentals.

### Computation

| # | Signal | Condition | Score = 1 If |
|---|--------|-----------|-------------|
| **Profitability** | | | |
| 1 | ROE | Positive | `net_profit_parent_ttm > 0` |
| 2 | ROA | Positive | `net_profit_parent_ttm / total_assets > 0` |
| 3 | CFO | Positive | `net_cash_flow_operating_ttm > 0` |
| 4 | Accruals | CFO > Net Income | `net_cash_flow_operating_ttm > net_profit_parent_ttm` |
| **Leverage / Liquidity** | | | |
| 5 | Leverage Change | Decreased | `(total_assets / equity)[t] < (total_assets / equity)[t-1]` |
| 6 | Liquidity Change | Increased | `current_ratio[t] > current_ratio[t-1]` |
| 7 | Equity Offering | No | `total_shares[t] <= total_shares[t-1]` |
| **Operating Efficiency** | | | |
| 8 | Gross Margin Change | Increased | `gross_margin[t] > gross_margin[t-1]` |
| 9 | Asset Turnover Change | Increased | `(revenue / total_assets)[t] > (revenue / total_assets)[t-1]` |

**Total**: 0 (weak) to 9 (strong)

### Pandadata Implementation

```python
def compute_fscore(df_current, df_prev):
    """
    df_current: Current quarter data
    df_prev: One-year-prior quarter data (t-4 quarters)
    """
    points = 0
    
    # 1. Positive ROE
    if df_current['net_profit_parent_ttm'] > 0:
        points += 1
    
    # 2. Positive ROA
    roa = df_current['net_profit_parent_ttm'] / df_current['total_assets_latest']
    if roa > 0:
        points += 1
    
    # 3. Positive CFO
    if df_current['net_cash_flow_operating_ttm'] > 0:
        points += 1
    
    # 4. CFO > Net Income (low accruals)
    if df_current['net_cash_flow_operating_ttm'] > df_current['net_profit_parent_ttm']:
        points += 1
    
    # 5. Leverage decreased
    lev_curr = df_current['total_assets_latest'] / df_current['equity_parent_common_latest']
    lev_prev = df_prev['total_assets_latest'] / df_prev['equity_parent_common_latest']
    if lev_curr < lev_prev:
        points += 1
    
    # 6. Liquidity increased (requires current assets / current liabilities from fina_reports)
    # Skip if data unavailable, or approximate with (total_assets - total_liabilities) / total_assets
    # For simplicity, skip this signal if not available
    
    # 7. No equity offering
    if df_current['total_shares'] <= df_prev['total_shares']:
        points += 1
    
    # 8. Gross margin increased
    gm_curr = df_current['gross_profit_ttm'] / df_current['operating_revenue_ttm']
    gm_prev = df_prev['gross_profit_ttm'] / df_prev['operating_revenue_ttm']
    if gm_curr > gm_prev:
        points += 1
    
    # 9. Asset turnover increased
    at_curr = df_current['operating_revenue_ttm'] / df_current['total_assets_latest']
    at_prev = df_prev['operating_revenue_ttm'] / df_prev['total_assets_latest']
    if at_curr > at_prev:
        points += 1
    
    return points
```

### Interpretation

| F-Score | Label | Expected Performance |
|---------|-------|---------------------|
| 0-2 | Weak | Underperform value universe |
| 3-4 | Below Average | Mixed |
| 5-6 | Average | Neutral |
| 7-8 | Strong | Outperform |
| 9 | Very Strong | Strongly outperform |

**Strategy**: Long high F-Score (8-9) value stocks, short low F-Score (0-2) value stocks.

## 2. Quality Minus Junk (QMJ)

**Origin**: Asness, Frazzini, Pedersen (2019) "Quality Minus Junk"

**Logic**: Quality = profitability + growth + safety + payout. High quality → high returns.

### Computation

```python
def compute_qmj_score(df):
    """
    Composite quality score: average z-score of quality metrics minus junk metrics
    """
    # Profitability (z-score average)
    profitability = zscore_mean([
        df['ROE'],
        df['ROA'],
        df['Gross_Margin'],
        df['Operating_Margin'],
    ])
    
    # Growth (z-score average)
    growth = zscore_mean([
        df['Earnings_Growth'],
        df['Revenue_Growth'],
    ])
    
    # Safety (z-score average, signs inverted for risk metrics)
    safety = zscore_mean([
        -df['Accruals'],     # Negate: low accruals = good
        -df['Leverage'],     # Negate: low leverage = good
        df['CF_Quality'],    # High = good
    ])
    
    # Payout (approximate with past data)
    # payout = dividend_payout_ratio
    
    # QMJ = average
    qmj_score = (profitability + growth + safety) / 3
    
    return qmj_score


def zscore_mean(factors_list):
    """Compute z-score for each factor then average"""
    import numpy as np
    from scipy import stats
    
    z_scores = []
    for f in factors_list:
        z = stats.zscore(f, nan_policy='omit')
        z = np.clip(z, -3, 3)
        z_scores.append(z)
    
    return np.nanmean(z_scores, axis=0)
```

## 3. PEG Ratio

| Field | Value |
|-------|-------|
| **Formula** | `PE / Earnings_Growth_Rate` |
| **Interpretation** | Lower = cheaper growth. PEG < 1 = undervalued |
| **Data** | PE = `market_cap / net_profit_parent_ttm` |

### Limitations
- Not computable for negative earnings
- Not computable for negative growth
- Growth is backward-looking (TTM); forward PEG requires analyst estimates
- Use as a factor, not a hard rule

## 4. GARP (Growth at a Reasonable Price)

**Composition**: Combines value and growth metrics:
```
GARP = z-score(EP) + z-score(BP) + z-score(Earnings_Growth)
```

**Interpretation**: Stocks that are reasonably valued AND growing. Opposite of "value traps" (cheap but stagnant) and "growth at any price."

## 5. Value + Quality Composite

```python
def compute_value_quality(df):
    """
    Value factor: ~EP, BP, CP
    Quality factor: ROE, Gross Margin, low Accruals
    Composite = z-score(value_avg + quality_avg)
    """
    value_avg = (
        df['EP_z'] + df['BP_z'] + df['CP_z']
    ) / 3
    
    quality_avg = (
        df['ROE_z'] + df['Gross_Margin_z'] - df['Accruals_z']
    ) / 3
    
    composite = (value_avg + quality_avg) / 2
    
    return composite
```
