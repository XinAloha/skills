# Validation

Run from the repository root:

```bash
python scripts/audit_universe.py --demo
python validation/smoke.py
python -B -m unittest discover -s tests -v
```

The repository-local suite covers CLI exclusivity, strict dates, lifecycle consistency, duplicate identity dates, binary eligibility, missing delisting returns, stable identifiers, point-in-time reconstruction, file errors, missing columns, and report contracts. The demo intentionally contains lifecycle defects.

PandaData integration was tested separately with sanitized results. Complete historical coverage and standardized delisting returns remain external evidence requirements. The `runnable` label records the validation scope demonstrated by the commands above.
