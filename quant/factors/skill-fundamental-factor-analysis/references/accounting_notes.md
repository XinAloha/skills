# Accounting Notes: Special Situations in A-Share Fundamental Analysis

## 1. Financial Sector (银行/保险/券商)

Financial institutions have fundamentally different balance sheets:

| Item | Standard Firm | Financial Firm |
|------|---------------|----------------|
| Debt | Liability | Raw material (deposits) |
| Leverage ratio | 1.0-3.0 | 8.0-15.0+ |
| Operating revenue | Product sales | Net interest income + fees |
| Accruals | Earnings quality signal | Less meaningful |
| Total assets | Productive assets | Largely financial assets |
| ROA | 2-10% | 0.5-1.5% |

**Recommendation**: Either:
1. **Exclude** financial sector stocks from factor analysis entirely
2. **Compute z-scores within sector** — normalize financial firms against each other, not against all firms

```python
# Option: Within-sector standardization
sector_financial = ['银行', '保险', '证券', '多元金融']
df['is_financial'] = df['sector_code_name'].isin(sector_financial)
df['sector_group'] = np.where(df['is_financial'], 'financial', 'non_financial')
df['EP_z'] = df.groupby(['date', 'sector_group'])['EP'].transform(
    lambda x: (x - x.mean()) / x.std()
)
```

## 2. ST / *ST Stocks

**Issue**: Special treatment stocks have distorted financials and trading restrictions.

**Handling**:
```python
# Filter out ST stocks
def filter_st_stocks(df):
    return df[~df['name'].str.contains('ST|退市', na=False)]
```

## 3. IPO Effect

**Issue**: Newly listed stocks have:
- Limited historical financial data
- Different return patterns (underpricing, lockup expiration)
- First financial reports may be pre-IPO restated

**Recommendation**: Exclude stocks listed < 12 months.

```python
def filter_ipo(df, min_months=12):
    df = df.copy()
    listed_date_col = 'listed_date'  # from get_stock_detail
    df['months_listed'] = (
        pd.to_datetime('today') - pd.to_datetime(df[listed_date_col])
    ) / pd.Timedelta(days=30)
    return df[df['months_listed'] >= min_months]
```

## 4. Seasonal Adjustments

**Issue**: Quarterly data has strong seasonality:
- Q4 typically has highest revenue (year-end sales)
- Q1 earnings may be lower (CNY holiday)
- Interim reports may be unaudited (Q1, Q3), annual is audited (Q4)

**Solution**: Always use TTM (trailing 12 months) for income statement items, or YoY growth (compare same quarter year-over-year).

## 5. Restated Financials

**Issue**: Companies restate prior-year financials, creating breaks in the time series.

**Pandadata Parameter**: `if_adjusted` in `get_fina_reports`
- `if_adjusted=0`: Current-period reported data
- `if_adjusted=1`: Adjusted data (back-filled restatements)

**Recommendation**: Use `if_adjusted=1` for backtesting (avoids look-ahead from restatements), but flag this in the report.

## 6. Sector Z-Score Normalization

Many fundamental factors are sector-dependent. Always consider within-sector z-scoring:

| Factor | Recommended Normalization |
|--------|-------------------------|
| EP, BP, SP, CP | Cross-section or within-sector |
| Gross Margin | **Must** be within-sector (margins vary 10x across sectors) |
| ROE | Cross-section or within-sector |
| Leverage | **Must** be within-sector (banks vs tech) |
| Earnings Growth | Cross-section (growth is comparable across sectors) |
| Revenue Growth | Cross-section or within-sector |
| PEG | Cross-section with sector filter |

## 7. Data Lag and Look-Ahead Bias

**The most common bug in fundamental factor research.**

**Timeline**: Q4 ends Dec 31 → Q4 report published by April 30 (A-share rules)

| Quarter | Report End Date | Latest Filing Date | Signal Usable From |
|---------|----------------|-------------------|-------------------|
| Q1 | Mar 31 | Apr 30 | May 1 |
| Q2 (Mid-year) | Jun 30 | Aug 31 | Sep 1 |
| Q3 | Sep 30 | Oct 31 | Nov 1 |
| Q4 | Dec 31 | Apr 30 (next yr) | May 1 (next yr) |

**Implementation**: Add ~2 months buffer for safety:
```python
report_available_date = quarter_end_date + pd.DateOffset(months=2)
# Only use factor after this date
```

## 8. Wind / CSRC Industry Classification

Pandadata `get_stock_detail()` provides `sector_code_name` which uses Wind/GICS-style sector classification. Use this for sector-level z-scoring and industry-neutralization.

**Sectors available**: 金融, 房地产, 工业, 信息技术, 原材料, 可选消费, 主要消费, 医药卫生, 公用事业, 能源, 电信服务

## 9. Data Quality Checks

Before any factor computation, run these sanity checks:

```python
def validate_financial_data(df):
    errors = []
    
    # Check NaN rates
    for col in ['net_profit_parent', 'total_assets', 'equity_parent_common']:
        nan_rate = df[col].isna().mean()
        if nan_rate > 0.3:
            errors.append(f"WARN: {col} has {nan_rate:.1%} NaN")
    
    # Check for implausible values
    if (df['total_assets'] <= 0).any():
        errors.append("ERROR: Negative total assets found")
    if (df['equity_parent_common'] <= 0).any():
        errors.append("ERROR: Negative equity found (may be legitimate for distressed firms)")
    
    # Check for market_cap consistency
    if 'market_cap' in df.columns:
        if (df['market_cap'] <= 0).any():
            errors.append("ERROR: Non-positive market cap")
    
    # Check for date alignment
    if 'end_date' in df.columns and 'date' in df.columns:
        date_diff = (pd.to_datetime(df['date']) - pd.to_datetime(df['end_date'])).dt.days
        if (date_diff < 0).any():
            errors.append("WARN: factor_date before end_quarter (look-ahead risk)")
    
    return errors
```
