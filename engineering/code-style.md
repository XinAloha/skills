---
description: 代码规范 - 导入顺序、类设计、异常处理
type: sub-document
parent: dev-guidelines.md
auto_execution_mode: 2
---

# 代码规范

## 导入顺序

```python
# 标准库
import os
import time
from datetime import datetime
from typing import List, Optional

# 第三方库
import pandas as pd
from sqlalchemy import create_engine

# 本项目模块（使用相对导入）
from ..collectors import RetryableDataClient
from .stock_collector import StockDataCollector
```

## 类设计原则

**单一职责原则 (SRP)**

```python
# ✅ Good: 数据采集器只负责采集
class StockDataCollector:
    def collect_daily_kline(self, stock_code: str) -> pd.DataFrame:
        pass

# ❌ Bad: 混合了采集、分析、可视化
class StockDataHandler:  # 职责过多
    def collect_data(self): pass
    def analyze_data(self): pass  # 应该分离
    def plot_chart(self): pass     # 应该分离
```

**依赖注入 (DI)**

```python
# ✅ Good: 通过参数注入依赖
class StockDataCollector:
    def __init__(self, db_url: str, retry_client: Optional[RetryableDataClient] = None):
        self.engine = create_engine(db_url)
        self._retry_client = retry_client  # 可替换的依赖

# ❌ Bad: 硬编码依赖
class StockDataCollector:
    def __init__(self):
        self.engine = create_engine('sqlite:///fixed.db')  # 无法替换
```

## 异常处理规范

```python
def collect_data(self, stock_code: str) -> int:
    try:
        df = self._fetch_data(stock_code)
        return len(df)
    except NetworkError as e:
        # 特定异常：可恢复，记录日志
        self._log_error(f"网络错误: {e}")
        return 0
    except ValidationError as e:
        # 特定异常：数据格式问题
        self._log_error(f"数据验证失败: {e}")
        return 0
    except Exception as e:
        # 未知异常：记录并抛出
        self._log_error(f"未预期错误: {e}")
        raise
```
