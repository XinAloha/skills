---
description: 扩展性设计原则 - 开闭/接口隔离/依赖倒置
type: sub-document
parent: dev-guidelines.md
auto_execution_mode: 2
---

# 扩展性设计原则

## 1. 开闭原则 (OCP)

**对扩展开放，对修改关闭**

```python
# ✅ Good: 通过扩展而非修改来增加功能

# 原有代码不变
class StockDataCollector:
    def collect_daily_kline(self, stock_code: str, source: DataSourceStrategy):
        return source.get_data(stock_code)

# 新功能通过扩展实现
class TushareStrategy(DataSourceStrategy):  # 新增类
    def get_data(self, stock_code: str):
        pass

# 使用时传入新策略
collector.collect_daily_kline('000001', TushareStrategy())
```

## 2. 接口隔离原则 (ISP)

```python
# ✅ Good: 细粒度接口

class IStockInfoProvider(ABC):
    @abstractmethod
    def get_stock_list(self) -> List[str]:
        """获取股票列表"""
        pass

class IPriceDataProvider(ABC):
    @abstractmethod
    def get_daily_kline(self, stock_code: str) -> pd.DataFrame:
        """获取日K线"""
        pass

class IFundamentalDataProvider(ABC):
    @abstractmethod
    def get_financial_reports(self, stock_code: str):
        """获取财务报表"""
        pass

# 采集器根据需要实现特定接口
class AdataCollector(IPriceDataProvider):  # 只实现需要的接口
    def get_daily_kline(self, stock_code: str):
        pass
```

## 3. 依赖倒置原则 (DIP)

```python
# ✅ Good: 依赖抽象而非具体

from abc import ABC, abstractmethod

class IDatabase(ABC):
    @abstractmethod
    def save_kline(self, data: pd.DataFrame):
        pass

class SQLiteDatabase(IDatabase):
    def save_kline(self, data: pd.DataFrame):
        # SQLite 实现
        pass

class PostgreSQLDatabase(IDatabase):
    def save_kline(self, data: pd.DataFrame):
        # PostgreSQL 实现
        pass

# 高层模块依赖抽象
class DataCollector:
    def __init__(self, database: IDatabase):  # 依赖接口
        self._db = database
```
