# skill-model-hpo-evidence-driven

**简体中文** | [English](README.en.md)

> **项目定位 / Project Positioning**
>
> 本项目是面向 Codex / QUANTSKILLS 的模型超参数搜索 Skill，用于在给定本地因子和标签后，对 LGBM / MLP 多因子模型进行 evidence-driven LLM decision 搜索空间调整或确定性 grid 搜索。
>
> 本仓库不是因子库，不负责生成 Alpha 因子，也不是生产级组合回测引擎；它提供的是可运行、可检查、可归档的模型超参数研究工作流。

本项目作为 QUANTSKILLS 社区贡献提交，不代表官方认证、投资建议或生产交易验证。

维护者：QUANTSKILLS 社区贡献者。

不是因子库，也不是回测引擎，而是一个**面向量化多因子模型的 HPO Skill**：把“寻找一组可复现实验参数”拆成数据读取、训练验证、trial evidence 记录、搜索空间决策、最终参数输出等标准步骤。

`role: skill` `platform: codex` `category: tooling` `status: active` `validation: runnable` `output: best-hyperparameters` `paradigm: evidence-driven hpo / grid search`

---

`skill-model-hpo-evidence-driven` 是一个自包含的 QUANTSKILLS 社区贡献 Skill。它支持两类搜索方式：

- **evidence-driven search**：每轮记录 trial 参数、验证指标、风险信号和边界信息，可由 LLM decision 文件或规则控制器决定下一轮搜索空间应 `keep / expand / shift / narrow / stop`。
- **grid search**：把 `search.space` 离散为预算化 Cartesian grid，或直接使用显式 `grid_trials`，用于确定性超参数搜索。

本仓库提供的是一套研究工作流：从本地因子和标签出发，训练 LGBM / MLP 候选模型，使用验证集指标选择最佳参数，并输出可审计 JSON / CSV / Markdown 产物。Holdout 指标只用于最终报告，不反馈给搜索过程。

## 这个 Skill 解决什么问题

模型超参数研究常见的失败模式包括：

- **只给单组参数**：缺少 trial 记录，难以判断参数是否稳定
- **搜索空间靠人工拍脑袋**：不知道应该扩大、平移还是收缩
- **LLM 直接生成参数**：结果不可控，容易越界或缺少验证依据
- **网格搜索不可复盘**：没有保存实际展开后的参数列表和候选数量
- **验证与测试边界混乱**：容易把 holdout 结果反馈进搜索过程
- **结果不可追溯**：不知道最佳参数来自哪次 trial、哪种 sampler、哪些指标

本 Skill 会提供：

- LGBM / MLP 多因子模型超参数搜索
- evidence-driven LLM decision 搜索空间自适应调整
- budgeted Cartesian grid search 与显式 `grid_trials`
- trial evidence、decision memory、leaderboard 和 search report
- LLM decision 文件 handoff，使外部决策过程可审计、可校验、可复盘
- 可选 offline final selection，用已有 run 的 trial 记录重新做最终参数选择
- 显式注册的 factor provider、feature pipeline 和 model plugin，方便接入用户自己的因子存储与模型
- 默认 `legacy_v1` 复现旧版 `rankic_ir`、逐 trial seed 和自动测试集评估
- 可显式切换 `research_v2`，启用严格 point-in-time、共同 seed、多 seed 确认和封存 holdout

## 工作流

```text
1. 准备本地 factor CSV/parquet 和 label CSV/parquet
2. 准备 input JSON，指定 model_type、search.method、validation、evaluation 和 search.space
3. 运行 smoke test，确认路径、数据 schema、训练和输出契约可用
4. 每个 trial 训练 LGBM 或 MLP，并计算验证集指标
5. evidence-driven 模式下，runtime 汇总 trial evidence，由 LLM decision 文件或规则控制器决定下一轮搜索空间
6. grid 模式下，runtime 固定展开参数组合并按预算顺序评估
7. 输出 leaderboard、confirmation artifacts、best_params 和 search_report
8. `legacy_v1` 自动输出测试结果；`research_v2` 冻结参数后再用独立命令启封 holdout
9. 后续做交易成本、风险暴露和组合级验证
```

默认 LGBM smoke test：

```bash
python scripts/run_hpo_search.py --input examples/hpo_lgbm_smoke.json
```

默认输出目录来自 input JSON 中的 `output_root`，例如：

```text
outputs/lgbm_smoke/<run_id>/
```

## 输入要求

至少需要两个本地表格文件：

- `feature_path`：因子文件，必须包含 `date`、ticker 列和数值型因子列
- `label_path`：标签文件，必须包含同样的 `date`、ticker 列和标签列，默认 `y`
- 每行表示一个 `(date, ticker)` 样本
- 同一文件内 `(date, ticker)` 不允许重复
- 数据必须是用户有权使用的数据
- `available_date`、`label_start_date`、`label_end_date` 可选；缺失时 runtime 会给出 point-in-time / label-window 风险提示

示例输入文件：

```text
examples/hpo_lgbm_smoke.json
examples/hpo_mlp_smoke.json
examples/hpo_lgbm_grid_search.json
examples/hpo_mlp_grid_search.json
examples/hpo_lgbm_codex_external.json
examples/hpo_custom_extension_smoke.json
```

关键字段见：

```text
references/input_schema.md
```

本 Skill 的 LLM decision 通过 `decision_provider.type=codex_external` 承载：runtime 写出 evidence 和 decision template 文件，由外部 LLM/Agent 补充 decision JSON，再由 runtime 做 schema 和边界校验。

## 仓库内容

```text
skill-model-hpo-evidence-driven/
├── SKILL.md                            # Agent skill 入口
├── README.md / README.en.md            # 用户向介绍
├── requirements.txt                    # Python 运行依赖
├── examples/
│   ├── hpo_lgbm_smoke.json             # LGBM evidence-driven smoke 示例
│   ├── hpo_mlp_smoke.json              # MLP evidence-driven smoke 示例
│   ├── hpo_lgbm_grid_search.json       # LGBM generated grid 示例
│   ├── hpo_mlp_grid_search.json        # MLP generated grid 示例
│   ├── hpo_lgbm_grid_smoke.json        # 显式 grid_trials 示例
│   ├── hpo_lgbm_codex_external.json    # LLM decision 示例
│   ├── hpo_custom_extension_smoke.json # 自定义 provider/pipeline/model 示例
│   ├── toy_factors.csv                 # toy 因子数据
│   └── toy_labels.csv                  # toy 标签数据
├── references/
│   ├── source_boundary.md              # 数据、LLM 决策与研究边界
│   ├── input_schema.md                 # 输入字段说明
│   ├── output_contract.md              # 输出产物契约
│   ├── extension_api.md                # 用户扩展接口与变量说明
│   ├── codex_external_workflow.md      # LLM decision handoff 说明
│   └── validation_notes.md             # 假设、限制与风险边界
├── scripts/
│   ├── run_hpo_search.py               # CLI 入口
│   ├── run_offline_final_selection.py  # 离线最终参数选择入口
│   ├── run_holdout_evaluation.py        # 显式、可审计的 holdout 入口
│   └── hpo_runtime/                    # 自包含 HPO runtime
├── extension_templates/
│   └── example_extensions.py           # 独立的用户扩展示例区
└── agents/
    ├── openai.yaml                     # Codex/agent metadata
    ├── cursor-rule.mdc                 # Cursor rule metadata
    └── portable-loader.md              # 非原生 Skill 平台加载提示
```

## 快速开始

安装依赖：

```bash
python -m pip install -r requirements.txt
```

`requirements.txt` 覆盖 LGBM 与 MLP 示例依赖；如只手动安装 LGBM 最小依赖，可不安装 `torch`。

先跑 LGBM smoke test：

```bash
python scripts/run_hpo_search.py   --input examples/hpo_lgbm_smoke.json
```

运行 MLP smoke test：

```bash
python scripts/run_hpo_search.py   --input examples/hpo_mlp_smoke.json
```

运行 generated grid search：

```bash
python scripts/run_hpo_search.py   --input examples/hpo_lgbm_grid_search.json

python scripts/run_hpo_search.py   --input examples/hpo_mlp_grid_search.json
```

运行 LLM decision 示例：

```bash
python scripts/run_hpo_search.py   --input examples/hpo_lgbm_codex_external.json
```

运行自定义扩展示例：

```bash
python scripts/run_hpo_search.py --input examples/hpo_custom_extension_smoke.json
```

冻结搜索结果后显式运行 holdout：

```bash
python scripts/run_holdout_evaluation.py \
  --source-run-dir <run-dir> \
  --confirm-holdout-access
```

## 自定义因子和模型

用户可改部分已隔离在 `extension_templates/`。这里提供 factor provider、feature pipeline 和 model plugin 的完整示例；生产代码建议放在 Skill 目录之外的用户项目中，再通过 `extensions.plugin_roots` 和 `extensions.modules` 显式加载。

旧配置仍默认使用 `file_panel`、`cross_sectional` 以及内置 `lgbm`/`mlp`。自定义扩展必须遵守新的目标隔离接口；完整变量定义见 `references/extension_api.md`。

运行时会输出类似：

```text
run_id: skill_lgbm_smoke_YYYYMMDDHHMMSS
run_dir: outputs/lgbm_smoke/skill_lgbm_smoke_YYYYMMDDHHMMSS
model_type: lgbm
status: evaluated
num_trials_run: 4
num_successful_trials: 4
best_trial_id: lgbm_trial_0000
best_score: ...
```

## 输入变量说明

`examples/*.json` 是 CLI 的主配置文件。相对路径会按 input JSON 所在目录解析，生成的 native YAML 会写入输出目录下的 `_generated_configs/`。

### 基础字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `output_root` | string | 输出根目录；每次运行会生成时间戳 run 目录 |
| `config.input.feature_path` | string | 因子文件路径，CSV/parquet |
| `config.input.label_path` | string | 标签文件路径，CSV/parquet |
| `config.data.date_col` | string | 原始日期列名 |
| `config.data.ticker_col` | string | 原始股票/资产列名 |
| `config.data.label_col` | string | 标签列名，合并后标准化为 `y` |
| `config.data.start_date` / `end_date` | integer/string | 可选数据截断区间 |

### 搜索配置

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `config.search.model_type` | string | `lgbm` 或 `mlp` |
| `config.search.method` | string | `evidence_driven` 或 `grid`；兼容旧别名 `adaptive_tpe`、`fixed_grid` |
| `config.search.max_trials` | integer | 总 trial 预算 |
| `config.search.max_rounds` | integer | 最大搜索轮数 |
| `config.search.trials_per_round` | integer | 每轮 trial 数 |
| `config.search.space` | object | 搜索空间定义 |
| `config.search.grid` | object | generated grid 配置，`method=grid` 时使用 |
| `config.search.grid_trials` | list[object] | 显式参数列表，优先级高于 generated grid |

默认 `compatibility.profile=legacy_v1`，用于复现旧版 `rankic_ir` 实验。需要严格 PIT、`robust_rankic`、共同 seed、多 seed 确认和封存 holdout 时，显式设置 `compatibility.profile=research_v2`。

### LLM decision

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `config.llm.enabled` | boolean | LLM decision 文件化 handoff 通常保持 `false`；决策由 `decision_provider.type=codex_external` 接管 |
| `config.decision_provider.type` | string | `rule` 或 `codex_external`；`codex_external` 表示文件化 LLM decision handoff |
| `config.decision_provider.on_missing` | string | `fallback` 或 `stop` |
| `config.space_controller.enabled` | boolean | evidence-driven 模式下是否允许搜索空间调整 |
| `config.final_selector.enabled` | boolean | 是否启用最终参数选择层 |

## 输出产物

稳定输出包括：

```text
search_manifest.json
resolved_config.yaml
trials.jsonl
trial_leaderboard.csv
trial_window_metrics.csv
search_space_versions.json
round_history.json
trial_evidence_history.json
space_controller_decisions.json
decision_memory.json
failure_modes.json
score_best_params.json
best_params.json
final_selection.json
confirmation_seed_metrics.csv
confirmation_leaderboard.csv
confirmation_summary.json
run_summary.json
search_report.md
```

条件输出包括：

```text
grid_manifest.json                 # search.method=grid
grid_trials_resolved.json          # search.method=grid
codex_decisions/                   # decision_provider.type=codex_external
final_neighbor_trials.csv          # 运行进入最终选择阶段
final_neighbor_window_metrics.csv  # 运行进入最终选择阶段
final_selection_evidence.json      # final_selector.enabled=true
```

`legacy_v1` 主搜索会生成 `final_holdout_*` 文件；`research_v2` 使用独立 holdout 目录：

```text
holdout_access_manifest.json
final_holdout_metrics.json
final_holdout_predictions.csv
final_holdout_window_metrics.csv
```

Grid search 额外输出的 `grid_manifest.json` 记录网格来源、候选数量、选择策略和参数顺序；`grid_trials_resolved.json` 记录实际执行的有序参数列表。

LLM decision 模式额外输出：

```text
codex_decisions/*_evidence.json
codex_decisions/*_decision.template.json
codex_decisions/*_decision.json       # 外部 LLM/Agent 写入后存在
external_decision_required.json          # on_missing=stop 时存在
```

完整字段见：

```text
references/output_contract.md
```

## 边界说明

本 Skill 用于量化研究自动化。它只优化模型超参数，不生成因子，不承诺收益，不替代组合级回测。为严格隔离测试集应使用 `research_v2`；任何最终参数仍应在交易成本、风险暴露和组合约束下重新验证。

## License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE).
