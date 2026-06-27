---
description: 外部系统集成 - VNPY适配器、集成原则
type: sub-document
parent: dev-guidelines.md
auto_execution_mode: 2
---

# 外部系统集成

**重要原则**：外部系统适配器**不应放入** `data_collection/` 目录，以免破坏核心模块的纯净性。

## 集成示例：VNPY 数据适配器

```python
# 文件位置：项目根目录（如 integrations/vnpy_adapter.py）
# 不在 data_collection/ 内，避免外部依赖污染核心模块

class DataCollectionFeed:
    """VNPY 数据源适配器 - 直接读取 data_collection 的数据库"""
    
    def __init__(self, db_url: str = 'sqlite:///data/stock_data.db'):
        self.engine = create_engine(db_url)
    
    def query_history_data(
        self,
        symbol: str,
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> pd.DataFrame:
        """查询历史K线数据（VNPY 格式）"""
        sql = """
            SELECT 
                trade_date as datetime,
                open, high, low, close, volume, amount as turnover
            FROM daily_kline
            WHERE stock_code = :symbol AND adjust_type = 1
        """
        
        params = {'symbol': symbol}
        if start:
            sql += " AND trade_date >= :start"
            params['start'] = start
        if end:
            sql += " AND trade_date <= :end"
            params['end'] = end
            
        sql += " ORDER BY trade_date"
        
        return pd.read_sql(sql, self.engine, params=params)
```

## 集成原则

| 项目 | 处理方式 | 原因 |
|------|---------|------|
| VNPY 适配器 | 放 `integrations/` 或根目录 | 外部系统依赖，非核心功能 |
| Web 展示 | 放 `web/` 目录 | Flask/Django 独立运行 |
| 数据分析 | 放 `analysis/` 目录 | 使用 Jupyter/Streamlit |
| 交易执行 | 放 `trading/` 目录 | 与券商 API 对接 |

**核心思想**：`data_collection/` 只负责**数据采集和存储**，其他功能通过**读取数据库**与之集成。
