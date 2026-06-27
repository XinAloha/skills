---
description: 数据库集成测试 - 唯一约束、批量插入性能、查询性能
type: sub-document
parent: dev-guidelines.md
auto_execution_mode: 2
---

# 数据库集成测试

```python
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

class TestDatabaseOperations:
    @pytest.fixture(scope='function')
    def test_db(self):
        engine = create_engine('sqlite:///:memory:')
        with engine.begin() as conn:
            conn.execute(text('''
                CREATE TABLE daily_kline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    trade_date DATE NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    amount REAL,
                    adjust_type INTEGER DEFAULT 1,
                    UNIQUE(stock_code, trade_date, adjust_type)
                )
            '''))
        yield engine
        engine.dispose()
    
    def test_unique_constraint(self, test_db):
        with test_db.begin() as conn:
            conn.execute(text('''
                INSERT INTO daily_kline 
                (stock_code, trade_date, open, high, low, close, volume)
                VALUES ('000001', '2024-01-01', 10.0, 11.0, 9.0, 10.5, 1000000)
            '''))
            with pytest.raises(Exception):
                conn.execute(text('''
                    INSERT INTO daily_kline 
                    (stock_code, trade_date, open, high, low, close, volume)
                    VALUES ('000001', '2024-01-01', 10.1, 11.1, 9.1, 10.6, 1000001)
                '''))
    
    def test_bulk_insert_performance(self, test_db):
        import time
        data = [
            {
                'stock_code': f'{i:06d}',
                'trade_date': '2024-01-01',
                'open': 10.0, 'high': 11.0, 'low': 9.0, 'close': 10.5,
                'volume': 1000000
            }
            for i in range(10000)
        ]
        start = time.time()
        with test_db.begin() as conn:
            conn.execute(
                text('''
                    INSERT INTO daily_kline 
                    (stock_code, trade_date, open, high, low, close, volume)
                    VALUES (:stock_code, :trade_date, :open, :high, :low, :close, :volume)
                '''),
                data
            )
        elapsed = time.time() - start
        assert elapsed < 5.0, f"批量插入 10000 条耗时 {elapsed:.2f}s"
    
    def test_query_performance(self, test_db):
        import time
        with test_db.begin() as conn:
            for i in range(1000):
                conn.execute(text(f'''
                    INSERT INTO daily_kline 
                    (stock_code, trade_date, open, high, low, close, volume)
                    VALUES ('000001', '2024-01-{i%30+1:02d}', 10.0, 11.0, 9.0, 10.5, 1000000)
                '''))
        start = time.time()
        with test_db.connect() as conn:
            result = conn.execute(text('''
                SELECT * FROM daily_kline 
                WHERE stock_code = '000001' 
                ORDER BY trade_date DESC
            '''))
            rows = result.fetchall()
        elapsed = time.time() - start
        assert elapsed < 1.0, f"查询 1000 条记录耗时 {elapsed:.3f}s"
```
