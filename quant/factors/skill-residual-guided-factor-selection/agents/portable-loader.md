# Portable Loader

Load the skill from this repository and read `SKILL.md` before acting.

Use `scripts/run_factor_selection.py` for factor materialization, cache validation, residual-guided search, stability runs, and sealed OOS evaluation. Read `references/usage.md` before preparing the YAML configuration and `references/algorithm.md` before changing search semantics.

Use only Train and Valid during search. Freeze one development checkpoint before `evaluate-oos`.

When return-level evaluation is requested, read `references/backtest_integration.md`, run `scripts/run_selection_backtest.py --export-only`, parse the handoff JSON, and invoke `$factor-backtest`. Keep portfolio construction and return calculation in `$factor-backtest`; use direct external CLI execution only when explicitly requested.
