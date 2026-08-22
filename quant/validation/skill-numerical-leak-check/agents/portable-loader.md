# Portable Loader

Use this skill when the user asks to check future leakage, lookahead bias, numerical causality, factor leakage, label leakage, signal leakage, or backtest leakage.

Load order:

1. `SKILL.md`
2. `references/adapter-contract.md` when an adapter or harness is needed
3. `references/checkpoint-design.md` when selecting checkpoints
4. `references/result-interpretation.md` when interpreting results
5. `references/report-template.md` when writing the final report

Core rule: do not assume a fixed factor shape. Define the target computation, input, output, prefix operation, future mutation, and comparison method before running tests.

For batch checking, implement `discover_cases(config)` in the adapter so the runner can test many factors or cases in one run.
