---
description: 故障恢复测试 - 网络异常、部分失败、数据库恢复
type: sub-document
parent: dev-guidelines.md
auto_execution_mode: 2
---

# 故障恢复测试

## 网络异常恢复

```python
class TestFaultRecovery:
    def test_retry_mechanism(self, retry_client):
        with patch.object(retry_client, '_fetch', side_effect=[
            NetworkError("Timeout"),
            NetworkError("Timeout"),
            pd.DataFrame({'close': [10.0]})
        ]):
            result = retry_client.get_data_with_retry('000001', max_retries=3)
            assert result is not None, "重试后应成功获取数据"
    
    def test_partial_failure_handling(self, stock_collector):
        """某只股票失败不应影响其他股票"""
        stock_codes = ['000001', 'INVALID_CODE', '000002']
        results = {}
        for code in stock_codes:
            try:
                results[code] = stock_collector.collect_daily_kline(code)
            except Exception as e:
                results[code] = f"Error: {e}"
        
        assert results['000001'] > 0
        assert results['000002'] > 0
        assert 'Error' in str(results['INVALID_CODE'])
    
    def test_database_connection_recovery(self, db_collector):
        db_collector.engine.dispose()
        result = db_collector.save_data(pd.DataFrame({'test': [1]}))
        assert result is True, "数据库连接断开后应能恢复"
```
