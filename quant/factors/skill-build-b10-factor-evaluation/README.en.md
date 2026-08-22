# 📊 skill-factor-evaluation

[简体中文](README.md) | **English**

> IC Test & Factor Evaluation System: A unified, reusable IC testing, factor evaluation, and visualization report generation tool for Alpha factor research.

<p align="center">
  <img alt="role" src="https://img.shields.io/badge/role-Factor_Evaluation_Tool-brightgreen">
  <img alt="output" src="https://img.shields.io/badge/output-RankIC%20%C2%B7%20ICIR%20%C2%B7%20Stratified_Backtest%20%C2%B7%20HTML_Report-blue">
  <img alt="validation" src="https://img.shields.io/badge/validation-38%2F38_Tests_Passed-orange">
  <img alt="data" src="https://img.shields.io/badge/data-Framework_Neutral-9cf">
  <img alt="license" src="https://img.shields.io/badge/license-GPLv3-blue">
</p>

`skill-factor-evaluation` is a factor evaluation Skill provided by the QuantSkills organization. It performs comprehensive evaluation of Alpha factors including IC testing, stratified backtesting, turnover analysis, decay curves, and generates research-grade HTML visualization reports.

QuantSkills GitHub Organization: https://github.com/quantskills

## 🎯 What This Skill Solves

When you develop a new Alpha factor and need to quickly and systematically evaluate its cross-sectional predictive ability, use this Skill.

It automatically performs:

- **IC/RankIC Calculation**: Cross-sectional Pearson IC, Spearman RankIC, ICIR, t-statistics (with Newey-West HAC)
- **Stratified Backtesting**: Default quintile/decile groups, group daily returns, cumulative returns, long-short cumulative returns and IR
- **Turnover Analysis**: Jaccard distance of top portfolio holdings changes
- **Decay Curve**: Multi-period RankIC decay (1/2/3/5/10/20 periods)
- **Monotonicity Test**: Whether stratified returns increase monotonically with group rank
- **Distribution Diagnostics**: IC skewness/kurtosis, factor cross-sectional distribution, extreme value ratios
- **Bootstrap Noise Baseline**: Null hypothesis p-values and confidence intervals
- **Transaction Cost Sensitivity Scan**: Net returns/IR under multiple bps scenarios
- **Industry + Style Neutralization**: Cross-sectional OLS residuals
- **Stock Pool Filtering**: All A-shares, CSI 300, CSI 500/1000/2000
- **HTML Visualization Reports**: Embedded SVG charts, no external dependencies

## 📦 Input Data Requirements

Input data must contain the following four core fields:

| Field | Type | Description |
|---|---|---|
| `trade_date` | date/string | Signal date |
| `ts_code` | string | Asset code |
| `factor_value` | float | Factor value |
| `forward_return` | float | Forward return for the signal |

## 🚀 Quick Start

### Install Dependencies

```bash
pip install pandas numpy pyarrow
```

### Basic Usage

```python
from scripts.build import run, write_report, write_production

# Run evaluation
result = run(input_data, config={
    "group_mode": "quintile",
    "turnover_quantile": 0.8,
    "decay_horizons": [1, 2, 3, 5, 10, 20],
    "annualization_factor": 252,
})

# Generate HTML report
report_path = write_report(input_data, "reports/factor_report.html", config={
    "target_id": "my_factor",
    "group_count": 5,
})
```

## ⚙️ Configuration Options

| Config | Default | Description |
|---|---|---|
| `group_mode` | `quintile` | Group mode: quintile or decile |
| `group_count` | `5` | Number of stratification layers |
| `turnover_quantile` | `0.8` | Top portfolio turnover threshold |
| `factor_direction` | `positive` | Factor direction |
| `stock_pool` | `all_a` | Stock pool: all_a, hs300, zz500, zz1000, zz2000 |
| `bootstrap_n` | `0` | Bootstrap iterations (0=off) |
| `neutralize` | `false` | Enable neutralization |

## 📁 Project Structure

```
├── 开发产物/
│   ├── SKILL.md              # Main documentation
│   ├── scripts/              # Core code
│   │   ├── build.py          # Standard entry
│   │   ├── metrics.py        # Evaluation metrics
│   │   └── visual/           # HTML report
│   └── references/           # API docs, samples
├── 生产产物/
│   └── 数据库.parquet         # Production output
└── demo_output/              # Demo output
```

## 🧪 Run Tests

```bash
python scripts/test.py
```

## 📄 License

GPLv3 - see [LICENSE](LICENSE).
