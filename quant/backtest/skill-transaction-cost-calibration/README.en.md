<div align="center">
  <h1>Transaction Cost Calibration</h1>
  <p>Calibrate an interpretable execution-friction model from fills and pre-trade market data.</p>
  <p>
    <a href="README.md">简体中文</a>
    ·
    <a href="https://github.com/quantskills/skill-transaction-cost-calibration/issues">Report an issue</a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/QuantSkills-runnable-2f6fdb?style=flat-square" alt="QuantSkills runnable">
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python 3.10 or newer">
    <img src="https://img.shields.io/badge/license-GPL--3.0-2ea44f?style=flat-square" alt="GPL-3.0 license">
  </p>
</div>

> 📌 **Positioning**: Execution-cost research and backtest calibration. It does not infer alpha, trade advice, or broker quality.

## 🧭 Capability Map

| Capability | Result |
| --- | --- |
| Fill attribution | Reference price, slippage, spread, and commission per fill |
| Quote-first reference | Prefer quote mid available at or before execution |
| Bar fallback | Use prior bar close when quotes are unavailable |
| Impact diagnostics | Fit a transparent curve within observed participation |

## ⚡ Quick Start

```bash
pip install -r requirements.txt
python scripts/calibrate_costs.py --demo --output-dir out
```

Typical real-data run:

```bash
python scripts/calibrate_costs.py \
  --executions fills.csv \
  --quotes quotes.csv \
  --bars bars.csv \
  --commission-bps 2.5 \
  --output-dir cost_out
```

## 📥 Inputs and 📤 Outputs

| Dataset | Required columns | Notes |
| --- | --- | --- |
| `executions.csv` | `timestamp,symbol,side,quantity,price` | `side` is `buy` or `sell` |
| `quotes.csv` | `timestamp,symbol,bid,ask` | Optional; preferred reference |
| `bars.csv` | `timestamp,symbol,close,volume` | Optional fallback and participation |

Generated artifacts:

- `execution_costs.csv`: slippage, spread, participation, commission, and total cost per fill.
- `cost_curve.csv`: median and p95 cost by participation bin.
- `summary.json`: coverage, cost distribution, impact coefficients, and warnings.

## 🔬 Workflow

```text
Input contract → UTC parsing → pre-fill as-of reference → cost decomposition → participation curve → coverage review
```

Keep signed slippage separate from absolute cost. Do not extrapolate beyond maximum observed participation without an explicit sensitivity assumption.

## 🧱 Boundaries and Sources

- Use only permitted public or user-provided sources; see [`references/source_boundary.md`](references/source_boundary.md).
- Never use quotes or bars after the fill, and never silently fill a missing reference.
- This does not replace portfolio liquidation stress testing or generic backtest tooling.

## 📁 Repository Layout

```text
SKILL.md                       # Agent workflow
scripts/calibrate_costs.py     # Deterministic calibrator
references/input_contract.md   # Input fields and time rules
references/source_boundary.md  # Source boundary
agents/openai.yaml             # Agent UI metadata
agents/cursor-rule.mdc         # Cursor runtime entrypoint
agents/portable-loader.md      # Hermes/portable runtime entrypoint
requirements.txt               # Python dependencies
```

## ✅ Local Validation

```bash
node scripts/validate-qsh-form.mjs SKILL.md
python scripts/calibrate_costs.py --demo --output-dir out
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
