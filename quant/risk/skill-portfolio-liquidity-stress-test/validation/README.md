# Validation

Run from the repository root:

```bash
python scripts/stress_liquidity.py --demo
python scripts/stress_liquidity.py --demo --redemption-value 50000000
python validation/smoke.py
python -B -m unittest discover -s tests -v
```

The repository-local suite covers CLI exclusivity, finite parameters, duplicate holdings, capacity and pro-rata redemption calculations, shortfalls, input/output failures, missing columns, report contracts, and package metadata.

PandaData integration was tested separately with sanitized results. User holdings, redemption targets, and spread provenance are not embedded. `runnable` is a community self-validation level, not official verification.
