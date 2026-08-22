# statistical-arbitrage-time-series

统计套利与时间序列建模 Agent Skill（中文优先）。输入候选配对、篮子或资产池，生成可复现、可溯源的研究报告，覆盖数据处理、训练窗 ADF/KPSS、价差建模、均值回归、偏差控制回测、现实成本与稳健性风险。

本项目只用于研究与方法验证，不构成投资建议，不承诺收益，也不代表 QuantSkills 或任何平台的官方背书。

## 使用

- 技能定义：[`SKILL.md`](SKILL.md)
- 研究指南：[`references/statarb-guide.md`](references/statarb-guide.md)
- 可执行脚本：[`scripts/run_statarb.py`](scripts/run_statarb.py)
- English: [`README.en.md`](README.en.md)

```bash
python scripts/run_statarb.py --source synthetic --mode strong
```

依赖安装与 Claude Code、Codex、Cursor、Hermes、OpenClaw 的入口说明见 [`agents/portable-loader.md`](agents/portable-loader.md)。

## 许可证

GPL-3.0-only，详见 [`LICENSE`](LICENSE)。
