# Interface Design - 备选接口设计

用户为某个深化候选探索备选接口时，用这个**并行 sub-agent 模式**。基于 Ousterhout 的 "Design It Twice" —— 你的第一个想法多半不是最好的。

沿用 [LANGUAGE.md](LANGUAGE.md) 词汇：**module / interface / seam / adapter / leverage**。

## 流程

### 1. 框定问题空间

派 sub-agent 之前，写一份**面向用户**的问题空间说明：

- 新接口需要满足的约束。
- 它会依赖哪些依赖、属于哪个类别（见 [DEEPENING.md](DEEPENING.md)）。
- 一段粗略的代码草图，把约束**具体化**——不是提案，只是让约束可触摸。

把这个给用户看，**立即进入第 2 步**。用户在读、在想，sub-agent 在并行干活。

### 2. 派 sub-agent

用 Agent 工具并行派 **3 个或更多** sub-agent。每个产出**根本不同**的接口形状。

每个 sub-agent 的 brief 独立（文件路径、耦合细节、依赖类别、seam 后是什么），与第 1 步对用户的说明分开。给每个 agent **不同的设计约束**：

- Agent 1: 「最小化接口——目标 1-3 个入口点。**最大化每入口点的杠杆**」。
- Agent 2: 「最大化灵活——支持多用例、可扩展」。
- Agent 3: 「为最常见调用方优化——让默认情况一行代码」。
- Agent 4（如适用）：「围绕 ports & adapters 设计跨 seam 依赖」。

把 [LANGUAGE.md](LANGUAGE.md) 的架构词汇 + `CONTEXT.md` 的领域词汇都包含到 brief，让每个 agent 命名都一致。

每个 sub-agent 输出：

1. **接口**（类型、方法、参数 —— 加不变量、顺序、错误模式）。
2. **使用示例** —— 调用方怎么用。
3. **接口背后藏什么** —— seam 后面的实现概要。
4. **依赖策略与 adapter** —— 见 [DEEPENING.md](DEEPENING.md)。
5. **取舍** —— 哪里杠杆高、哪里薄。

### 3. 展示与对比

**逐个**展示设计，让用户消化每一个，然后用文字对比。从 **depth（接口处的杠杆）**、**locality（变更集中处）**、**seam 位置** 三个维度对照。

对比之后给**你自己的推荐**：你认为哪个最强、为什么。如果不同设计的元素可以组合，提议混合方案。**要有立场**——用户要的是有力的判断，不是菜单。

## 本项目示例（启动器）

「采集器入口」深化候选的 3 种备选：

- **A 最小接口**：`Collection.run(symbol, start, end)` → 内部决定数据源、字段、写入。
- **B 最大灵活**：`CollectionPipeline().with_source(...).with_normalizer(...).with_writer(...).run()` → 链式构建。
- **C 最常见路径**：`fetch_and_store_daily(symbol)` 直函数 → 一行解决 80% 的日常调用。

对比维度：

- depth：A 最深；B 接口宽；C 接口最小但内部假设最多。
- locality：A 修改集中；B 修改分散到多个 builder；C 介于其间。
- seam：A 默认 mock 整个 Collection；B 可换 source / normalizer / writer 任一；C 只能 mock 函数本身。
