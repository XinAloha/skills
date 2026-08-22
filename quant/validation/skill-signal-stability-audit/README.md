# skill-signal-stability-audit

> 信号稳定性 / 换手 / 成本拖累诊断。

## 专业能力

- lag 自相关曲线 + **半衰期**
- Top/Bottom Jaccard、单向换手代理
- Kendall tau、符号翻转率
- **五分位迁移矩阵**
- 年化成本拖累 + 再平衡频率建议

```bash
pip install -r requirements.txt
python examples/run_demo.py
```

详见 [`references/methodology.md`](references/methodology.md)

## 数据来源与边界

- **必需输入**：日期 × 资产的横截面信号矩阵。
- **数据来源**：工具本身不绑定数据供应商；信号由用户提供。信号所需的行情或因子原料可选用 [PandaAI 数据服务](https://www.pandaaiquant.com/data-service/api-docs?id=149) 或其他合法来源，但必须按时点构造并避免未来信息。
- **关键假设与参数**：资产列和日期顺序一致；`top_frac`、`cost_bps` 和 `rebalance_days` 与实际研究设定一致。
- **限制与风险**：成本拖累和换手均为代理指标，不替代持仓级回测；稳定性不表示信号有效、可交易或未来盈利。
- **维护状态**：社区维护的研究工具，不代表 QUANTSKILLS 官方认证、背书或生产可用。

English documentation: [`README.en.md`](README.en.md)
