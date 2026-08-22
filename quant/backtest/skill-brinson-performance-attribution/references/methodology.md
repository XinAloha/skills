# Methodology

## Single-period

Supports:

- **Brinson–Fachler**: allocation `(w_p−w_b)*(r_b − R_b)`
- **Brinson–Hood–Beebower (BHB)**: allocation `(w_p−w_b)*r_b`

Plus selection `w_b*(r_p−r_b)` and interaction `(w_p−w_b)*(r_p−r_b)`.

## Multi-period

Carino (1999) smoothing links period arithmetic effects to geometric active return.

## Diagnostics

- Sector uniqueness, finite values, and portfolio/benchmark weight sums
- Weight-sum sanity
- Residual check (active − explained)
- Herfindahl concentration
- Top absolute contributors

For multi-period reports, headline returns and effects are Carino-linked geometric
totals; sector rows and HHI are the latest-period snapshot.

## References

- Brinson, Hood, Beebower (1986)
- Brinson, Fachler (1985)
- Carino (1999), “Combining attribution effects over time”
