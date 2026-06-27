# UI Prototype - UI 原型

在**单一路由上**生成几个**根本不同**的 UI 变体，从 floating bottom bar 切换。用户在浏览器里翻看，挑一个（或从每个偷点东西），其他扔掉。

> 本项目主要是 Python 后端，UI 原型场景较少。仅在以下情况启用：**回测可视化前端、数据质量看板、监控面板** 等需要面向用户的视图。技术栈通常是 **Streamlit / Dash / FastAPI + Jinja2**。

如果问题是关于**逻辑 / 状态而不是外观** —— 错分支。用 [LOGIC.md](LOGIC.md)。

## 适用场景

- "这个页面应该长什么样？"
- "我想看几个 dashboard 选项再做决定。"
- "试试 settings 页面的另一种布局。"

## 两个子形状 —— 强烈优先 A

UI 原型在**贴着应用其余部分**时才好判断——真实 header、真实 sidebar、真实数据、真实密度。**单独的 throwaway 路由是真空**：每个变体单看都还行。**默认子形状 A**，除非确实没有合理 host 页面才用 B。

### 子形状 A —— 在已有页面上调整（首选）

路由已存在。变体在**同一路由上**渲染，由 URL search param `?variant=` gate。已有的数据获取、参数、认证全部保留——**只换渲染部分**。

新东西没页面但**自然属于某个页面内**（dashboard 新区块、settings 新卡片、流程新一步）—— **仍是子形状 A**。把变体挂到 host 页面里。

### 子形状 B —— 新页面（最后手段）

只有当原型化的东西**没有任何已有页面可挂**——比如全新顶层界面、无法嵌入的流程——才用。

按项目已有路由约定建一个 throwaway 路由——**不要发明新顶层结构**。命名要明显是原型（路径或文件名包含 `prototype`）。同样用 `?variant=`。

子形状 B 之前 sanity-check：**真的没有现存页面能嵌进去吗？** 空路由会掩盖被填满的页面会暴露的设计问题。

两个子形状里 floating bar 完全一样。

## 流程

### 1. 写下问题、选 N

**默认 3 个变体**。超过 5 就不再是"根本不同"，开始变 noise——封顶。

写一行计划，原型位置或文件顶部注释：

> "Settings 页面的 3 个变体，通过 `?variant=` 切换，挂在已有的 `/settings` 路由上。"

### 2. 生成根本不同的变体

每个变体：

- 紧扣页面目的与可用数据。
- 用项目组件库 / 样式系统（Tailwind、Streamlit 组件、Dash 等）。
- 显式导出组件名 `VariantA` / `VariantB` / `VariantC`。

变体必须**结构性不同**——不同布局、不同信息层次、不同主操作位置，**不只是颜色**。三个微调的 card grid 不是 UI 原型，是壁纸。如果两个草稿出来太像，用「不要用 card grid」明示重做一个。

### 3. 接起来

路由上一个 switcher 组件。

```python
# Streamlit 示例
variant = st.query_params.get("variant", "A")
if variant == "A":
    render_variant_a(data)
elif variant == "B":
    render_variant_b(data)
elif variant == "C":
    render_variant_c(data)
render_prototype_switcher(["A", "B", "C"], current=variant)
```

子形状 A：所有数据获取留在 switcher 之上；只有渲染子树随变体变。
子形状 B：throwaway 路由 `/prototype/<name>` 上挂同一个 switcher。

### 4. floating switcher

页面底部居中固定小条，三块：

- **左箭头** —— 切前一个变体（环回）。
- **变体标签** —— 显示 key + 变体名（如 `B — Sidebar layout`）。
- **右箭头** —— 切下一个（环回）。

行为：

- 点击箭头更新 URL search param（用框架 router）—— 变体可分享、reload 稳定。
- 键盘 `←` `→` 同样切换。**`<input>` / `<textarea>` / `[contenteditable]` 聚焦时不要拦截方向键**。
- 视觉上和页面分离（高对比 pill、浅阴影），明显不是被评估的设计的一部分。
- **生产构建中隐藏**——gate 在 `os.environ.get("ENV") != "production"` 等等价检查上，避免误合到 prod。

把 switcher 放在共享 UI 组件位置，让两个子形状都能复用。

### 5. 交付

把 URL（和 `?variant=` keys）告诉用户。他们什么时候有空什么时候翻。**最有价值的反馈通常是：「我想要 B 的 header + C 的 sidebar」**——那才是他们真正想要的设计。

### 6. 捕获答案、清理

某变体胜出后，写下哪一个、为什么（commit、ADR、issue 或原型旁 `NOTES.md`）。然后：

- **子形状 A** —— 删掉落选变体和 switcher；把胜者折回已有页面。
- **子形状 B** —— 把胜者升级为真路由，删 throwaway 路由和 switcher。

**不要让变体组件和 switcher 留在 repo 里**。它们腐烂得很快，会让下一个读代码的人困惑。

## 反模式

- **变体只换颜色或文案**。那是微调，不是原型。**真变体在结构上有分歧**。
- **变体之间共享太多代码**。共享 `<Header>` 行，共享 `<Layout>` 就违背了目的。每个变体都该自由扔掉布局。
- **变体接真实写操作**。只读原型没问题。变体要写就指向 stub——问题是"长什么样"，不是"后端能不能跑"。
- **直接把原型推到生产**。变体代码是按原型约束写的（无测试、最简错误处理）。**折回时重写**。
