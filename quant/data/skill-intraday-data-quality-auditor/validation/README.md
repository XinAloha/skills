# Validation

Run from the repository root:

```bash
python scripts/audit_bars.py --demo
python validation/smoke.py
python -B -m unittest discover -s tests -v
```

The repository-local regression suite covers valid minute bars, legal cross-date night sessions, input-order inversion, mixed timezone awareness, invalid parameters, and report contracts. The demo is intentionally anomalous and may return `warning` or `fail`; successful execution and valid JSON are the smoke-test criteria.

PandaData integration was tested separately with sanitized results. No credentials or raw account responses are stored in this repository. `validation_level: runnable` means the deterministic script and offline checks run; it does not mean official QuantSkills verification.
