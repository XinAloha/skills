# Factor Mason

[简体中文](README.md) | **English**

> A quality-control skill for single-factor equity research: evaluate whether a signal is real alpha, risk exposure, leakage, or a sample illusion after universe cleaning, timing alignment, turnover, cost, and neutralization.

![type](https://img.shields.io/badge/type-alpha--research-blue)
![domain](https://img.shields.io/badge/domain-equity--factor-teal)
![license](https://img.shields.io/badge/license-GPLv3-blue)

## What This Is

Factor Mason turns factor ideas into auditable research workflows. It is useful for A-share, HK, US, or other equity cross-sectional studies where attractive backtests may be driven by future leakage, stale prices, sector bias, or unrealistic cost assumptions.

## Project Status and Boundaries

| Item | Statement |
| --- | --- |
| Status | Community Project; not reviewed, certified, or endorsed by QUANTSKILLS |
| Maintainers | Repository maintainers and contributors |
| Data sources | User-provided or user-designated market data, disclosures, corporate actions, index constituents, and industry classifications |
| Assumptions | Information timing, historical universe, trading lag, and cost model match the research setting |
| Limitations | Data revisions, suspensions, delistings, constituent changes, borrow availability, and cost estimates can change results |
| Risk boundary | Research and educational example only; it neither fetches data nor executes trades |

## Core Logic

```text
raw_factor        = user-defined signal
tradable_factor   = lag(raw_factor, tradable delay)
clean_factor      = winsorize/standardize/filter(tradable_factor)
ic_series         = corr(rank(clean_factor_t), future_return_t+h)
long_short_return = top_quantile_return - bottom_quantile_return
net_return        = gross_return - turnover_cost - slippage - spread_cost
usable_alpha      = stable out of sample + usable after cost + explainable exposure
```

## Quick Start

```bash
python3 scripts/check_test_cases.py
sed -n '1,220p' references/playbook.md
```

## Parameters

| Parameter | Required | Description |
| --- | --- | --- |
| universe | yes | Market, index, sector, liquidity scope |
| factor_definition | yes | Formula, fields, update time |
| label_horizon | yes | Forward-return window |
| rebalance_frequency | yes | Daily, weekly, monthly, etc. |
| lag_rule | yes | When the signal becomes tradable |
| cost_model | yes | Fee, slippage, spread, borrow |
| neutralization | no | Industry, size, beta, style |
| sample_split | no | In-sample, out-of-sample, rolling windows |

## Validation

Run:

```bash
python3 scripts/check_test_cases.py
```

## Disclaimer

For quantitative research workflow design. Validate all conclusions against source data and execution constraints.
