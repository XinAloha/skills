# 为可测性设计接口

好接口让测试自然：

## 1. 接受依赖，别在内部创建

```python
# 易测
def process_daily(symbol: str, source: DataSource) -> pd.DataFrame:
    return source.fetch_daily(symbol)

# 难测（内部硬编码 Tushare 客户端）
def process_daily(symbol: str) -> pd.DataFrame:
    api = TushareApi(token=os.environ["TUSHARE_TOKEN"])
    return api.fetch(symbol)
```

## 2. 返回结果，别只产副作用

```python
# 易测
def calculate_adjustment(prices: pd.DataFrame, factor: float) -> pd.DataFrame:
    return prices.assign(close=prices["close"] * factor)

# 难测（直接写库）
def apply_adjustment(prices: pd.DataFrame, factor: float) -> None:
    db.execute("UPDATE daily_kline SET close = close * %s", (factor,))
```

## 3. 小接口面积

- 方法越少 → 测试越少。
- 参数越少 → 测试 setup 越简单。

## 本项目落地

- 采集器全部接受 `DataSource` / `Database` 等依赖作为构造参数（依赖注入）。
- `normalize_*` 函数纯函数化：输入 raw DataFrame，输出标准 DataFrame，不写库不打日志。
- 写库与采集分层：`Writer.write(df)` 单独可测。

> 详见 [extensibility](../../engineering/extensibility.md)（接口设计、插件架构）。
