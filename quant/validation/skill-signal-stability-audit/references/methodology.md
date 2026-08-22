# Methodology

## Purpose

A factor can have positive IC and still be untradeable if ranks reshuffle every day. This skill measures **persistence** and **implied turnover cost**.

## Metrics

| Metric | Meaning |
| --- | --- |
| Rank autocorr lag1..K | How sticky cross-sectional ranks are |
| Half-life | Days for autocorr to decay by half (exp fit) |
| Top/Bottom Jaccard | Membership overlap of extreme baskets |
| One-way turnover proxy | `1 - top Jaccard` |
| Kendall tau-b | Rank concordance with tie correction |
| Quintile transition | Where names migrate across quintiles |
| Annual cost drag | `turnover × 2 × cost_bps × (252/rebalance_days)` |

## Decision aids

- Recommended rebalance horizon from half-life
- Scorecard gates for STABLE / MIXED / UNSTABLE

## Limits

- Jaccard churn ≠ share-level turnover; treat as a research proxy.
- Supply the actual `rebalance_days`; otherwise the tool derives an interval from half-life.
