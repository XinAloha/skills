# Validation

Run from the repository root:

```bash
python scripts/study_index_rebalance.py --demo
python validation/smoke.py
python -B -m unittest discover -s tests -v
```

The repository-local suite covers CLI source exclusivity, event windows, strict inputs, duplicate observations, separate announcement/effective anchors, CAR and weight summaries, missing-anchor limitations, missing columns, and report contracts.

PandaData integration was tested separately with sanitized results. Official announcement provenance remains an external evidence requirement. `runnable` is a community self-validation level, not official verification.
