# Quant Risk and Reporting

Use this reference to turn a performance table into an implementability and risk assessment.

## Contents

- [Risk inventory](#risk-inventory)
- [Portfolio diagnostics](#portfolio-diagnostics)
- [Capacity and stress](#capacity-and-stress)
- [Attribution](#attribution)
- [Report format](#report-format)

## Risk inventory

Review risks at four levels:

1. **Market**: beta, sector, country, style, duration, curve, volatility, commodity, FX, and concentration exposures.
2. **Trading**: spread, impact, gap risk, latency, partial fills, turnover, liquidity, borrow, financing, margin, and venue constraints.
3. **Model**: parameter instability, feature drift, regime dependence, crowding, factor decay, data revisions, and implementation mismatch.
4. **Operational**: stale data, failed jobs, missing files, calendar errors, identifier changes, limit breaches, reconciliation, and monitoring gaps.

Make each risk measurable where possible and assign a mitigation or monitoring signal.

## Portfolio diagnostics

Report gross and net exposure, long and short exposure, leverage, cash, beta, factor and sector exposures, position concentration, issuer concentration, turnover, average holding period, liquidity participation, and borrow utilization. Show distributions over time, not only averages.

Decompose performance into at least allocation, selection, timing, factor, currency, and cost effects when the data supports it. Attribute drawdowns to positions, sectors, factors, instruments, and execution costs. Check that attribution reconciles to portfolio PnL within rounding and cash conventions.

For risk metrics, state the window and convention. Include maximum drawdown and duration, downside deviation, tail loss or expected shortfall, stress loss, volatility clustering, and the count and size of independent bets. Use drawdown charts and rolling metrics when they reveal instability.

## Capacity and stress

Estimate capacity from participation limits, spread and impact assumptions, borrow, position limits, turnover, and available volume. Run a cost sweep and show where net performance or risk-adjusted performance becomes unacceptable. Do not infer capacity from average daily volume alone.

Stress at least:

- 2x and 3x baseline spread, slippage, impact, and borrow cost;
- execution delayed by one or more bars;
- reduced liquidity and capped participation;
- large overnight or intraday gaps;
- volatility and correlation shocks;
- missing or stale data, delayed data, and failed rebalance days;
- forced de-risking, leverage reduction, or short-sale restrictions where relevant.

Use historical scenarios only when the underlying data is comparable; supplement them with transparent hypothetical shocks. Explain which assumptions are conservative and which are unknown.

## Attribution

For cross-sectional strategies, inspect factor IC, rank IC, breadth, hit rate by bucket, long-short spread, turnover by bucket, and factor neutralization. For time-series strategies, inspect signal level, position mapping, forecast error, exposure persistence, and return contribution by regime.

Separate alpha from unintended beta. A strategy can have a positive backtest while simply loading on market, size, value, momentum, carry, volatility, duration, or liquidity. Compare raw and neutralized results and disclose the benchmark and hedge methodology.

## Report format

Use this order for a decision-ready report:

1. **Decision**: classification, primary evidence, and next action.
2. **Hypothesis**: mechanism, target, horizon, and expected failure modes.
3. **Data**: sources, point-in-time availability, universe, coverage, cleaning, exclusions, and quality results.
4. **Method**: signal, portfolio rules, split dates, execution, costs, constraints, and benchmark.
5. **Results**: gross and net metrics, equity curve, drawdown, turnover, exposure, attribution, and uncertainty.
6. **Validation**: walk-forward, robustness, ablation, placebo, multiple-testing treatment, and sensitivity.
7. **Risks**: market, trading, model, operational, capacity, and stress findings.
8. **Reproduction**: command, environment, configuration, data snapshot, seed, and artifact paths.
9. **Limitations**: known gaps and the evidence required before the next gate.

Keep tables internally consistent. Reconcile beginning capital, PnL, costs, cash, and ending equity. Round only at presentation time and retain full precision in calculations.

