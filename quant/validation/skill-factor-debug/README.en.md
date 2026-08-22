# skill-factor-debug

[简体中文](./README.md) | [English](./README.en.md)

Not an IDE debugger, but a **diagnostic playbook for factor crashes / failures / numerical anomalies**: a 9-category symptom lookup organized as "symptom → candidate cause → verification". Specializes in "factor crashed" and "looks too good, suspect a bug".

`role: skill` `output: diagnostic playbook` `paradigm: cross-section research`

---

`skill-factor-debug` is the **factor troubleshooting Skill** provided by PandaAI Quant Skills. When a factor crashes / produces something off / is suspected of look-ahead bias, this Skill helps the AI Agent prescribe by symptom — not blind-edit.

## 🎯 What This Skill Solves

90% of factor crashes fall into 5 buckets:

- Forbidden-token hit (attempting to read future data)
- Signal validation failure (cross-section mean / std / NaN ratio)
- Look-ahead bias (IC looks like 0.20, live trading dies)
- Data checksum mismatch (parquet was modified)
- Correlation ≥ 0.85 (re-skinned old factor)

Each has a typical repair path. This Skill provides a **9-category symptom lookup** + **6 classic look-ahead patterns** + **bisection localization**, so debugging becomes "symptom → cause → verify" instead of "guess → edit → guess again".

## ⚡ Debug Workflow

```
1. Read error log: cat journal/last_failed/run_XXXX_error.txt
2. Use symptom lookup to classify
3. Read corresponding references for the fix
4. Isolated minimal repro: python -c "import alpha; alpha.run(...)"
5. Smoke test → py runner.py once
```

When errors aren't clear: **bisection** — halve FACTORS repeatedly to localize the offending factor.

## 🩺 9-Category Symptom Lookup

| Symptom | Cause | references |
|---|---|---|
| `PermissionError: forbidden-token` | alpha.py contains forbidden token | `forbidden-tokens.md` |
| `ValueError: HORIZON not in (1,3,5,10,20)` | HORIZON out of whitelist | `horizon-mismatch.md` |
| `ValueError: cross-section mean/std out of range` | Signal not z-scored | `signal-validation.md` |
| `RuntimeError: checksum mismatch` | parquet data modified | `data-integrity.md` |
| Signal validates but IC > 0.20 | **Look-ahead bias** | `look-ahead-bias.md` |
| Backtest empty / Sharpe NaN | universe wrong / over-strict limit-up filter | `backtest-anomaly.md` |
| Factor correlation > 0.85 | Re-skinned factor | `correlation-violation.md` |
| Sharpe >> IC_IR | close-as-price / no fees / T+0 | `look-ahead-bias.md` |
| Same code, different results | dict order / float reduction | `nondeterminism.md` |

## 🚨 Danger Signals

Seeing any of the following → **suspect look-ahead bias first**, don't trust the result:

- rank IC > 0.15
- Annual return > 50% with MDD < 5%
- Sharpe > 5
- Sharpe / IC_IR > 1.0
- val/train IC ratio > 95%

Real factors should have val IC 30~70% lower than train IC.

## 📦 Repository Layout

```
skill-factor-debug/
├── SKILL.md
├── README.md / README.en.md
├── references/
│   ├── forbidden-tokens.md             # Forbidden tokens list + fix
│   ├── signal-validation.md            # Signal validation failure diagnosis
│   ├── horizon-mismatch.md             # HORIZON / LABEL_KIND mismatch
│   ├── look-ahead-bias.md              # 6 classic look-ahead patterns
│   ├── backtest-anomaly.md             # Backtest anomalies + 5-item check
│   ├── correlation-violation.md        # Correlation too high + 3 redesign directions
│   ├── data-integrity.md               # checksum mismatch handling
│   └── nondeterminism.md               # Non-reproducibility + standard seed-fixing
└── agents/
    ├── openai.yaml
    ├── cursor-rule.mdc
    └── portable-loader.md
```

## 🚀 Quick Start

Drop `skill-factor-debug/` into your Agent's skills directory. Auto-loaded on triggers ("factor crashed / CRASH / suspicious IC / debug factor").

## 🔬 6 Classic Look-Ahead Patterns (most dangerous)

1. Using `close[T]` as T-day execution price (must be T+1 open)
2. `fwd_ret = close.pct_change(h)` (backward, direction reversed)
3. `fillna(method='bfill')` (filling past with future)
4. Fitting parameters on full set (train+val+test) and reapplying
5. Rolling window includes current (need `.shift(1)`)
6. Using future field to slice subsamples (e.g., 2026 market cap to slice 2021)

See `references/look-ahead-bias.md`.

## 🧭 Relation to Other PandaAI Quant Skills

| Repository | Purpose |
|---|---|
| skill-factor-mine | Normal iteration |
| skill-factor-evaluate | Score (when it crashes → debug) |
| skill-backtest | When backtest looks wrong → debug |
| skill-ic-analysis | When IC is suspiciously high → debug |
| **skill-factor-debug** (this) | 9-category symptom lookup |
| skill-factor-review | Whole library review |

## 📜 Project Status & Boundaries

- **Status**: Community Project, not officially reviewed / certified / endorsed
- **Data Source**: This repository ships no market data. Users must supply their own market panel; data legality and licensing are the user's responsibility
- **Core Assumptions**: Symptom lookup targets projects with "cross-section research + T+1 open execution + 3-way split (train/val/test) + locked evaluation constitution"; other paradigms need self-mapping
- **Known Limitations**: This Skill is a diagnostic playbook, not auto-repair — fixes still require human (or Agent) editing per references
- **Risk Boundary**: Diagnostics use heuristic thresholds (e.g., "Sharpe / IC_IR > 1.0 almost certainly a bug"); occasional legitimate factors exceed thresholds, final judgment requires human review
- **Usage**: For quantitative research, education, and methodology reference only. **Does not constitute investment advice, trading signals, or profit guarantees of any form**

## 📜 License

This repository is licensed under the GNU General Public License v3.0. See LICENSE.

Copyright (C) 2026 QuantSkills.

## 🐼 PandaAI / QUANTSKILLS Community

<div align="center">
  <img src="https://raw.githubusercontent.com/quantskills/.github/main/profile/assets/pandaai-community-qr.jpg" alt="PandaAI community QR code" width="220">
  <br>
  <sub>Scan the QR code to join the PandaAI community for QUANTSKILLS skills, agent workflows, and quantitative research practice.</sub>
</div>
