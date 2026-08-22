# Methodology — Overseas Equity Factor Mining

The discovery loop for HK/US cross-sectional alpha factors: how to scope a run, build
point-in-time panels, generate candidates, compute cross-sections, and validate each by
rank IC, IC decay, and turnover. The **exact Pandadata call contract (parameters, field
names, symbol formats) comes from the `skill-pandadata-api` skill**; this file describes
the computations and the pitfalls, and `references/pandadata-overseas-map.md` gives the
HK↔US method routing.

## 0. Scope a run first

Fix these before pulling any data and echo them in the report's 摘要:

| Choice | Options / rule |
|---|---|
| Market | **HK or US, never mixed.** Method family and currency follow the market. |
| Universe | An explicit symbol list, or an index-constituent set. State it and its size. |
| Rebalance calendar | From `get_trade_cal(exchange=HK|US)`; e.g. month-end or every 20 trading days. |
| Forward-return horizons | e.g. 5 / 10 / 20 trading days. Drives both IC and decay. |
| Factor families | momentum/reversal, value/quality, liquidity/turnover (subset the user asked for). |
| Compute budget | candidates × rebalance dates × universe size. Keep the batch small and named. |

## 1. Point-in-time panel construction (no look-ahead, no survivorship)

For each rebalance date `t`:

1. **Price/volume**: `get_hk_daily` / `get_us_daily` up to and including `t` (for momentum,
   reversal, volatility, liquidity). Never read a bar dated after `t`.
2. **Identity / sector**: `get_hk_detail` / `get_us_detail` for the peer-group key.
3. **Fundamentals (long)**: `get_stock_operating_indicator` / `get_stock_operating_metric`
   — one row per `item_name` per report; requires `start_year` and `end_year`.
4. **Fundamentals (wide)**: `get_stock_mktfin_indicator` / `get_stock_mktfin_metric` —
   latest market-financial snapshot (valuation multiples, yields).
5. **Peer median**: `get_stock_industry_median` (HK) / `get_stock_sector_median` (US).

Point-in-time rules:

- **No look-ahead**: only use a fundamental report whose `financial_period_end_date` (and,
  where available, disclosure/announcement date) is on or before `t`. A factor computed at
  `t` may never see a figure that was not yet public at `t`.
- **No survivorship**: the universe at `t` is the set of symbols listed/alive at `t`; do not
  backfill today's index membership into the past or silently drop delisted names.
- **Forward return**: for horizon `h`, the label at `t` is the return from `t` to the
  `h`-th following trading date (from the same calendar). Align so no return overlaps its
  own formation window.

## 2. Report-caliber dedup for long fundamental tables

`get_stock_operating_indicator` / `get_stock_operating_metric` return **long** rows keyed by
`item_name`, with multiple report calibers per period. Before computing any fundamental
factor:

1. Filter to **one report basis** — default `report_type == "Recent To Recent"`; within it
   prefer `data_type == "Restatement"` where present, else `Original`. State the choice.
2. Pivot `index=symbol, columns=item_name, values=item_num` for a single aligned period.
3. Carry `item_currency`, `item_unit`, `is_percent_item` per item so code never
   cross-currency compares and never double-scales a percentage.
4. Compare an item only across names that actually report it (banks, REITs, industrials
   carry different `item_name` sets). Never impute a missing `item_num`.

For the wide market-financial table, pick **one convention and hold it across the whole
cross-section**: TTM vs non-TTM (default TTM), non-issue vs `_issue`, and a single PE base
(`curr_pe_dil_excl` / `_norm` / `_incl`).

## 3. Candidate factor families (examples, not a fixed set)

Generate a small named batch; each candidate is a formula + inputs + expected sign.

| Family | Example candidate | Inputs | Expected sign |
|---|---|---|---|
| Momentum | 12-1 month return (skip most recent month) | daily close | + |
| Reversal | short-horizon (5-day) return | daily close | − |
| Value | earnings yield = 1 / `curr_pe_dil_excl_ttm`; EV/EBITDA_TTM inverse | mktfin wide | + (cheap) |
| Quality | ROE / margin from operating items, peer-normalized | operating long + median | + |
| Liquidity | Amihud illiquidity = mean(|ret| / turnover value) | daily close + turnover | + (illiq premium) |
| Turnover | avg turnover ratio over window | daily volume, shares | context-dependent |

Fundamental / quality / value factors must be expressed **relative to the peer median**
(§4). Price-based factors are already cross-sectionally comparable within one market but
should still be winsorized and standardized (§5).

## 4. Peer normalization (mandatory for fundamental factors)

ROE, margins, and valuation multiples are **not comparable across sectors**. For each
fundamental candidate:

- Subtract the peer median (`get_stock_industry_median` / `get_stock_sector_median`) or take
  a within-group z-score / percentile.
- Never rank a fundamental percentile across different industries, and never across HK vs US.
- If a peer set is tiny (< 5 names), say so — percentiles are unstable; report levels + the
  median instead of a rank.

## 5. Cross-section hygiene per rebalance date

- **Winsorize** each raw factor (e.g. 1st/99th percentile) to tame outliers.
- **Standardize** to a cross-sectional z-score (or rank) within the market so factors are
  comparable across dates.
- Handle NaNs explicitly: a name missing an input is dropped from that factor's
  cross-section for that date, not imputed to zero.

## 6. Validation math

For a factor `f` and forward return `r_h` at horizon `h`:

- **Rank IC (per date)** = Spearman rank correlation between the cross-section `f(t)` and
  `r_h(t)`. Spearman (rank) is preferred over Pearson because factor scales differ and
  monotonic association is what matters.
- **Mean IC** = average of per-date rank ICs over the rebalance dates.
- **IC std** = standard deviation of per-date ICs.
- **IC IR** = mean IC / IC std (higher = more stable signal). This is the default ranking key.
- **Hit rate** = fraction of dates with IC of the expected sign.
- **IC decay** = the mean-IC profile across horizons (5 → 10 → 20 days). A factor whose IC
  collapses to ~0 by 10 days is a very-short-horizon signal; note it. A monotone, slowly
  decaying profile is more robust.
- **Turnover** = average fraction of the top (and bottom) bucket names that change from one
  rebalance to the next. High IC with ~100% turnover per period may be uncapturable after
  costs; report it, do not hide it.

Guidance (not thresholds to over-fit): treat |mean IC| ≳ 0.03 with IC IR ≳ 0.3 and moderate
turnover as "worth keeping and studying further," but always in-sample and descriptive.

## 7. Ranking rule

Default: rank surviving candidates by **IC IR**, penalized by turnover (e.g. subtract a
turnover penalty, or break ties toward lower turnover). State whichever rule you use in the
排名 section. Report the **top-K** with full stats; keep discarded candidates in a short
"rejected" note with the reason (near-zero IC, sign flip, fast decay, extreme turnover).

## 8. Differentiation

- `skill-hk-us-fundamental-factor` **applies** a fixed, peer-standardized fundamental factor
  set to describe who is cheap/expensive/high-quality. This skill **discovers** factors and
  screens them by IC / decay / turnover — a mining loop, not an application.
- The A-share `quant-factor-*` collections are OHLCV factor libraries for A-shares; this
  skill is overseas (HK/US) and mixes price with fundamentals.

## 9. Pitfalls

- **Cross-sector fundamental comparison** — always normalize within peer group via `*_median`.
- **Report-caliber double counting** — dedup the long operating table to one restatement
  caliber before pivoting; mixing calibers inflates or corrupts a factor.
- **Look-ahead / survivorship** — enforce point-in-time report dates and as-of-date universe.
- **HK vs US method routing** — the two markets use different method names (event vs activity,
  indicator vs metric, median methods differ); route by market and never mix the two.
- **Currency mixing** — HKD and USD figures are never summed or compared; keep one market.
- **IC on a tiny cross-section** — with very few names, IC is noisy; state universe size.
- **Overlapping forward returns** — space rebalances by at least the horizon, or treat
  overlapping-window IC series as autocorrelated when reading IC IR.

## 10. Graceful degradation

- If a Pandadata pull is empty for a window, keep the section and write
  `无数据（<method>，<market>，<window>）`; optionally fall back to Yahoo Finance for
  price/volume only, labeled as a third-party fallback.
- If peer medians are missing, report fundamental factors as raw levels flagged
  non-comparable, and skip their cross-sector ranking.
- If the universe is too small for a stable IC, report per-name factor levels and the median,
  and say the IC estimate is unreliable.
- Never fabricate an IC, a decay curve, or a turnover number to fill a gap.
