# Fundamental Factor Analysis — README.en

Compute, validate, and analyze fundamental (financial statement) factors for Chinese A-shares. Fills the gap of **zero fundamental factors** in the existing 800+ OHLCV-only QUANTSKILLS ecosystem.

## What It Does

| Area | Factors |
|------|---------|
| **Valuation** | EP, BP, SP, CP, FCFP, GP/A (all as inverse ratios) |
| **Quality** | ROE, ROA, Gross Margin, Operating Margin, Accruals, Leverage, Cash Flow Quality |
| **Growth** | Earnings Growth, Revenue Growth, ROE Growth, Growth Stability |
| **Composite** | Piotroski F-Score, Quality Minus Junk, PEG, GARP, Value+Quality |

### Validation

- Rank IC analysis (mean, IR, t-stat, positive ratio)
- Decile grouped portfolio returns (monotonicity, long-short spread)
- Fama-MacBeth cross-sectional regression (with control variables)
- IC decay curve and half-life estimation
- Sub-sample stability tests

## Data Sources (Pandadata)

- `panda_data.get_fina_performance()` — Financial snapshots (30+ fields)
- `panda_data.get_fina_reports()` — Detailed financial statements (100+ fields)
- `panda_data.get_factor()` — Daily data + market_cap
- `panda_data.get_market_data()` — Daily price/volume

## Usage

```python
import panda_data

# Step 1: Fetch financial data
fina = panda_data.get_fina_performance(
    symbol=['000001.SZ', '000002.SZ'],
    end_quarter='2024q4',
    fields=['symbol', 'net_profit_parent', 'equity_parent_common']
)

# Step 2: Get market_cap
mkt = panda_data.get_factor(
    symbol=['000001.SZ', '000002.SZ'],
    start_date='20250115',
    end_date='20250115',
    factors=['market_cap']
)

# Step 3: Compute factor
bp = fina.merge(mkt, on='symbol')
bp['BP'] = bp['equity_parent_common'] / bp['market_cap']
```

## Quick Start

```
"Compute EP factor for CSI 300 constituents, run IC analysis and decile returns"
"Build ROE + gross margin composite quality factor with Fama-MacBeth regression"
"Calculate Piotroski F-Score for all A-shares, compare top vs bottom group performance"
"Analyze BP factor IC decay curve — what is optimal rebalance frequency?"
```
