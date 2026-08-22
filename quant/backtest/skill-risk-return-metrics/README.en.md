# skill-risk-return-metrics

[简体中文](README.md) | **English**

Single-symbol risk/return dossier. Given a ticker and a date window, it computes in one call the annualized return, annualized volatility, Sharpe, Sortino, max drawdown, Calmar, win-rate and other allocator-side metrics, auto-routing A-share / HK / US by suffix. Ratios whose denominator is 0 (flat series, zero drawdown) return `null` rather than `NaN` or a crash. It reports statistical facts only — no buy/sell instructions.

<p align="center">
  <img alt="role" src="https://img.shields.io/badge/role-risk%2Freturn%20dossier-brightgreen">
  <img alt="output" src="https://img.shields.io/badge/output-annualized·Sharpe·drawdown·Calmar-blue">
  <img alt="market" src="https://img.shields.io/badge/market-A--share·HK·US-9cf">
  <img alt="data" src="https://img.shields.io/badge/data-panda__data·tqx__data-yellow">
  <img alt="license" src="https://img.shields.io/badge/license-GPLv3-blue">
</p>

`skill-risk-return-metrics` is a QuantSkills community single-symbol risk/return Skill. It answers "how risky is X, and was the return worth it", and is complementary to `skill-ma-crossover-signal` (single-symbol signal) and `skill-pair-correlation` (two-symbol relationship), with no overlap.

## What problem it solves

"How risky is X? Does this return justify its volatility?" is a recurring allocator question that otherwise means re-deriving Sharpe / max-drawdown / Calmar in pandas every time.

This skill folds it into one checkable call:

- one close series → a full set of allocator ratios (**annualized return, volatility, Sharpe, Sortino, max / current drawdown, Calmar, win-rate**);
- undefined ratios (flat series, zero drawdown, no down-days) return `null` explicitly instead of a silent `NaN`;
- a consistent cross-market convention (252 trading days/year), so A-share and HK/US names compare directly on the same metrics.

## How it is computed

| Field | Formula |
|---|---|
| `total_return` | `last_close / first_close − 1` |
| `annualized_return_cagr` | `(last_close / first_close) ** (252 / observations) − 1` |
| `annualized_return_mean` | `mean(daily_return) × 252` |
| `annualized_volatility` | `std(daily_return, ddof=1) × sqrt(252)` |
| `sharpe` | `(annualized_return_mean − risk_free_rate) / annualized_volatility` |
| `sortino` | `(annualized_return_mean − risk_free_rate) / (downside_std × sqrt(252))` |
| `max_drawdown` | `min(cum / cummax(cum) − 1)`, `cum = cumprod(1 + daily_return)` |
| `current_drawdown` | last value of the drawdown series |
| `calmar` | `annualized_return_cagr / abs(max_drawdown)` |
| `win_rate` | `mean(daily_return > 0)` |

Ratios whose denominator is 0 (flat series, no drawdown, no down-days) return `null`. Results are point-in-time and use only the upstream feed's adjustment convention.

## Quick start

```bash
# deps: pandas / numpy + panda_data (A-share) / tqx_data (HK/US)
python scripts/risk_return_metrics.py 600519.SH --lookback-days 250 --risk-free-rate 0.02
python scripts/risk_return_metrics.py 0700.HK --start-date 20260101 --end-date 20260601
```

As a platform skill the entry point is `async def run(...) -> str` in `scripts/risk_return_metrics.py` (Panda QuantFlow skill contract, same shape as the shipped `analysis_technical` / `fx_rates`). Missing data libs → a structured `Error: …` string rather than a raise.

## Example output

`0700.HK` example (full files in [`examples/output/`](./examples/output/)):

```
total return +8.29%    CAGR +24.31%    ann. vol 28.74%
Sharpe 0.874    Sortino 1.201    Calmar 1.587    win rate 54.1%
max drawdown -15.32%    current drawdown -2.10%
```

> ~24% annualized on ~29% vol, Sharpe 0.87 is upper-middle; Calmar 1.59 means ~1.6x annualized per unit of max drawdown.
> Structured JSON: [`examples/output/risk_return_metrics.json`](./examples/output/risk_return_metrics.json).
> Example values are taken from the SKILL.md output schema, not a live feed.

## Where the data comes from

The suffix drives market routing (when `market=auto`):

- **A-share** `.SH` / `.SZ` / `.BJ` or a bare 6-digit code → `panda_data` daily closes;
- **HK** `.HK` → `tqx_data`;
- **US** `.NB` / `.US` / `.NY` → `tqx_data`.

You can also force it with `--market cn|hk|us`. Data is injected by the platform runtime; output quality depends on upstream availability and correctness.

## Directory layout

```
skill-risk-return-metrics/
├── SKILL.md                        # Agent spec (core): usage, params, output schema, formulas, when-NOT-to-use
├── README.md                       # Chinese readme (first paragraph = platform summary)
├── README.en.md                    # this file (English)
├── LICENSE                         # full GPLv3 license text
├── quantskills.yaml                # QuantSkills upstream manifest: provenance / deps / license: GPL-3.0-only
├── agents/                         # per-platform runtime entrypoints (all fall back to the same SKILL.md)
│   ├── cursor-rule.mdc             #   Cursor rule entrypoint
│   ├── openai.yaml                 #   OpenAI-style / OpenClaw runtime manifest (display_name / default_prompt)
│   └── portable-loader.md          #   Hermes / OpenClaw portable loader
├── scripts/
│   └── risk_return_metrics.py      # executable: async def run(...) -> str + standalone CLI; return/risk/ratio calc
└── references/
    └── example_output.md           # per-field output notes
└── examples/
    └── output/                     # example output (values from the SKILL.md schema)
        ├── risk_return_metrics.json    #   structured JSON example
        └── risk_return_metrics.txt     #   human-readable summary + reading + disclaimer
```

## Runtime entrypoints

This Skill supports Claude Code, Codex, Cursor, Hermes and OpenClaw. Claude Code, Codex and native skill runtimes load `SKILL.md` directly; Cursor uses `agents/cursor-rule.mdc`; Hermes / OpenClaw use `agents/portable-loader.md` when they cannot discover the skill natively (`agents/openai.yaml` provides OpenClaw display info). Every entrypoint falls back to the same `SKILL.md` and the same script — no parallel business logic.

## How it divides work with sibling skills

- **this skill**: single-symbol Sharpe / drawdown / Calmar risk-return dossier — **risk/return of one name**;
- `skill-ma-crossover-signal`: single-symbol trend / golden-death cross — **timing signal on one name**;
- `skill-pair-correlation`: two-symbol correlation / hedge beta / spread — **relationship between two names**;
- multi-symbol ranking / screening → use a factor skill; raw OHLCV / minute bars only → use a market-data skill.

## Disclaimer

- **Research & educational use only.** Output is informational research, **not investment advice**, and makes **no promise of returns**.
- **Data sources:** A-share via `panda_data`; HK / US via `tqx_data` (platform-provided). Output quality depends entirely on upstream data availability and correctness.
- **Assumptions & limitations:** metrics use daily closes, annualized with 252 trading days/year; ratios whose denominator is 0 (flat series, no drawdown/down-days) return `null`; results are point-in-time with no adjustment beyond the upstream feed.
- **Risk boundary:** do not use as the sole basis for real-money decisions; validate independently and understand market risk.

## License

GPL-3.0-only. This skill is original to the QuantSkills community; the risk/return metrics are standard quant methods. Full text in [`LICENSE`](./LICENSE).
