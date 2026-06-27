# 何时 Mock

**只在系统边界 mock**：

- 外部 API（Tushare、AKShare、adata）。
- 数据库（有时——更优先用测试库 / SQLite）。
- 时间 / 随机性。
- 文件系统（有时）。

**不要 mock**：

- 自己的类 / 模块。
- 内部协作者。
- 任何你能控制的东西。

## 为可 mock 性设计

### 1. 用依赖注入

把外部依赖**传进来**，而不是在内部创建：

```python
# 易 mock
def process_payment(order, payment_client):
    return payment_client.charge(order.total)

# 难 mock
def process_payment(order):
    client = TushareApi(os.environ["TUSHARE_TOKEN"])
    return client.fetch(order)
```

### 2. 优先 SDK 风格接口，而不是通用 fetcher

```python
# 好：每个函数独立可 mock
class TushareSdk:
    def get_daily(self, symbol, date): ...
    def get_basic(self, symbol): ...
    def get_adj_factor(self, symbol): ...

# 坏：mock 时要在内部加条件分支
class TushareSdk:
    def fetch(self, endpoint, params): ...
```

SDK 风格的好处：

- 每个 mock 只需返回一个特定 shape。
- 测试 setup 没有条件逻辑。
- 一眼看出测试碰了哪些端点。
- 每个端点类型独立。

## 本项目实践

- 用 `pytest-mock` 的 `mocker.patch` 在系统边界打 mock（如 `tushare.pro_api`、`requests.get`）。
- 在测试 fixture 里准备真实抓取的 DataFrame 样本（pickle/parquet），重放给采集器。
- 数据库测试优先用 SQLite + tmp_path，而不是 mock SQLAlchemy。

> 详见 [collector-testing](../../testing/collector-testing.md)（采集器测试模板）和 [database-testing](../../testing/database-testing.md)。
