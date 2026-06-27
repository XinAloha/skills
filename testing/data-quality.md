---
description: 数据质量测试 - 完整性/可靠性/多源一致性
type: sub-document
parent: dev-guidelines.md
auto_execution_mode: 2
---

# 数据质量测试

> 核心原则：数据可靠性 > 代码正确性 > 功能完整性

## 字段完整性测试

```python
class TestFieldCompleteness:
    REQUIRED_KLINE_FIELDS = [
        'trade_date', 'stock_code', 'open', 'high', 
        'low', 'close', 'volume', 'amount'
    ]
    
    def test_no_missing_required_fields(self, sample_kline_df):
        missing = set(self.REQUIRED_KLINE_FIELDS) - set(sample_kline_df.columns)
        assert len(missing) == 0, f"缺少必需字段: {missing}"
    
    def test_no_null_in_critical_fields(self, sample_kline_df):
        critical_fields = ['open', 'high', 'low', 'close', 'volume']
        for field in critical_fields:
            null_count = sample_kline_df[field].isna().sum()
            assert null_count == 0, f"{field} 字段存在 {null_count} 个空值"
    
    def test_date_continuity(self, stock_data_collector):
        df = stock_data_collector.get_kline('000001', '2024-01-01', '2024-01-31')
        df['date_diff'] = df['trade_date'].diff().dt.days
        unusual_gaps = df[df['date_diff'] > 5]
        assert len(unusual_gaps) == 0, f"发现日期断点: {unusual_gaps['trade_date'].tolist()}"
```

## 数据范围完整性测试

```python
class TestDataRangeCompleteness:
    def test_all_stocks_covered(self, stock_collector, stock_list):
        collected_codes = stock_collector.get_collected_stocks()
        missing = set(stock_list) - set(collected_codes)
        missing_ratio = len(missing) / len(stock_list)
        assert missing_ratio <= 0.01, f"{len(missing)} 只股票未采集"
    
    def test_historical_data_completeness(self, db_inspector):
        stock_code = '000001'
        expected_start = '2020-01-01'
        actual_start = db_inspector.get_earliest_date(stock_code)
        assert actual_start <= expected_start, \
            f"{stock_code} 历史数据不完整，最早记录 {actual_start}"
```

## 数值逻辑验证

```python
class TestDataReliability:
    def test_ohlc_logic(self, kline_df):
        assert all(kline_df['high'] >= kline_df['open'])
        assert all(kline_df['high'] >= kline_df['close'])
        assert all(kline_df['high'] >= kline_df['low'])
        assert all(kline_df['low'] <= kline_df['open'])
        assert all(kline_df['low'] <= kline_df['close'])
    
    def test_volume_positive(self, kline_df):
        negative_volume = kline_df[kline_df['volume'] < 0]
        assert len(negative_volume) == 0
    
    def test_price_positive(self, kline_df):
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            non_positive = kline_df[kline_df[col] <= 0]
            assert len(non_positive) == 0
    
    def test_price_change_reasonable(self, kline_df):
        kline_df['price_change_pct'] = (
            (kline_df['close'] - kline_df['open']) / kline_df['open'] * 100
        )
        unusual_changes = kline_df[abs(kline_df['price_change_pct']) > 25]
        assert len(unusual_changes) <= len(kline_df) * 0.001
```

## 多源数据一致性测试

```python
class TestMultiSourceConsistency:
    def test_cross_source_ohlc_match(self, adata_collector, akshare_collector):
        stock_code = '000001'
        trade_date = '2024-01-15'
        df_adata = adata_collector.get_daily_kline(stock_code, trade_date, trade_date)
        df_ak = akshare_collector.get_daily_kline(stock_code, trade_date, trade_date)
        
        tolerance = 0.001
        for col in ['open', 'high', 'low', 'close']:
            price_adata = df_adata[col].iloc[0]
            price_ak = df_ak[col].iloc[0]
            diff_pct = abs(price_adata - price_ak) / price_adata
            assert diff_pct <= tolerance
    
    def test_volume_order_of_magnitude_match(self, adata_collector, akshare_collector):
        stock_code = '000001'
        df_adata = adata_collector.get_daily_kline(stock_code, '2024-01-01', '2024-01-31')
        df_ak = akshare_collector.get_daily_kline(stock_code, '2024-01-01', '2024-01-31')
        
        merged = pd.merge(
            df_adata[['trade_date', 'volume']], 
            df_ak[['trade_date', 'volume']], 
            on='trade_date', suffixes=('_adata', '_ak')
        )
        merged['volume_ratio'] = merged['volume_adata'] / merged['volume_ak']
        reasonable_ratio = merged[
            (merged['volume_ratio'] >= 0.1) & (merged['volume_ratio'] <= 10)
        ]
        match_ratio = len(reasonable_ratio) / len(merged)
        assert match_ratio >= 0.95
```
