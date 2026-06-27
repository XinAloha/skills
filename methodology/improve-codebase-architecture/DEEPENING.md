# Deepening - 深化方法论

如何在已知依赖的前提下，**安全地**深化一组浅模块。沿用 [LANGUAGE.md](LANGUAGE.md) 的术语：**module / interface / seam / adapter**。

## 依赖类别

评估深化候选时，先把它的依赖归类。类别决定深化模块如何跨 seam 测试。

### 1. In-process（进程内）

纯计算、内存状态、无 I/O。**永远可深化**——合并模块、直接通过新接口测。**不需要 adapter**。

> 本项目示例：`normalize_kline` 把 raw DataFrame 转标准 schema——无 I/O，可直接深化。

### 2. Local-substitutable（本地可替代）

依赖有本地测试替身（SQLite 替代 PostgreSQL、内存 FS 替代真 FS）。**替身存在则可深化**。深化模块用替身在测试套件内运行。**Seam 是内部的**，不在模块外部接口上。

> 本项目示例：数据库写入用 SQLite + tmp_path 替代生产 PostgreSQL。

### 3. Remote but owned（远程但自有）—— Ports & Adapters

你自己的服务跨网络（微服务、内部 API）。在 seam 处定义 **port**（接口）。深模块拥有逻辑；传输作为 **adapter** 注入。测试用内存 adapter，生产用 HTTP/gRPC/队列 adapter。

> 本项目暂无此类（单进程 Python 应用），但若未来引入 worker 队列、gRPC 数据网关，则按此模式。

建议形状：「在 seam 处定义 port，生产实现一个 HTTP adapter，测试实现一个内存 adapter，让逻辑住在一个深模块里——哪怕部署上跨网络」。

### 4. True external（真外部）—— Mock

第三方服务（Tushare、AKShare、adata 等你不控制的）。深化模块以注入 port 接收外部依赖；测试给 mock adapter。

> 本项目主要场景：所有外部数据源都属于这一类。

## Seam 纪律

- **一个 adapter = 假想 seam；两个 adapter = 真 seam**。除非至少有两个 adapter 能被合理化（典型是生产 + 测试），不要引入 port。**单 adapter 的 seam 只是绕弯**。
- **内部 seam vs 外部 seam**。深模块可以有内部 seam（私有于实现、自己测试用）和外部 seam（接口处）。**不要因为测试用了就把内部 seam 暴露到接口**。

## 测试策略：替换，不要叠加

- 深化模块的接口测试一旦存在，**老的浅模块单元测试就变成废物——删掉**。
- 在深化模块的接口处写新测试。**接口就是测试面**。
- 测试断言**通过接口可观察的结果**，不断言内部状态。
- 测试要在内部重构后存活——它们描述行为，不描述实现。如果测试在实现变化时必须改，它在测**接口之外**的东西。
