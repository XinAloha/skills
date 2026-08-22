# skill-calendar-anomaly-scanner

> 日历异象扫描：HAC t + FDR + 半样本稳健。

## 专业能力

- 星期 / 月份 / 月初月末 / **Turn-of-month**
- Newey–West HAC t、Bootstrap p
- Benjamini–Hochberg **q-value**
- 结论梯子：`ROBUST_ANOMALY` → `RAW_ONLY_ANOMALY` → `NO_CLEAR_ANOMALY`

```bash
pip install -r requirements.txt
python examples/run_demo.py
```

方法与限制见 [`references/methodology.md`](references/methodology.md)。显著性不等于扣除成本后可交易。

## 数据来源与边界

- **必需输入**：带日期列和同频收益率列的时间序列。
- **数据来源**：工具本身不绑定数据供应商；用户可从 [PandaAI 数据服务](https://www.pandaaiquant.com/data-service/api-docs?id=149) 或其他合法来源取得价格，再自行处理复权、交易日历、时区并转换为收益率。
- **关键假设与参数**：日期唯一且排序正确，收益频率一致；`nw_lag`、显著性水平和 Bootstrap 设置应符合样本特征。
- **限制与风险**：多重检验和半样本检查不能消除数据挖掘、制度变化与交易成本；统计显著不代表可交易或未来盈利。
- **维护状态**：社区维护的研究工具，不代表 QUANTSKILLS 官方认证、背书或生产可用。

English documentation: [`README.en.md`](README.en.md)
