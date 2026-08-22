# skill-walk-forward-validator

> Purged / embargoed walk-forward：把全样本 IC 推进到可审计的样本外协议。

## 专业能力

- rolling / expanding 窗口 + **embargo**（防标签重叠）
- Rank IC / Pearson IC / **ICIR** / 多空 Sharpe / **Q5−Q1**
- bootstrap **CI95** + train→test 退化率
- 多门禁 scorecard：`PASS` / `WEAK_PASS` / `FAIL`

## 运行

```bash
pip install -r requirements.txt
python examples/run_demo.py
```

独立仓 CLI 示例及输入契约见 `SKILL.md`。本 skill 不依赖 monorepo 包即可运行。

方法细节：[`references/methodology.md`](references/methodology.md)

## License

GPL-3.0 · 研究/教育用途，不构成投资建议。

## 数据来源与边界

- **必需输入**：按日期与资产严格对齐的横截面信号矩阵和远期收益矩阵。
- **数据来源**：工具本身不绑定数据供应商；数据由用户提供。行情数据可来自 [PandaAI 数据服务](https://www.pandaaiquant.com/data-service/api-docs?id=149) 或其他合法来源，但原始价格必须先转换为与 `label_horizon` 一致的远期收益；信号值仍需由用户的研究流程生成。
- **关键假设与参数**：信号在当时可获得且不存在未来信息；`label_horizon`、`embargo`、训练窗和测试窗必须与研究设计一致。
- **限制与风险**：本工具只验证样本外统计稳定性，不模拟费用、流动性、涨跌停、融券或市场冲击；通过门禁不代表未来有效或可交易。
- **维护状态**：社区维护的研究工具，不代表 QUANTSKILLS 官方认证、背书或生产可用。

English documentation: [`README.en.md`](README.en.md)
