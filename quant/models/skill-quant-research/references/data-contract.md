# Quant Data Contract

Use this checklist before feature engineering or backtesting. A result is only as reliable as the information set available at each historical decision point.

## Contents

- [Research data contract](#research-data-contract)
- [Market data](#market-data)
- [Fundamental and alternative data](#fundamental-and-alternative-data)
- [Point-in-time joins](#point-in-time-joins)
- [Quality checks](#quality-checks)
- [Provenance](#provenance)

## Research data contract

Write these fields in the experiment configuration:

| Field | Required definition |
| --- | --- |
| Universe | Security identifiers, venue, eligibility rules, listing and delisting treatment |
| Availability | Publication, receipt, or vendor availability timestamp; include revision policy |
| Observation | Economic event timestamp and local timezone |
| Price convention | Raw or adjusted; split, dividend, and other corporate-action treatment |
| Currency | Native currency, FX source, conversion timestamp, and base currency |
| Frequency | Bar interval, session calendar, and aggregation convention |
| Target | Return definition, horizon, overlapping or non-overlapping labels |
| Execution | Earliest executable timestamp, order type, price field, delay, and fill rule |
| Costs | Commission, spread, impact, slippage, financing, borrow, taxes, and FX |

Do not call a dataset "clean" without recording what was removed, corrected, imputed, adjusted, or unavailable.

## Market data

Check the following for OHLCV, trades, quotes, and derived bars:

- unique key is appropriate, usually `(asset_id, observation_timestamp)`;
- timestamps are parseable, monotonic within asset, timezone-aware, and aligned to a known exchange calendar;
- `high >= max(open, close)`, `low <= min(open, close)`, and all prices are positive unless the instrument convention says otherwise;
- zero or negative volume, crossed quotes, zero bid-ask spread, stale quotes, and extreme returns are flagged and investigated;
- adjusted and unadjusted fields are not mixed in a return calculation;
- splits, dividends, symbol changes, delistings, suspensions, and contract rolls are represented explicitly;
- futures use a stated roll rule and continuous-contract construction; options use contract identity, expiry, strike, and implied-volatility conventions;
- intraday bars document session boundaries, auction handling, late prints, and whether the bar close was available before the signal.

## Fundamental and alternative data

For every observation, preserve the economic period, publication timestamp, vendor receipt timestamp when available, revision or restatement status, and identifier mapping. Join by the latest record available at the decision time, never by the period end alone. Treat restated values as a separate vintage unless the research question explicitly concerns revised history.

For text, sentiment, web, estimates, and vendor scores, record collection time, language or market coverage, missingness, vendor changes, and any human or model labels. Validate that the feature would have existed in the claimed form at the signal timestamp.

## Point-in-time joins

Use an as-of join:

```text
eligible_feature(asset, signal_time)
  = latest observation for the same asset
    where availability_time <= signal_time
```

Require a deterministic tie rule for multiple records at the same availability time. Preserve unmatched rows and expose the missingness rate. Add a negative test with a deliberately future-dated observation; the join must reject or exclude it.

For universe membership, use the membership known at each date. Current index constituents, current exchange listings, and current sector classifications are not valid historical substitutes unless the task is explicitly retrospective and non-investable.

## Quality checks

At minimum, quantify:

- row count, unique assets, date range, frequency, and coverage by asset and period;
- duplicate keys, unsorted rows, gaps, missing fields, stale values, and outlier rates;
- cross-field invariants such as OHLC consistency and nonnegative volume;
- price jumps around corporate actions, rolls, currency changes, and ticker mappings;
- train, validation, and test overlap; feature availability after every join;
- whether exclusions depend on future information;
- data drift across time, vendors, venues, and regimes.

Fail closed for malformed timestamps, duplicate keys, impossible prices, or unknown adjustment status. Warnings are acceptable only when they are quantified and the result is labeled accordingly.

## Provenance

Record source and vendor, download or snapshot time, query or file path, schema version, transformation version, row counts before and after cleaning, hashes where practical, and the exact code and configuration used. A backtest without a reproducible data snapshot should be treated as exploratory.

