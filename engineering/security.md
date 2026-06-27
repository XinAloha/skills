---
description: 项目安全机制 - 密钥管理、敏感信息保护、安全配置规范
auto_execution_mode: 2
---

# 项目安全机制规范

> **核心原则**：密钥绝不以明文形式硬编码在代码中，绝不提交到版本控制。

## 1. 密钥管理优先级

按优先级从高到低选择配置方式：

| 优先级 | 方式 | 适用场景 | 示例 |
|--------|------|---------|------|
| 1 | 环境变量 | 生产环境 / CI/CD | `TUSHARE_TOKEN=xxx` |
| 2 | `.env` 文件 | 本地开发 | `TUSHARE_TOKEN=xxx` |
| 3 | 运行时传入 | 临时测试 / 脚本参数 | `TushareDataClient(token="xxx")` |
| 禁止 | 硬编码 | 任何场景 | `token = "abc123"` |

## 2. .env 文件规范

### 文件位置
项目根目录创建 `.env`：

```bash
# .env
TUSHARE_TOKEN=your_token_here
DB_PASSWORD=your_db_password
```

### 必须加入 .gitignore
```gitignore
# 敏感配置文件
.env
.env.local
.env.*.local
config.ini
config.json
secrets.json
credentials.json
*.key
*.pem
```

### 加载方式
```python
# 自动加载（推荐）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 读取
token = os.environ.get('TUSHARE_TOKEN')
```

## 3. 代码实现规范

### Token 解析顺序
```python
@staticmethod
def _resolve_token() -> Optional[str]:
    """按优先级解析 Token (环境变量 > .env)"""
    return os.environ.get('TUSHARE_TOKEN')

def __init__(self, token: Optional[str] = None):
    self.token = token or self._resolve_token()
```

### 未配置时的友好提示
```python
def _ensure_token(self) -> str:
    if not self.token:
        raise ValueError(
            "Tushare Token 未配置。请按以下任一方式配置:\n"
            "  1. 环境变量: export TUSHARE_TOKEN=your_token\n"
            "  2. .env 文件: 在项目根目录创建 .env\n"
            "  3. 直接传入: TushareDataClient(token='your_token')\n"
            "获取 Token: https://tushare.pro/register"
        )
    return self.token
```

### 数据库连接信息
```python
# 错误示例（绝对禁止）
DB_URL = "postgresql://admin:password123@localhost/stock_db"

# 正确示例
DB_URL = os.environ.get('DATABASE_URL', 'sqlite:///stock_data.db')
```

## 4. 测试安全规范

### 必须使用 Mock
```python
def test_api_call(self):
    client = TushareDataClient(token="dummy")  # 测试专用假token
    mock_pro = Mock()
    with patch.object(client, "_get_pro_api", return_value=mock_pro):
        df = client.get_daily_prices(...)
```

### 禁止在测试中打印真实密钥
```python
# 错误
def test_token(self):
    print(os.environ['TUSHARE_TOKEN'])  # 泄漏风险

# 正确
def test_token(self):
    assert os.environ.get('TUSHARE_TOKEN') is not None
```

## 5. Git 提交前检查清单

```bash
# 运行检查脚本（推荐集成到 pre-commit）
git add -N .
git diff --cached --name-only | grep -E "\.(py|json|ini|yaml|yml|md)$" | xargs grep -n -i -E "(token|password|secret|key|api_key)" | grep -v "mock\|test\|#\|\.env\|example"
```

### 手动检查项
- [ ] `.env` 是否在 `.gitignore` 中？
- [ ] 代码中是否存在硬编码的 URL/密码/Token？
- [ ] 配置文件中是否包含敏感信息？
- [ ] 日志中是否可能打印敏感数据？
- [ ] 错误信息中是否包含连接字符串？

## 6. CI/CD 安全

### GitHub Actions 示例
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      TUSHARE_TOKEN: ${{ secrets.TUSHARE_TOKEN }}
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: pytest
```

### Secrets 命名规范
- `TUSHARE_TOKEN` - 数据源 Token
- `DATABASE_URL` - 数据库连接串
- `SMTP_PASSWORD` - 邮件密码

## 7. 密钥泄露应急处理

1. **立即重置 Token**：到对应平台（如 Tushare）重置 Token
2. **检查提交历史**：`git log --all --source --remotes --oneline -- .env`
3. **强制推送清理后的历史**（如已推送到远程，需配合平台通知）
4. **轮换所有相关密码**
5. **审查日志和监控**：确认泄露范围和影响

## 8. 新项目初始化检查

每次创建新数据源适配器时，执行以下步骤：

1. 实现 `_resolve_token()` 静态方法
2. 在 `__init__` 中支持 `token: Optional[str] = None` 参数
3. 添加 `try/except` 的 `.env` 加载逻辑
4. 在 `.gitignore` 中排除相关敏感文件
5. 编写测试时使用 mock，不依赖真实 API
6. 在 `docs/` 中添加配置指南（如 `tushare_setup.md`）
