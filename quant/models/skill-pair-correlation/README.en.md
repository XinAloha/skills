# skill-pair-correlation

[简体中文](README.md) | **English**

Two-symbol relationship analysis. Given two tickers, it computes in one call the return correlation (full window + recent 20/60d), the hedge beta (A on B), and the latest log-spread z-score for pairs trading / hedging / correlation checks. Each leg is routed independently across A-share / HK / US and the two are **inner-joined on shared trading dates before any statistic**. It reports statistical facts and inferences only — no buy/sell instructions.

<p align="center">
  <img alt="role" src="https://img.shields.io/badge/role-correlation·hedge-brightgreen">
  <img alt="output" src="https://img.shields.io/badge/output-corr·hedge%20beta·spread%20z-blue">
  <img alt="market" src="https://img.shields.io/badge/market-A--share·HK·US-9cf">
  <img alt="data" src="https://img.shields.io/badge/data-panda__data·tqx__data-yellow">
  <img alt="license" src="https://img.shields.io/badge/license-GPLv3-blue">
</p>

`skill-pair-correlation` is a QuantSkills community two-symbol relationship Skill. It answers "do these two move together / what hedge ratio / has the spread diverged", and is complementary to `skill-ma-crossover-signal` (single-symbol signal) and `skill-risk-return-metrics` (single-symbol risk profile), with no overlap.

## What problem it solves

"Are Tencent and Alibaba correlated?" "What hedge ratio for this pair?" "Has the spread diverged?" Correlation and hedge beta underpin every pair trade and every "are these two redundant in my book" question, but they are error-prone by hand: **the classic bug is correlating two return series that were never aligned on the same dates** — one halt day can silently distort the result.

This skill turns it into a checkable, structured result:

- **inner-join first, then compute** — the two legs are aligned on shared trading dates before any statistic, so cross-market pairs (e.g. `0700.HK` vs `BABA.NB`) work correctly;
- returns **full + recent 20/60d correlation, hedge beta / hedge_ratio, and log-spread z-score** in one call, plus a readable interpretation hint;
- a degenerate leg (0 variance) yields `null` for the affected field — never a crash.

## How it is computed

| Field | Formula |
|---|---|
| `correlation` | Pearson corr of daily simple returns over the full aligned window |
| `correlation_recent_20 / _60` | same, on the last 20 / 60 aligned rows (`null` if too few) |
| `beta_a_on_b` / `hedge_ratio` | `cov(ret_a, ret_b) / var(ret_b)` |
| `spread_zscore` | `spread = ln(Pa) − beta·ln(Pb)`; `(spread_last − mean) / std` over `zscore_window` |
| `price_ratio` | `last_close_a / last_close_b` |

Any statistic whose denominator is 0 (a flat leg, `var(ret_b)=0`, `std(spread)=0`) returns `null`.

## Quick start

```bash
# deps: pandas / numpy + panda_data (A-share) / tqx_data (HK/US)
python scripts/pair_correlation.py 0700.HK 9988.HK --lookback-days 250
python scripts/pair_correlation.py 600519.SH 000858.SZ --zscore-window 60
```

As a platform skill the entry point is `async def run(...) -> str` in `scripts/pair_correlation.py` (Panda QuantFlow skill contract). Missing data libs → a structured `Error: …` string rather than a raise.

## Example output

`0700.HK ↔ 9988.HK` example (full files in [`examples/output/`](./examples/output/)):

```
correlation: full 0.712    recent20 0.664    recent60 0.731
hedge beta (A on B): 0.884    price ratio 5.121
log-spread z-score: -1.83 (window 60)
```

> Moderately-high correlation; spread z = −1.83 < 0 means A is relatively "cheap" vs B, close to but not at the ±2 mean-reversion trigger.
> Structured JSON: [`examples/output/pair_correlation.json`](./examples/output/pair_correlation.json).
> Example values are taken from the SKILL.md output schema, not a live feed.

## Where the data comes from

Each leg's suffix independently drives market routing (when `market_a` / `market_b = auto`):

- **A-share** `.SH` / `.SZ` / `.BJ` or a bare 6-digit code → `panda_data` daily closes;
- **HK** `.HK` → `tqx_data`;
- **US** `.NB` / `.US` / `.NY` → `tqx_data`.

You can also force each leg with `--market-a` / `--market-b`. Data is injected by the platform runtime; output quality depends on upstream availability and correctness.

## Directory layout

```
skill-pair-correlation/
├── SKILL.md                     # Agent spec (core): usage, params, output schema, formulas, when-NOT-to-use
├── README.md                    # Chinese readme (first paragraph = platform summary)
├── README.en.md                 # this file (English)
├── LICENSE                      # full GPLv3 license text
├── quantskills.yaml             # QuantSkills upstream manifest: provenance / deps / license: GPL-3.0-only
├── agents/                      # per-platform runtime entrypoints (all fall back to the same SKILL.md)
│   ├── cursor-rule.mdc          #   Cursor rule entrypoint
│   ├── openai.yaml              #   OpenAI-style / OpenClaw runtime manifest (display_name / default_prompt)
│   └── portable-loader.md       #   Hermes / OpenClaw portable loader
├── scripts/
│   └── pair_correlation.py      # executable: async def run(...) -> str + standalone CLI; align + corr/beta/spread z
└── references/
    └── example_output.md        # per-field output notes
└── examples/
    └── output/                  # example output (values from the SKILL.md schema)
        ├── pair_correlation.json    #   structured JSON example
        └── pair_correlation.txt     #   human-readable summary + reading + disclaimer
```

## Runtime entrypoints

This Skill supports Claude Code, Codex, Cursor, Hermes and OpenClaw. Claude Code, Codex and native skill runtimes load `SKILL.md` directly; Cursor uses `agents/cursor-rule.mdc`; Hermes / OpenClaw use `agents/portable-loader.md` when they cannot discover the skill natively (`agents/openai.yaml` provides OpenClaw display info). Every entrypoint falls back to the same `SKILL.md` and the same script — no parallel business logic.

## How it divides work with sibling skills

- **this skill**: two-symbol correlation / hedge beta / spread — **relationship between two names**;
- `skill-ma-crossover-signal`: single-symbol trend / golden-death cross — **timing signal on one name**;
- `skill-risk-return-metrics`: single-symbol Sharpe / drawdown / Calmar — **risk/return of one name**;
- multi-symbol factor screening → use a factor skill.

## Disclaimer

- **Research & educational use only.** Output is informational research, **not investment advice**, and makes **no promise of returns**.
- **Data sources:** A-share via `panda_data`; HK / US via `tqx_data` (platform-provided). Output quality depends entirely on upstream data availability and correctness.
- **Assumptions & limitations:** the two legs are inner-joined on shared trading dates first; correlation and hedge beta use daily simple returns; spread = `ln(Pa) − beta·ln(Pb)`. Correlation/beta are historical and unstable out-of-sample; a degenerate leg returns `null`; cross-market pairs shrink the aligned sample due to calendar differences.
- **Risk boundary:** do not use as the sole basis for real-money pair/hedge decisions; validate independently and understand market risk.

## License

GPL-3.0-only. This skill is original to the QuantSkills community; correlation and hedge beta are standard quant methods. Full text in [`LICENSE`](./LICENSE).
