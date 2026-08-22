# statistical-arbitrage-time-series

An Agent Skill for reproducible, sourced statistical-arbitrage and time-series research. It covers training-window ADF/KPSS tests, spread and hedge-ratio modeling, mean reversion, bias-controlled backtests, realistic costs including short borrow, significance checks, and robustness risks.

This project is for research and method validation only. It makes no return claims, is not investment advice, and does not imply official endorsement by QuantSkills or any platform.

Start with [`SKILL.md`](SKILL.md), the [research guide](references/statarb-guide.md), and the runnable [script](scripts/run_statarb.py). Offline self-test:

```bash
python scripts/run_statarb.py --source synthetic --mode strong
```

Runtime entrypoints for Claude Code, Codex, Cursor, Hermes, and OpenClaw are documented in [`agents/portable-loader.md`](agents/portable-loader.md).

## License

GPL-3.0-only. See [`LICENSE`](LICENSE).
