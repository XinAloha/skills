---
description: 文档规范 - 代码注释、核心功能文档、CHANGELOG
type: sub-document
parent: dev-guidelines.md
auto_execution_mode: 2
---

# 文档规范

## 核心功能文档 (`docs/core_features.md`)

**规则**：每个核心功能的变更必须被记录，方便后续查看变动。

| 场景 | 操作 |
|------|------|
| **修改现有核心功能** | 在 `docs/core_features.md` 对应功能下追加改动摘要 |
| **新增核心功能** | 在 `docs/core_features.md` 中新建一个 Feature 区块，写明模块、描述、变更详情 |
| **README 同步** | 任何功能变更后，检查 `README.md` 的目录树、技术栈、核心功能列表是否过期 |

### 核心功能定义

以下模块/能力属于"核心功能"，变更时必须更新文档：

- **数据采集**：股票列表、日K线、概念板块、复权因子
- **数据源适配**：主源(adata/akshare)、备用源(Tushare)、降级采集器
- **并发与限流**：ThreadPoolExecutor、Semaphore 限速
- **重试与容错**：指数退避重试、多源降级、配置系统
- **数据库**：表结构、inspector、SQLAlchemy ORM
- **任务调度**：daily_job 全量/增量/扩展模式
- **配置管理**：集中配置系统、环境变量覆盖
- **安全机制**：Token 管理、.gitignore、mock 测试

## 代码注释

```python
def collect_daily_kline(
    self,
    stock_code: str,
    start_date: Optional[str] = None,
    adjust_type: int = 1
) -> int:
    """
    采集单只股票的日K数据

    Args:
        stock_code: 股票代码，如 '000001'
        start_date: 开始日期，格式 'YYYY-MM-DD'，默认从数据库最新日期开始
        adjust_type: 复权类型
            - 0: 不复权
            - 1: 前复权（默认）
            - 2: 后复权

    Returns:
        采集到的记录数

    Raises:
        NetworkError: 网络请求失败
        ValidationError: 返回数据格式错误

    Example:
        >>> collector = StockDataCollector('sqlite:///test.db')
        >>> count = collector.collect_daily_kline('000001', '2024-01-01')
        >>> print(f"采集了 {count} 条记录")
    """
```

## 变更日志 (CHANGELOG.md)

```markdown
## [Unreleased]

### Added
- 新增北交所股票数据采集支持
- 新增并发采集模式，速度提升 5x

### Changed
- 重构采集器使用策略模式
- 优化数据库初始化逻辑

### Fixed
- 修复 92xxx 股票字段映射错误
```
