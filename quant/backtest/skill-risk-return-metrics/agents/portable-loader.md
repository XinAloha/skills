# Portable loader

Load `../SKILL.md` as the primary instruction file. Run `../scripts/risk_return_metrics.py`
with the user-provided ticker and window, then verify the reported risk/return ratios against
the returned series before presenting the result (treat `null` ratios as undefined, not zero).
Load only the referenced files needed for the current case. Reproduce the disclaimer from
`../README.md` verbatim; never promise returns.
