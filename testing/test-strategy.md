---
description: 测试执行策略 - 标记分类、执行命令、覆盖率、CI、测试数据
type: sub-document
parent: dev-guidelines.md
auto_execution_mode: 2
---

# 测试执行策略

## 测试目录结构

```
test/
├── README.md                 # 测试文档与执行指南
├── TESTING_REPORT.md         # 测试开发完成报告
├── conftest.py               # pytest 全局配置与 fixtures
├── fixtures/                 # 测试数据夹具
├── unit/                     # 单元测试（mock 隔离）
│   ├── test_adjust_factor_collector.py
│   ├── test_column_mapping.py
│   ├── test_concept_collector.py
│   ├── test_config.py
│   ├── test_fallback_tushare.py
│   ├── test_fundflow_collector.py
│   ├── test_longhu_collector.py
│   ├── test_retry_client.py
│   ├── test_stock_collector.py
│   └── test_tushare_client.py
├── integration/              # 集成测试（多模块协同）
│   ├── test_akshare_real_api.py
│   ├── test_daily_job.py
│   └── test_daily_job_imports.py
├── data_quality/             # 数据质量测试
│   └── test_api_column_schema.py
└── diagnostics/              # 手动诊断脚本（网络/数据源排查）
    ├── test_data_sources.py
    └── test_network.py
```

## 测试标记分类

```python
# conftest.py
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "data_quality: 数据质量测试")
    config.addinivalue_line("markers", "diagnostics: 手动诊断脚本")
    config.addinivalue_line("markers", "slow: 耗时测试")
    config.addinivalue_line("markers", "network: 需要网络连接的测试")

@pytest.fixture(scope='session')
def test_db_url():
    return 'sqlite:///./test/data/test_stock_data.db'
```

## 分层执行命令

```bash
# 1. 快速验证 - 仅单元测试（开发阶段频繁运行）
pytest test/unit -v -m "not slow" --tb=short

# 2. 数据质量检查（每次采集后必须运行）
pytest test/data_quality -v --tb=short

# 3. 完整回归测试（发布前运行，排除诊断脚本）
pytest test/unit test/integration test/data_quality -v --tb=short --cov=data_collection --cov-report=html

# 4. 特定采集器测试
pytest test/unit/test_xxx_collector.py -v

# 5. 跳过网络测试（CI 环境）
pytest test/unit test/integration test/data_quality -v -m "not network" --tb=short

# 6. 诊断脚本（手动运行，排查网络/数据源问题）
python test/diagnostics/test_network.py
python test/diagnostics/test_data_sources.py
```

## 覆盖率要求

| 测试类型 | 覆盖率 | 重点关注 |
|---------|--------|---------|
| **单元测试** | ≥ 90% | 核心业务逻辑、异常分支 |
| **集成测试** | ≥ 70% | 数据流、数据库操作 |
| **数据质量测试** | 100% | 所有验证规则必须覆盖 |
| **异常处理** | 100% | 每个错误分支必须测试 |

## 测试数据准备

```python
# test/fixtures/mock_kline_data.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_mock_kline(
    stock_code: str = '000001',
    start_date: str = '2024-01-01',
    days: int = 30,
    base_price: float = 10.0,
    volatility: float = 0.02
) -> pd.DataFrame:
    dates = pd.date_range(start=start_date, periods=days, freq='B')
    returns = np.random.normal(0, volatility, days)
    prices = base_price * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        'trade_date': dates,
        'stock_code': stock_code,
        'open': prices * (1 + np.random.normal(0, 0.005, days)),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.01, days))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.01, days))),
        'close': prices,
        'volume': np.random.randint(100000, 10000000, days),
        'amount': np.random.randint(1000000, 100000000, days)
    })
    
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)
    return df

def generate_invalid_kline(case: str) -> pd.DataFrame:
    base_df = generate_mock_kline(days=5)
    if case == 'missing_field':
        return base_df.drop(columns=['volume'])
    elif case == 'null_value':
        base_df.loc[2, 'close'] = None
        return base_df
    elif case == 'invalid_ohlc':
        base_df.loc[2, 'high'] = base_df.loc[2, 'low'] - 1
        return base_df
    elif case == 'negative_price':
        base_df.loc[2, 'close'] = -10
        return base_df
    elif case == 'negative_volume':
        base_df.loc[2, 'volume'] = -1000
        return base_df
    return base_df
```

## 持续集成测试流程

```yaml
# .github/workflows/test.yml
name: Data Quality Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Run Unit Tests
      run: pytest test/unit -v -m "not slow"
    - name: Run Data Quality Tests
      run: pytest test/data_quality -v
    - name: Run Integration Tests
      run: pytest test/integration -v -m "not network"
    - name: Generate Coverage Report
      run: pytest test/unit test/integration test/data_quality --cov=data_collection --cov-report=xml
```

## 数据质量检查清单

每次数据采集完成后运行：

- [ ] **字段完整性**：所有必需字段存在且无空值
- [ ] **日期连续性**：交易日无异常断点
- [ ] **价格逻辑**：OHLC 关系正确，价格 > 0
- [ ] **成交量验证**：成交量 > 0，数量级合理
- [ ] **唯一性约束**：无重复记录
- [ ] **范围覆盖**：所有目标股票都有数据
- [ ] **多源一致**：多数据源采集结果一致性检查

## 测试审查清单

- [ ] 新增功能是否包含对应单元测试？
- [ ] 数据验证规则是否全部覆盖？
- [ ] 异常处理分支是否测试？
- [ ] 多数据源一致性是否验证？
- [ ] 数据完整性检查是否通过？
- [ ] 测试是否可以在隔离环境中运行？
- [ ] 测试是否依赖外部网络？（应尽量 mock）
- [ ] 测试执行时间是否在合理范围？
- [ ] 测试数据是否可在 fixture 中复用？
