# skill-portfolio-attribution

[简体中文](README.md) | **English**

Portfolio performance attribution skill: decompose a portfolio's active return versus its benchmark into sector allocation, stock selection, interaction, and factor contributions — answering the question that comes after a backtest: where did the excess return actually come from.

<p align="center">
  <img alt="role" src="https://img.shields.io/badge/role-performance%20attribution-brightgreen">
  <img alt="output" src="https://img.shields.io/badge/output-Brinson%20%C2%B7%20Carino%20%C2%B7%20factor%20%C2%B7%20txt%2Fjson%2FHTML-blue">
  <img alt="validation" src="https://img.shields.io/badge/validation-13%2F13%20identities%20%26%20guards-orange">
  <img alt="data" src="https://img.shields.io/badge/data-framework--neutral-9cf">
  <img alt="license" src="https://img.shields.io/badge/license-GPLv3-blue">
</p>

`skill-portfolio-attribution` is a QuantSkills community skill. The community factor ecosystem already covers mining, evaluation, decay, blending, and backtesting; this skill fills the missing link after signals become a portfolio: attribution.

QuantSkills GitHub organization: https://github.com/quantskills

## What it solves

A backtest tells you the portfolio beat its benchmark by 8%, but not where that 8% came from: overweighting the right sectors, picking the right stocks within sectors, or loading on factors like momentum and value. Attribution decomposes the active return by source, and the components sum exactly to the interval active return.

Two layers of attribution:

- **Brinson-Fachler sector attribution**: active return split into allocation, selection, and interaction, with Carino multi-period geometric linking so per-period effects are additive across time.
- **Factor attribution**: per-period cross-sectional regression estimates factor returns; active exposure × factor return gives factor contributions, with the residual as specific (selection) return.

Both panels reconcile to the same interval active return — factor attribution uses the same Carino scaling as sector attribution, so the factor panel total equals the sector panel total equals the interval active return.

## Attribution is one of the few quant tools that can prove itself correct

The components must sum exactly to the active return, and this identity is a built-in runtime assertion: if it does not balance, the skill refuses to emit a report. Input validation is equally strict — non-conforming input raises rather than being silently handled:

- **Weight-sum guard**: daily weights deviating from 1 by more than 1e-4 raise, no silent renormalization
- **Duplicate-key guard**: duplicate `(date, symbol)` rows in weights/returns raise, preventing double-counted weights and wrong attribution
- **Zero-weight-sector guard**: a sector with zero weight in both portfolio and benchmark yields exactly zero effects, no NaN in the report
- **Falsifiable**: `scripts/validate.py` verifies 13 identities and guards on synthetic data, including "factor panel and sector panel reconcile to the same interval active return" — all pass

## Quick start

```bash
pip install -r requirements.txt
python scripts/validate.py                                          # 13 identity & guard tests
python examples/run_example.py                                      # end-to-end synthetic example
python scripts/attribution.py \
  --portfolio p.csv --benchmark b.csv --returns r.csv --sectors s.csv \
  --exposures e.csv --out report/
```

Example output (synthetic portfolio overweighting semiconductors, underweighting banks): the interval active return is +0.06%, and both the Brinson panel total and the factor panel total equal +0.06% — reconciled to the same account.

## Input: only holdings are required

The only required input is a **daily holdings** time series (from any backtest, broker statement, or live account — any platform):

```
date, symbol, weight        # or give market_value; the agent derives the weight
20240102, 600519.SH, 0.20
20240102, CASH,       0.05  # cash as a row, otherwise cash drag is lost
```

The other three tables are filled in by the agent from **public data**:

- **Stock returns** ← public forward-adjusted (qfq) daily prices (akshare / Pandadata); `close/pre_close` is a clean daily return
- **Sector map** ← public industry classification
- **Benchmark (default: held-universe equal weight)** ← derived from the holdings, equal-weighting the stocks the portfolio held. Needs only the holdings, reconciles exactly, and carries no suspension / composition / look-ahead noise. An optional "vs CSI300 / SSE index" benchmark needs clean index-constituent data (naive reconstruction has look-ahead bias — use point-in-time constituents).

**Security boundary**: this skill ships **no database connection or adapter**. It consumes only "holdings + public data" and never connects to the caller's private database. Exporting backtest holdings to a file is the platform's job, not part of this skill.

## Runtime entrypoints

This Skill supports Claude Code, Codex, Cursor, Hermes, and OpenClaw. Claude Code, Codex, and native Skill runtimes load `SKILL.md` directly; Cursor uses `agents/cursor-rule.mdc`; Hermes/OpenClaw can use `agents/portable-loader.md` when native discovery is unavailable. All entrypoints converge on the same `SKILL.md`, methodology, and attribution script rather than maintaining parallel business logic.

## Boundaries

- Assumes rebalancing to the given weights each period; intra-period trades and fees are out of scope in v1
- Cash drag/contribution is captured when a `CASH` row is present in the holdings; omitted otherwise
- Factor returns are estimated by OLS, without industry neutralization or weighted regression (planned for v2)
- **No database adapter**: consumes only user holdings + public data, connects to no private database
- The return-sanity guard warns without modifying data; adjustment and cleaning are the data-ingestion layer's job, not the attribution engine's

## License

GPL-3.0. Original QuantSkills community work; Brinson-Fachler and Carino linking are standard portfolio-attribution methods.
