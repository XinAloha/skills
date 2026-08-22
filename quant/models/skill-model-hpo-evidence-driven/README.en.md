# Model HPO Evidence Driven Skill

**English** | [简体中文](README.md)

> Hyperparameter optimization skill for quant factor models. It supports evidence-driven LLM decision search-space adaptation and deterministic grid search for built-in LGBM/MLP and explicitly registered local model extensions.

This repository is maintained as a QUANTSKILLS community contribution. It is not an official, certified, endorsed, or production-validated QUANTSKILLS project.

Maintainer: QUANTSKILLS community contributors.

## What It Does

This repository packages a model hyperparameter optimization workflow as a reusable agent skill. It does not compute alpha factors and does not run a production portfolio backtest. It assumes local factor and label files are already prepared.

The runtime records validation metrics, parameters, sampler provenance, and risk signals for each trial. With `search.method=evidence_driven` and `decision_provider.type=codex_external`, the runtime writes structured evidence and decision templates under `codex_decisions/`; an external LLM decision step can then write guarded decision JSON files. With `search.method=grid`, the runtime evaluates explicit `grid_trials` or a budgeted Cartesian grid generated from `search.space`.

The default `compatibility.profile=legacy_v1` reproduces the historical RankIC-IR workflow, including trial-index seeds and automatic fixed-test evaluation. Explicitly select `research_v2` for block-robust RankIC, common-seed trials, multi-seed confirmation, strict point-in-time checks, and a separately audited holdout.

## Quick Start

```bash
pip install -r requirements.txt
python scripts/run_hpo_search.py --input examples/hpo_lgbm_smoke.json
```

MLP smoke test:

```bash
python scripts/run_hpo_search.py --input examples/hpo_mlp_smoke.json
```

Grid search:

```bash
python scripts/run_hpo_search.py --input examples/hpo_lgbm_grid_search.json
python scripts/run_hpo_search.py --input examples/hpo_mlp_grid_search.json
```

LLM decision mode:

```bash
python scripts/run_hpo_search.py --input examples/hpo_lgbm_codex_external.json
```

Custom factor-provider, feature-pipeline, and model-plugin smoke test:

```bash
python scripts/run_hpo_search.py --input examples/hpo_custom_extension_smoke.json
```

User-editable examples are isolated under `extension_templates/`. Production extensions should live in a user-owned directory outside the skill and be loaded explicitly with `extensions.allow_external`, `plugin_roots`, and `modules`. Existing configs keep the original built-in behavior. See `references/extension_api.md` for contracts and variable definitions.

Explicit holdout evaluation after freezing a run:

```bash
python scripts/run_holdout_evaluation.py \
  --source-run-dir <run-dir> \
  --confirm-holdout-access
```

## Key Outputs

Each search run writes trial records, selected parameters, and a markdown report. `legacy_v1` writes automatic holdout results and returns `evaluated`; `research_v2` writes confirmation artifacts, returns `selected_not_tested`, and uses the explicit holdout command.

See `references/input_schema.md`, `references/codex_external_workflow.md`, and `references/output_contract.md` for the full contract.

## Boundary

This is a research tool for model hyperparameter search. It does not provide investment advice and does not guarantee trading performance.

## License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE).
