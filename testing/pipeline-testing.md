---
description: 端到端数据流测试 - 完整采集流程、增量更新
type: sub-document
parent: dev-guidelines.md
auto_execution_mode: 2
---

# 端到端数据流测试

```python
class TestDataPipeline:
    def test_full_collection_pipeline(self, test_db, stock_collector):
        stock_code = '000001'
        
        # 1. 采集数据
        count = stock_collector.collect_daily_kline(stock_code, '2024-01-01', '2024-01-31')
        assert count > 0, "应采集到数据"
        
        # 2. 验证数据入库
        with test_db.connect() as conn:
            result = conn.execute(text('''
                SELECT COUNT(*) FROM daily_kline 
                WHERE stock_code = :code
            '''), {'code': stock_code})
            db_count = result.scalar()
        
        assert db_count == count, f"数据库记录数 {db_count} 与采集数 {count} 不一致"
        
        # 3. 验证数据完整性
        with test_db.connect() as conn:
            result = conn.execute(text('''
                SELECT MIN(trade_date), MAX(trade_date) FROM daily_kline 
                WHERE stock_code = :code
            '''), {'code': stock_code})
            min_date, max_date = result.fetchone()
        
        assert min_date <= '2024-01-01'
        assert max_date >= '2024-01-31'
    
    def test_incremental_update(self, test_db, stock_collector):
        stock_code = '000001'
        
        # 首次采集
        count1 = stock_collector.collect_daily_kline(stock_code, '2024-01-01', '2024-01-15')
        
        # 追加采集
        count2 = stock_collector.collect_daily_kline(stock_code, '2024-01-16', '2024-01-31')
        
        # 重复采集应去重
        count3 = stock_collector.collect_daily_kline(stock_code, '2024-01-01', '2024-01-31')
        
        assert count3 <= max(count1, count2) * 0.1, "重复采集不应产生大量重复数据"
```
