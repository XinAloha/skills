# Methodology

## Purpose

Walk-forward is a **temporal out-of-sample protocol**, not a full production backtester. It asks: does the signal keep working after the sample used to “see” it?

## Protocol

1. Split the panel into nominal train / embargo / test folds (`rolling` or `expanding`).
2. Purge every training row whose forward label, defined by `label_horizon`, reaches the test start.
3. Apply an additional optional `embargo` gap.
4. On each fold compute:
   - Rank IC (Spearman) and Pearson IC
   - ICIR from daily ICs
   - Long-short top/bottom return Sharpe
   - Q5−Q1 quintile spread
   - Train→test IC degradation
5. Aggregate daily OOS Rank IC with a moving-block bootstrap CI95.
6. Multi-gate scorecard → `PASS` / `WEAK_PASS` / `FAIL`.

## References

- López de Prado, *Advances in Financial Machine Learning* (2018), Ch.7 (purged/embargoed CV)
- Qian, Hua, Sorensen, *Quantitative Equity Portfolio Management* (IC / ICIR usage)

## Limits

- `label_horizon` must equal the forward-return holding horizon.
- The caller must still ensure every signal field was observable at its timestamp.
- Does not model costs, limits, or borrow constraints (use stability + backtest skills for that).
