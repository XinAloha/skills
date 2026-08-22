<div align="center">
  <h1>Forecast Calibration Audit</h1>
  <p>Measure whether probability forecasts are trustworthy, not merely well ranked.</p>
  <p>
    <a href="README.md">简体中文</a>
    ·
    <a href="https://github.com/quantskills/skill-forecast-calibration-audit/issues">Report an issue</a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/QuantSkills-runnable-2f6fdb?style=flat-square" alt="QuantSkills runnable">
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python 3.10 or newer">
    <img src="https://img.shields.io/badge/license-GPL--3.0-2ea44f?style=flat-square" alt="GPL-3.0 license">
  </p>
</div>

> 📌 **Positioning**: Probability-forecast quality audit covering reliability, scores, thresholds, and time drift. Not investment advice.

## 🧭 Capability Map

| Capability | Result |
| --- | --- |
| Reliability | Probability bins, observed rates, gaps, and weighted gaps |
| Proper scores | Brier score and clipped log loss |
| Calibration | Intercept, slope, ECE, and MCE |
| Time audit | Contiguous slices, class balance, and drift warnings |

## ⚡ Quick Start

```bash
pip install -r requirements.txt
python scripts/calibrate_forecasts.py --demo --output-dir out
```

Typical real-data run:

```bash
python scripts/calibrate_forecasts.py \
  --input forecasts.csv \
  --output-dir calibration_out \
  --threshold 0.5 \
  --time-bins 5
```

## 📥 Inputs and 📤 Outputs

| Dataset | Required columns | Notes |
| --- | --- | --- |
| `forecasts.csv` | `date,probability,outcome` | Probability in `[0,1]`; outcome is `0` or `1` |
| Grouping | Optional `regime` or `--regime-column` | Enables subgroup diagnostics |

Generated artifacts:

- `scored_predictions.csv`: original predictions plus per-row Brier and log-loss terms.
- `reliability.csv`: probability bins, forecast mean, observed rate, and gaps.
- `time_metrics.csv`: calibration metrics for chronological slices.
- `summary.json`: aggregate metrics, calibration coefficients, class balance, and warnings.

## 🔬 Workflow

```text
Input contract → probability/label checks → chronological sort → contiguous bins → scores and calibration → drift review
```

Probabilities are clipped only inside the log-loss calculation; original values remain in the scored output. Interpret small bins with count, date range, and class balance. When recalibrating, train on an earlier window and validate on a later one.

## 🧱 Boundaries and Sources

- Use only permitted public or user-provided sources; see [`references/source_boundary.md`](references/source_boundary.md).
- Never randomly shuffle a time series or treat a perfect tiny-sample score as generalization evidence.
- This does not replace factor evaluation, IC analysis, or event tracking.

## 📁 Repository Layout

```text
SKILL.md                        # Agent workflow
scripts/calibrate_forecasts.py  # Deterministic auditor
references/input_contract.md    # Input fields and checks
references/source_boundary.md   # Source boundary
agents/openai.yaml              # Agent UI metadata
agents/cursor-rule.mdc          # Cursor runtime entrypoint
agents/portable-loader.md       # Hermes/portable runtime entrypoint
requirements.txt                # Python dependencies
```

## ✅ Local Validation

```bash
node scripts/validate-qsh-form.mjs SKILL.md
python scripts/calibrate_forecasts.py --demo --output-dir out
```

## Disclaimer

This repository organizes research methods only. It is not official, is not affiliated with any covered entity, does not verify performance claims, and does not constitute investment advice.

## License

GNU General Public License v3.0. See [LICENSE](LICENSE).

## PandaAI / QUANTSKILLS Community

<div align="center">
  <img src="https://raw.githubusercontent.com/quantskills/.github/main/profile/assets/pandaai-community-qr.jpg" alt="PandaAI community QR code" width="220">
  <br>
  <sub>Scan the QR code to join the PandaAI community for QUANTSKILLS skills, agent workflows, and quantitative research practice.</sub>
</div>
