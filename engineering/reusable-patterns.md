---
description: 可复用模式 - 数据源适配、异常处理、数据验证、数据库优化
type: sub-document
parent: dev-guidelines.md
auto_execution_mode: 2
---

# 可复用模式

> **references/ 目录结构**
> ```
> references/
> ├── clone/      # 克隆的参考项目源码
> ├── analysis/   # 项目分析文档
> └── snippets/   # 提取的可复用代码片段（存放位置）
> ```

## 1. 数据源适配层设计

**借鉴 akshare 的接口设计**：

```python
from abc import ABC, abstractmethod
from typing import Protocol
import pandas as pd

class DataSource(Protocol):
    """数据源协议"""
    
    def get_daily_kline(
        self, symbol: str, start_date: str = None,
        end_date: str = None, adjust: str = "qfq"
    ) -> pd.DataFrame:
        """获取日K线数据 - 统一接口"""
        ...
    
    def get_stock_list(self) -> list[str]:
        """获取股票列表"""
        ...

class BaseCollector(ABC):
    """采集器基类 - 借鉴 akshare 的模板方法模式"""
    
    def __init__(self, rate_limit: int = 10):
        self.rate_limit = rate_limit
        self._session = self._create_session()
    
    def collect(self, symbol: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        params = self._build_params(symbol, start_date, end_date)
        self._apply_rate_limit()
        raw_data = self._fetch_with_retry(params)
        df = self._parse(raw_data)
        return self._validate(df)
    
    @abstractmethod
    def _build_params(self, symbol: str, start: str, end: str) -> dict:
        pass
    
    @abstractmethod
    def _fetch(self, params: dict) -> dict:
        pass
    
    @abstractmethod
    def _parse(self, raw_data: dict) -> pd.DataFrame:
        pass
```

## 2. 异常处理与容错设计

```python
class DataCollectionError(Exception):
    """数据采集错误基类"""
    pass

class NetworkError(DataCollectionError):
    """网络错误 - 可恢复"""
    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable

class DataFormatError(DataCollectionError):
    """数据格式错误 - 可能是数据源变更"""
    pass

class ValidationError(DataCollectionError):
    """数据验证错误"""
    pass

def robust_collect(collector, symbol: str) -> pd.DataFrame:
    try:
        return collector.collect(symbol)
    except NetworkError as e:
        if e.retryable:
            logger.warning(f"网络错误，将重试: {e}")
            raise
        else:
            logger.error(f"不可恢复的网络错误: {e}")
            return pd.DataFrame()
    except DataFormatError as e:
        logger.error(f"数据格式错误，可能需要更新解析逻辑: {e}")
        notify_admin(f"数据源格式变更: {symbol}")
        return pd.DataFrame()
    except Exception as e:
        logger.exception(f"未知错误采集 {symbol}: {e}")
        raise
```

## 3. 数据验证与清洗

**借鉴 quantaxis 的验证链设计**：

```python
from typing import List, Callable
import pandas as pd

class DataValidator:
    def __init__(self):
        self.rules: List[Callable[[pd.DataFrame], bool]] = []
    
    def add_rule(self, rule: Callable[[pd.DataFrame], bool], description: str):
        """添加验证规则"""
        self.rules.append((rule, description))
        return self  # 链式调用
    
    def validate(self, df: pd.DataFrame) -> tuple[bool, List[str]]:
        errors = []
        for rule, desc in self.rules:
            if not rule(df):
                errors.append(desc)
        return len(errors) == 0, errors

def ohlc_logic_check(df: pd.DataFrame) -> bool:
    return (
        (df['high'] >= df[['open', 'close', 'low']].max(axis=1)).all() and
        (df['low'] <= df[['open', 'close', 'high']].min(axis=1)).all()
    )

def no_missing_trading_days(df: pd.DataFrame) -> bool:
    date_diff = df['trade_date'].diff().dt.days
    unusual_gaps = date_diff[(date_diff > 5) & (date_diff != 7)]
    return len(unusual_gaps) == 0

# 使用
validator = (DataValidator()
    .add_rule(lambda df: not df.empty, "数据不能为空")
    .add_rule(ohlc_logic_check, "OHLC 逻辑错误")
    .add_rule(no_missing_trading_days, "存在异常日期断点")
    .add_rule(lambda df: (df['volume'] > 0).all(), "成交量必须为正")
)
```

## 4. 数据库存储优化

**借鉴 vnpy_datamanager 的设计**：

```python
from sqlalchemy import create_engine, Column, String, Float, Date, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.sqlite import insert

Base = declarative_base()

class DailyKline(Base):
    __tablename__ = 'daily_kline'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    adjust_type = Column(Integer, default=1)

class DatabaseManager:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def bulk_insert_kline(self, df: pd.DataFrame, batch_size: int = 1000) -> int:
        session = self.Session()
        inserted = 0
        try:
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                records = batch.to_dict('records')
                stmt = insert(DailyKline).values(records)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=['symbol', 'trade_date', 'adjust_type']
                )
                session.execute(stmt)
                inserted += len(records)
            session.commit()
            return inserted
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
```
