---
description: 采集器单元测试规范
type: sub-document
parent: dev-guidelines.md
auto_execution_mode: 2
---

# 采集器单元测试规范

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

class TestBaseCollector:
    @pytest.fixture
    def mock_response(self):
        return {
            'code': 200,
            'data': [
                {
                    'trade_date': '2024-01-15',
                    'open': 10.0, 'high': 11.0,
                    'low': 9.5, 'close': 10.5,
                    'volume': 1000000
                }
            ]
        }
    
    def test_collector_initialization(self, collector_class):
        collector = collector_class()
        assert collector is not None
        assert hasattr(collector, 'get_daily_kline')
    
    def test_successful_data_fetch(self, collector, mock_response):
        with patch.object(collector, '_fetch_api', return_value=mock_response):
            df = collector.get_daily_kline('000001', '2024-01-01', '2024-01-31')
            assert isinstance(df, pd.DataFrame)
            assert len(df) > 0
            assert 'close' in df.columns
    
    def test_empty_response_handling(self, collector):
        with patch.object(collector, '_fetch_api', return_value={'code': 200, 'data': []}):
            df = collector.get_daily_kline('000001', '2024-01-01', '2024-01-31')
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 0
    
    def test_api_error_handling(self, collector):
        with patch.object(collector, '_fetch_api', side_effect=Exception("API Error")):
            with pytest.raises(Exception) as exc_info:
                collector.get_daily_kline('000001', '2024-01-01', '2024-01-31')
            assert "API Error" in str(exc_info.value)
    
    def test_invalid_stock_code_handling(self, collector):
        invalid_codes = ['', '123', 'INVALID', '000000']
        for code in invalid_codes:
            with pytest.raises((ValueError, Exception)):
                collector.get_daily_kline(code, '2024-01-01', '2024-01-31')
    
    def test_date_format_validation(self, collector):
        invalid_dates = ['2024/01/01', '01-01-2024', '20240101', 'invalid']
        for date in invalid_dates:
            with pytest.raises((ValueError, Exception)):
                collector.get_daily_kline('000001', date, '2024-01-31')
```

## 数据验证器测试

```python
class TestDataValidators:
    def test_kline_schema_validation(self):
        from data_collection.validators import KlineValidator
        validator = KlineValidator()
        
        valid_df = pd.DataFrame({
            'trade_date': pd.to_datetime(['2024-01-01']),
            'open': [10.0], 'high': [11.0], 'low': [9.0], 'close': [10.5],
            'volume': [1000000], 'amount': [10500000]
        })
        assert validator.validate(valid_df) is True
        
        invalid_df = pd.DataFrame({
            'trade_date': pd.to_datetime(['2024-01-01']),
            'open': [10.0], 'close': [10.5]
        })
        with pytest.raises(ValidationError):
            validator.validate(invalid_df)
    
    def test_data_type_validation(self):
        from data_collection.validators import KlineValidator
        validator = KlineValidator()
        
        invalid_df = pd.DataFrame({
            'trade_date': ['2024-01-01'],
            'open': ['10.0'], 'high': [11.0], 'low': [9.0], 'close': [10.5],
            'volume': [1000000], 'amount': [10500000]
        })
        with pytest.raises(ValidationError):
            validator.validate(invalid_df)
```
