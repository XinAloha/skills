# Backtesting & Bias Avoidance Guide

Read this guide when generating or revising a backtest-and-bias-audit dossier. Use it as a compact operating checklist, not as a replacement for a backtesting textbook or the exact library documentation.

## Default Scope

- Target: one strategy on one asset or a small universe; default to a momentum demonstration on synthetic data when the user has no specific strategy, so the "true" edge is known.
- Engine: vectorized, next-bar execution, explicit decision/execution lag, 252-day annualization.
- Split: chronological train/test with the most recent ~30% held strictly out of sample; never tune on the test window.
- Costs: realistic round-trip costs (commission + spread + slippage) applied per unit of turnover, with a cost-sensitivity sweep.
- Output: Markdown report unless the user requests HTML, Word, PDF, or another deliverable.

## Engine-Construction Rules

The engine is where look-ahead bias is born or prevented. Enforce all of these:

- **Decision vs. execution lag.** A signal known at the close of bar `t` may only act on the return from `t` to `t+1`. In code: `pnl_t = position_{t-1} · return_t`. Forgetting this single shift is the most common look-ahead bug.
- **Past-only signals.** Every input to the signal at time `t` must use data with timestamp ≤ `t`. Rolling statistics must use trailing windows with no centering.
- **No same-bar fills from the deciding price.** Do not assume you transact at the very close that generated the signal unless that is realistic for the strategy and stated.
- **Costs on turnover, including impact.** Charge a linear cost proportional to `|position_t − position_{t-1}|` plus a square-root-law market-impact term; report gross and net, and a cost-sensitivity sweep.
- **Point-in-time data.** Prices, fundamentals, and index membership must reflect what was actually known then, not later-restated values.

## Bias Taxonomy And How It Is Tested

| Bias | What it is | How this skill tests / surfaces it |
|---|---|---|
| Look-ahead | Using information not yet available at decision time (e.g. forgetting the execution lag). | Run the same signal clean (lagged) and leaky (unlagged) and quantify how much the leak inflates the Sharpe. |
| Survivorship | A universe that excludes delisted/bankrupt names, inflating returns. | Qualitative checklist item: state whether delisted names were included and whether membership is point-in-time. |
| Overfitting / data-snooping | Choosing a parameter or strategy by mining many trials on the same data. | Measure PBO via CSCV across many IS/OOS splits, and deflate the selected Sharpe for the number of trials (DSR); report both rather than relying on a single split. |
| Cost neglect | Ignoring commission, spread, slippage, or market impact. | Cost-sensitivity sweep: report net performance across cost levels and the breakeven cost. |
| Multiple testing | Reporting the best of many strategies without correction. | Disclose how many configurations were tried; recommend correction or a held-out confirmation set. |

## Metrics To Derive

State the formula and inputs used whenever a metric is derived.

- **Strategy return**: `r_t = position_{t-1} · asset_return_t − cost_t` (next-bar execution, net of cost).
- **Cost model**: `cost_t = linear · |Δposition_t| + impact · |Δposition_t|^1.5` — a linear commission/spread term plus a square-root-law market-impact term (stylized; without ADV/volume it is an approximation, state this).
- **Sharpe significance (two lenses, report both)**:
  - *HAC (Newey-West / Lo 2002)*: correct the Sharpe standard error for serial correlation. Long-run variance `S = γ0 + 2·Σ_{k=1}^L (1−k/(L+1))·γk` (Bartlett kernel), bandwidth `L` set to the signal horizon; `SE(mean) = √(S/T)`, `t = mean/SE`. Report the **variance-inflation factor `S/γ0`** (not its square root) and the effective sample size `N_eff = T / (S/γ0)`, so that `N_eff = T / factor` is directly verifiable. The factor is window-specific (IS and OOS can differ because their realized autocorrelation differs). For strategies whose daily P&L is sticky-position × near-iid return, this daily correction is often modest.
  - *Per-bet / per-segment*: aggregate daily P&L into one observation per holding segment (a maximal run of constant position); compute the Sharpe and t-statistic on the `n_bets` segment returns. This reflects the true number of independent directional bets and is the binding lens when within-segment noise is small. The two lenses are complementary — which is wider depends on the segment-level noise, so report both rather than picking one.
- **Probability of Backtest Overfitting (PBO, CSCV)**: build a T×N matrix of the N candidate strategies' returns; split the rows into S submatrices; over all `C(S, S/2)` ways of choosing half as in-sample, pick the in-sample-best strategy and find its out-of-sample rank; `PBO = fraction of splits where the IS-best lands in the bottom half OOS`. PBO near or above 50% indicates the selection is driven by overfitting. Report a **bootstrap CI on PBO** (resampling the combinations; note they overlap, so the CI is approximate and narrow), and — for synthetic data, where the generating process is known — the **distribution of PBO across hundreds of independent paths** plus a false-discovery rate, since the single-path PBO is itself one draw from that distribution.
- **Deflated Sharpe Ratio (DSR, Bailey & López de Prado 2014)**: deflate the selected strategy's Sharpe for the number of trials `N` and the return skewness/kurtosis; `DSR = Φ( (SR − SR0)·√(T−1) / √(1 − skew·SR + (kurt−1)/4·SR²) )`, where `SR0` is the expected maximum Sharpe under the null given `N` trials. DSR is the probability the true Sharpe is positive; below ~0.95 it is not significant. **DSR is an optimistic upper bound**: `N` must include all researcher degrees of freedom (cost levels, HAC bandwidth, long/short rules tried), not just the disclosed window scan, so the reported DSR overstates significance.
- **Annualized return**: `mean(r) · 252` (arithmetic; state if geometric).
- **Sortino / Max drawdown / Calmar / Hit rate / Turnover**: as standard; report alongside Sharpe.
- **Look-ahead inflation**: `Sharpe(leaky) − Sharpe(clean)` for the same signal, each with its t-statistic.

## Audit Rules

Use these defaults unless the user supplies thresholds. If an input is missing, downgrade the rule to a qualitative checklist note and say what is missing.

| Level | Trigger |
|---|---|
| High | PBO > 50% — the in-sample-best strategy is more likely than not to underperform out of sample (overfitting). |
| High | Deflated Sharpe Ratio < 95% — after correcting for the number of trials, the Sharpe is not significantly positive. |
| High | Net (after-cost) Sharpe ≤ 0 while gross is positive — the edge is entirely eaten by costs and impact. |
| High | Look-ahead inflation is large: the leaky Sharpe is materially above the clean Sharpe, confirming the result depends on a leak. |
| Medium | Out-of-sample Sharpe 95% CI contains zero (t < 1.96, HAC) — no significant net edge (report as "无显著净边际", not "策略无效"). |
| Medium | Few independent bets: fewer than ~30 holding segments out of sample, or a small HAC N_eff — the daily sample size overstates the real information content. |
| Medium | 25% < PBO ≤ 50% — moderate overfitting risk. |
| Medium | Fewer than ~30 completed trades over the test window — insufficient statistical power. |
| Medium | High turnover makes net performance very sensitive to the cost/impact assumption. |
| Medium | Survivorship or point-in-time status is unknown or unverified for a real-data universe. |
| Low | A single minor diagnostic with limited impact; record in the appendix rather than the headline flag list. |

For combined signals, name the combination explicitly, for example `PBO高 + DSR不显著` or `扣费后归零 + 高换手`.

## Report Blueprint

Use this chapter order unless the user asks for a custom structure:

1. `摘要与结论`: three to six bullets — the honest out-of-sample, net-of-cost result; how much look-ahead would inflate it; the in-sample-vs-out-of-sample gap; the key audit flags.
2. `数据与策略设定`: asset/universe, signal rule, period, sample size, and the train/test split.
3. `回测引擎设定`: decision/execution lag, execution convention, annualization, and the cost model — the engine-construction choices that prevent look-ahead.
4. `偏差检测：前视偏差`: clean (lagged) vs. leaky (unlagged) results for the same signal, each with its t-statistic and 95% CI, and the quantified inflation.
5. `过拟合检验：CSCV/PBO`: the Probability of Backtest Overfitting over many IS/OOS splits, plus a single-path scan table (each value's IS and OOS Sharpe) as intuition; state the number of trials.
6. `成本敏感性`: net performance across linear-cost levels (with market impact included) and the breakeven cost.
7. `绩效与显著性`: the clean strategy's full metric set with the Sharpe's t-statistic and 95% CI, and the Deflated Sharpe Ratio.
8. `偏差审计清单`: table of high/medium/low flags (PBO, DSR, significance, look-ahead, cost) plus the qualitative checklist (survivorship, point-in-time).
9. `方法附录`: stage-by-stage table with inputs, windows, parameters, and caveats.

## Evidence And Output Requirements

- Include at least one source/method table in the appendix with columns similar to: `分析阶段`, `方法`, `窗口/样本`, `关键参数`, `结果`, `备注`.
- For each audit flag, include the metric, the numeric evidence, and the triggering threshold in the same row or the immediately following sentence.
- Always present the look-ahead-free, out-of-sample, net result as the headline, with its t-statistic and 95% CI; show gross/in-sample/leaky only as contrast.
- Always report PBO and DSR when a parameter was selected from a scan, and report multiple performance metrics, never a single number alone.
- Discipline the wording: when the out-of-sample result is not significant, write "无显著净边际", not "策略无效".
- Prefer concise tables over long prose when comparing windows, parameters, or cost levels.
- Keep the final tone analytical and non-promotional; avoid buy/sell language.

## Final QA Checklist

- The headline number is look-ahead-free, out-of-sample, and net of costs, with a t-statistic and 95% CI.
- Decision/execution lag and the cost model (linear + market impact) are stated.
- The look-ahead test shows clean vs. leaky with quantified inflation and significance.
- Overfitting is assessed with CSCV/PBO (multi-path); any scanned parameter reports the number of trials and a Deflated Sharpe Ratio.
- Survivorship and point-in-time status are stated (or flagged as unknown) for real data.
- Multiple performance metrics are reported, not a single number.
- Wording follows the discipline: "无显著净边际" rather than "策略无效" when out-of-sample is not significant.
- High/medium/low flags cite the triggering rule.
- Final disclaimer is present exactly as required by `SKILL.md`.
