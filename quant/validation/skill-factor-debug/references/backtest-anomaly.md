# 回测异常诊断

| 症状 | 病因 | 修复 |
|---|---|---|
| **全空仓**（持仓 = 0） | universe 全被涨跌停 / 停牌剔除 | 检查 `trade_status` / `limit_up` 字段是否齐 |
| **全满仓**（每日选 100% 股票） | `top_pct` 阈值反了 | 改 `rank >= 1 - top_pct` |
| **持仓股数 = 1** | `top_pct` 太小 | 提到至少 5% |
| **Sharpe = NaN** | `daily_ret` 全 NaN | 检查 fwd_ret 计算 |
| **净值起点不是 1.0** | 复利口径错（线性而非乘法） | 用 `(1 + ret).cumprod()` |
| **MDD < 5%** | 几乎一定是未来函数 | 见 `look-ahead-bias.md` |
| **换手 = 0%** | 信号没在变 | 检查信号是否有 NaN 一直传过来 |
| **换手 > 200%** | 信号噪声主导 | 算 Top 篮 Jaccard，多半 < 0.5 |

## 5 项体检不通过怎么办

| 不通过项 | 优先排查 |
|---|---|
| 持仓股数 < 期望 50% | 涨跌停 mask 太严？trade_status 字段缺？ |
| 单日换手 > 期望 2 倍 | 信号变化太快，看 Top 篮 Jaccard |
| Sharpe / IC_IR > 1.0 | close 当成交价 / 没扣手续费 / T+0 / 没剔涨跌停 |
| MDD < 5% | 未来函数（最大嫌疑） |
| 全仓时间 < 80% | 信号生成早期 NaN 太多 → 截早期段 |

## 隔离测试脚本

```python
import alpha, prepare, backtest

train = prepare.load_train_panel()
val = prepare.load_val_panel()
sig_train, sig_val = alpha.run(train, val)

# 手动跑回测
result = backtest.backtest_long_only(sig_val, val, horizon=alpha.HORIZON)

# 5 项体检
positions = result["positions"]
n_holding = (positions > 0).sum(axis=1)
print(f"持仓股数 mean: {n_holding.mean():.1f}  (期望 ~{positions.shape[1] * 0.10:.0f})")
print(f"换手 daily_mean: {result['turnover_series'].mean():.4f}  (期望 ~{2/alpha.HORIZON:.4f})")
print(f"Sharpe: {result['sharpe']:.2f}")
print(f"MDD:    {result['max_drawdown']:.2%}")
print(f"全仓时间占比: {(n_holding > 0).mean():.2%}")
```

## 调试技巧

### 看某一日的细节

```python
t = pd.Timestamp("2023-06-15")
print(f"信号 Top 10: {sig_val.loc[t].nlargest(10)}")
print(f"涨停股: {(close.loc[t] >= limit_up.loc[t] * 0.99).sum()}")
print(f"停牌股: {(trade_status.loc[t] == 1).sum()}")
print(f"持仓: {positions.loc[t][positions.loc[t] > 0]}")
```

### 看持仓时间序列

```python
n_holding.plot()  # 应该接近水平线（每日 ~Top 10%）
```

如果有断崖式下跌 → 那一天 universe 被大量剔除，看 mask 逻辑。

## 反模式

- ❌ 回测结果不对，第一反应是改 top_pct —— 先确认数据完整性
- ❌ 看到 MDD < 5% 不查 bug —— 这是最大嫌疑信号
- ❌ 体检不通过就改阈值放宽通过 —— 是在掩盖问题
