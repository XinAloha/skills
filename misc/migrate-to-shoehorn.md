---
description: 测试中类型断言治理（Python 改写参考） - 上游为 TS shoehorn，本文件作 Python 项目类比
type: misc
parent: dev-guidelines.md
auto_execution_mode: 2
source: Matt Pocock skills - misc/migrate-to-shoehorn（TS 专属，已改写为 Python 类比参考）
adapted-for: A 股量化数据采集系统 (Python / pytest / PostgreSQL)
---

# Migrate to Shoehorn —— Python 类比参考

> **改写说明**：原 Matt Pocock skill 是把 TS 测试中的 `as` 断言迁移到 `@total-typescript/shoehorn`。**本项目是 Python，没有直接对应物**。本文件保留作为类比参考，让团队理解其背后的"测试中类型治理"思想，并给出 Python 等价做法。

## 原 skill 解决的问题

TS 中测试想传"部分数据"时，常用 `as Type` / `as unknown as Type` 强制类型——这会绕过类型检查、误导未来读者、丢失自动补全。`shoehorn` 提供 `fromPartial()` / `fromAny()` / `fromExact()`，让"部分数据"也能类型安全地传。

## Python 中等价的痛点

Python 类型系统更弱，但相同的"测试中传部分数据"问题存在：

```python
# 测试只关心 body.id，但被迫构造完整 Request
def test_get_user():
    req = Request(
        body={"id": "123"},
        headers={},
        cookies={},
        method="GET",
        path="/users/123",
        # ... 还要填 20 个字段
    )
    get_user(req)
```

## Python 等价做法

### 1. dataclass + field defaults

让 dataclass 字段有默认值，测试只覆盖关心的：

```python
from dataclasses import dataclass, field

@dataclass
class Request:
    body: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    method: str = "GET"
    path: str = "/"

# 测试
req = Request(body={"id": "123"})
```

### 2. pydantic + 默认值 + 严格模式

```python
from pydantic import BaseModel, ConfigDict

class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: dict = {}
    headers: dict = {}
    method: str = "GET"
```

### 3. factory_boy / pytest fixtures 工厂

测试数据用 factory，关心的字段单独覆盖：

```python
import factory

class RequestFactory(factory.Factory):
    class Meta:
        model = Request
    body = factory.LazyFunction(dict)
    headers = factory.LazyFunction(dict)
    method = "GET"

# 测试
req = RequestFactory(body={"id": "123"})
```

### 4. typing.cast + TypedDict（最接近 shoehorn 的形态）

```python
from typing import TypedDict, cast

class RequestPartial(TypedDict, total=False):
    body: dict
    headers: dict

def test_get_user():
    partial: RequestPartial = {"body": {"id": "123"}}
    get_user(cast(Request, partial))  # 类似 fromPartial，但显式 cast
```

## 何时考虑

- 测试 setup 出现大量"凑数据"代码，掩盖测试本意。
- DataClass 字段多、变更频繁，测试每次都要更新。
- 想让测试只"显式声明它在意的字段"。

## 何时**不要**

- 生产代码里——绝对不要用 cast 绕过类型，等同 TS 中的 `as`。
- 简单测试——直接构造完整对象更清晰。
- 已经有 `pydantic` / `dataclass` 默认值能解决的问题。

## 与本项目的关系

本项目主要数据载体是 `pandas.DataFrame`，不是强类型对象。**测试中"部分数据"问题表现为**：

- 在测试 fixture 里要造 50 列的完整 daily_kline DataFrame，但测试只关心 close 与 volume。
- **本项目推荐做法**：用 `pd.DataFrame.from_records()` 配合 `pytest fixture`，让 fixture 提供"满字段空 DataFrame 模板"，测试用 `df.assign(close=..., volume=...)` 覆盖关心的列。

## 相关 skill

- [test-strategy](../testing/test-strategy.md) - 测试策略
- [collector-testing](../testing/collector-testing.md) - 采集器测试模板
- [code-style](../engineering/code-style.md) - 类型注解约定
