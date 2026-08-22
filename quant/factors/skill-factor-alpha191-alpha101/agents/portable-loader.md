# Portable Loader Prompt

在不原生识别 `SKILL.md` 文件夹的 Agent 平台中，使用下面的提示词加载本 Skill。

```text
你可以访问一个名为 factor-alpha191-alpha101 的本地 Skill，路径是：

<FACTOR_ALPHA191_ALPHA101_SKILL_ROOT>

当用户请求匹配该 Skill 的 SKILL.md 描述时：

1. 先读取 <FACTOR_ALPHA191_ALPHA101_SKILL_ROOT>/SKILL.md。
2. 严格按照 SKILL.md 中的工作流和边界说明执行。
3. 仅在需要时读取 <FACTOR_ALPHA191_ALPHA101_SKILL_ROOT>/references/ 下的引用文件。
4. 在读取相关说明后，从 Skill 根目录运行内置脚本。
5. 保持文档中定义的 API 名称、参数名、文件路径、公式名称、输出约定、验证边界和数据来源边界。
6. 不要编造 Skill 文件中未支持的数据接口、凭证、因子定义、公式行为或运行时行为。
7. 将输出视为公式因子值，不要解释为投资建议、交易信号、收益承诺或生产交易验证。
```

## 用途

本仓库提供一个可移植的 Skill 入口，用于根据参考自 JoinQuant 的 Alpha101 / Alpha191 公式，从长表 OHLCV CSV 行情数据中计算每日因子值并导出宽表 CSV。

## 运行入口

在仓库根目录运行：

```bash
python scripts/compute_alpha_factors.py --input <input-json> [--output <output-dir>]
```

最小示例：

```bash
python scripts/compute_alpha_factors.py --input examples/compute_input.json
```

## 运行流程

1. 按照 `references/input_schema.md` 准备输入 JSON。
2. 通过 `market_data_csv_path` 提供长表 OHLCV CSV。
3. 通过 `alpha_sets` 选择 `alpha101`、`alpha191` 或两者。
4. 如需指定因子，设置 `alpha_names`。
5. 执行入口命令。
6. 按照 `references/output_contract.md` 读取输出产物。

## 输出产物

根据配置，运行结果可能包含：

```text
alpha101_values.csv
alpha191_values.csv
alpha_compute_summary.json
skipped_factors.json
run_config.json
```

输出目录按以下优先级确定：

1. CLI 参数 `--output`
2. 输入 JSON 中的 `output_dir`
3. 默认输出目录

## 参考文件

- `SKILL.md`：Agent 使用说明。
- `README.md`：中文说明文档。
- `README.en.md`：英文说明文档。
- `references/input_schema.md`：输入参数说明。
- `references/output_contract.md`：输出文件和字段约定。
- `references/source_boundary.md`：数据来源和使用边界。
- `references/validation_notes.md`：验证范围、假设和限制。

## 边界说明

本 Skill 仅计算公式因子值，不提供因子有效性评价、投资建议、调仓建议、收益承诺或生产交易验证。用户需要自行确认数据授权、字段定义、复权口径、股票池和后续验证流程。
