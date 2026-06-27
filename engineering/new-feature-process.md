---
description: 新功能开发完整流程 - 开发步骤、测试规范
type: sub-document
parent: dev-guidelines.md
auto_execution_mode: 2
---

# 新功能开发完整流程

## 开发前准备

1. **明确需求**：功能目标、数据来源、存储表结构、更新频率
2. **设计评审**：是否符合 SOLID 原则？是否复用现有采集器模式？异常处理是否完善？

## 开发步骤

```
Step 1: 创建采集器模块（collectors/）
   └── 实现核心采集逻辑
   └── 添加异常处理
   └── 添加类型注解

Step 2: 集成到 StockDataCollector（core/）
   └── 添加 public API 方法
   └── 实现入库逻辑
   └── 添加去重机制

Step 3: 添加任务调度（daily_job.py）
   └── 新增 mode 选项
   └── 实现任务函数
   └── 添加进度显示

Step 4: 编写测试（test/）
   ├── unit/                    # 单元测试（必须）
   │   ├── test_xxx_collector.py
   │   └── 覆盖正常/异常/边界情况
   └── integration/             # 集成测试（必须）
       └── test_xxx_integration.py

Step 5: 更新文档
   ├── README.md
   ├── FEATURES.md
   └── requirements.txt

Step 6: 运行测试
   └── pytest test/unit/test_xxx_collector.py -v
   └── pytest test/integration/test_xxx_integration.py -v
   └── 确保所有测试通过
```

## 测试覆盖率要求

| 类型 | 覆盖率 | 说明 |
|------|--------|------|
| **单元测试** | ≥ 90% | 核心采集逻辑、异常处理 |
| **集成测试** | ≥ 70% | 数据库操作、数据流完整链路 |
| **异常分支** | 100% | 所有错误处理路径必须测试 |

## 测试文件命名规范

| 被测模块 | 单元测试文件 | 集成测试文件 |
|----------|-------------|-------------|
| `xxx_collector.py` | `test/unit/test_xxx_collector.py` | `test/integration/test_xxx_integration.py` |
| `daily_job.py` 新增功能 | `test/unit/test_daily_job.py` | `test/integration/test_job_integration.py` |

## 测试用例清单（每个新功能必须包含）

```python
# 单元测试必含用例
class TestXXXCollector:
    def test_init(self)                          # 初始化测试
    def test_success_case(self)                  # 正常采集
    def test_empty_data(self)                    # 空数据处理
    def test_api_error(self)                     # API 错误处理
    def test_network_error(self)                 # 网络错误
    def test_data_validation(self)               # 数据验证
    def test_duplicate_handling(self)            # 重复数据处理

# 集成测试必含用例
class TestXXXIntegration:
    def test_table_schema(self)                  # 表结构验证
    def test_insert_data(self)                   # 数据插入
    def test_unique_constraint(self)             # 唯一约束
    def test_data_flow(self)                     # 完整数据流
```

## 依赖处理

测试文件必须使用**条件导入**，避免未安装依赖时失败：

```python
try:
    from data_collection.collectors import XXXCollector
    HAS_XXX_COLLECTOR = True
except ImportError:
    HAS_XXX_COLLECTOR = False
    XXXCollector = None

@pytest.mark.skipif(not HAS_XXX_COLLECTOR, reason="模块未安装")
@pytest.mark.unit
class TestXXXCollector:
    """测试类"""
    pass
```
