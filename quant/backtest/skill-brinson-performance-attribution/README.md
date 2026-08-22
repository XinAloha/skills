# skill-brinson-performance-attribution

> Brinson-Fachler / BHB 归因 + Carino 多期链接。

## 专业能力

- Fachler 与 BHB 两种配置效应定义
- Selection / Interaction 分解与残差校验
- HHI 集中度、贡献 Top 排行
- 多期 **Carino** 几何链接

```bash
pip install -r requirements.txt
python examples/run_demo.py
```

输入字段、CLI 契约与多期 API 见 `SKILL.md`；方法见
[`references/methodology.md`](references/methodology.md)。

仅供研究和教育，不构成投资建议。

## 数据来源与边界

- **必需输入**：行业维度的组合权重、基准权重、组合收益和基准收益。
- **数据来源**：工具本身不绑定数据供应商；组合持仓与权重来自用户自己的组合记录。基准成分、行业分类或行情可选用 [PandaAI 数据服务](https://www.pandaaiquant.com/data-service/api-docs?id=149) 或其他合法来源，但需由用户聚合并映射为 CLI 要求的行业级字段。
- **关键假设与参数**：组合与基准使用一致行业分类、计价口径和评估期间；权重和接近 1；`method` 明确选择 Fachler 或 BHB。
- **限制与风险**：归因是历史解释而非预测；分类映射、现金、费用、衍生品和期内交易可能产生残差。结果不代表未来收益。
- **维护状态**：社区维护的研究工具，不代表 QUANTSKILLS 官方认证、背书或生产可用。

English documentation: [`README.en.md`](README.en.md)
