# 好测试 vs 坏测试

## 好测试

**集成式**：通过真实接口，而不是 mock 内部。

```python
# 好：测可观察的行为
def test_user_can_fetch_daily_with_valid_symbol():
    collector = TushareCollector(api=mock_api_with_fixture("600000_20251010"))
    df = collector.fetch_daily("600000.SH", "20251010")
    assert df.iloc[0]["close"] == 12.34
    assert df.iloc[0]["symbol"] == "600000.SH"
```

特征：

- 测调用方真正在意的行为。
- 只走公开 API。
- 在内部重构后能存活。
- 描述**做什么**，不描述**怎么做**。
- 每个测试一个逻辑断言。

## 坏测试

**实现细节测试**：和内部结构耦合。

```python
# 坏：测实现细节
def test_collector_calls_normalize_internal():
    collector = TushareCollector()
    with mock.patch.object(collector, "_normalize_columns") as m:
        collector.fetch_daily("600000.SH")
        m.assert_called_once()  # 在测内部方法被调用
```

红旗：

- mock 内部协作者。
- 测私有方法。
- 断言"调用次数 / 调用顺序"。
- 行为没变、重构后测试坏掉。
- 测试名描述**怎么做**而不是**做什么**。
- 通过外部手段（直接查库）验证，而不是通过接口。

```python
# 坏：绕开接口去验证
def test_collector_writes_to_db():
    collector.fetch_and_store("600000.SH")
    row = db.execute("SELECT * FROM daily_kline WHERE symbol='600000.SH'").fetchone()
    assert row is not None

# 好：通过接口验证
def test_collector_results_are_retrievable():
    collector.fetch_and_store("600000.SH")
    retrieved = db_reader.get_daily("600000.SH")
    assert retrieved is not None
```

## 本项目特别提醒

- **不要直接 mock SQLAlchemy 的 `session.execute`**——用 `tmp_path` + SQLite 测试库。
- **不要在测试里 hardcode 真实 token**——用 `mocker.patch("tushare.pro_api")`。
- **不要测"采集器的字段顺序"**——测字段值与 schema 一致即可。
