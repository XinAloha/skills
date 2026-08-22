# skill-factor-review

[简体中文](./README.md) | [English](./README.en.md)

Not single-factor evaluation, but a **whole-library review Skill**: scans experiment logs + factor cards, outputs a 3-layer report (quantitative inventory + structural analysis + research recommendations) — answering "what's been done, where the optimum is, what to mine next".

`role: skill` `output: 3-layer review report` `paradigm: library-level review`

---

`skill-factor-review` is the **factor library review Skill** provided by PandaAI Quant Skills. After N iterations, it's time to "stop and think". This Skill systematically reviews factor library + experiment log, producing actionable next-step research recommendations.

## 🎯 What This Skill Solves

Common situations after 50+ iterations and 20+ factors:

- No idea where to mine next (blindly adding new factors)
- 30% of the library is already homogeneous, no one notices
- Marginal returns down to +0.002/iter but still mining
- Want to do stage acceptance but no comparable data
- Want to write a research report but no structured output

This Skill enforces a 3-layer structure:

1. **Quantitative Inventory** — accept rate / CRASH rate / score trajectory / momentum
2. **Structural Analysis** — factor family distribution / correlation matrix / best path traceback
3. **Research Recommendations** — 3-5 concrete hypotheses (with op_type + reason + expected score) + risk warnings

## ⚡ Review Flow

```
1. Scan runs.jsonl / INDEX.md / factor cards → raw data
2. Layer 1: accept rate, CRASH rate, score trajectory, momentum curve
3. Layer 2: family classification, correlation matrix, key-decision traceback
4. Layer 3: Based on Layer 2 findings, give 3-5 concrete next hypotheses
5. Output standard report + charts
```

## 🗃️ Input Requirements

- Experiment log: `runs.jsonl` / `experiments.jsonl` / git log (any works)
- Factor library index: `INDEX.md` / `models/registry.json`
- Factor cards: each factor has `card.json` with score, metrics
- Best marker: `best.json` or current alpha.py

**Minimum**: ≥ 30 iterations, ≥ 10 factors for review to be meaningful. Below this, just check `runner status` directly.

## 📦 Repository Layout

```
skill-factor-review/
├── SKILL.md
├── README.md / README.en.md
├── references/
│   ├── quantitative-stats.md           # Layer 1 computation
│   ├── structural-analysis.md          # Layer 2 sub-analyses
│   ├── research-recommendations.md     # Layer 3 hypothesis format
│   ├── report-template.md              # Standard report template
│   └── anti-patterns.md                # 12 anti-patterns
└── agents/
    ├── openai.yaml
    ├── cursor-rule.mdc
    └── portable-loader.md
```

## 🚀 Quick Start

Drop `skill-factor-review/` into your Agent's skills directory. Auto-loaded on triggers ("review factor library / what's been done / what to mine next / stage acceptance").

## 📄 Report Sample

```markdown
# Factor Library Review — 2026-06-12

## Layer 1: Quantitative Inventory
- Total runs 67, accept rate 34%, CRASHED 6
- Score +0.05 → +0.63 (5 big jumps + 30+ micro-iterations)
- Momentum: marginal return down to +0.002/iter

## Layer 2: Structural Analysis
- Current FACTORS: [size_inv, max_ret_120, vol_cv_120]
- Family coverage: liquidity 1 / lottery 1 / volume-stat 1; reversal/momentum/vol all empty
- Correlation matrix: mean |ρ| = 0.43 (medium)
- Best path: 4 big jumps came from family change / horizon change

## Layer 3: Next Hypotheses (with priority)
1. [add_factor] f_reversal_5         expected +0.03 ~ +0.07
2. [horizon]    try H=10             expected +0.03 ~ +0.06 (from turnover reduction)
3. [combine_method] Ridge α=10       expected ±0.05
4. [label_kind] vol_adjusted         high-variance, run last

## Risk Warnings
- Library biased toward "lottery + liquidity", may collapse on regime shift
- 67 iterations approaching "naive mining" margin; consider Phase 2 or more complex models
```

## 🧭 Relation to Other PandaAI Quant Skills

| Repository | Purpose |
|---|---|
| skill-factor-mine | Single iteration |
| skill-factor-evaluate | Single-factor scoring |
| skill-backtest | Single-factor backtest |
| skill-ic-analysis | Single-factor deep diagnostic |
| skill-factor-debug | Single-crash debugging |
| **skill-factor-review** (this) | Library-level review |

Review output feeds back into skill-factor-mine's next-round hypothesis design.

## 📜 Project Status & Boundaries

- **Status**: Community Project, not officially reviewed / certified / endorsed
- **Data Source**: This repository ships no market data. Users must supply their own market panel and experiment log; data legality and licensing are the user's responsibility
- **Core Assumptions**: Project uses 3-way frozen split (train / val / test), with test strictly invisible; evaluation constitution locked (`primary_score()` immutable)
- **Known Limitations**: Recommendations based on historical experiment data; limited predictive power for structural changes like regime shifts; Layer 3 hypotheses still need human review, not auto-execute
- **Risk Boundary**: Review conclusions reflect statistical trends under historical data + assumptions only, not future performance
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
