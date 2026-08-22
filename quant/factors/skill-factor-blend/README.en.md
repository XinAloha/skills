# skill-factor-blend

[简体中文](./README.md) | [English](./README.en.md)

Multi-factor signal-level blending: redundancy removal via correlation matrix and top-bucket overlap → three weighting schemes (equal/ICIR/score) → daily cross-sectional z-score synthesis → composite re-evaluation.

`role: skill` `output: composite_signal + blend report` `paradigm: signal-level merge, NOT portfolio allocation`


---

`skill-factor-blend` is a **multi-factor signal blending Skill** provided by PandaAI Quant Skills. It merges multiple evaluated cross-sectional factor signals into one composite alpha signal.

> ⚠️ **This is signal-level merging, NOT portfolio-level**: output is `composite_signal[date × symbol]` (cross-sectional z-score). No capital allocation, position sizing, or portfolio weights involved.

## 🎯 What This Skill Solves

Got 10 factors with IC > 0 — can you just equal-weight average them?

- 5 of 10 factors are highly correlated → equal-weight overexposes to one signal family
- ICIR varies widely → equal-weight lets noisy factors dilute strong ones
- Blind merging → composite turnover could be 3× that of individual factors

**Without blend analysis, the composite factor can underperform the best single factor.**

## ⚡ 8-Step Workflow

```
1. Validate input factor contracts: shape, horizon, label, universe, z-score, coverage
2. Read ScoreReport per factor: score, rank_ic_ir, Sharpe, MDD, turnover
3. Filter unusable: score ≤ 0, unstable IC, deep MDD, excessive turnover
4. Compute inter-factor correlation matrix + top-bucket Jaccard overlap
5. De-duplicate: same cluster (corr > 0.7) — keep only highest ICIR
6. Select weighting: equal / score-weighted / IR-weighted
7. Generate composite_signal = Σ w_i * factor_i, daily z-score
8. Re-evaluate composite via factor-evaluate
```

## 🗃️ Input Requirements

- Factor library: multiple `[date, symbol, factor_value]` parquet files
- Each factor must have an independent evaluation report (IC, Sharpe, MDD, turnover, coverage)
- All factors must share the same horizon, universe, and z-score convention

## 📦 Project Script

```python
# Load → de-duplicate → weight → synthesize
factors = load_all("data/factors/F*.parquet")
survivors = remove_redundant(factors, corr_threshold=0.7)
composite_equal = make_equal_weight_composite(survivors)
composite_icir   = make_icir_weighted_composite(survivors)
composite_score  = make_score_weighted_composite(survivors)
```

Output:
- `data/composite_equal.parquet` — equal-weight composite
- `data/composite_ICIR-weighted.parquet` — ICIR-weighted composite
- `data/composite_score-weighted.parquet` — score-weighted composite
- `data/combine_report.json` — diagnostic report

## 🆚 vs Portfolio Combination

| | Factor Blending (this Skill) | Portfolio Combination |
|---|---|---|
| **Layer** | Signal-level | Portfolio-level |
| **Output** | `composite_signal[date × symbol]` | Position vector or NAV curve |
| **Core problem** | De-duplicate → weight → synthesize one signal | Risk budget → optimizer → allocate capital |

## 🔗 Pipeline Position

```
Factor Evaluation → Orthogonalize → Decay Analysis → Blending (this Skill) → Backtest
```

Final signal-processing step before backtesting, after decay analysis.

## 📜 License

GPL-3.0. Copyright (C) 2026 QuantSkills.
