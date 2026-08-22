---
name: model-hpo-evidence-driven
description: "Run evidence-driven or deterministic grid hyperparameter search for quantitative multi-factor models. Use when an agent needs legacy-compatible RankIC-IR LGBM/MLP results, or explicitly opts into robust block RankIC, common-seed confirmation, strict point-in-time checks, and sealed holdout evaluation."
quantSkills:
  organization: https://github.com/quantskills
  repository: quantskills/skill-model-hpo-evidence-driven
  repository_url: https://github.com/quantskills/skill-model-hpo-evidence-driven
  project_type: skill
  collection: model-hpo
  license: GPL-3.0-only
  category: tooling
  tags: [model-hpo, hyperparameter-search, evidence-driven, grid-search]
  platforms: [codex]
  language: zh-en
  status: active
  validation_level: runnable
  maintainer_type: community
  requires: []
  summary_zh: 使用 trial evidence 驱动的 LLM 搜索空间调整或确定性 grid 搜索优化 LGBM/MLP 多因子模型超参数。
  summary_en: Optimize LGBM/MLP quant factor model hyperparameters with trial-evidence-driven LLM search-space adaptation or deterministic grid search.
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "说明本地因子/标签文件、特征列、标签列、切分方式和优化目标，或上传输入配置",
    "required": true
  },
  "fields": [
    {
      "key": "model_type",
      "label": "模型类型",
      "type": "select",
      "default": "lgbm",
      "options": [
        { "value": "lgbm", "label": "LightGBM" },
        { "value": "mlp", "label": "MLP" }
      ]
    },
    {
      "key": "search_method",
      "label": "搜索方法",
      "type": "select",
      "default": "evidence_driven",
      "options": [
        { "value": "evidence_driven", "label": "证据驱动自适应" },
        { "value": "grid", "label": "确定性网格搜索" }
      ]
    },
    {
      "key": "trial_budget",
      "label": "试验预算",
      "type": "number",
      "placeholder": "例如 50"
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}基于本地因子和标签数据，为 {{model_type}} 执行 {{search_method}} 超参数搜索。{{#trial_budget}}试验预算为 {{trial_budget}}。{{/trial_budget}}先做小规模冒烟测试，再生成可复现的试验清单、排行榜、最佳参数和证据链；不生成新因子，也不把本任务扩展成完整交易回测，输出中文报告。"
}
```

# Model HPO Evidence Driven

Use this skill to select quantitative model hyperparameters. LGBM and MLP remain built in; factor loading, target-isolated feature preprocessing, and model construction may be supplied through explicitly enabled local extensions.

The default `compatibility.profile=legacy_v1` preserves the historical test behavior and scores. It uses `rankic_ir`, trial-index-derived model seeds, no date sample weights, no multi-seed confirmation, non-strict point-in-time checks, and automatic fixed-test evaluation. Use `research_v2` explicitly for robust block RankIC, common-seed trials, equal-date weights, multi-seed confirmation, strict point-in-time checks, and a sealed holdout.

## Core Workflow

1. Read `references/input_schema.md` before preparing the input JSON.
2. Choose `compatibility.profile`: keep `legacy_v1` to reproduce earlier runs, or explicitly use `research_v2` for the stricter workflow.
3. Prepare factor and label data with one row per `(date, ticker)`; `research_v2` additionally requires point-in-time metadata and a universe.
4. Choose built-in `search.model_type`: `lgbm` or `mlp`. For custom components, read `references/extension_api.md` and start from `extension_templates/example_extensions.py`.
5. Choose `search.method`: `evidence_driven` or `grid`.
6. Run a local smoke test first:

```bash
python scripts/run_hpo_search.py --input examples/hpo_lgbm_smoke.json
```

7. For grid search, run `examples/hpo_lgbm_grid_search.json` or `examples/hpo_mlp_grid_search.json`.
8. Under `legacy_v1`, expect `status=evaluated` and inspect `final_holdout_metrics.json`. Under `research_v2`, expect `status=selected_not_tested`, inspect confirmation artifacts, then explicitly unlock holdout once:

```bash
python scripts/run_holdout_evaluation.py \
  --source-run-dir <run-dir> \
  --confirm-holdout-access
```

9. Read `references/output_contract.md` before consuming generated artifacts.

Do not auto-discover, download, or install extension code. Load only modules explicitly listed under `extensions.modules`, with `extensions.allow_external=true` and a local `plugin_roots` entry.

## Output Contract

Produce a timestamped run directory under `output_root`, including:

- `search_manifest.json`
- `resolved_config.yaml`
- `trials.jsonl`
- `trial_leaderboard.csv`
- `best_params.json`
- confirmation artifacts when multi-seed confirmation is enabled
- `final_holdout_metrics.json` and holdout predictions under `legacy_v1` automatic holdout
- `search_report.md`
- `grid_manifest.json` and `grid_trials_resolved.json` when `search.method=grid`
- `codex_decisions/` evidence and decision templates when `decision_provider.type=codex_external`

Under `research_v2`, the independent holdout command writes metrics under a separate audited directory.

## References

- Use `references/source_boundary.md` for data, LLM decision, and research boundaries.
- Use `references/input_schema.md` for input fields, search methods, and decision-provider settings.
- Use `references/output_contract.md` for artifact names and result fields.
- Use `references/codex_external_workflow.md` for the LLM decision handoff workflow.
- Use `references/validation_notes.md` for assumptions, checks, limitations, and risk boundaries.
- Use `references/extension_api.md` for custom factor providers, feature pipelines, model plugins, and registration.
