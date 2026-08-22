---
name: statistical-arbitrage-time-series
name_zh: 统计套利与时间序列建模
description: Generate a sourced, reproducible statistical-arbitrage research dossier
  from a candidate pair, basket, or asset universe, covering data preparation, pair
  selection, cointegration and stationarity testing (train-window ADF + KPSS), spread
  modeling with hedge-ratio stability, mean-reversion estimation, z-score signal
  construction, bias-controlled backtesting with realistic costs (including short-leg
  borrow) and Sharpe significance testing, and robustness risk flags. Use when the
  user asks for 统计套利研究、配对交易回测、协整检验、价差均值回归建模、信号有效性验证、回测偏差排查,
  or a one-stop stat-arb strategy due-diligence report.
description_zh: 输入一组候选标的（配对、篮子或资产池），输出一份可复现、可溯源的统计套利研究报告：数据处理、配对筛选、协整与平稳性检验（训练窗
  ADF+KPSS）、价差建模与对冲比率稳定性、均值回归估计、z-score 信号构建、带偏差控制与现实成本（含融券）的回测及
  Sharpe 显著性检验、稳健性风险清单。适用于统计套利研究、配对交易回测、协整检验、价差均值回归建模、信号有效性验证、回测偏差排查等场景。
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-statistical-arbitrage-time-series
  repository_url: https://github.com/quantskills/skill-statistical-arbitrage-time-series
  project_type: skill
  collection: statistical-arbitrage-time-series
quantSkills:
  project_type: skill
  category: research
  tags:
  - statistical-arbitrage
  - pairs-trading
  - cointegration
  - time-series
  - mean-reversion
  - backtesting
  platforms:
  - claude-code
  - codex
  - openclaw
  - cursor
  status: stable
  validation_level: runnable
  maintainer_type: community
  summary_zh: 输入一组候选标的，输出一份可复现的统计套利研究报告：配对筛选、训练窗协整与平稳性检验、价差均值回归与对冲比率稳定性、信号构建、含融券成本与
    Sharpe 显著性的带偏差控制回测，一次验真伪。
  summary_en: A statistical-arbitrage skill that screens pairs, tests cointegration
    on the training window (ADF + KPSS), models spread mean-reversion and hedge-ratio
    stability, builds z-score signals, and runs a bias-controlled backtest with
    realistic costs and Sharpe significance to judge whether an apparent edge is real.
  license: GPL-3.0-only
  requires: []
---

# Statistical Arbitrage & Time Series Modeling

Use this skill to turn one candidate pair such as `["600519.SH", "000858.SZ"]`, a basket, or a screening universe into a sourced, reproducible statistical-arbitrage research dossier covering data preparation, pair selection, cointegration and stationarity testing, spread modeling, mean-reversion estimation, signal construction, bias-controlled backtesting, and robustness risk flags.

The single most important job of this skill is to decide **whether an apparent edge is real or spurious**. A pretty out-of-sample equity curve means nothing until it is statistically significant (the Sharpe has a meaningful t-statistic), free of look-ahead leakage, survives realistic costs **including the short leg's borrow/financing carry**, and is not just directional beta in disguise. Default to skepticism: design the analysis to disprove the edge, and when the evidence is only indicative, say so and recommend continued testing rather than a tradable conclusion.

## Core Workflow

1. Normalize the input. Accept an explicit pair `[A, B]`, a basket of symbols, or a universe plus a screening rule. Normalize each A-share symbol to `XXXXXX.SH` or `XXXXXX.SZ`; for other markets keep the user-provided ticker convention. Ask only when the input is ambiguous.
2. Confirm the study scope. Default to daily close prices over roughly three to five years, a chronological train/test split with the most recent ~30% held out of sample, and realistic round-trip transaction costs (commission on both legs, sell-side stamp duty where applicable, slippage, and short-leg borrow carry) unless the user specifies otherwise.
3. Read `references/statarb-guide.md` before the first dossier in a session. Use it for the stage-by-stage method map, the formulas for derived metrics, the default robustness thresholds, the report blueprint, the explicit "implemented vs. agent-supplied" split, and the appendix requirements.
4. Fetch raw price/volume data with the bundled `scripts/run_statarb.py`, whose `load_prices()` pulls from `akshare` (A-share, free, no token) or `yfinance` (US/overseas); set `source` accordingly. Do not invent symbols, fields, date ranges, or credentials. Use standard Python statistical libraries (e.g. `statsmodels`, `numpy`, `pandas`) for the analysis; install them with `pip install statsmodels akshare pandas numpy scipy` (swap `akshare`→`yfinance` for US markets). The script degrades to a numpy ADF/KPSS approximation only for offline self-test; real research must use statsmodels for exact p-values.
5. Collect evidence first, then analyze. Keep raw price tables, alignment diagnostics, test statistics, p-values, estimated coefficients, and trade logs long enough to cite the data window, sample size, and missing-data status in the final report.
6. Produce Markdown by default. If the user asks for Word, PDF, or a polished deliverable, generate the analytical content here first, then use the relevant document skill for final layout.

## Analysis Rules

- Separate facts, derived metrics, and judgment. Label every derived quantity (hedge ratio, ADF/KPSS statistics and p-values, Johansen trace, half-life, z-score, Sharpe and **its t-statistic**, max drawdown, cost-adjusted returns) with its formula and the field/series names it was computed from.
- Align series before any test. State how prices were aligned (common trading days, forward-fill policy, log vs. level), and report the usable sample size after alignment.
- Test stationarity and cointegration explicitly on the **training window**, never assume it and never test it on the full sample while estimating β on the training window only (that is look-ahead leakage). Report ADF and KPSS (opposite nulls; they should agree), the statistic, the p-value, and the critical values; add Engle-Granger/Johansen when the question warrants.
- Always separate in-sample and out-of-sample. Estimate the hedge ratio, thresholds, and any tuned parameter on the training window only, then evaluate on the untouched test window. Check **both** failure modes: in-sample good / out-of-sample bad (overfitting) **and** in-sample bad / out-of-sample good (regime dependence or luck — an edge with no in-sample support is not a stable edge).
- Report hedge-ratio stability, not just a point estimate. Show chunk-wise or rolling β and its drift; a spread whose own definition drifts is not tradable.
- Model costs as evidence, not an afterthought. State commission (both legs), sell-side stamp duty where applicable, slippage, market impact for large notionals, **and the short leg's borrow/financing carry over the holding period**. Report both gross and net. For A-shares, treat single-name short availability (`融券`) as a risk to flag, not a given.
- Report Sharpe with its significance. Give the approximate t-statistic and an overlap-deflated effective t (positions held ~half-life days are autocorrelated). A Sharpe with |t| < ~2 is not distinguishable from zero — never present it as an edge.
- Watch for leaked beta. When the hedge ratio is low and both legs co-move strongly, spread PnL may contain directional market/sector exposure; recommend or run a factor regression of spread returns before concluding the edge is alpha.
- Treat empty or insufficient results as evidence. State "无数据" or "样本不足" with the method name, window, and usable sample size instead of silently omitting the section.
- Use high/medium/low robustness levels only when a rule in `references/statarb-guide.md` or a user-provided rule is triggered. Include the triggering rule text beside each flag.
- Be honest about provenance. The bundled script does OLS β, ADF+KPSS (on the training-window spread, with full/OOS cross-checks), **returns-space hedge-ratio stability (a Chow-style first-half-vs-second-half β break test plus a noise-corrected chunk-dispersion diagnostic)**, half-life, an adaptive z-score backtest with a multi-component cost model, Sharpe t-stats with overlap deflation, and **two-level factor attribution** (strategy-PnL alpha/beta and spread-return market-neutrality vs a market proxy). Johansen, Kalman dynamic hedging, full CUSUM, and true walk-forward are agent extensions; if not run, report them as "未做" rather than implying they were done.
- End every report with this disclaimer: `本报告基于公开数据与规则化分析生成，仅供研究参考，不构成任何投资建议。`

## Resource Guide

- `references/statarb-guide.md`: stage-by-stage method map, derived-metric formulas, robustness/risk rules, the implemented-vs-agent-supplied split, report blueprint, and final QA checklist.
- `scripts/run_statarb.py`: runnable backbone — loads prices (akshare/yfinance/synthetic), tests cointegration on the training window (ADF + KPSS, with full/OOS cross-checks), estimates the hedge ratio plus its returns-space stability (Chow-style half-sample β break test + noise-corrected chunk dispersion) and half-life, builds an adaptive z-score signal, runs a bias-controlled gross/net backtest with commission + stamp duty + borrow carry, computes Sharpe with a t-statistic and overlap-deflated effective t, runs two-level factor attribution (strategy-PnL alpha/beta and spread-return market-neutrality), applies the robustness rules, and writes the Markdown report. Built-in offline self-test: `python scripts/run_statarb.py --source synthetic --mode {coint,nocoint,strong,inversion,leaked,drift}` exercises each verdict branch (e.g. `strong`→green light, `inversion`→IS/OOS-mismatch flag, `leaked`→spread-not-market-neutral flag, `drift`→hedge-ratio-break flag) without network access.

## Quality Bar

- Every material claim traces to a data source, a window/sample size, and a named test or formula.
- The hedge ratio and all thresholds are estimated on the training window only; cointegration is tested on the training-window spread; report any residual look-ahead or survivorship risk explicitly.
- The headline Sharpe is reported with its t-statistic; a sub-2 t is called out as statistically insignificant rather than presented as an edge.
- The net cost model includes the short leg's borrow carry, and A-share single-name short feasibility is flagged.
- Multiple-testing is disclosed: if many pairs were screened, say how many and whether a correction (e.g. Bonferroni, FDR) or a held-out confirmation was applied.
- Advanced steps not performed (Johansen, Kalman, Chow/CUSUM, walk-forward) are listed as not done, never implied as automatic.
- Do not overstate an edge. Prefer "可能存在均值回归", "需要样本外确认", "Sharpe 与 0 不可区分", "扣费后优势消失", and never use buy/sell language.
