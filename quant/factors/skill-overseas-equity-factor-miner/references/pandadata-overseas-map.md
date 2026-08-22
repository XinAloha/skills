# Pandadata Overseas Method Map — HK ↔ US Routing

Method routing for the factor-mining loop. **This skill never calls Pandadata directly** —
it delegates to `skill-pandadata-api`, which owns the exact parameters, field names, and
symbol formats. Use only the method names below; do not invent a signature. Route strictly
by market: HK methods for Hong Kong, US methods for US, and never mix the two markets or
their currencies.

## Method families used by this skill

| Purpose | HK method | US method | Key params / notes |
|---|---|---|---|
| Daily price/volume | `get_hk_daily` | `get_us_daily` | `symbol`, date range `YYYYMMDD`; momentum / reversal / liquidity / turnover inputs |
| Identity & sector | `get_hk_detail` | `get_us_detail` | `symbol`; peer-group key, listing status |
| Standardized operating indicators (LONG) | `get_stock_operating_indicator` | `get_stock_operating_metric` | `start_year`, `end_year` (both required), `symbol`, `fields`; one row per `item_name` |
| Market-financial statistics (WIDE, latest) | `get_stock_mktfin_indicator` | `get_stock_mktfin_metric` | `symbol`, `fields`; latest snapshot, valuation multiples & yields |
| Peer-group median (normalizer) | `get_stock_industry_median` | `get_stock_sector_median` | industry/sector median for within-group standardization |
| Trade calendar | `get_trade_cal` | `get_trade_cal` | `exchange=HK` or `exchange=US`; drives rebalance dates & forward windows |

Naming rule of thumb: HK uses `indicator` / `industry`; US uses `metric` / `sector`. Confirm
exact fields per market in `skill-pandadata-api` — do not assume US field names equal HK
field names verbatim.

## Long operating table — field notes (for dedup + pivot)

Returned by `get_stock_operating_indicator` / `get_stock_operating_metric`, one row per
`item_name` per report:

| Field | Use |
|---|---|
| `symbol`, `financial_year`, `financial_period_end_date` | keying, point-in-time cutoff |
| `item_name` | pivot column (industry-specific item) |
| `item_num` | pivot value |
| `is_pershare_item`, `is_percent_item` | scaling / meaning |
| `item_unit`, `item_currency` | unit & currency discipline (never cross-currency compare) |
| `report_type` (`Recent To Recent` / `Original To Original`) | **report-caliber dedup** |
| `data_type` (`Original` / `Restatement`) | **report-caliber dedup** |
| `is_final` (`1` audited / `0` preliminary) | reliability flag |
| `report_source` | provenance |

Dedup default: keep `report_type == "Recent To Recent"`, prefer `data_type == "Restatement"`
else `Original`; pivot `index=symbol, columns=item_name, values=item_num` for one aligned
period. State the chosen basis.

## Wide market-financial table — convention notes

`get_stock_mktfin_indicator` / `get_stock_mktfin_metric` return one latest row per symbol.
Fields come in convention pairs — fix one across the whole cross-section:

- TTM vs non-TTM (e.g. `curr_ev_to_ebitda` vs `curr_ev_to_ebitda_ttm`) — default TTM.
- Non-issue vs `_issue` (发行特定) — default non-issue.
- PE base: `curr_pe_dil_excl` (稀释扣非) / `curr_pe_dil_norm` (标准化) / `curr_pe_dil_incl`.

Common value/quality inputs: `curr_ev_to_ebitda(_ttm)`, `curr_ev_to_fcf(_ttm)`,
`curr_ev_to_rev(_ttm)`, `curr_price_to_fcf_pershr(_ttm)`, `curr_price_to_ocf_pershr(_ttm)`,
`curr_div_yld_issue_ratio(_ttm)`, `curr_cash_to_mcap_ratio`, `curr_pe_dil_*`.

## Calendar

`get_trade_cal(exchange=HK|US)` supplies trading dates for building rebalance dates and
forward-return windows. Dates are `YYYYMMDD` strings. `get_prev_trade_date` /
`get_last_trade_date` help with cutoffs. The A-share exchange code `SH` is not used here.

## Optional public fallback

If a Pandadata price pull is empty, Yahoo Finance daily bars may back-fill price/volume
**only** (never fundamentals), and must be labeled as a third-party fallback source in the
report's 数据说明.

## Coverage caveats (overseas)

- No Pandadata overseas futures, FX, crypto, or HK/US minute bars; this skill is daily,
  equity, cross-section only.
- Symbol formats for HK/US differ from A-share `.SH` / `.SZ`; follow the `get_hk_detail` /
  `get_us_detail` examples in `skill-pandadata-api`.
- Overseas coverage has not expanded in recent Pandadata versions; do not assume new
  overseas endpoints exist.
