# Source Boundary

This skill operates on user-provided local factor and label files. It does not download market data, compute factor libraries, or call external research APIs.

## Data Boundary

- Inputs are local CSV/parquet files only.
- Factor rows are merged with label rows on `(date, ticker)`.
- The skill assumes labels have already been constructed by the user.
- When strict mode is explicitly disabled, missing `available_date` or label-window metadata is reported as a warning.

`legacy_v1` defaults to non-strict checks and reports missing metadata as warnings. `research_v2` defaults to strict checks, where missing availability dates, label windows, or universe data are errors.

The built-in provider reads local CSV/parquet files. An explicitly enabled user factor provider may adapt another user-controlled local source, but must return the same canonical `PanelData` contract and must enforce its own point-in-time guarantees.

## Extension Boundary

- External extension loading is disabled by default.
- The runtime imports only module names listed in `extensions.modules` from explicit `plugin_roots`.
- It does not recursively discover plugins, download source, install dependencies, or execute configuration strings.
- Imported extension code is trusted local Python code and has the same process permissions as the runtime.
- Extension module file paths, versions, and SHA-256 values are written to `search_manifest.json`.
- Feature pipelines are instantiated per model/window. They receive `y_train` only during `fit`; validation and holdout transforms receive features plus date/ticker context without targets.
- Custom providers and models must not inspect holdout outcomes to change search behavior.

## Holdout Boundary

- Under `research_v2`, search data is truncated at the validation boundary before the panel is built.
- Under `legacy_v1`, a configured fixed test period is evaluated automatically for historical compatibility; this is not a sealed-holdout workflow.
- Offline final selection does not call the holdout evaluator.
- Holdout access requires the separate CLI and explicit `--confirm-holdout-access`.
- Each access writes source artifact hashes and an append-only audit log.
- Local audit controls cannot prevent a user from copying data or rerunning the command; organizational test-set governance remains necessary.

## LLM Boundary

The LLM only receives structured trial evidence, search-space summaries, decision memory, and risk flags. It does not receive raw factor matrices or labels.

The LLM is not allowed to invent arbitrary parameters outside the validated search-space schema. Runtime guardrails validate:

- action names
- changed parameter names
- numeric bounds
- choice values
- maximum expansion ratios
- final selected trial IDs

If LLM output is invalid, the runtime falls back to the guarded rule decision or score-best selection, depending on the stage.

## Research Boundary

This skill is a model hyperparameter optimization harness. It does not provide investment advice, does not claim positive returns, and does not replace a production backtest. Use generated parameters as research candidates that require independent validation.
