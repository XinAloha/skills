# Validation

Run from the repository root:

```bash
python scripts/audit_adjustments.py --demo
python validation/smoke.py
python -B -m unittest discover -s tests -v
```

The repository-local offline suite covers CLI source exclusivity, clean split and dividend events, adjusted-return mismatch, unexplained jumps, invalid event inputs, strict dates, configurable thresholds, missing columns, and report contracts. The demo intentionally contains an unexplained raw-price jump.

PandaData integration was tested separately with sanitized results. No credentials or raw account responses are stored here. `runnable` is a community self-validation level, not official verification.
