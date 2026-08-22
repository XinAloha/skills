# Validation Notes

## Scope

- This skill is a deterministic factor-library computation tool.
- It does not call an LLM and does not require API keys.
- The supported input shape is long-form CSV, and the output shape is wide CSV.
- `L3 verified` means formula-library reproduction, real-data runtime completeness, and Codex runtime consistency verification. It does not mean predictive-performance or trading-performance verification.

## Formula Basis

- Alpha101 and Alpha191 formulas are migrated from the upstream local `compute_alpha101_skill.py` and `compute_alpha191_skill.py` workflow.
- Alpha101 and Alpha191 are implemented based on JoinQuant official factor documentation and corrected against JoinQuant factor-value API comparisons from the upstream workflow.

## Real-Data Validation

- Real-data run: A-share long-form OHLCV data, `20230601` to `20251231`.
- Alpha101: 101 requested, 82 computed, 19 skipped.
- Alpha191: 191 requested, 186 computed, 5 skipped.
- Codex integration consistency: Codex outputs match development-directory outputs on row count, columns, `date` / `symbol` keys, and NaN positions.
- Selected-factor consistency: selected-factor runs match the corresponding columns from full runs exactly.

## Known Boundaries

- Some factors may be skipped when they require unavailable fields, benchmark data, or formula definitions that return `None`.
- Outputs are factor values only. They are not IC/ICIR, backtest, risk, portfolio, or trading signals.
- Users should revalidate results when the data vendor, universe, date range, price adjustment method, or field definitions change.
