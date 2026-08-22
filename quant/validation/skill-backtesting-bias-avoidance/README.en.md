# Backtesting & Bias Avoidance Skill

This repository provides a runtime-portable skill for Codex, Claude Code, Cursor, Hermes, and OpenClaw. It builds look-ahead-free backtests and audits look-ahead, survivorship, overfitting, data-snooping, and transaction-cost risks.

## Quick start

```bash
pip install numpy pandas scipy matplotlib
python scripts/run_backtest.py --out backtest-report.md
```

The default workflow uses offline synthetic data. For real data, document the source, date range, point-in-time handling, and delisted-asset coverage. See [SKILL.md](SKILL.md) for the full workflow and [agents/README.md](agents/README.md) for the Chinese-first guide.

This project is for research and engineering validation only. It does not provide investment advice, performance guarantees, or claims of financial returns.

## License

Licensed under the [GNU General Public License v3.0](LICENSE), identified in metadata as `GPL-3.0-only`.
