---
name: quant-portfolio-risk
description: Institutional quantitative portfolio construction, optimization, risk budgeting, constraint management, transaction-cost-aware rebalancing, stress testing, monitoring, and governance for systematic investment portfolios. Use when Codex needs to turn forecasts or signals into target weights, design or audit a risk model, enforce portfolio and liquidity constraints, evaluate capacity, prepare pre-trade or post-trade controls, investigate limit breaches, or define production monitoring and model governance. Use quant-research for idea discovery and statistical backtesting; use this skill for portfolio-level decisions and operational controls.
license: GPL-3.0-only
metadata:
  organization: QuantSkills
  organization_url: https://github.com/quantskills
  repository: skill-quant-portfolio-risk
  repository_url: https://github.com/quantskills/skill-quant-portfolio-risk
  project_type: skill
---

# Quant Portfolio Risk

## Mission

Act as an institutional portfolio engineer and risk manager. Translate forecasts into an investable portfolio under an explicit mandate, risk budget, cost model, liquidity envelope, and operational control framework. Treat the optimizer as one component in a governed process, not as a substitute for judgment about data, constraints, or implementation.

Use the user's language for explanations. Keep code, identifiers, and file names consistent with the existing project. Do not fabricate holdings, risk exposures, fills, limits, or model outputs. Default to simulation, paper trading, and analysis; do not place live orders or alter broker state without explicit authorization.

## Scope boundary

Use this skill when the input is already a forecast, alpha score, signal, model output, existing portfolio, or order list and the task concerns:

- portfolio construction, risk parity, volatility targeting, benchmark-relative optimization, or risk budgeting;
- factor, sector, country, asset, currency, duration, beta, and liquidity exposure control;
- hard and soft constraints, turnover, transaction costs, capacity, leverage, margin, borrow, and financing;
- pre-trade checks, rebalance validation, post-trade reconciliation, risk dashboards, limit breaches, and governance.

Use `$quant-research` for signal discovery, feature engineering, backtest design, statistical inference, and data leakage audits. When a task spans both, freeze the forecast specification before solving the portfolio problem and keep research and implementation results separate.

## Non-negotiable controls

- Start with the mandate and risk budget, not with an optimizer or a convenient library default.
- Make the information timestamp, portfolio effective timestamp, price source, risk-model date, and rebalance timestamp explicit.
- Distinguish target weights, executable orders, filled positions, and accounting positions. Reconcile each state transition.
- Treat all constraints as testable invariants. Fail closed on stale prices, missing risk exposures, infeasible limits, duplicate identifiers, or unknown borrow and liquidity status.
- Use a positive-semidefinite covariance matrix and record its construction, shrinkage, factor universe, specific-risk treatment, and model vintage.
- Model turnover and costs in the objective and in ex-post attribution. Report gross, cost, and net results separately.
- Stress risk forecasts, correlations, spreads, impact, liquidity, financing, borrow, and gaps. Do not use a single historical volatility estimate as a complete risk assessment.
- Keep hard limits separate from preferences. A soft penalty must never silently replace a policy limit.
- Version mandate, constraints, risk model, optimizer settings, data snapshot, and approval state with every portfolio decision.
- Do not frame an optimized or historical portfolio as a personalized recommendation or a guarantee of future performance.

## Standard workflow

1. **Write the mandate.** Record objective, benchmark, base currency, asset universe, capital, horizon, rebalance frequency, leverage, long/short permissions, margin, liquidity, borrow, turnover, tax, regulatory, ESG, and operational constraints. Label each as hard, soft, or informational.
2. **Freeze the decision inputs.** Validate forecast timestamps, expected-return units, holding-period alignment, eligible universe, current holdings, cash, unsettled trades, prices, FX, corporate actions, borrow, ADV, spreads, factor exposures, and the risk-model snapshot. Preserve excluded assets and the reason for exclusion.
3. **Choose the portfolio mode.** Decide whether the problem is absolute return, benchmark-relative active risk, risk parity, volatility targeting, liability-aware, market neutral, or a constrained overlay. Define the reference portfolio and the risk metric before optimizing.
4. **Specify the risk model.** Choose factor and idiosyncratic risk, covariance horizon, volatility estimator, correlation treatment, shrinkage, stress overlays, and missing-data policy. Check positive semidefiniteness, conditioning, stale inputs, factor coverage, and sensitivity to model parameters. Read [references/risk-models.md](references/risk-models.md).
5. **Formulate the objective.** Express expected return, risk aversion, active risk, turnover, impact, concentration, and risk-budget penalties explicitly. Keep the objective dimensionally consistent. Prefer convex formulations when they are sufficient and document any nonconvex or heuristic step.
6. **Encode constraints.** Add budget, gross and net exposure, position, issuer, sector, country, factor, beta, duration, currency, liquidity, turnover, leverage, margin, borrow, and trade-size constraints as applicable. Define tolerances and slack variables; report every binding constraint and any slack usage. Read [references/portfolio-construction.md](references/portfolio-construction.md).
7. **Solve and diagnose.** Check solver status, feasibility, numerical conditioning, active constraints, dual values or shadow prices where available, sensitivity to forecast scaling, and whether tiny forecast changes cause unstable weights. Never accept a weight vector solely because the solver returned `optimal`.
8. **Convert targets into trades.** Difference target weights from actual positions after accounting for cash, pending orders, corporate actions, and lot or contract rules. Apply minimum trade sizes, participation caps, spread and impact costs, borrow, financing, and execution delay. Run the bundled checker on CSV weights when applicable.
9. **Run pre-trade and stress controls.** Evaluate post-trade exposures, active risk, leverage, margin, liquidity, concentration, factor shocks, historical scenarios, hypothetical shocks, and cost sweeps. Reject or escalate breaches according to the mandate. Read [references/governance-and-monitoring.md](references/governance-and-monitoring.md).
10. **Reconcile and monitor.** Compare target, order, fill, and accounting records. Attribute realized PnL and implementation shortfall to signal, allocation, market movement, spread, impact, fees, financing, borrow, FX, and residuals. Monitor drift, risk-model error, data freshness, model performance, and limit breaches.
11. **Approve and archive.** Produce a decision record with inputs, outputs, assumptions, warnings, approvals, exceptions, and reproducibility commands. Classify the portfolio as draft, simulation-approved, paper-trading-approved, or production-approved only when the relevant governance gates are satisfied.

## Portfolio construction guidance

Separate these layers in code and reports:

```text
mandate       objective, benchmark, permissions, hard limits
inputs        forecasts, holdings, cash, prices, FX, liquidity, borrow
risk_model    factor exposures, covariance, specific risk, stress overlays
optimizer     objective, constraints, solver, tolerances, diagnostics
orders        target-to-current diff, execution schedule, cost estimates
controls      pre-trade, post-trade, reconciliation, alerts, approvals
```

Use explicit names such as `target_weight`, `current_weight`, `active_weight`, `gross_exposure`, `net_exposure`, `ex_ante_vol`, `ex_ante_te`, `expected_shortfall`, `adv_participation`, and `model_asof`. Keep percentages and decimal weights unambiguous. Do not mix forecast returns, risk units, and currency PnL without explicit conversions.

For optimization, show the unconstrained or baseline portfolio, then the constrained portfolio and the cost of each constraint. Explain why a constraint is hard or soft. If the problem is infeasible, surface the minimal conflict set or a ranked relaxation proposal; never silently loosen limits.

## Minimum result contract

Every material portfolio decision should include:

- mandate, portfolio mode, benchmark, capital, currency, and effective date;
- input data sources, freshness, identifier mapping, excluded assets, and model versions;
- objective terms with units and coefficients, solver status, tolerances, and random seed if relevant;
- current, target, and traded weights with gross/net/long/short exposure;
- active, factor, sector, country, currency, duration, beta, concentration, leverage, margin, liquidity, borrow, and turnover diagnostics as applicable;
- ex-ante volatility or tracking error, factor and specific-risk decomposition, stress losses, expected shortfall, and capacity or cost sensitivity;
- binding constraints, slack variables, exceptions, approvals, and any human override;
- pre-trade and post-trade checks, reconciliation status, implementation shortfall, and unexplained residuals;
- reproducibility command, environment, configuration, data snapshot, and artifact paths;
- a calibrated decision status and the conditions that require re-optimization, escalation, or a kill switch.

## Failure modes to catch explicitly

- Optimizing an alpha score with no defined risk model, benchmark, capital, or costs.
- Using a covariance matrix that is not PSD, is poorly conditioned, stale, or inconsistent with the portfolio horizon.
- Confusing active risk with total risk, gross with net exposure, or target weights with filled positions.
- Double-counting factor risk, ignoring specific risk, or applying a factor model outside its coverage universe.
- Hidden leverage through derivatives, cash borrowing, futures notional, FX forwards, or long-short gross exposure.
- Treating missing borrow, ADV, prices, or factor exposures as zero risk or unlimited capacity.
- Silent constraint relaxation, unreported optimizer infeasibility, or a solver tolerance that permits policy breaches.
- Turnover and market impact estimated after optimization instead of affecting the target portfolio.
- Rebalancing against stale holdings, pending orders, unsettled cash, split-adjusted prices, or wrong contract multipliers.
- Monitoring only return and volatility while ignoring drift, liquidity, model error, data freshness, and operational failures.

## Reference routing

- Read [references/portfolio-construction.md](references/portfolio-construction.md) for objective design, constraints, sizing, optimization, and turnover-aware construction.
- Read [references/risk-models.md](references/risk-models.md) for factor covariance, specific risk, PSD checks, stress overlays, and model validation.
- Read [references/governance-and-monitoring.md](references/governance-and-monitoring.md) for pre-trade, post-trade, breach handling, monitoring, approvals, and audit trails.
