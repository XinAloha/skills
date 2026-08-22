# Statistical Arbitrage Guide

Read this guide when generating or revising a statistical-arbitrage dossier. Use it as a compact operating checklist, not as a replacement for the exact data-source documentation or the statistical-library references.

The single job of this skill is to decide **whether an apparent edge is real or spurious**. Default to disproof, not confirmation: a pretty out-of-sample equity curve is not evidence until it is statistically significant, leakage-free, survives realistic costs (including short-side borrow), and is not just directional beta in disguise. When the data is only indicative, say so and stop.

## Default Scope

- Target: one candidate pair `[A, B]`, a small basket, or a universe plus a screening rule.
- Price window: daily close (and volume when needed) over roughly three to five years unless the user requests another window.
- Split: chronological train/test split with the most recent ~30% held strictly out of sample; never tune on the test window.
- Costs: realistic round-trip costs — commission (both legs), sell-side stamp duty where applicable, slippage, **and the short leg's borrow/financing carry over the holding period** (add market impact for large notionals). For A-shares, treat single-name short availability itself as a risk, not a given.
- Output: Markdown report unless the user requests HTML, Word, PDF, or another deliverable.

## What The Bundled Script Computes vs. What The Agent Must Add

Be honest in the report about provenance. `scripts/run_statarb.py` implements:

- price load (akshare/yfinance/synthetic), calendar alignment, log prices, usable-sample reporting;
- OLS hedge ratio on the **training window only**, AR(1) half-life;
- **chunk-wise β** as a cheap structural-stability proxy;
- ADF + KPSS, run on the **training-window spread** for the headline decision (full-sample and OOS shown only as a cross-check);
- a vectorized z-score backtest with an adaptive lookback, in/out-of-sample split, a multi-component cost model, and completed-round-trip counting;
- Sharpe with an approximate **t-statistic** and an overlap-deflated effective t;
- the robustness rule engine below.

The following are **NOT** in the script and must be added by the agent when the question warrants, and must never be reported as "automatically done": Johansen cointegration, Kalman/dynamic hedge ratio, a full Chow/CUSUM break-test suite, and true walk-forward re-estimation. If the agent did not run them, say "未做" with the reason.

**Now implemented in the script** (previously agent-only): factor attribution at two levels — (a) the strategy's OOS net PnL regressed on a market proxy (reports market β, residual α, and their t-stats; insignificant residual α flags an edge that may be leaked beta), and (b) the spread's daily returns regressed on the market proxy (market-neutrality check that directly addresses the low-hedge-ratio / co-moving-legs concern). The market proxy is CSI300 (`sh000300`) for akshare, SPY for yfinance, and an independent synthetic factor in self-test mode; if no proxy is available the report states attribution was not done.

## Stage Map

| Stage | Methods / Tests | Use |
|---|---|---|
| Data preparation | price load via `scripts/run_statarb.py`, calendar alignment, log-price transform, return series, gap/outlier audit | Build clean, aligned, same-currency series; report usable sample size after alignment. |
| Pair / universe selection | correlation screen, sector/cluster filter, distance method (SSD), preliminary cointegration scan | Narrow to economically related pairs before formal testing; record how many pairs were screened (multiple-testing exposure). |
| Cointegration & stationarity | ADF (`adfuller`) + KPSS (`kpss`) on the **training-window** spread; Engle-Granger (`coint`) / Johansen (`coint_johansen`) when the agent adds them | Decide whether a stationary tradable spread exists; report statistic, p-value, and critical values. Correlation is not cointegration. |
| Spread modeling & mean reversion | OLS/TLS hedge ratio (train only), chunk-wise/rolling/Kalman β, AR(1)/OU fit, half-life | Build the spread, estimate hedge ratio + reversion speed; report β stability. |
| Signal construction | rolling mean/std, z-score with lookback **≥ half-life**, entry/exit/stop bands, holding cap | Convert the spread into signals with explicit, past-only thresholds. |
| Backtesting & bias control | vectorized backtest, train/test isolation, walk-forward (agent), full cost model incl. borrow, structural-break tests (agent) | Evaluate out of sample with realistic frictions; check parameter drift. |
| Performance & risk | annualized return, Sharpe **+ its t-stat**, Sortino, max drawdown, Calmar, hit rate, holding period, turnover | Summarize gross and net performance, downside profile, and statistical significance. |

## Metrics To Derive

State the formula and the series/field names used whenever a metric is derived.

- **Hedge ratio (β)**: OLS `log(A) = α + β·log(B) + ε`, estimated on the training window only; report chunk-wise/rolling β and its drift `(max−min)/|mean|`.
- **Spread**: `spread_t = log(A_t) − β·log(B_t)`; report the construction used.
- **Cointegration**: ADF statistic + p-value and KPSS statistic + p-value on the **training-window** spread; ADF and KPSS test opposite nulls and ideally agree (ADF rejects unit root *and* KPSS fails to reject stationarity). Add Engle-Granger/Johansen when needed.
- **Mean-reversion half-life**: AR(1) `Δspread_t = a + b·spread_{t−1} + e_t`, `half-life = −ln(2) / ln(1+b)`. Flag half-lives too long to be tradable after carry.
- **Z-score**: `z_t = (spread_t − rolling_mean_t) / rolling_std_t`; lookback uses only past data and should be **at least the half-life** (a window shorter than the half-life manufactures false crossings).
- **Performance**: `Sharpe = mean(daily PnL)/std × √252`; Sortino; max drawdown; `Calmar = annual return / |max DD|`; hit rate; holding period; turnover.
- **Sharpe significance**: approximate `t ≈ Sharpe_annual × √years`. Because positions are held for ~half-life days, daily PnL is autocorrelated and this t is optimistic; also report an overlap-deflated `t_eff ≈ Sharpe_annual × √(years / half-life)` and the implied number of independent bets ≈ `days / half-life`. **A Sharpe with |t| < ~2 is not distinguishable from zero — do not call it an edge.**
- **Cost-adjusted edge**: per-round-trip edge minus modeled round-trip cost = commission (both legs) + sell-side stamp duty + slippage + short-leg borrow carry over the holding period; report gross and net, and the breakeven cost.

## Robustness / Risk Rules

Use these defaults unless the user supplies thresholds. If an input is missing (no OOS window, no cost assumption), downgrade the rule to a qualitative watch item and say what is missing.

| Level | Trigger |
|---|---|
| High | No cointegration: spread ADF p-value > 0.10 (and/or KPSS rejects stationarity on the training-window spread). |
| High | Does not revert: AR(1) coefficient ≥ 0 (half-life = ∞). |
| High | Half-life > 60 trading days — reversion too slow to survive carry. |
| High | Hedge ratio breaks: a Chow-style first-half-vs-second-half β test (in log-return space) is significant (|z| ≥ 4) with a material relative gap (> 0.2). Medium at |z| ≥ 2.5. A secondary noise-corrected chunk-dispersion `excess_drift` is reported as color. Returns space is used because chunk OLS on I(1) price levels gives spurious instability when the regressor barely moves within a window. Prefer a full Chow/CUSUM break test as the authoritative check. |
| High | Edge vanishes after costs: net OOS Sharpe ≤ 0, or per-trade edge below modeled round-trip cost. |
| High | **Edge has no in-sample support: in-sample net Sharpe ≈ 0 or negative while out-of-sample net Sharpe is clearly positive** — the apparent edge exists only out of sample, which points to regime dependence or luck, not a stable relationship. (This is the failure mode the engine previously missed.) |
| High | Overfitting: OOS net Sharpe < ~half of in-sample net Sharpe. |
| High | **Leaked beta: spread daily returns load significantly on the market (|t|≥1.96) with material R² (≥0.10)** — the spread is not market-neutral, so "edge" may be directional beta. The script also flags HIGH when the *strategy's* net PnL has significant market β but insignificant residual α. |
| High (A-share) | Single-name short feasibility: individual A-share `融券` is often unavailable, capacity-constrained, or expensive and unstable; net results assuming a freely shortable leg may be optimistic. |
| Medium | Weak cointegration: spread ADF p between 0.05 and 0.10, or ADF and KPSS disagree. |
| Medium | **Sharpe not significant: out-of-sample Sharpe |t| < ~1.96** (and worse once overlap-deflated). |
| Medium | **Residual alpha not significant: after regressing strategy PnL on the market, |t(α)| < 1.96** — what looks like edge survives only as noise once beta is removed. |
| Medium | **Spread mildly non-neutral: market β significant but R² < 0.10** — modest directional leakage. |
| Medium | Low power: fewer than ~30 completed round-trip trades in the test window. |
| Medium | Data snooping: many pairs screened without a multiple-testing correction or a held-out confirmation set. |
| Medium | Half-life between 20 and 60 days, or a Chow-style β break with 2.5 ≤ |z| < 4. |
| Medium | z-score lookback shorter than the half-life. |
| Low | Minor data gaps, a single outlier, or a borderline single metric; record in the appendix rather than the headline flag list. |

Green light (verdict = "证据指向可进一步研究") requires **all** of: ADF p ≤ 0.05 on the training-window spread, finite half-life ≤ 60 days, OOS net Sharpe |t| ≥ 1.96, ≥ 30 completed round-trips, and (no attribution OR significant residual α). Slow-reverting or thin-sample pairs will therefore usually be rejected — that is the tool working as a disproof engine, not a bug.

Name combined signals explicitly, e.g. `协整边际 + Sharpe不显著`, `半衰期过长 + 扣费后归零`, `样本外有效但样本内无效 + 样本量不足`.

## Report Blueprint

Use this chapter order unless the user asks for a custom structure:

1. `摘要与结论`: a one-line overall verdict (tradable-evidence vs. reject/keep-disproving), the candidate(s), in-sample vs. out-of-sample net result **with the Sharpe t-stat**, net-of-cost edge, and the top robustness flags.
2. `数据与标的池`: symbols, market, price window, alignment policy, usable sample size, gaps/outliers handled.
3. `配对筛选`: screening rule, candidates evaluated, why this pair; disclose multiple-testing exposure.
4. `协整与平稳性检验`: ADF + KPSS on the **training-window** spread (headline) with full-sample/OOS as cross-checks; Engle-Granger/Johansen if run; the cointegration conclusion.
5. `价差建模与均值回归`: hedge-ratio estimation **and returns-space stability (Chow-style half-sample β break + `excess_drift`)**, spread construction, AR(1)/OU fit, half-life with its formula.
6. `信号构建`: z-score lookback (≥ half-life), entry/exit/stop thresholds, holding cap, signal description.
7. `回测与偏差控制`: in-sample vs. out-of-sample, the full cost model (commission + stamp duty + slippage + borrow carry), gross vs. net, **Sharpe t-stat / effective independent bets**, **factor attribution (strategy α/β + spread market-neutrality)**, and any structural-break / walk-forward work (or its absence).
8. `稳健性与风险信号清单`: table with level, signal, triggering rule, evidence, window/sample, and the test or formula used.
9. `方法附录`: stage-by-stage source table with data window, usable rows, test names, key statistics, and caveats — including an explicit list of advanced steps **not** performed.

## Evidence And Output Requirements

- Include at least one source/method table in the appendix: `分析阶段`, `数据来源/方法`, `查询或样本窗口`, `可用样本量`, `关键统计量/参数`, `备注`.
- For each robustness flag, include the test name, statistic/p-value, and window in the same row or the next sentence.
- Report cointegration on the training window, never silently on the full sample alongside a train-only β.
- Always report a Sharpe **with its t-statistic**; never present a Sharpe number as an edge without its significance.
- Report both gross and net; the net cost model must include short-leg borrow carry when a leg is shorted.
- If a section has no usable data or insufficient sample, keep the heading and state method, window, and what is missing.
- Disclose multiple-testing exposure when a universe was screened.
- Keep the tone analytical and non-promotional; avoid buy/sell language. Prefer "可能存在均值回归", "需要样本外确认", "Sharpe 与 0 不可区分", "扣费后优势消失".

## Final QA Checklist

- Symbols and the studied pair are normalized and displayed consistently.
- Data window and usable sample size appear in each major section.
- Derived metrics have formulas or field/series names.
- Cointegration is tested **on the training window** (ADF + KPSS), reported with critical values, not assumed.
- Hedge ratio and thresholds were estimated on the training window only; an untouched OOS result is reported.
- The Sharpe is reported with its t-statistic, and a sub-2 t is called out as non-significant.
- Costs are modeled including short-leg borrow; both gross and net are shown.
- In-sample/out-of-sample inversion (good OOS, bad IS) is checked, not just IS-good/OOS-bad overfitting.
- For A-shares, single-name short feasibility is flagged.
- Advanced steps not performed (Johansen, Kalman, Chow/CUSUM, walk-forward) are listed as not done, not implied.
- Multiple-testing exposure is disclosed when a universe was screened.
- Empty or insufficient data is disclosed rather than hidden.
- Final disclaimer is present exactly as required by `SKILL.md`.
