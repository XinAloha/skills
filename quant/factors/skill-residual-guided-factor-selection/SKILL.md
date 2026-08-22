---
name: residual-guided-factor-selection
description: "Run residual-guided multi-path factor selection for quantitative factor banks using Ridge training residuals or LightGBM temporal OOF residuals, deterministic or randomized Beam Search, exhaustive joint-CV pool search, validated feature caches, multi-run stability diagnostics, sealed OOS evaluation, and explicit handoff of frozen OOS signals to the registered $factor-backtest Skill. Use when Codex needs complementary factor discovery, compact factor-set search, temporal-CV path selection, factor-bank materialization, frozen OOS predictions, or selected-signal backtesting for returns, NAV, drawdown, holdings, turnover, benchmark-relative, or hedged performance, including Chinese requests such as 因子筛选后回测、收益验证、净值、回撤、持仓、换手或对冲表现."
---

# Residual-Guided Factor Selection

Use this skill to search a factor bank for compact sets that explain complementary return structure. Keep OOS data sealed until the development search has selected and frozen one checkpoint.

## Project Scope

- Treat this repository as a QuantSkills Community Project maintained by `X-Tech-group`; it is not an officially reviewed, certified, or endorsed QuantSkills project.
- Read the repository metadata from `skill.yml` without adding community-only fields to this file's Codex frontmatter.
- Require users to provide legally usable point-in-time factor, label, and market data, and record the data provenance and timing assumptions used for each study.
- Treat selected factors, IC metrics, OOS predictions, and downstream backtest results as research evidence whose interpretation depends on data quality, temporal alignment, universe construction, model settings, costs, and execution assumptions. Do not present them as investment advice, production approval, or guaranteed returns.

## Workflow

1. Read `references/usage.md` before preparing data or configuration.
2. Read `references/algorithm.md` before changing residual construction, candidate scoring, temporal CV, path retention, or checkpoint selection.
3. Prepare a wide label Parquet and either:
   - one wide Parquet per factor; or
   - a validated prepared-feature cache with its manifest.
4. Define non-overlapping Train, Valid, and OOS periods. Set `embargo_bars` from the forward-label horizon.
5. Choose one search command:
   - `run`: one Ridge residual-forward path;
   - `run-many`: multiple Ridge paths with different initial factors;
   - `run-beam`: deterministic or randomized multi-path search;
   - `run-many-beam`: repeated randomized Beam paths;
   - `run-pool`: exhaustive joint temporal-CV factor-pool search.
6. Inspect `summary.json`, `iteration_history.csv`, `beam_history.csv`, and `residual_top10.csv` as applicable.
7. Freeze one development checkpoint before calling `evaluate-oos`.
8. Route the requested evaluation:
   - For prediction quality, IC, or label-level metrics, stop after `evaluate-oos`.
   - For returns, NAV, drawdown, holdings, turnover, or hedged performance, read `references/backtest_integration.md` and require the registered `$factor-backtest` Skill.
   - Run `scripts/run_selection_backtest.py --export-only` to materialize the frozen signal and emit its handoff JSON.
   - Pass `input_file`, `factor_column`, `timespan`, `signal_manifest`, and signal direction from that JSON to `$factor-backtest`.
   - Let `$factor-backtest` validate market data, execute the portfolio backtest, verify expected outputs, and report results.
   - If `$factor-backtest` is unavailable, request installation; use direct external CLI execution only when the user explicitly asks for that fallback.

## Commands

Generate and run the smoke example:

```bash
python examples/generate_residual_search_toy_data.py
python scripts/run_factor_selection.py \
  --config examples/residual_search/toy_config.yaml run
python scripts/run_factor_selection.py \
  --config examples/residual_search/toy_config.yaml run-beam
python scripts/run_factor_selection.py \
  --config examples/residual_search/toy_config.yaml run-pool
```

Evaluate a frozen run without overwriting existing OOS artifacts:

```bash
python scripts/run_factor_selection.py \
  --config <config.yaml> evaluate-oos \
  --run-dir <frozen-run-directory>
```

Use `--force` only when the user explicitly requests replacement of an existing OOS evaluation.

Prepare the frozen OOS prediction for an explicit Codex Skill handoff:

```bash
python scripts/run_selection_backtest.py \
  --run-dir <frozen-run-directory> \
  --export-only
```

Read the emitted JSON and invoke `$factor-backtest` with its `input_file`, `factor_column=prediction`, `timespan`, `signal_manifest`, and `signal_direction`, plus the user-provided market-data root and portfolio assumptions. The export-only path does not locate or execute an external backtest process. The adapter retains direct CLI execution as an explicit compatibility fallback; see `references/backtest_integration.md`.

General entry point:

```bash
python scripts/run_factor_selection.py --config <config.yaml> <command>
```

## Method Invariants

- Use only Train and Valid data during search.
- Apply preprocessing independently by date or causally through time, according to `factor_transform`.
- Purge the fit tail of temporal folds by `embargo_bars`.
- For `run` and `run-many`, rank Ridge candidates with Train in-sample residuals.
- For Ridge Beam, rank candidates with Train+Valid development-period in-sample residuals.
- For LightGBM Beam, rank candidates with residuals from predictions generated only by earlier temporal folds.
- Rank candidates by the absolute mean daily cross-sectional residual correlation; retain its signed value in outputs.
- Refit the full selected factor set after every addition.
- With `beam.search_objective: cv`, retain paths and choose the final checkpoint using joint temporal-CV evidence.
- With Ridge `beam.search_objective: residual`, retain paths using development-period weighted Ridge R^2, freeze `residual_selection_depth`, and preserve temporal-CV metrics as checkpoint evidence.
- Preserve the resolved configuration, cache manifest, factor names, seeds, and path history.
- Do not inspect OOS outputs before the search decision is frozen.
- Backtest only the frozen OOS `prediction`; never export the realized `target` as a signal.
- Keep portfolio construction and return calculation in `$factor-backtest`; the residual Skill exports only the frozen signal and handoff metadata.

## Technical Documentation

- `references/usage.md`: data contract, YAML sections, commands, and outputs.
- `references/algorithm.md`: residual objectives, candidate scores, Beam search, pool search, and checkpoint rules.
- `references/downstream_evaluation.md`: boundary between factor selection and portfolio backtesting.
- `references/backtest_integration.md`: frozen-signal schema, explicit `$factor-backtest` handoff, ticker mapping, compatibility fallback, and result contract.
