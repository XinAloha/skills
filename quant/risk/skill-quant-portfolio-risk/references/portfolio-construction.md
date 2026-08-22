# Institutional Portfolio Construction

Use this reference when translating forecasts and current holdings into a target portfolio.

## Contents

- [Mandate translation](#mandate-translation)
- [Objective design](#objective-design)
- [Constraint taxonomy](#constraint-taxonomy)
- [Turnover and costs](#turnover-and-costs)
- [Solver diagnostics](#solver-diagnostics)
- [Portfolio review](#portfolio-review)

## Mandate translation

Convert policy language into measurable variables before optimization:

| Policy concept | Portfolio variable |
| --- | --- |
| Benchmark-relative | active weight `w - b`, tracking error, active factor exposure |
| Long-only | `w_i >= 0`, fully invested or explicit cash range |
| Market neutral | net exposure interval and beta tolerance, not only sum of weights |
| Liquidity | notional / ADV, spread, participation, liquidation horizon |
| Risk budget | ex-ante volatility, marginal contribution, factor or sleeve budget |
| Concentration | issuer, sector, country, instrument, and correlated-cluster limits |
| Turnover | one-way and two-way turnover over a defined horizon |
| Leverage | gross exposure, derivative notional, margin, financing, and stress leverage |

Every limit needs a unit, a measurement time, a tolerance, an owner, and an escalation path.

## Objective design

Choose the mode before choosing coefficients:

- **Absolute:** maximize expected return minus risk, cost, and concentration penalties subject to total-risk limits.
- **Active:** maximize expected active return minus tracking-error, turnover, and cost penalties subject to benchmark-relative limits.
- **Risk budget:** allocate risk contributions across assets, factors, sleeves, or strategies, with explicit return or diversification preferences.
- **Volatility target:** scale a feasible portfolio to a target risk only after applying leverage, margin, liquidity, and stress caps.
- **Overlay:** optimize incremental trades around a frozen base portfolio and protect the base portfolio's constraints.

Keep forecast scaling visible. A score is not automatically an expected return. Calibrate or rank forecasts deliberately, document the horizon, and test whether the result is dominated by one arbitrary scaling choice.

A common active formulation is:

```text
maximize  alpha' * (w - b)
          - risk_aversion * (w - b)' * Sigma * (w - b)
          - turnover_penalty * ||w - w_prev||_1
          - impact_penalty * cost(w - w_prev)
          - concentration_penalty * concentration(w)
```

Treat this as a template, not a universal answer. Confirm that all terms use compatible units and that hard policy limits are enforced outside soft penalties.

## Constraint taxonomy

Apply constraints in layers and report which layer binds:

1. **Accounting:** budget, cash, currency conversion, contract multiplier, lot size, and settlement.
2. **Permission:** long/short, instrument, venue, borrow, derivatives, leverage, margin, and financing.
3. **Position:** name, issuer, sector, country, sleeve, and correlated-cluster limits.
4. **Risk:** total volatility, tracking error, beta, factor exposure, duration, delta, vega, and scenario loss.
5. **Trading:** turnover, minimum trade, ADV participation, spread, impact, price bands, and liquidation horizon.
6. **Operational:** stale data, missing exposure, market status, restricted list, model version, and approval status.

Use hard constraints for policy, legal, or safety limits. Use soft penalties for preferences such as smoothness or diversification only when the maximum permissible breach is separately enforced. Add slack variables only to quantify infeasibility; each slack must have a cost, limit, and escalation rule.

For factor or sector neutrality, distinguish exact neutrality, bounded exposure, and benchmark-relative exposure. A zero beta estimate does not imply zero stress loss or zero exposure to non-modeled risks.

## Turnover and costs

Compute trades from actual positions, not prior target weights:

```text
trade_notional_i = (target_weight_i - current_weight_i) * portfolio_value
```

Include pending orders, fills, corporate actions, cash, FX, and derivative multipliers before computing the difference. Estimate cost as a function of spread, volatility, participation, order size, and liquidity bucket. Use conservative sweeps and report the marginal cost of each constraint or turnover reduction.

Do not assume every target can be filled at a single price. For illiquid assets, model partial fills and residual risk during the execution window. Recalculate post-trade risk after fills rather than treating the target vector as achieved.

## Solver diagnostics

Require:

- explicit solver status and feasibility residuals;
- maximum equality and inequality violation, not only a rounded display;
- covariance PSD and conditioning checks;
- active constraints, dual values or shadow prices where supported;
- weight stability under small forecast, covariance, and cost perturbations;
- a baseline comparison and an explanation for large active positions;
- deterministic solver settings and a fallback or escalation path.

If infeasible, identify conflicting constraints and propose ranked relaxations. Never remove a limit silently. If a numerical solution is unstable, prefer a stable approximate portfolio with a disclosed tradeoff over an apparently optimal but fragile vector.

## Portfolio review

Review target weights in four views: holdings, exposures, risk contributions, and trades. A good review explains why a portfolio changed, which risks paid for the change, what costs it incurs, and how it behaves under the stated stress scenarios. Archive the input snapshot, target, orders, checks, approvals, and final fills together.

