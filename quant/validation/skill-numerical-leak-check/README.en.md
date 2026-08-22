# skill-numerical-leak-check

A generic numerical future-leakage checking skill. It teaches agents to use prefix replay and future mutation to test whether future inputs can change historical outputs in time-series computations, quantitative factors, feature pipelines, label generation, backtest signals, or research workflows.

The skill does not assume a fixed factor function shape, schema, asset class, or output column. Use an adapter to connect project-specific code to the generic numerical causality runner.

## Batch Checking

The adapter function `discover_cases(config)` may return many cases, so one run can check many factors, features, labels, parameter sets, markets, universes, or pipeline nodes.

## Outputs

```text
<out_dir>/
├── leak_check_results.csv
├── leak_check_results.json
├── leak_check_summary.json
└── leak_check_report.md
```

## Runtime Entry Points

| Runtime | Entry |
|---|---|
| Codex / Claude Code | `SKILL.md` |
| Cursor | `agents/cursor-rule.mdc` |
| Hermes / OpenClaw / portable agents | `agents/portable-loader.md` |

## License

GPL-3.0-only.
