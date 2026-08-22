# Factor Ranking SAGE

**简体中文** | [English](README.en.md)

> **项目定位**
>
> `skill-factor-ranking-sage` 面向量化多因子研究，对本地因子和标签数据运行回归 mRMR 或固定模型 Marginal-SAGE，输出可复现、可检查、可归档的 Top-K 因子排名。

---

本项目提供两种相互独立的因子排名方法：

- **mRMR**：使用回归 F 统计量衡量因子与标签的相关性，使用绝对值 Pearson 相关系数衡量因子间冗余度，通过贪心比值规则选择 Top-K。
- **Marginal-SAGE**：训练一个固定的 LGBM 或 MLP 模型，在验证样本上通过经验边际填充和随机排列估计全局均方误差（MSE）贡献及标准误。

两种方法均通过统一的 JSON 配置和命令行入口运行，并输出可检查、可复现的排名结果与运行记录。

## 主要功能

主要功能包括：

- 在固定输入和配置下生成可复现的 mRMR Top-K 排名
- 对固定 LGBM / MLP 估计全局 Marginal-SAGE 因子贡献
- 输出输入哈希、时间窗口、配置副本、排名 CSV 和运行清单
- 输出 Top-K 候选因子集

## 工作流

~~~text
1. 准备本地因子 CSV 和标签 CSV
2. 配置固定训练/验证窗口与隔离期
3. 选择 `mode=mrmr` 或 `mode=sage`
4. 先运行对应的示例配置
5. 运行研究配置 JSON
6. 检查运行清单、排名、标准误和提示信息
7. 在 Skill 外部锁定测试集
8. 比较全量、Top-K 和多个随机 Top-K 基线
~~~

## 仓库内容

~~~text
skill-factor-ranking-sage/
├── SKILL.md
├── README.md / README.en.md
├── LICENSE
├── requirements.txt
├── agents/
│   ├── openai.yaml
│   ├── cursor-rule.mdc
│   └── portable-loader.md
├── examples/
│   ├── factor_selection_mrmr_smoke.json
│   ├── factor_selection_lgbm_smoke.json
│   ├── factor_selection_mlp_smoke.json
│   ├── toy_factors.csv
│   └── toy_labels.csv
├── references/
│   ├── source_boundary.md
│   ├── input_schema.md
│   ├── output_contract.md
│   ├── metric_definitions.md
│   ├── validation_notes.md
│   └── algorithm_sources.md
├── scripts/
│   ├── run_factor_selection.py
│   └── factor_selection_runtime/
└── tests/
~~~

## 数据要求

至少提供两个本地 CSV：

- `feature_path`：包含日期列、证券代码列和数值型因子列
- `label_path`：包含相同日期列、证券代码列和标签列

约束：

- 每行表示一个 `(date, ticker)` 样本
- 两个文件内部的 `(date, ticker)` 必须唯一
- 日期支持 YYYYMMDD 或可解析日期字符串
- 因子列必须为数值类型
- 运行程序按日期和证券代码执行内连接，并删除标签缺失行
- `available_date` 为可选字段；如未提供，运行结果会记录时点信息提示

完整字段见 [references/input_schema.md](references/input_schema.md)。

## 快速开始

安装依赖：

~~~bash
python -m pip install -r requirements.txt
~~~

运行三组示例配置：

~~~bash
python scripts/run_factor_selection.py --input examples/factor_selection_mrmr_smoke.json
python scripts/run_factor_selection.py --input examples/factor_selection_lgbm_smoke.json
python scripts/run_factor_selection.py --input examples/factor_selection_mlp_smoke.json
~~~

运行自定义配置：

~~~bash
python scripts/run_factor_selection.py --input <input-json>
~~~

## 核心输入变量

### 通用字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `run_name` | string | 运行标识前缀 |
| `output_root` | string | 输出根目录；每次生成 `runs/<run_id>` |
| `random_seed` | integer | SAGE 模型、背景、验证抽样和排列随机种子 |
| `mode` | string | `mrmr` 或 `sage` |
| `selection_count` | integer | 输出 Top-K 数量 |
| `input.feature_path` | string | 因子 CSV 路径 |
| `input.label_path` | string | 标签 CSV 路径 |
| `data.date_col` | string | 原始日期列名 |
| `data.ticker_col` | string | 原始证券代码列名 |
| `data.label_col` | string | 标签列名 |
| `data.feature_include` | list[string] | 可选因子白名单 |
| `data.feature_exclude` | list[string] | 可选因子排除列表 |

### 固定窗口

| 字段 | 说明 |
|---|---|
| `validation.train_start / train_end` | 训练闭区间 |
| `validation.valid_start / valid_end` | 验证闭区间 |
| `validation.embargo_days` | 两窗口间至少需要存在的交易日期数量 |

mRMR 只使用训练行；SAGE 在训练行拟合模型并在验证行估计贡献。

### mRMR 字段

| 字段 | 可选值 |
|---|---|
| `mrmr.relevance` | 固定为 `f` |
| `mrmr.redundancy` | 固定为 `c` |
| `mrmr.denominator` | `mean` 或 `max` |

### SAGE 字段

| 字段 | 说明 |
|---|---|
| `model.type` | `lgbm` 或 `mlp` |
| `model.params` | 直接传给对应模型适配器的参数 |
| `sage.loss` | 当前固定为 `mse` |
| `sage.background_size` | 经验边际填充背景行数 |
| `sage.evaluation_size` | 验证候选池最大行数 |
| `sage.batch_size` | 每轮采样数量 |
| `sage.n_permutations` | 样本/排列预算；`null` 表示使用收敛检测 |
| `sage.detect_convergence` | 是否允许满足阈值后提前停止 |
| `sage.convergence_threshold` | 最大标准误与贡献范围之比的停止阈值 |

## 输出产物

每次运行写入：

~~~text
output_root/runs/<run_id>/
├── selected_factors.json
├── selection_report.md
├── resolved_config.json
├── input_manifest.json
└── run_manifest.json
~~~

mRMR 额外输出 `mrmr_ranking.csv` 和 `mrmr_redundancy_matrix.csv`。SAGE 额外输出 `sage_values.csv` 和 `sage_metadata.json`。

完整字段见 [references/output_contract.md](references/output_contract.md)。

## 如何解释结果

- mRMR 的相关性指标使用单变量回归 F 统计量刻画因子与目标之间的关联强度。
- SAGE 贡献值刻画固定模型在不同因子联盟中的平均 MSE 贡献。
- SAGE 标准误和收敛状态用于辅助判断贡献估计及排序的稳定性。
- Top-K 数量由用户结合研究目标设定，也可以比较多个候选规模。
- 排名结果可在锁定样本外数据上与全量因子和多个随机 Top-K 基线比较。

## 验证范围

当前版本已通过以下自动化验证：

- 三组合成数据示例覆盖 mRMR、LGBM SAGE 和 MLP SAGE 运行流程
- 配置校验、方法计算、收敛诊断和输出格式均有自动化测试

## 项目状态与使用边界

- **项目状态**：QUANTSKILLS 社区项目，未经官方审核、认证或背书。
- **数据来源**：仓库包含人工构造的合成示例数据，不对应真实证券、行情或账户；用户负责自有因子、标签和行情数据的许可与合规。
- **时间边界**：用户需要根据实际数据确认因子可用时间、标签窗口和信息时点。
- **算法边界**：本项目复现回归 mRMR 和 Marginal-SAGE 的核心计算流程，专注于可检查的因子排名。
- **研究边界**：输出包括因子排名、贡献估计和 Top-K 候选因子集。
- **用途**：仅供量化研究、教育和方法论参考，不构成投资建议。

## 许可证

本项目采用 GNU General Public License v3.0，详见 [LICENSE](LICENSE)。
