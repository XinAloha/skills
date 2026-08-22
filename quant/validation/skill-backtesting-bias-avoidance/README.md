# 回测与偏差规避 Skill

中文说明请参阅 [agents/README.md](agents/README.md)。本仓库提供一个面向 Codex、Claude Code、Cursor、Hermes 和 OpenClaw 的量化回测审计技能，重点检查前视偏差、幸存者偏差、过拟合、数据窥探和交易成本影响。

## 快速开始

```bash
pip install numpy pandas scipy matplotlib
python scripts/run_backtest.py --out 回测审计.md
```

默认使用离线合成数据；使用真实数据时请明确数据来源、时间范围、时点一致性和退市标的覆盖情况。完整工作流见 [SKILL.md](SKILL.md)，英文说明见 [README.en.md](README.en.md)。

本项目仅用于研究与工程验证，不构成投资建议或任何收益承诺。

## 许可证

本项目采用 [GNU GPLv3](LICENSE)，元数据标识为 `GPL-3.0-only`。
