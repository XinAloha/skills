# Factor Definitions

Complete formulas, Pandadata field mappings, edge cases, and interpretation guidelines for all fundamental factors.

## 1. Valuation Factors

### EP (Earnings Yield)

| Field | Value |
|-------|-------|
| **Formula** | `EP = net_profit_parent_ttm / market_cap` |
| **Units** | Ratio (decimal) |
| **Interpretation** | Higher = cheaper relative to earnings |
| **Typical Range** | -0.05 to 0.15 (A-shares) |

**TTM Computation:**
```python
# Income statement items need 4 quarters accumulated
# Portfolio date: 2025-01-15 → use 2024q4 financials
# net_profit_parent_ttm = 2024q4 + 2024q3 + 2024q2 + 2024q1 values
```

**Edge Cases:**
- Negative earnings → EP is negative (valid signal, but don't sort these with positive EP)
- Solution: Use positive-only EP, or rank separately
- Financial sector: Standard EP formula applies (banks have earnings)

**Pandadata:**
```python
fina = panda_data.get_fina_performance(
    symbol=stocks,
    end_quarter="2024q4",
    fields=["symbol", "end_date", "net_profit_parent"]
)
mkt = panda_data.get_factor(
    symbol=stocks,
    start_date="20250115",
    end_date="20250115",
    factors=["market_cap", "close"],
    type="stock"
)
```

### BP (Book-to-Market)

| Field | Value |
|-------|-------|
| **Formula** | `BP = equity_parent_common_latest / market_cap` |
| **Units** | Ratio (decimal) |
| **Interpretation** | Higher = cheaper relative to book value |
| **Typical Range** | 0.1 to 2.0 (A-shares) |

**Edge Cases:**
- Negative equity → BP undefined (exclude these stocks)
- Financial sector: Book-to-market is a classic value metric for banks
- Insurance: Complex equity calculation; use as-is

### SP (Sales Yield)

| Field | Value |
|-------|-------|
| **Formula** | `SP = operating_revenue_ttm / market_cap` |
| **Units** | Ratio (decimal) |
| **Interpretation** | Higher = cheaper relative to sales |
| **Typical Range** | 0.1 to 5.0 (varies by sector) |

**Edge Cases:**
- Always positive for active companies (revenue > 0 even with losses)
- Cyclical: SP is more stable through cycles than EP
- No negative issue (unlike EP)

### CP (Cash Flow Yield)

| Field | Value |
|-------|-------|
| **Formula** | `CP = net_cash_flow_operating_ttm / market_cap` |
| **Units** | Ratio (decimal) |
| **Interpretation** | Higher = cheaper relative to operating cash flow |
| **Typical Range** | -0.1 to 0.2 |

**Edge Cases:**
- Real estate / construction firms often have negative operating cash flow
- Use in combination with Gross Profit to verify cash generation

### GP/A (Gross Profit to Total Assets)

| Field | Value |
|-------|-------|
| **Formula** | `GP/A = gross_profit_ttm / total_assets_latest` |
| **Units** | Ratio (decimal) |
| **Interpretation** | Higher = more efficient asset utilization |
| **Typical Range** | 0.01 to 0.30 |

**Note**: Used in Novy-Marx (2013) as a strong predictor of cross-sectional returns.

## 2. Quality Factors

### ROE (Return on Equity)

| Field | Value |
|-------|-------|
| **Formula** | `ROE = net_profit_parent_ttm / equity_parent_common_latest` |
| **Pandadata Direct** | `roe_diluted` (from `get_fina_performance` — already computed) |
| **Interpretation** | Higher = more profitable use of shareholder capital |
| **Typical Range** | 0.02 to 0.20 (annualized) |

**Which ROE to use?**
- `roe_diluted` — Pandadata pre-computed, TTM basis
- `roe_weighted` — Weighted average, slightly different computation
- Manual: `net_profit_parent_ttm / equity_parent_common_latest`
- Recommendation: Use `roe_diluted` for consistency, compute manually if you need to match a specific academic paper

### ROA (Return on Assets)

| Field | Value |
|-------|-------|
| **Formula** | `ROA = net_profit_parent_ttm / total_assets_latest` |
| **Interpretation** | Higher = more efficient use of total assets |
| **Typical Range** | 0.01 to 0.10 |

### Gross Margin

| Field | Value |
|-------|-------|
| **Formula** | `Gross_Margin = gross_profit_ttm / operating_revenue_ttm` |
| **Interpretation** | Higher = stronger pricing power |
| **Typical Range** | 0.10 to 0.60 |

**Sector-specific:**
- High margin: Software (0.50-0.80), Pharma (0.40-0.70)
- Low margin: Retail (0.10-0.25), Manufacturing (0.15-0.30)
- Cross-section z-score by sector removes sector bias

### Accruals

| Field | Value |
|-------|-------|
| **Formula** | `Accruals = (net_profit_parent_ttm - net_cash_flow_operating_ttm) / total_assets_latest` |
| **Interpretation** | Higher = more accrual-based earnings (lower quality). Based on Sloan (1996) |
| **Typical Range** | -0.05 to 0.10 |

**Why it works**: Firms with high accruals tend to reverse (mean-reverting earnings). Low accruals = cash-backed earnings = higher quality.

### Leverage

| Field | Value |
|-------|-------|
| **Formula** | `Leverage = total_assets_latest / equity_parent_common_latest` |
| **Interpretation** | Higher = more financial risk |
| **Typical Range** | 1.0 to 5.0 |

**Edge Cases:**
- Financial sector: Banks have naturally high leverage (10x+). Exclude or use sector z-score.
- Negative equity → undefined (exclude)

### Cash Flow Quality

| Field | Value |
|-------|-------|
| **Formula** | `CF_Quality = net_cash_flow_operating_ttm / operating_profit_ttm` |
| **Interpretation** | Higher = earnings are backed by cash |
| **Typical Range** | 0.5 to 2.0 |
| **Winsorization** | Clip to [-10, 10] to avoid division-by-zero issues |

## 3. Growth Factors

### Earnings Growth (YoY)

| Field | Value |
|-------|-------|
| **Pandadata Field** | `net_profit_parent_yoy` (from `get_fina_performance`) |
| **Units** | Decimal (already in %) |
| **Interpretation** | Higher = faster earnings growth |

**Edge Cases:**
- Base effect: Previous year's profit near zero → extreme growth values
- Negative to positive swing → large positive growth
- Winsorize at ±200% for cross-sectional analysis

### Revenue Growth (YoY)

| Field | Value |
|-------|-------|
| **Pandadata Field** | `operating_revenue_yoy` |
| **Units** | Decimal (already in %) |
| **Interpretation** | Higher = faster revenue growth |

**Note**: Revenue growth is more stable than earnings growth (less affected by one-time items).

### Growth Stability

| Field | Value |
|-------|-------|
| **Formula** | `-stddev(quarterly_net_profit_yoy over 8 quarters)` |
| **Interpretation** | Higher (less negative) = more stable growth |
| **Units** | Same as growth rate stddev |

## 4. Additional Computations

### Dividend Yield

| Field | Value |
|-------|-------|
| **Data Source** | `get_fina_reports()` with dividend fields |
| **Formula** | `total_dividends / market_cap` |
| **Typical Range** | 0 to 0.05 |

### Payout Ratio

| Field | Value |
|-------|-------|
| **Formula** | `total_dividends / net_profit_parent` |
| **Interpretation** | Higher = more cash returned to shareholders |

### Negative Earnings Handling

When net profit is negative:
1. **EP**: Negative by definition. Some researchers set EP = 0 or exclude.
2. **ROE**: Negative by definition. Use next-12-months-ROE if available.
3. **Growth**: If previous year negative, growth computation is unreliable.
4. **Recommendation**: Include negative-EP stocks but use rank-based (non-parametric) methods.
