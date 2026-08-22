# skill-ic-analysis

[简体中文](./README.md) | [English](./README.en.md)

Not a scoring system, but an **IC multi-dimensional diagnostic Skill**: dual IC comparison + IC decay curve + subsample slicing + Top basket Jaccard + cumulative timeline. Answers "on which stocks / over what horizon does this factor work".

`role: skill` `output: 5-section diagnostic report` `paradigm: pooled cross-section`

---

`skill-ic-analysis` is the **IC multi-dimensional diagnostic Skill** provided by PandaAI Quant Skills. A single IC_IR number tells you "is the factor effective", but not "where it's effective, how long it lasts, how stable it is". This Skill decomposes IC into 5 dimensions.

## 🎯 What This Skill Solves

Overall IC = 0.04 could be:

- Small-cap IC=0.08, large-cap IC=0 (capacity-limited)
- High-vol IC=0.07, low-vol IC=0.01 (eats risk premium)
- H=1 IC=0.01, H=20 IC=0.05 (low-frequency signal)
- 2020 IC=0.10, 2023 IC=-0.02 (regime shift)
- Jaccard < 0.5 (noise-dominated, annual turnover 100+)

A single overall IC number cannot reveal these. This Skill enforces all 5 analyses and synthesizes a verdict.

## ⚡ 5 Analyses

```
1. Dual IC comparison (rank vs Pearson) — basic health check
2. IC decay curve (H=1/3/5/10/20/40/60) — pick horizon
3. Subsample IC (size / vol / industry 3-way slice) — find where it works
4. Top basket Jaccard — signal inertia vs noise
5. Cumulative IC timeline — find crashes / plateaus / regime shifts
6. Synthesis — factor type / recommended H / live-trading risk / next action
```

## 🗃️ Input Requirements

- Signal: `[date × symbol]` float DataFrame
- Market panel: with `open` / `close` (for forward return), size proxy (rolling `close * volume` works)
- Industry field (optional): used for industry slicing if available

## 📦 Repository Layout

```
skill-ic-analysis/
├── SKILL.md
├── README.md / README.en.md
├── references/
│   ├── dual-ic.md                      # rank vs Pearson comparison
│   ├── ic-decay.md                     # Decay curve + shape classification
│   ├── subsample-ic.md                 # Size / vol / industry slicing
│   ├── top-basket-stability.md         # Jaccard algorithm + interpretation
│   ├── ic-timeline.md                  # Timeline + regime shift detection
│   └── report-format.md                # Diagnostic report template
└── agents/
    ├── openai.yaml
    ├── cursor-rule.mdc
    └── portable-loader.md
```

## 🚀 Quick Start

Drop `skill-ic-analysis/` into your Agent's skills directory. Auto-loaded on triggers ("IC decay / subsample IC / signal stability").

## 📄 Synthesis Report Sample

```
=== IC Analysis Report ===
Factor      : f_neg_max_ret_120
Period      : 2021-12-04 → 2024-12-03 (val)

[1] Dual IC
    rank IC mean    : +0.038       rank_ic_ir   : 2.14
    pearson IC mean : +0.029       pearson_ic_ir: 1.87
    Diagnosis       : Slight magnitude distortion, rank > pearson by 30%

[2] IC Decay
    H=1   ic=0.012  ir=1.05
    H=20  ic=0.038  ir=2.14   ← current horizon
    H=40  ic=0.029  ir=1.74
    Diagnosis : Mid-frequency signal (peak at H=20), recommend H ∈ [10, 20]

[3] Subsample IC (by size)
    Q1 (smallest) : ic=0.062     ← dominant
    Q5 (largest)  : ic=0.011
    Diagnosis : Small-cap dominated, capacity-limited in live

[4] Top 10% Jaccard
    mean=0.91  std=0.03
    Diagnosis : Slow signal, low turnover

[5] IC timeline: monotonic upward, no regime break

=== Verdict ===
- Factor type : Mid-frequency lottery, works mainly on small-cap high-vol
- Recommended H : 20
- Live risk : Capacity (small-cap liquidity), high-vol concentration (deeper MDD)
- Next action : Add low-vol factor for hedging (op_type=combine_method)
```

## 🧭 Relation to Other PandaAI Quant Skills

| Repository | Purpose |
|---|---|
| skill-factor-mine | Propose + modify code |
| skill-factor-evaluate | Composite score (includes simplified IC) |
| skill-backtest | NAV / quantiles / benchmark |
| **skill-ic-analysis** (this) | IC multi-dim (no NAV) |
| skill-factor-debug | When IC suspiciously high → suspect bug |
| skill-factor-review | Library-level review |

## 📜 Project Status & Boundaries

- **Status**: Community Project, not officially reviewed / certified / endorsed
- **Data Source**: This repository ships no market data. Users must supply their own market panel; data legality and licensing are the user's responsibility
- **Core Assumptions**: Cross-section research paradigm (pooled cross-section); forward return uses `open.shift(-1).pct_change(H).shift(-H)`
- **Known Limitations**: Subsample slicing must use past info (cannot use future market cap to slice past); for ultra-low-frequency factors (H > 60), IC decay magnitudes can be very noisy
- **Risk Boundary**: IC diagnostics reflect statistical performance under historical data + assumptions only, not future performance
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
