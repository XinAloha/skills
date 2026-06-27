---
description: 设计模式应用 - 策略/工厂/观察者/模板方法
type: sub-document
parent: dev-guidelines.md
auto_execution_mode: 2
---

# 设计模式应用

## 1. 策略模式 - 数据源切换

```python
# data_collection/collectors/base.py
from abc import ABC, abstractmethod

class DataSourceStrategy(ABC):
    @abstractmethod
    def get_daily_kline(self, stock_code: str) -> pd.DataFrame:
        pass

class AdataStrategy(DataSourceStrategy):
    def get_daily_kline(self, stock_code: str) -> pd.DataFrame:
        return adata.stock.market.get_market(stock_code=stock_code)

class AkshareStrategy(DataSourceStrategy):
    def get_daily_kline(self, stock_code: str) -> pd.DataFrame:
        return akshare.stock_zh_a_hist(symbol=stock_code)

# 使用
class FallbackCollector:
    def __init__(self, strategies: List[DataSourceStrategy]):
        self._strategies = strategies
    
    def get_data(self, stock_code: str):
        for strategy in self._strategies:
            try:
                return strategy.get_daily_kline(stock_code)
            except Exception:
                continue
        raise AllSourcesFailed()
```

## 2. 工厂模式 - 创建采集器

```python
# data_collection/factories.py
class CollectorFactory:
    @staticmethod
    def create_collector(source_type: str) -> DataSourceStrategy:
        if source_type == 'adata':
            return AdataStrategy()
        elif source_type == 'akshare':
            return AkshareStrategy()
        elif source_type == 'tushare':  # 未来扩展
            return TushareStrategy()
        else:
            raise ValueError(f"未知数据源: {source_type}")
```

## 3. 观察者模式 - 事件通知

```python
class DataCollectionEvent:
    def __init__(self):
        self._observers = []
    
    def attach(self, observer):
        self._observers.append(observer)
    
    def notify(self, stock_code: str, count: int):
        for observer in self._observers:
            observer.on_data_collected(stock_code, count)

class CollectionLogger:
    def on_data_collected(self, stock_code: str, count: int):
        # 记录到 collection_log 表
        pass
```

## 4. 模板方法模式 - 采集流程

```python
from abc import ABC, abstractmethod

class DataCollectionTemplate(ABC):
    def collect(self, stock_code: str) -> int:
        self._before_collect(stock_code)
        try:
            data = self._do_collect(stock_code)
            self._save_data(data)
            self._log_success(stock_code, len(data))
            return len(data)
        except Exception as e:
            self._log_failure(stock_code, e)
            return 0
        finally:
            self._after_collect(stock_code)
    
    @abstractmethod
    def _do_collect(self, stock_code: str) -> pd.DataFrame:
        """子类实现具体采集逻辑"""
        pass
    
    def _before_collect(self, stock_code: str):
        """钩子方法：采集前准备"""
        pass
    
    def _save_data(self, data: pd.DataFrame):
        """通用保存逻辑"""
        data.to_sql('daily_kline', self.engine, if_exists='append')
```

## 重构模式速查

### 模式 1: 策略模式（多数据源）

```python
# 重构前：if-else 判断
if source == 'adata':
    data = adata.get_data()
elif source == 'akshare':
    data = akshare.get_data()

# 重构后：策略模式
strategy = DataSourceFactory.create(source)
data = strategy.get_data(symbol)
```

### 模式 2: 模板方法（采集流程）

```python
class BaseCollector:
    def collect(self, symbol):
        params = self._build_params(symbol)  # 抽象
        data = self._fetch(params)           # 通用
        return self._parse(data)             # 抽象
```

### 模式 3: 装饰器（横切关注点）

```python
# 重构后：装饰器分离
@retry(max_attempts=3)
@rate_limit(calls=10, period=60)
def collect(symbol):
    return fetch(symbol)
```
