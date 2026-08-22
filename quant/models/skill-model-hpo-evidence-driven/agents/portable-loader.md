# Portable Loader Prompt

在不原生识别 `SKILL.md` 文件夹的 Agent 平台中，使用下面的提示词加载本 Skill。

```text
你可以访问一个名为 model-hpo-evidence-driven 的本地 Skill，路径是：

<MODEL_HPO_EVIDENCE_DRIVEN_SKILL_ROOT>

当用户请求匹配该 Skill 的 SKILL.md 描述时：

1. 先读取 <MODEL_HPO_EVIDENCE_DRIVEN_SKILL_ROOT>/SKILL.md。
2. 严格按照 SKILL.md 中的工作流和边界说明执行。
3. 仅在需要时读取 <MODEL_HPO_EVIDENCE_DRIVEN_SKILL_ROOT>/references/ 下的引用文件。
4. 在读取相关说明后，从 Skill 根目录运行内置脚本。
5. 保持文档中定义的 API 名称、参数名、环境变量、文件路径、输出约定、验证边界和数据来源边界。
6. 不要编造 Skill 文件中未支持的数据接口、本地凭据、评价指标、模型结构、输出字段或运行时行为。
7. 将输出视为量化研究候选参数，不要解释为投资建议、交易信号、收益承诺或生产交易验证。
```

## 用途

本仓库提供一个可移植的 Skill 入口，用于对本地或用户适配的因子和标签数据运行内置 LGBM/MLP 或显式注册模型的超参数搜索，支持 evidence-driven LLM 搜索空间调整和确定性 grid search。

## 运行入口

在仓库根目录运行：

```bash
python scripts/run_hpo_search.py --input <input-json> [--output-root <output-root>]
```

最小示例：

```bash
python scripts/run_hpo_search.py --input examples/hpo_lgbm_smoke.json
```

离线最终参数选择：

```bash
python scripts/run_offline_final_selection.py --source-run-dir <run-dir> --output-root <output-root>
```

## 真实运行流程

1. 按照 `references/input_schema.md` 准备输入 JSON。
2. 通过 `feature_path` 和 `label_path` 提供本地因子与标签文件。
3. 设置 `search.model_type` 为 `lgbm`、`mlp` 或已注册模型名；自定义扩展先读取 `references/extension_api.md`。
4. 设置 `search.method` 为 `evidence_driven` 或 `grid`。
5. 如需 LLM decision 参与搜索空间调整，使用 `decision_provider.type=codex_external`，由外部 LLM/Agent 写入 decision JSON。
6. 执行入口命令。
7. 默认 `legacy_v1` 检查逐 trial seed、`rankic_ir` 和 `status=evaluated`；显式 `research_v2` 检查共同 seed、多 seed confirmation 和 `status=selected_not_tested`。
8. `research_v2` 参数冻结后，使用独立 holdout 命令并显式确认测试集访问。

## LLM decision handoff

LLM decision 模式通过 `codex_decisions/` 下的 evidence/template/decision 文件完成外部决策 handoff。

## 输出产物

稳定输出包括：

```text
search_manifest.json
resolved_config.yaml
trials.jsonl
trial_leaderboard.csv
best_params.json
confirmation_seed_metrics.csv
confirmation_leaderboard.csv
search_report.md
```

Holdout 独立入口：

```bash
python scripts/run_holdout_evaluation.py --source-run-dir <run-dir> --confirm-holdout-access
```

Grid search 额外输出：

```text
grid_manifest.json
grid_trials_resolved.json
```

## 参考文件

- `SKILL.md`：Agent 使用说明。
- `README.md`：中文说明文档。
- `README.en.md`：英文说明文档。
- `references/input_schema.md`：输入参数说明。
- `references/output_contract.md`：输出文件和字段约定。
- `references/extension_api.md`：用户 factor provider、feature pipeline 和 model plugin 接口。
- `references/codex_external_workflow.md`：LLM decision handoff 说明。
- `references/validation_notes.md`：验证边界和限制说明。

## 边界说明

本 Skill 仅用于量化研究自动化。生成的超参数、验证指标和 holdout 报告不是投资建议、收益承诺或生产交易验证。
