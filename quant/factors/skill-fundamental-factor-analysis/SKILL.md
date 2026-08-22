---
name: fundamental-factor-analysis
description: "Compute, validate, and analyze fundamental (financial statement) factors for Chinese A-shares. Covers value (EP, BP, SP, CP, FCFP, GP/A), quality (ROE, ROA, gross margin, accruals, leverage), growth (earnings growth, revenue growth, analyst revision), and composite factors. Uses Pandadata APIs (get_fina_performance, get_factor, get_market_data) to fetch financial data, compute factors, and validate through IC analysis, grouped returns, and Fama-MacBeth regressions."
quantSkills:
  organization: https://github.com/quantskills
  repository: quantskills/skill-fundamental-factor-analysis
  repository_url: https://github.com/quantskills/skill-fundamental-factor-analysis
  project_type: skill
  collection: factor-research
  license: GPL-3.0
  category: tooling
  tags: [fundamental-factors, financial-statements, value-factor, quality-factor, growth-factor, a-share, ic-analysis, fama-macbeth, pandadata]
  platforms: [claude-code, codex, openclaw]
  language: zh-en
  status: draft
  validation_level: listed
  maintainer_type: community
  requires: []
  summary_zh: 计算、验证和分析A股基本面因子。覆盖估值(EP/BP/SP/CP/FCFP/GP/A)、质量(ROE/ROA/毛利率/应计利润/杠杆)、成长(盈利增长/营收增长/分析师预期调整)和复合因子。使用Pandadata财务API获取数据，通过IC分析、分组收益、Fama-MacBeth回归进行因子验证
  summary_en: Compute, validate, and analyze A-share fundamental factors. Covers value (EP/BP/SP/CP/FCFP/GP/A), quality (ROE/ROA/gross margin/accruals/leverage), growth (earnings growth/revenue growth/analyst revision) and composite factors. Uses Pandadata financial APIs with IC analysis, grouped returns, and Fama-MacBeth regression for validation.
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "补充样本期、财报口径、行业处理、控制变量或复合因子要求"
  },
  "fields": [
    {
      "key": "factor",
      "label": "基本面因子",
      "type": "select",
      "default": "EP",
      "options": [
        { "value": "EP", "label": "EP（盈利收益率）" },
        { "value": "BP", "label": "BP（账面市值比）" },
        { "value": "SP", "label": "SP（营收市值比）" },
        { "value": "CP", "label": "CP（经营现金流市值比）" },
        { "value": "ROE", "label": "ROE（净资产收益率）" },
        { "value": "ROA", "label": "ROA（总资产收益率）" },
        { "value": "Accruals", "label": "应计利润" },
        { "value": "Earnings_Growth", "label": "盈利增长" },
        { "value": "QMJ", "label": "质量减垃圾（QMJ）" },
        { "value": "F_Score", "label": "Piotroski F-Score" }
      ]
    },
    {
      "key": "universe",
      "label": "股票池",
      "type": "select",
      "default": "000300.SH",
      "options": [
        { "value": "000300.SH", "label": "沪深300" },
        { "value": "000905.SH", "label": "中证500" },
        { "value": "000852.SH", "label": "中证1000" },
        { "value": "all_a", "label": "全A股" }
      ]
    },
    {
      "key": "date",
      "label": "分析基准日",
      "type": "date",
      "help": "留空由前端使用今天，并按可得财报日期对齐"
    },
    {
      "key": "horizon",
      "label": "预测周期",
      "type": "select",
      "default": "20",
      "options": [
        { "value": "1", "label": "未来1日" },
        { "value": "5", "label": "未来5日" },
        { "value": "20", "label": "未来20日" },
        { "value": "60", "label": "未来60日" }
      ]
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}请分析 A 股基本面因子 {{factor}} 在股票池 {{universe}}{{#date}}、基准日 {{date}}{{/date}} 和预测周期 {{horizon}} 日下的表现，按财报实际可得时间对齐并处理 TTM、异常值及金融行业差异，完成 Rank IC、分组收益、Fama-MacBeth 与衰减检验，输出中文报告。"
}
```

# Fundamental Factor Analysis

Compute and analyze **financial-statement-driven** factors for Chinese A-shares. This skill bridges the gap between raw financial data (quarterly reports) and actionable alpha signals.

> **Why this exists**: QUANTSKILLS currently has 800+ OHLCV (price/volume) alpha factors, but **zero fundamental factors**. This skill fills that gap.

## Data Sources

### Primary APIs (Pandadata)

| API | Data Provided | Update Frequency |
|-----|--------------|-----------------|
| `panda_data.get_fina_performance()` | Financial snapshot: revenue, profit, cash flow, ROE, EPS, BVPS (30+ fields) | Quarterly (aligned with report dates) |
| `panda_data.get_fina_reports()` | Detailed financial statements: balance sheet, income statement, cash flow (100+ fields) | Quarterly |
| `panda_data.get_factor()` | Daily market data + `market_cap` / `turnover` | Daily |
| `panda_data.get_market_data()` | Price/volume daily data | Daily |
| `panda_data.get_stock_detail()` | Stock static info: sector, board type, listing date | Static |

### Key Financial Fields from `get_fina_performance()`

| Field | Description | YOY Field |
|-------|-------------|-----------|
| `operating_revenue` | 营业收入 | `operating_revenue_yoy` |
| `gross_profit` | 主营业务利润 | `gross_profit_yoy` |
| `operating_profit` | 营业利润 | `operating_profit_yoy` |
| `net_profit_parent` | 归属母公司净利润 | `net_profit_parent_yoy` |
| `net_profit_excluding_nonrecurring` | 扣非净利润 | — |
| `net_cash_flow_operating` | 经营活动现金流 | `net_cash_flow_operating_yoy` |
| `total_assets` | 总资产 | `total_assets_growth_rate` |
| `equity_parent_common` | 归属母公司普通股东权益 | `equity_parent_growth_rate` |
| `basic_eps` | 基本每股收益 | `basic_eps_yoy` |
| `roe_diluted` | ROE(摊薄) | `roe_diluted_yoy` |
| `roe_weighted` | ROE(加权) | — |
| `bvps` | 每股净资产 | `bvps_growth_rate` |
| `cf_operating_per_share` | 每股经营现金流 | — |

## Factor Universe

### 1. Valuation Factors (估值因子)

Investors buy undervalued stocks and sell overvalued ones. Computed as **inverse multiples** so that higher = more undervalued.

| Factor | Formula | Pandadata Derivation |
|--------|---------|---------------------|
| **EP** (E/P) | `net_profit_parent / market_cap` | `get_fina_performance()` → `net_profit_parent`; `get_factor()` → `market_cap` |
| **BP** (B/P) | `equity_parent_common / market_cap` | `equity_parent_common / market_cap` |
| **SP** (S/P) | `operating_revenue / market_cap` | `operating_revenue / market_cap` |
| **CP** (Cash Flow/P) | `net_cash_flow_operating / market_cap` | `net_cash_flow_operating / market_cap` |
| **FCFP** (FCF/P) | `(net_cash_flow_operating - capital_expenditure) / market_cap` | Requires `get_fina_reports()` for capex |
| **GP/A** (Gross Profit / Total Assets) | `gross_profit / total_assets` | `gross_profit / total_assets` |

### 2. Quality Factors (质量因子)

Companies with higher profitability, safer financial structures, and cleaner earnings outperform.

| Factor | Formula | Notes |
|--------|---------|-------|
| **ROE** | `net_profit_parent / equity_parent_common` | Core profitability. Available as `roe_diluted` directly |
| **ROA** | `net_profit_parent / total_assets` | Asset efficiency |
| **Gross Margin** | `gross_profit / operating_revenue` | Pricing power |
| **Operating Margin** | `operating_profit / operating_revenue` | Operating efficiency |
| **Accruals** | `(net_profit_parent - net_cash_flow_operating) / total_assets` | Earnings quality. High accruals = low quality |
| **Leverage** | `total_assets / equity_parent_common` | Financial risk |
| **Cash Flow Quality** | `net_cash_flow_operating / operating_profit` | Cash realization ratio |

### 3. Growth Factors (成长因子)

Companies with accelerating earnings/revenue momentum outperform.

| Factor | Formula | Pandadata Field |
|--------|---------|-----------------|
| **Earnings Growth (YoY)** | `(net_profit_parent[t] - net_profit_parent[t-4]) / abs(net_profit_parent[t-4])` | `net_profit_parent_yoy` |
| **Revenue Growth (YoY)** | `(revenue[t] - revenue[t-4]) / revenue[t-4]` | `operating_revenue_yoy` |
| **ROE Growth (YoY)** | `roe_diluted[t] - roe_diluted[t-4]` | `roe_diluted_yoy` |
| **Earnings Surprise** | `(actual_eps - expected_eps) / expected_eps` | Requires analyst data (not available via standard Pandadata) |
| **Growth Stability** | stddev of quarterly net profit growth over 8 quarters | Computed from multi-quarter data |
| **Sustainable Growth** | `roe * (1 - dividend_payout_ratio)` | Dividend data from `get_fina_reports()` |

### 4. Composite Factors (复合因子)

| Factor | Composition | Interpretation |
|--------|-------------|---------------|
| **Quality Minus Junk (QMJ)** | Average z-score of ROE, ROA, Gross Margin, minus Accruals, Leverage | Long high-quality, short low-quality |
| **Value + Quality** | Average z-score of EP, BP, CP, ROE | Cheap + profitable |
| **PEG** | `PE / earnings_growth_rate` | Price paid per unit of growth (lower = cheaper growth) |
| **F-Score** | Piotroski F-Score (9-point composite of profitability, leverage, and operating efficiency) | See detailed computation below |

## Factor Computation Pipeline

### Step 1: Merge Financial Data with Market Data

```python
import pandas as pd
import numpy as np
import panda_data
from scipy import stats

def get_fundamental_factor_data(
    symbol_list,
    start_quarter,
    end_quarter,
    factor_date
):
    """
    Fetch quarterly financial data and merge with market data (market_cap, price)
    
    Parameters:
    -----------
    symbol_list : list[str]
        Stock symbols, e.g. ['000001.SZ', '000002.SZ']
    start_quarter, end_quarter : str
        Format 'YYYYqN', e.g. '2024q1'
    factor_date : str
        The date (YYYYMMDD) to use for market data alignment.
        Typically uses: fiscal quarter end + ~2 months (reports available date)
    
    Returns:
    --------
    DataFrame with columns: [symbol, date, market_cap] + financial fields
    """
    # 1. Fetch financial data
    fina_fields = [
        'symbol', 'end_date', 'operating_revenue', 'gross_profit',
        'operating_profit', 'net_profit_parent',
        'net_profit_excluding_nonrecurring', 'net_cash_flow_operating',
        'total_assets', 'equity_parent_common', 'equity_parent',
        'total_shares', 'basic_eps', 'roe_diluted', 'roe_weighted',
        'bvps', 'cf_operating_per_share',
        'operating_revenue_yoy', 'net_profit_parent_yoy',
        'roe_diluted_yoy', 'equity_parent_growth_rate',
    ]
    
    fina = panda_data.get_fina_performance(
        symbol=symbol_list,
        end_quarter=end_quarter,
        fields=fina_fields
    )
    
    # 2. Fetch market data (market cap at factor_date)
    # Use get_factor to get market_cap
    mkt = panda_data.get_factor(
        symbol=symbol_list,
        start_date=factor_date,
        end_date=factor_date,
        factors=['market_cap', 'close', 'turnover'],
        type='stock'
    )
    
    # 3. Merge
    # Use the latest available quarter's financial data
    merged = fina.merge(
        mkt[['symbol', 'date', 'market_cap', 'close', 'turnover']],
        on='symbol',
        how='inner'
    )
    
    return merged
```

### Step 2: Compute Trailing 12-Month (TTM) Financial Figures

Quarterly financial data must be accumulated for TTM figures:

```python
def compute_ttm_financials(df, quarter_col='quarter'):
    """
    Accumulate quarterly data to TTM (trailing 12 months).
    
    For income statement items (revenue, profit): sum last 4 quarters
    For balance sheet items (assets, equity): use latest quarter
    
    Parameters:
    -----------
    df : DataFrame
        Must have columns: [symbol, quarter, operating_revenue, net_profit_parent,
                            net_cash_flow_operating, ...]
    """
    result = df.copy()
    result = result.sort_values(['symbol', 'quarter'])
    
    # TTM for income statement items
    ttm_fields = [
        'operating_revenue', 'gross_profit', 'operating_profit',
        'net_profit_parent', 'net_profit_excluding_nonrecurring',
        'net_cash_flow_operating'
    ]
    
    for field in ttm_fields:
        if field in df.columns:
            result[f'{field}_ttm'] = (
                result.groupby('symbol')[field]
                .rolling(window=4, min_periods=4)
                .sum()
                .reset_index(0, drop=True)
            )
    
    # For balance sheet fields, use the latest quarter value
    bs_fields = ['total_assets', 'equity_parent_common', 'total_shares']
    for field in bs_fields:
        if field in df.columns:
            result[f'{field}_latest'] = result.groupby('symbol')[field].transform('last')
    
    return result
```

### Step 3: Compute Factor Values

```python
def compute_value_factors(df):
    """
    Compute valuation factors: EP, BP, SP, CP, FCFP, GP/A
    
    All factors are in "inverse" form so HIGHER factor value = more undervalued.
    """
    df = df.copy()
    
    # E/P (earnings yield)
    df['EP'] = df['net_profit_parent_ttm'] / df['market_cap']
    
    # B/P (book-to-market)
    df['BP'] = df['equity_parent_common_latest'] / df['market_cap']
    
    # S/P (sales yield)
    df['SP'] = df['operating_revenue_ttm'] / df['market_cap']
    
    # C/P (cash flow yield)
    df['CP'] = df['net_cash_flow_operating_ttm'] / df['market_cap']
    
    # GP/A (gross profit to total assets)
    df['GP/A'] = df['gross_profit_ttm'] / df['total_assets_latest']
    
    return df


def compute_quality_factors(df):
    """
    Compute quality factors: ROE, ROA, gross margin, operating margin,
    accruals, leverage, cash flow quality
    """
    df = df.copy()
    
    # ROE (return on equity)
    df['ROE'] = df['net_profit_parent_ttm'] / df['equity_parent_common_latest']
    
    # ROA (return on assets)
    df['ROA'] = df['net_profit_parent_ttm'] / df['total_assets_latest']
    
    # Gross Margin
    df['Gross_Margin'] = df['gross_profit_ttm'] / df['operating_revenue_ttm']
    
    # Operating Margin
    df['Operating_Margin'] = df['operating_profit_ttm'] / df['operating_revenue_ttm']
    
    # Accruals (high accruals = low earnings quality)
    df['Accruals'] = (
        (df['net_profit_parent_ttm'] - df['net_cash_flow_operating_ttm'])
        / df['total_assets_latest']
    )
    
    # Leverage (high = more financial risk)
    df['Leverage'] = df['total_assets_latest'] / df['equity_parent_common_latest']
    
    # Cash Flow Quality
    df['CF_Quality'] = (
        df['net_cash_flow_operating_ttm'] / df['operating_profit_ttm']
    )
    # Winsorize to avoid extreme values
    df['CF_Quality'] = df['CF_Quality'].clip(-10, 10)
    
    return df


def compute_growth_factors(df):
    """
    Compute growth factors using YoY growth rates from financial data.
    """
    df = df.copy()
    
    # Use the YoY fields directly from Pandadata
    df['Earnings_Growth'] = df['net_profit_parent_yoy'] / 100.0
    df['Revenue_Growth'] = df['operating_revenue_yoy'] / 100.0
    df['ROE_Growth'] = df['roe_diluted_yoy'] / 100.0
    df['Equity_Growth'] = df['equity_parent_growth_rate'] / 100.0
    
    return df
```

### Step 4: Cross-Sectional Standardization (Z-Score)

```python
def cross_sectional_standardize(df, factor_columns, date_col='date'):
    """
    For each date, convert factor values to cross-sectional z-scores.
    Also applies outlier treatment (MAD winsorization).
    
    Parameters:
    -----------
    df : DataFrame
    factor_columns : list[str]
        Column names to standardize
    date_col : str
        Column identifying the cross-section date
        
    Returns:
    --------
    DataFrame with '_z' suffix columns added
    """
    df = df.copy()
    
    for factor in factor_columns:
        z_col = f'{factor}_z'
        
        # MAD winsorization: cap at ±5 median absolute deviations
        median = df[factor].median()
        mad = (df[factor] - median).abs().median()
        if mad > 0:
            upper = median + 5 * mad * 1.4826  # Normal MAD constant
            lower = median - 5 * mad * 1.4826
            df[factor] = df[factor].clip(lower, upper)
        
        # Cross-sectional z-score by date
        df[z_col] = df.groupby(date_col)[factor].transform(
            lambda x: (x - x.mean()) / x.std()
        )
        
        # Cap z-scores at ±3
        df[z_col] = df[z_col].clip(-3, 3)
    
    return df
```

## Factor Validation

### 1. Rank IC (Spearman Rank Correlation)

```python
def compute_rank_ic(df, factor_col, forward_return_col='ret_1d'):
    """
    Compute daily Rank IC between factor and forward returns.
    Returns daily IC series, mean IC, IR, t-stat.
    """
    ic_by_date = []
    
    for date, group in df.groupby('date'):
        factor_rank = group[factor_col].rank()
        ret_rank = group[forward_return_col].rank()
        ic = factor_rank.corr(ret_rank)
        ic_by_date.append({'date': date, 'IC': ic})
    
    ic_df = pd.DataFrame(ic_by_date)
    
    results = {
        'mean_IC': ic_df['IC'].mean(),
        'std_IC': ic_df['IC'].std(),
        'IR': ic_df['IC'].mean() / ic_df['IC'].std(),
        't_stat': ic_df['IC'].mean() / ic_df['IC'].std() * np.sqrt(len(ic_df)),
        'IC_positive_ratio': (ic_df['IC'] > 0).mean(),
        'daily_ic': ic_df
    }
    
    return results
```

### 2. Grouped Portfolio Returns

```python
def compute_grouped_returns(df, factor_col, n_groups=10, forward_return_col='ret_1d'):
    """
    Sort stocks into n_groups by factor value, compute equal-weighted forward returns.
    
    Returns group means, Q1-Q10 spread, monotonicity score.
    """
    results = []
    
    for date, group in df.groupby('date'):
        # Handle NaN
        group = group.dropna(subset=[factor_col, forward_return_col])
        if len(group) < n_groups:
            continue
        
        group['factor_rank'] = group[factor_col].rank()
        group['group'] = pd.qcut(group['factor_rank'], n_groups, labels=range(n_groups))
        
        for g in range(n_groups):
            g_ret = group[group['group'] == g][forward_return_col].mean()
            results.append({'date': date, 'group': g, 'return': g_ret})
    
    result_df = pd.DataFrame(results)
    
    # Time-series average by group
    avg_returns = result_df.groupby('group')['return'].mean()
    
    # Long-Short spread
    ls_spread = avg_returns.iloc[-1] - avg_returns.iloc[0]
    
    # Monotonicity: check if higher groups consistently have higher returns
    monotonic_up = all(
        avg_returns.iloc[i] <= avg_returns.iloc[i+1]
        for i in range(len(avg_returns) - 1)
    )
    
    return {
        'avg_returns_by_group': avg_returns,
        'long_short_spread': ls_spread,
        'monotonic': monotonic_up,
        'daily_returns': result_df
    }
```

### 3. Fama-MacBeth Regression

```python
import statsmodels.api as sm

def fama_macbeth_regression(df, factor_col, control_cols=[], return_col='ret_1d'):
    """
    Two-step Fama-MacBeth regression:
    Step 1: Cross-sectional regression each period
    Step 2: Time-series average of coefficients
    
    Tests if the factor has significant explanatory power for returns
    after controlling for market beta, size, etc.
    """
    dates = df['date'].unique()
    all_coefs = []
    
    for date in dates:
        cross_section = df[df['date'] == date].dropna(
            subset=[factor_col, return_col] + control_cols
        )
        if len(cross_section) < 50:  # Minimum observations
            continue
        
        y = cross_section[return_col].values
        X_cols = [factor_col] + control_cols
        X = sm.add_constant(cross_section[X_cols].values)
        
        try:
            model = sm.OLS(y, X).fit()
            all_coefs.append({
                'date': date,
                'const': model.params[0],
                **{f'coef_{col}': model.params[i+1]
                   for i, col in enumerate(X_cols)}
            })
        except Exception:
            continue
    
    coef_df = pd.DataFrame(all_coefs)
    
    # Step 2: Average coefficients across time
    results = {}
    for col in coef_df.columns:
        if col != 'date':
            coefs = coef_df[col].dropna()
            mean_coef = coefs.mean()
            t_stat = mean_coef / coefs.std() * np.sqrt(len(coefs))
            results[col] = {
                'mean': mean_coef,
                't_stat': t_stat,
                'positive_ratio': (coefs > 0).mean()
            }
    
    return results
```

### 4. Decay Analysis

```python
def compute_factor_decay(df, factor_col, horizons=[1, 5, 10, 20, 60]):
    """
    Compute IC at multiple forward horizons to determine factor half-life.
    
    Parameters:
    -----------
    horizons : list[int]
        Forward return periods in trading days (1d, 5d, 1w, 1m, 3m)
        
    Returns:
    --------
    DataFrame: IC values at each horizon
    """
    decay_results = {}
    
    for h in horizons:
        return_col = f'ret_{h}d'
        if return_col in df.columns:
            ic = compute_rank_ic(df, factor_col, return_col)
            decay_results[f'{h}d'] = ic['mean_IC']
    
    return pd.Series(decay_results).to_frame('IC')
```

## End-to-End Workflow

### Single-Factor Analysis

```python
def analyze_single_factor(
    symbol_list,
    quarter='2024q4',
    factor_date='20250115',
    factor_type='value'  # 'value' | 'quality' | 'growth'
):
    """
    Complete single-factor analysis: compute → standardize → validate → report
    """
    # Step 1: Data
    data = get_fundamental_factor_data(symbol_list, quarter, quarter, factor_date)
    data = compute_ttm_financials(data)
    
    # Step 2: Compute factors
    data = compute_value_factors(data)
    data = compute_quality_factors(data)
    data = compute_growth_factors(data)
    
    # Determine target factor based on type
    factor_map = {
        'value': 'EP',
        'quality': 'ROE',
        'growth': 'Earnings_Growth'
    }
    target_factor = factor_map.get(factor_type, 'EP')
    
    # Step 3: Standardize
    data = cross_sectional_standardize(data, [target_factor])
    
    # Step 4: Align with forward returns
    # (merge with future returns from get_market_data)
    
    # Step 5: Validate
    ic_result = compute_rank_ic(data, f'{target_factor}_z')
    grouped_result = compute_grouped_returns(data, f'{target_factor}_z')
    
    return {
        'factor': target_factor,
        'ic': ic_result,
        'grouped': grouped_result,
        'data': data
    }
```

## Reporting

For each factor analyzed, produce:

```markdown
## Fundamental Factor Analysis Report

### Factor: {name}

**Data Range**: {quarter} financials, aligned to {date}

### IC Statistics
| Metric | Value |
|--------|-------|
| Mean Rank IC | 0.032 |
| IC IR | 0.45 |
| t-stat | 2.85 |
| Positive IC Ratio | 58.2% |

### Grouped Decile Returns
| Group | Avg Return (nxt 1d) | Cumulative |
|-------|--------------------|------------|
| Q1 (Low) | -0.03% | ... |
| Q2 | 0.01% | ... |
| ... |
| Q10 (High) | 0.08% | ... |
| **Q10 - Q1** | **0.11%** | |

### Fama-MacBeth Results
| Variable | Coef | t-stat |
|----------|------|--------|
| {factor} | 0.042 | 2.15 |
| | Limited but significant |

### IC Decay
| Horizon | IC |
|---------|-----|
| 1d | 0.032 |
| 5d | 0.028 |
| 20d | 0.015 |
| 60d | 0.008 |
```

## References

| File | When to read |
|------|-------------|
| `references/factor_definitions.md` | When computing specific factors — full formulas, edge cases, and Pandadata field mappings |
| `references/composite_factors.md` | When building composite signals (Piotroski F-Score, QMJ, PEG, GARP) |
| `references/validation_report.md` | When generating factor validation reports — templates, charts, and interpretation guidelines |
| `references/accounting_notes.md` | When handling special accounting situations (financial sector, ST stocks, IPO effects) |
| `references/source_boundary.md` | When deciding which data/concepts are in scope |

## Examples

| File | Description |
|------|-------------|
| `examples/value_factor_analysis.py` | Full EP/BP/SP/CP/FCFP factor computation and IC validation |
| `examples/quality_factor_rotation.py` | ROE-based quality factor with grouped returns and Fama-MacBeth |
| `examples/f_score_pipeline.py` | Complete Piotroski F-Score computation and backtest |
| `examples/composite_factor.py` | Building Value+Quality composite and comparing to single factors |

## Constraints

| Constraint | Description |
|---|---|
| 📅 财务数据时滞 | Quarterly financial data is published ~2 months after quarter end. Factor signals must use `end_date` + 2M adjustment. Using stale financial data creates look-ahead bias. |
| ⚠️ 跨市股票不适用 | Financial sector (banks, insurance) has different accounting standards. Leverage, Accruals, and ROA computations need special handling. |
| 📊 非T日数据 | Financial data is quarterly (not daily). Cross-sectional standardization uses the last available financial period for each stock, not each date. |
| 🔄 财报与行情日期对齐 | The `factor_date` used for `get_factor()` market_cap may differ from `end_quarter`. Align by using the last trading day of the quarter + 2 months. |
| 🚫 新股/退市 | Stocks listed < 12 months should be excluded. De-listed stocks need status filtering via `get_stock_detail(status=1)`. |
| ⚖️ TTM vs 单季 | TTM figures smooth seasonal effects but introduce 12-month lag in signal. Single-quarter figures are noisier but more responsive. |
