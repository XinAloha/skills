# skill-rolling-beta-exposure

> 滚动 CAPM 暴露诊断（α/β/SE/CI、涨跌 beta、收缩估计）。

## 专业能力

- 带截距 OLS：α、β、SE、95% CI、R²、残差波动
- **Up/Down beta** 非对称暴露
- Vasicek 收缩 β（prior=1）
- 路径稳定性：最大 |Δβ|

```bash
pip install -r requirements.txt
python examples/run_demo.py
```

方法与限制见 [`references/methodology.md`](references/methodology.md)。

## 数据来源与边界

- **必需输入**：同频、同顺序的资产收益率和市场收益率序列。
- **数据来源**：工具本身不绑定数据供应商；用户可从 [PandaAI 数据服务](https://www.pandaaiquant.com/data-service/api-docs?id=149) 或其他合法来源取得资产与基准价格，再自行处理复权、交易日历和频率并转换为收益率。
- **关键假设与参数**：资产和市场收益严格对齐；滚动窗口有足够样本；市场代理、`window` 和先验参数适合研究目的。
- **限制与风险**：单因子 CAPM beta 对市场代理、窗口和制度变化敏感；beta 不是收益预测，也不覆盖完整风险模型。
- **维护状态**：社区维护的研究工具，不代表 QUANTSKILLS 官方认证、背书或生产可用。

English documentation: [`README.en.md`](README.en.md)
