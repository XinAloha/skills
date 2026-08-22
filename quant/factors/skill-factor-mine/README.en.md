# skill-factor-mine

[简体中文](./README.md) | [English](./README.en.md)

Not a factor library, but a **workflow SOP for factor mining**: turning "add a new factor" into a repeatable, attributable, revertible standard procedure.

`role: skill` `output: workflow` `paradigm: pooled cross-section`

---

`skill-factor-mine` is the **quantitative factor mining workflow Skill** provided by PandaAI Quant Skills. It defines a generic SOP — from reading the evaluation constitution, forming a single-point hypothesis, writing the experiment note (ITER_NOTE), modifying code, scoring, and accepting/reverting — turning factor mining from "inspiration-driven" into "protocol-driven".

QuantSkills community rules: see `Community Rules` at the organization root.

It is **not a factor library** and **not a backtest engine**, but a research protocol for **continuing to produce factor libraries**. If you want ready-made factors, look in PandaAI Quant Skills' sister repositories. If you want to mine your own with discipline, use this Skill.

## 🎯 What This Skill Solves

When you (or your AI Agent) iterate on `alpha.py` / `factors.py` / any factor file, the most common failure modes are:

- **Changing N things at once**: score went up, but you don't know which change worked, can't reuse next time
- **Hypothesis-free hacking**: 100 iterations of pure noise, no insight gained
- **Look-ahead bias sneaks in**: beautiful IC, but live trading crashes
- **New factor is just a re-skinned old factor**: ρ=0.9, adds nothing but collinearity

This Skill enforces:

- Single-point hypothesis principle (one op_type per iteration)
- ITER_NOTE four required fields (`op_type` / `hypothesis` / `change` / `expected`)
- Cross-section winsorize + z-score signal contract
- Factor correlation gate |ρ| ≥ 0.85
- 8-family decision tree (avoid same-family stacking)
- 12 anti-patterns checklist

Factor mining becomes an auditable loop: propose → experiment → accept/revert → archive.

## ⚡ Workflow

```
1. Read constitution (evaluation.md / program.md / project scoring function)
2. Read current alpha source
3. Form single-point hypothesis → write ITER_NOTE
4. Modify code (one op_type only)
5. Run scoring (py runner.py once or equivalent)
6. ACCEPTED → archive factor card
   REJECTED / CRASH → auto-revert to last best snapshot
```

## 🗃️ Input Requirements

This Skill doesn't require a specific data format, but your project should have:

- Market panel (OHLCV, at least `date / symbol / open / close / volume`)
- Scoring function (project's `primary_score()` or equivalent)
- Experiment logging (`runs.jsonl` / changelog / git log)
- Single-file factor interface (`alpha.run(train, val) → (signal_train, signal_val)` or similar)

If your project doesn't have this infrastructure yet, see `references/example-auto-alpha.md` for the full setup of `auto_research_alpha`.

## 📦 Repository Layout

```
skill-factor-mine/
├── SKILL.md                            # Claude Code skill entry
├── README.md / README.en.md            # User-facing intro (this file)
├── references/                         # Deep references (Agent loads on demand)
│   ├── op-types.md                     # 8 legal single-point change types
│   ├── iter-note.md                    # Experiment note template (mandatory)
│   ├── signal-contract.md              # Signal winsorize + z-score contract
│   ├── correlation-gate.md             # Correlation gate rules
│   ├── factor-families.md              # 8 factor families + decision tree
│   ├── anti-patterns.md                # 12 anti-patterns
│   └── example-auto-alpha.md           # Reference project example
└── agents/                             # Cross-tool adapters
    ├── openai.yaml                     # OpenAI Codex / Assistants
    ├── cursor-rule.mdc                 # Cursor project rule
    └── portable-loader.md              # Plain ChatGPT / Claude Web
```

## 🚀 Quick Start

### Claude Code (native)

Drop the whole `skill-factor-mine/` folder into `.claude/skills/` or `~/.claude/skills/`. When you say "add a new factor / mine an alpha / iterate alpha.py", Claude Code auto-loads.

### Cursor

Copy `agents/cursor-rule.mdc` into the project's `.cursor/rules/`. Activates automatically when editing `alpha.py` or `factors/*.py`.

### OpenAI Codex / Assistants

Pour the `instructions` field of `agents/openai.yaml` into your system prompt or Assistant configuration.

### Plain ChatGPT / Claude Web

Open `agents/portable-loader.md` and copy the "Activation Prompt" block to the start of your conversation.

## 🧪 ITER_NOTE Template

Required for every factor code change:

```python
ITER_NOTE: dict = {
    "op_type":    "add_factor",       # See references/op-types.md
    "hypothesis": "Add amihud illiquidity factor; expected to have low correlation with existing low-vol family and contribute new information.",
    "change":     "Append f_amihud_20 to FACTORS; nothing else changes.",
    "expected":   "score +0.35 → +0.40; turnover slightly up.",
    "parent_iter": 7,
    "reasoning":   "F0004 has monotonicity 0.93 but turnover=33 too high.",
    "new_factor":  "f_amihud_20",
}
```

## 🧭 Relation to Other PandaAI Quant Skills

| Repository | Purpose |
|---|---|
| **skill-factor-mine** (this) | Proposal + experiment SOP |
| skill-factor-evaluate | Composite score for a single factor (dual IC / Sharpe / MDD / monotonicity / turnover) |
| skill-backtest | Cross-section long-only backtest + 4-panel diagnostic chart |
| skill-ic-analysis | IC multi-dimensional diagnostic (decay / subsample / Jaccard / timeline) |
| skill-factor-debug | Factor crash / numerical anomaly / look-ahead self-check |
| skill-factor-review | Factor library 3-layer review |

Typical flow: mine → evaluate (auto-called) → debug (when it breaks) → ic-analysis (post-acceptance deep-dive).

## 📜 Project Status & Boundaries

- **Status**: Community Project, not officially reviewed / certified / endorsed
- **Data Source**: This repository ships no market data. Users must supply their own market panel; data legality and licensing are the user's responsibility
- **Core Assumptions**: Cross-section research paradigm (pooled cross-section); HORIZON ∈ (1, 3, 5, 10, 20); T+1 open execution
- **Known Limitations**: No market impact / call auction slippage / shorting constraints simulated; no dividend / split / corporate action handling
- **Risk Boundary**: Factor scores reflect statistical performance under historical data + assumptions only, not future performance
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
