# Portable Loader Prompt

在 Hermes、OpenClaw 或其他不原生识别 `SKILL.md` 文件夹的 Agent 平台中，使用下面的提示词加载本 Skill。

```text
你可以访问一个名为 factor-pool-evolution 的本地 Skill，路径是：

<FACTOR_POOL_EVOLUTION_SKILL_ROOT>

当用户请求对已有股票因子池做 mutation、crossover、RankIC/RankICIR 评估或下一轮因子推荐时：

1. 先读取 <FACTOR_POOL_EVOLUTION_SKILL_ROOT>/SKILL.md。
2. 严格按照 SKILL.md 中的工作流和边界执行。
3. 仅在任务需要时读取 references/input_schema.md、references/evolution_rules.md 和 references/output_contract.md。
4. 从 Skill 根目录运行 scripts/run_factor_pool_evolution.py。
5. prepare 阶段完成后，读取 generation/prompts/，由当前模型填写 generation/generated_candidates.json。
6. 再次运行主脚本完成 evaluate 阶段。
7. 保持文档中定义的输入字段、候选 schema、评价口径和输出约定。
8. 不要编造数据源、凭证、因子定义或运行结果。
9. 将输出视为研究候选，不要表述为投资建议、收益承诺、官方验证或生产交易结论。
```

## 运行入口

```bash
python scripts/run_factor_pool_evolution.py --input <evolution-input-json>
```

## 参考文件

- `SKILL.md`：Agent 工作流与边界。
- `README.md`：中文项目说明。
- `README.en.md`：英文项目说明。
- `references/input_schema.md`：输入配置。
- `references/evolution_rules.md`：候选生成规则。
- `references/output_contract.md`：输出产物。

## 边界

本 Skill 仅用于研究与教育场景。用户需自行确认数据授权、字段定义、股票池、目标收益构造、参数和后续验证流程。
