# HTML Report 格式

架构评审渲染为**单一自包含 HTML 文件**，放在操作系统 temp 目录。Tailwind 与 Mermaid 都来自 CDN。Mermaid 处理图状关系图；手写 div 与 inline SVG 处理更编辑感的视觉（mass diagram、横截面）。**两者混用**——别全靠 Mermaid，最后会显得套模板。

## 脚手架

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <title>架构评审 — {{repo name}}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
      mermaid.initialize({ startOnLoad: true, theme: "neutral", securityLevel: "loose" });
    </script>
    <style>
      .seam { stroke-dasharray: 4 4; }
      .leak { stroke: #dc2626; }
      .deep { background: linear-gradient(135deg, #0f172a, #1e293b); }
    </style>
  </head>
  <body class="bg-stone-50 text-slate-900 font-sans">
    <main class="max-w-5xl mx-auto px-6 py-12 space-y-12">
      <header>...</header>
      <section id="candidates" class="space-y-10">...</section>
      <section id="top-recommendation">...</section>
    </main>
  </body>
</html>
```

## Header

repo 名、日期、紧凑的 legend：实线框 = 模块，虚线 = seam，红色箭头 = 泄漏，加粗深色框 = 深模块。**不要写引言段落**——直接进入候选。

## 候选卡

图扛主要重量。文字稀疏、平实，自然使用 [LANGUAGE.md](LANGUAGE.md) 的术语。

每个候选一个 `<article>`：

- **Title** —— 短，命名深化（如「合并采集器入口管线」）。
- **Badge row** —— 推荐强度（`Strong` = emerald、`Worth exploring` = amber、`Speculative` = slate），依赖类别 tag（`in-process` / `local-substitutable` / `ports & adapters` / `mock`）。
- **Files** —— 等宽列表，`font-mono text-sm`。
- **Before / After 对比图** —— 中心元素。两列并排。
- **Problem** —— 一句话。哪里痛。
- **Solution** —— 一句话。改成什么样。
- **Wins** —— bullet，每条 ≤ 6 个词，如「测试碰一个接口」「定价逻辑停止泄漏」「删 4 个浅 wrapper」。
- **ADR callout**（如适用）—— 一行 amber 警示框。

**不要**段落式说明。如果图需要一段文字才能看懂，**重画图**。

## 图表模式

按候选挑一个。混用。**不要让每张图都长一样**。

### Mermaid graph（依赖 / 调用流的主力）

「X 调 Y 调 Z，看这一坨」用 `flowchart` / `graph`。Tailwind 卡片包一下，避免空降感。`classDef` 标红泄漏边、加深深模块。时序图适合"前：6 次往返；后：1 次"。

```html
<div class="rounded-lg border border-slate-200 bg-white p-4">
  <pre class="mermaid">
    flowchart LR
      A[TushareCollector] --> B[normalize_kline]
      B --> C[DailyKlineWriter]
      C -.leak.-> D[AdjFactorClient]
      classDef leak stroke:#dc2626,stroke-width:2px;
      class C,D leak
  </pre>
</div>
```

### 手画盒箭头（Mermaid 排版打架时用）

模块为带边框的 `<div>`。箭头为 inline SVG `<line>` / `<path>` 绝对定位。"after"图想让一个深模块以厚边框 + 灰化内部呈现时——Mermaid 渲染不出那个分量。

### 横截面（适合分层浅化）

水平条带（`h-12 border-l-4`）画一次调用经过的层。前：6 条薄层啥都不干。后：1 条厚层标着合并后的责任。

### Mass diagram（适合"接口与实现等宽"）

每个模块两个矩形——一个接口面积、一个实现面积。前：接口矩形几乎与实现矩形等高（浅）。后：接口矩形矮、实现矩形高（深）。

### Call-graph collapse

前：嵌套盒子表示调用树。后：树合并为一个盒子，原本的内部调用以淡化形式显示。

## 风格

- 编辑感 > 公司 dashboard 感。留白慷慨。Heading 可选 serif（`font-serif` 配 stone/slate 不错）。
- 颜色克制：一个 accent（emerald 或 indigo）+ 红色（泄漏）+ amber（警告）。
- 图保持约 320px 高，前后并排时不需要滚动。
- 模块标签用 `text-xs uppercase tracking-wider`——让它们读起来像 schematic，不像 UI。
- 唯一脚本是 Tailwind CDN 与 Mermaid ESM。报告其余完全静态——没有应用代码、没有除 Mermaid 自身渲染外的交互。

## Top recommendation 段

一张更大的卡。候选名 + 一句话理由 + 锚链接。完。

## 用词

平实英文 / 中文，但**架构名词与动词直接来自 [LANGUAGE.md](LANGUAGE.md)**。简练不是漂移的借口。

**严格使用**：module、interface、implementation、depth、deep、shallow、seam、adapter、leverage、locality（这些可保留英文，不必强译）。

**永不替换**：component / service / unit（替 module）；API / signature（替 interface）；boundary（替 seam）；layer / wrapper（替 module，当你指模块时）。

**符合风格的措辞**：

- "采集器入口模块是浅的——接口几乎和实现等宽"。
- "复权调整在 seam 处泄漏"。
- "深化：一个接口，一个测试位置"。
- "两个 adapter 撑起这个 seam：生产 HTTP，测试内存"。

**Wins bullets** 用术语命名收益：「locality：bug 集中在一个模块」、「leverage：一个接口，N 个调用点」、「接口收缩；实现吸收 wrapper」。**不要写**「更易维护」、「代码更干净」——这些词不在术语表里，不配。

不要含糊、不要清嗓子、不要"值得一提的是…"。能写成 bullet 就写 bullet。能砍就砍。词不在 [LANGUAGE.md](LANGUAGE.md)，先想想怎么用现有词，再考虑新词。
