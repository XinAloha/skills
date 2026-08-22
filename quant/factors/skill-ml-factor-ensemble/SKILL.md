---
name: ml-factor-ensemble
description: "Combine many existing alpha factors into one out-of-sample meta-signal with a leakage-safe rolling walk-forward and Purged & Embargoed K-fold CV (Lopez de Prado). Trains LightGBM / ElasticNet / Ridge per window, stitches OOS predictions, reports feature importance, and compares ICIR against an equal-weight baseline. Use when an agent has a panel of factor columns plus forward returns and needs a supervised factor combination without look-ahead bias."
quantSkills:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-ml-factor-ensemble
  repository_url: https://github.com/quantskills/skill-ml-factor-ensemble
  project_type: skill
  collection: factor-combination
  license: GPL-3.0-only
  category: tooling
  tags: [machine-learning, factor-combination, walk-forward, purged-cv, embargo, lightgbm, leakage]
  platforms: [claude-code, codex, openclaw]
  language: zh-en
  status: draft
  validation_level: runnable
  maintainer_type: community
  requires: []                 # 上游: 因子库提供因子列; 下游: skill-ic-analysis / skill-backtest
  summary_zh: 把上百个因子用防泄漏滚动窗口(Purged+Embargo CV)监督合成为一个样本外 meta-alpha，并给出特征重要性与对等权基线的提升。
  summary_en: Supervised, leakage-safe combination of many factors into one OOS meta-signal with purged/embargoed walk-forward.
---

# ML Factor Ensemble

Use this skill to combine many existing alpha factors into a single **out-of-sample**
meta-signal, using machine learning with strict leakage control. It sits downstream of the
factor libraries (which produce individual factor columns) and upstream of evaluation
(`skill-ic-analysis`) and backtest (`skill-backtest`).

This is **supervised combination**, fundamentally different from
`skill-factormad-debate-factor-mining` (LLM debate that *generates new factor formulas*)
and from `skill-factor-evaluate` (scores a *single* factor). Here the factors already
exist; the job is to learn their weighting without look-ahead.

## Why leakage control is the whole point

Naively fitting an ML model on a stacked panel and reading cross-validated scores
massively overstates performance, because overlapping forward-return windows leak future
information into the training folds. This skill enforces:

- **Rolling walk-forward**: train on `[t-train, t]`, predict only `(t, t+step]`, roll.
- **Purging**: drop training samples whose label window overlaps the test window.
- **Embargo**: additionally drop a buffer of samples right after each test window.

(Both purge and embargo follow López de Prado, *Advances in Financial Machine Learning*.)

## Models

- `ridge` / `elasticnet` — linear, fast, interpretable coefficients (robust default).
- `lightgbm` — gradient-boosted trees for non-linear factor interactions + SHAP/gain importance.

## Core Workflow

1. **Inputs**: a long panel `date, symbol, <factor_1..factor_k>, fwd_ret` (forward return
   horizon H, computed leak-free: T+1 open → T+1+H open).
2. **Split**: generate purged + embargoed walk-forward folds for horizon H.
3. **Train/predict**: fit the chosen model per window; collect OOS predictions only.
4. **Evaluate**: OOS Rank IC / ICIR of the combined signal vs an equal-weight-of-zscored-
   factors baseline; per-window IC stability; feature importance.
5. **Output**: OOS combined-score panel + diagnostics report.

## Output Contract

Produce:

- `combined_signal.csv` — `date, symbol, score` (OOS predictions only, no in-sample rows)
- `ensemble_report.md` — model, fold layout, OOS ICIR vs baseline, importance ranking, caveats
- a one-paragraph fact/caveat summary

## Data Sources

- Factor columns: supplied by the caller (factor libraries / custom factors).
- Forward returns: `panda_data.get_stock_daily` open-to-open, or `skill-pandadata-warehouse`.

## Limitations & Risk Boundary

- **Out-of-sample ≠ live**: even leak-free CV overstates live performance via survivorship,
  universe drift, and multiple-testing on factor selection. Treat ICIR as an upper bound.
- Tree models can overfit small panels; prefer linear models when factors are few or noisy.
- Purge/embargo must match the true label horizon H — a mismatch silently reintroduces leakage.
- This skill does not place orders and is **not investment advice**.
- Community Project; validate outputs against the cited data and local review requirements.

## ✅ Quality Bar

Before delivering artifacts (degrade & disclose rather than pass silently):

- **Traceable**: every key figure maps to a specific Pandadata interface + data date; missing data goes to `degraded[]` — never fabricate or pass approximations off as real values.
- **Transparent degradation**: when any source is empty/limited, the report states it and lowers confidence.
- **Consistent conventions**: units, frequency, and benchmark conventions are stated explicitly.
- **Research only**: artifacts are for research/education, not investment advice, with no return promises.
- OOS metrics only via purged & embargoed walk-forward; always report OOS-vs-baseline lift, never in-sample curves alone.

## References

- `references/leakage-control.md` — purge/embargo math, fold construction, common leakage traps.
- `references/source_boundary.md` — allowed data sources.
