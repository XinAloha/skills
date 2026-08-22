# 🧩 ML Factor Ensemble

[简体中文](README.md) | **English**

> Combine many existing factors into one out-of-sample meta-alpha with a leakage-safe
> rolling walk-forward.

## 📖 What This Is

The community has 800+ factors but no supervised layer to combine them. This skill takes a
long panel `date, symbol, <factors>, fwd_ret` and emits a combined signal containing
**out-of-sample predictions only**, plus feature importance and ICIR lift over an
equal-weight baseline.

It differs clearly from existing repos:

- Unlike `skill-factormad-debate-factor-mining` (LLM debate that *generates new formulas*),
  this skill *combines existing factors* by supervised learning.
- Unlike `skill-factor-evaluate` (scores a *single* factor), this learns a *multi-factor weighting*.

**The whole point is leakage control**: rolling walk-forward + purging + embargo
(López de Prado). Naive K-fold massively overstates performance on overlapping
forward-return labels; this skill prevents it at the fold-construction level.

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python scripts/ml_ensemble.py --model ridge --horizon 5   # toy demo
python scripts/test_ml_ensemble.py
```

Both `combined_signal.csv` and `ensemble_report.md` are produced. Short histories
degrade cleanly to an empty, typed OOS signal plus an explicit report warning.

## ⚠️ Disclaimer

This repository provides factor-combination research methods and a code skeleton only.
It places no orders, verifies no performance claims, and does not constitute investment
advice. OOS ≠ live. Community Project; validate outputs against the cited data and local
review requirements.

## 📜 License

GPL-3.0-only. See [LICENSE](LICENSE).

## 🐼 PandaAI / QUANTSKILLS Community

<div align="center">
  <img src="https://raw.githubusercontent.com/quantskills/.github/main/profile/assets/pandaai-community-qr.jpg" alt="PandaAI community QR code" width="220">
  <br>
  <sub>Scan the QR code to join the PandaAI community for QUANTSKILLS skills, agent workflows, and quantitative research practice.</sub>
</div>
