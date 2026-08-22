# Validation Notes

## 2026-07-14 Integration Check

本次检查验证 `factor-idea-generation` 与 `factor-pool-evolution` 的文件和代码接口是否可运行。

验证输入：

- `examples/idea_candidates.example.json`
- `examples/custom_seed_factors.example.json`
- 由 `factor-pool-evolution/scripts/init_factor_pool.py` 生成的合成 demo 行情
- 840 行日频面板数据

验证结果：

- 两份示例 JSON 均通过 JSON 解析
- 3 个 shortlist 因子均被下游自定义 seed 执行器成功加载
- 3 个因子均返回与行情输入等长、可转为数值的 Series
- 下游 prepare 阶段完成，`seed_factor_count = 3`
- strong pool 选择完成，`strong_pool_count = 2`
- crossover pairing 完成，`crossover_pair_count = 2`

## 验证边界

本次使用的是随机合成 demo 行情，只验证：

- schema 兼容性
- Python 因子代码可执行性
- 下游 prepare 流程兼容性

本次结果不能用于判断：

- 因子在真实市场是否有效
- RankIC / RankICIR 是否具备统计显著性
- 是否存在样本外稳定性
- 是否适合组合构建或实盘交易

正式研究仍需使用有授权的真实行情，补充未来信息检查、数值稳定性、覆盖率、样本外、风险、换手和回测验证。
