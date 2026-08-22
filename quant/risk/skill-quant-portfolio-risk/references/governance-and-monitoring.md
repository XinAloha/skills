# Portfolio Governance and Monitoring

Use this reference when designing pre-trade controls, production monitoring, approvals, incident handling, or audit records.

## Contents

- [Control layers](#control-layers)
- [Daily operating cycle](#daily-operating-cycle)
- [Breach handling](#breach-handling)
- [Monitoring dashboard](#monitoring-dashboard)
- [Audit and model change](#audit-and-model-change)

## Control layers

Separate responsibilities and data paths for:

- **signal and forecast:** produces inputs, not orders;
- **portfolio construction:** creates target weights under mandate and risk model;
- **order management:** converts target deltas into executable orders;
- **independent risk:** checks limits using an independent calculation path where practical;
- **execution and operations:** confirms fills, cash, borrow, and venue state;
- **accounting and reconciliation:** confirms positions, PnL, fees, and corporate actions;
- **governance:** approves models, exceptions, releases, and changes in mandate.

No single success metric should authorize a trade. A portfolio must pass data freshness, model validity, mandate, risk, liquidity, and operational checks before release.

## Daily operating cycle

1. Confirm market calendar, timezone, holiday, venue, and data cutoff.
2. Reconcile prior-day positions, cash, fills, fees, financing, borrow, and corporate actions.
3. Validate prices, FX, liquidity, factor exposures, forecasts, and risk-model freshness.
4. Generate targets with a versioned mandate, model, optimizer configuration, and data snapshot.
5. Run pre-trade checks on projected positions and orders, including stress and capacity.
6. Record approvals, exceptions, overrides, and the exact order release payload.
7. Monitor execution, partial fills, rejected orders, stale orders, and intraday risk.
8. Reconcile actual fills and projected risk; cancel or escalate when controls fail.
9. Produce post-trade attribution, implementation shortfall, drift, breaches, and unresolved residuals.

Make each step idempotent where possible. A retry must not duplicate orders or double-count fills.

## Breach handling

Define for every limit:

| Field | Requirement |
| --- | --- |
| Threshold | hard limit, warning level, and tolerance |
| Measurement | formula, source, timestamp, and frequency |
| Owner | accountable person or service |
| Action | block, reduce, hedge, investigate, or notify |
| Override | authority, expiry, reason, and compensating control |
| Evidence | immutable record of input, calculation, and resolution |

Classify breaches as data, model, market, execution, operational, or mandate issues. Do not hide a breach by changing the calculation window or rounding inputs. When a control is unavailable, fail closed or move to a documented reduced-risk mode.

## Monitoring dashboard

Monitor both state and change:

- total and active exposure, gross/net leverage, cash, margin, and collateral;
- ex-ante volatility, tracking error, expected shortfall, stress loss, and risk contributions;
- position, issuer, sector, country, factor, currency, duration, and liquidity concentration;
- turnover, ADV participation, spread, impact, fill rate, rejects, cancels, and implementation shortfall;
- forecast drift, realized versus forecast risk, factor-model error, and PnL attribution;
- data freshness, missingness, stale prices, schema changes, job latency, reconciliation breaks, and model version;
- limit headroom, open incidents, exceptions, overrides, and kill-switch state.

Use thresholds that reflect economic risk and measurement noise. Alert on persistent drift and rapid change, not only on absolute breaches. Preserve a time series of the dashboard inputs so an incident can be reconstructed.

## Audit and model change

Archive the mandate, input files or snapshot IDs, target weights, orders, fills, risk model, optimizer parameters, solver status, checks, approvals, overrides, and final reconciliation. Hash code and configuration where practical. Keep model versions immutable after release.

For a model or constraint change, record rationale, owner, affected portfolios, expected impact, test evidence, rollback plan, approval, release time, and post-release monitoring window. Re-run representative historical, stress, and failure-case tests. Treat changes to data vendors, identifiers, calendars, cost models, risk factors, and solver versions as material until assessed.

## Kill-switch policy

Define explicit conditions that block new risk or pause order release, such as stale or inconsistent positions, invalid covariance, missing prices, unexplained reconciliation breaks, severe limit breach, abnormal execution, or unavailable independent risk checks. A kill switch should be reversible only through an authenticated, logged approval and should specify the safe state: cancel, hold, reduce, hedge, or flatten according to the mandate.

