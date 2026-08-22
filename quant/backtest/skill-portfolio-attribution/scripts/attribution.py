"""组合绩效归因核心实现。

Brinson-Fachler 行业归因（单期 + Carino 多期几何链接）+ 基于横截面回归的因子归因。
框架中立：输入为 parquet/csv 长表，不依赖任何回测框架。

关键设计（相较早期版本的修正）：
- 重复主键校验：权重/收益表中出现重复的 (date, symbol) 直接报错，不静默重复计权；
- 零权重行业 NaN 防护：某行业在组合与基准中权重均为 0 时，其收益率填 0，
  三项效应恒为 0，不产生 NaN 混入报告；
- 因子归因与行业归因口径一致：因子贡献同样用 Carino 系数逐期缩放并在全域上计算，
  因此因子面板合计 ≡ 行业面板合计 ≡ 区间主动收益（三者对同一总账）。

输入数据约定（长表，列名固定）：
- 组合权重   [date, symbol, weight]   期初权重，每日加总应为 1
- 基准权重   [date, symbol, weight]   期初权重，每日加总应为 1
- 个股收益   [date, symbol, ret]      当期收益（与权重同期对齐）
- 行业分类   [symbol, sector]
- 因子暴露   [date, symbol, <因子列...>]（可选，宽表）

用法：
    python attribution.py \
        --portfolio p.parquet --benchmark b.parquet \
        --returns r.parquet --sectors s.csv \
        [--exposures e.parquet] [--out report_dir]
"""

import argparse
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd

WEIGHT_SUM_TOL = 1e-4      # 每日权重加总允许偏离 1 的幅度
IDENTITY_TOL = 1e-8        # 归因恒等式残差容忍度
MAX_ABS_RETURN = 0.21      # 日收益合理性阈值：A股主板±10%/创业板科创板±20%，超过多为脏数据

EFFECT_COLS = ["allocation", "selection", "interaction"]
STR_COLS = ("date", "symbol", "sector")


# 自包含 HTML 报告模板：内联 SVG + CSS + JS，零外部依赖、离线可用、明暗自适应。
# 占位符由 render_html() 用 str.replace 填充（不用 f-string，避免与 CSS/JS 的 {} 冲突）。
# 配色沿用 QuantSkills 一贯的暖中性 + 红涨绿跌（红=正贡献/加分，绿=负贡献/减分）。
_HTML_REPORT_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root{
    --ground:#f6f3ec;--surface:#fffdf8;--surface-2:#f0ebe0;
    --ink:#23201a;--ink-2:#6b655a;--ink-3:#9a9284;
    --hair:rgba(35,32,26,.12);--hair-strong:rgba(35,32,26,.26);
    --pos:#c0392b;--neg:#147d6f;--accent:#a9791f;--accent-soft:rgba(169,121,31,.12);
    --shadow:0 1px 2px rgba(35,32,26,.06),0 6px 20px rgba(35,32,26,.05);
  }
  @media (prefers-color-scheme:dark){:root{
    --ground:#17150f;--surface:#201d16;--surface-2:#2a261d;
    --ink:#ece7db;--ink-2:#a9a293;--ink-3:#746d5e;
    --hair:rgba(236,231,219,.12);--hair-strong:rgba(236,231,219,.24);
    --pos:#e15b4c;--neg:#2aa697;--accent:#d6a94a;--accent-soft:rgba(214,169,74,.14);
    --shadow:0 1px 2px rgba(0,0,0,.3),0 6px 22px rgba(0,0,0,.35);
  }}
  *{box-sizing:border-box}
  body{margin:0;background:var(--ground);color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei","Segoe UI","Noto Sans CJK SC",system-ui,sans-serif;
    line-height:1.6;font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
  .wrap{max-width:920px;margin:0 auto;padding:40px 24px 64px}
  .eyebrow{font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);font-weight:600;margin:0 0 8px}
  h1{font-size:clamp(24px,4vw,32px);font-weight:700;margin:0 0 6px;letter-spacing:-.01em;text-wrap:balance}
  .meta{color:var(--ink-2);font-size:14px;margin:0}
  .meta b{color:var(--ink);font-weight:600}
  /* hero 三大数 */
  .hero{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:26px 0 8px}
  .tile{background:var(--surface);border:1px solid var(--hair);border-radius:14px;box-shadow:var(--shadow);padding:18px 20px}
  .tile .lab{font-size:13px;color:var(--ink-3);margin:0 0 6px}
  .tile .num{font-size:clamp(22px,3.4vw,30px);font-weight:700;letter-spacing:-.01em}
  .tile.big{outline:2px solid var(--accent-soft)}
  .pos{color:var(--pos)}.neg{color:var(--neg)}
  section{margin-top:40px}
  .sec-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:6px;flex-wrap:wrap}
  h2{font-size:17px;font-weight:700;margin:0;letter-spacing:-.005em}
  .sec-note{font-size:13px;color:var(--ink-3);margin:0}
  .card{background:var(--surface);border:1px solid var(--hair);border-radius:14px;box-shadow:var(--shadow);padding:20px 20px 14px;margin-top:14px}
  .chart-scroll{overflow-x:auto}
  svg{display:block;width:100%;height:auto}
  .legend{display:flex;flex-wrap:wrap;gap:8px 20px;margin-top:10px;padding-top:12px;border-top:1px solid var(--hair);font-size:12.5px;color:var(--ink-2)}
  .legend .item{display:inline-flex;align-items:center;gap:7px}
  .sw{width:13px;height:13px;border-radius:3px;display:inline-block}
  .sw.pos{background:var(--pos)}.sw.neg{background:var(--neg)}
  #tip{position:fixed;pointer-events:none;z-index:20;opacity:0;transition:opacity .1s;background:var(--surface);color:var(--ink);
    border:1px solid var(--hair-strong);border-radius:10px;box-shadow:var(--shadow);padding:10px 12px;font-size:12.5px;max-width:260px;line-height:1.5}
  #tip .t-m{font-weight:700;margin-bottom:4px;font-size:13px}
  #tip .row{display:flex;justify-content:space-between;gap:16px;color:var(--ink-2)}
  #tip .row b{color:var(--ink);font-weight:600}
  .tbl-scroll{overflow-x:auto;margin-top:14px}
  table{border-collapse:collapse;width:100%;min-width:640px;font-size:13px}
  th,td{padding:8px 10px;text-align:right;white-space:nowrap}
  th{color:var(--ink-3);font-weight:600;font-size:12px;letter-spacing:.03em;border-bottom:1px solid var(--hair-strong)}
  td{border-bottom:1px solid var(--hair);color:var(--ink-2)}
  th:first-child,td:first-child{text-align:left}
  tbody tr:last-child td{border-top:1px solid var(--hair-strong);font-weight:700;color:var(--ink)}
  td.pos{color:var(--pos)}td.neg{color:var(--neg)}
  footer{margin-top:40px;padding-top:16px;border-top:1px solid var(--hair);font-size:12px;color:var(--ink-3);display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
  @media (max-width:620px){.hero{grid-template-columns:1fr}.wrap{padding:28px 16px 48px}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <p class="eyebrow">组合绩效归因 · Brinson-Fachler + Carino</p>
    <h1>主动收益从哪来</h1>
    <p class="meta" id="meta"></p>
  </header>

  <div class="hero" id="hero"></div>

  <section>
    <div class="sec-head"><h2>主动收益分解</h2><p class="sec-note">配置 → 选股 → 交互，逐步累加到主动收益</p></div>
    <div class="card"><div class="chart-scroll"><svg id="waterfall" viewBox="0 0 760 280" role="img" aria-label="主动收益瀑布分解"></svg></div></div>
  </section>

  <section>
    <div class="sec-head"><h2>行业贡献</h2><p class="sec-note">各行业对主动收益的合计贡献，按大小排序（红=加分 / 绿=减分）</p></div>
    <div class="card">
      <div class="chart-scroll"><svg id="sectors" role="img" aria-label="各行业贡献"></svg></div>
      <div class="legend">
        <span class="item"><span class="sw pos"></span>正贡献（加分）</span>
        <span class="item"><span class="sw neg"></span>负贡献（减分）</span>
        <span class="item">悬停看配置/选股/交互明细</span>
      </div>
    </div>
  </section>

  <section id="factor-sec" style="display:none">
    <div class="sec-head"><h2>因子归因</h2><p class="sec-note">主动收益按因子分解，残差为特质/选股收益（与行业面板对同一总账）</p></div>
    <div class="card"><div class="chart-scroll"><svg id="factors" role="img" aria-label="因子归因"></svg></div></div>
  </section>

  <section>
    <div class="sec-head"><h2>完整数据</h2><p class="sec-note">组合/基准权重 · 配置 · 选股 · 交互 · 合计</p></div>
    <div class="tbl-scroll"><table id="tbl"><thead><tr>
      <th>行业</th><th>组合权重</th><th>基准权重</th><th>配置</th><th>选股</th><th>交互</th><th>合计</th>
    </tr></thead><tbody></tbody></table></div>
  </section>

  <footer><span>由 skill-portfolio-attribution 生成</span><span>恒等式内建自证 · 各项加总 ≡ 主动收益</span></footer>
</div>
<div id="tip" aria-hidden="true"></div>
<script>
  const R = __DATA_JSON__;
  const SVGNS="http://www.w3.org/2000/svg";
  const el=(n,a={})=>{const e=document.createElementNS(SVGNS,n);for(const k in a)e.setAttribute(k,a[k]);return e;};
  const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const pct=(x,dp=2)=>(x>=0?"+":"")+(x*100).toFixed(dp)+"%";
  const pct0=x=>(x*100).toFixed(2)+"%";

  document.getElementById("meta").innerHTML =
    `区间 <b>${R.dateRange||"—"}</b> &nbsp;·&nbsp; <b>${R.periods}</b> 期 &nbsp;·&nbsp; ${R.method}`;

  // hero
  const hero=document.getElementById("hero");
  const tiles=[
    {lab:"组合收益 Rp",val:R.Rp},{lab:"基准收益 Rb",val:R.Rb},{lab:"主动收益",val:R.active,big:true}];
  hero.innerHTML=tiles.map(t=>
    `<div class="tile${t.big?' big':''}"><p class="lab">${t.lab}</p>`+
    `<div class="num ${t.val>=0?'pos':'neg'}">${pct(t.val)}</div></div>`).join("");

  const POS=()=>css("--pos"),NEG=()=>css("--neg"),ACC=()=>css("--accent"),
        HAIR=()=>css("--hair"),HAIRS=()=>css("--hair-strong"),INK=()=>css("--ink"),INK3=()=>css("--ink-3");
  const tip=document.getElementById("tip");
  const showTip=(e,html)=>{tip.innerHTML=html;tip.style.opacity=1;const r=tip.getBoundingClientRect();
    let px=(e.clientX||0)+14,py=(e.clientY||0)+14;
    if(px+r.width>innerWidth)px=e.clientX-r.width-14;if(py+r.height>innerHeight)py=e.clientY-r.height-14;
    tip.style.left=px+"px";tip.style.top=py+"px";};
  const hideTip=()=>{tip.style.opacity=0;};

  // 瀑布图：配置/选股/交互 累加 → 主动
  function waterfall(){
    const svg=document.getElementById("waterfall");svg.textContent="";
    const W=760,H=280,padL=48,padR=16,padT=24,padB=44,plotW=W-padL-padR,plotH=H-padT-padB;
    const e=R.effects,a=e.allocation,s=e.selection,i=e.interaction;
    const steps=[
      {label:"配置",val:a,from:0,to:a},
      {label:"选股",val:s,from:a,to:a+s},
      {label:"交互",val:i,from:a+s,to:a+s+i},
      {label:"主动收益",val:R.active,from:0,to:R.active,total:true}];
    const lv=[0];steps.forEach(st=>{lv.push(st.from,st.to);});
    const maxV=Math.max(...lv),minV=Math.min(...lv),span=(maxV-minV)||1e-9;
    const yOf=v=>padT+(maxV-v)/span*plotH;
    const band=plotW/steps.length,bw=Math.min(66,band*.5);
    // 0 轴
    const y0=yOf(0);
    svg.appendChild(el("line",{x1:padL,y1:y0,x2:W-padR,y2:y0,stroke:HAIRS(),"stroke-width":1.2}));
    steps.forEach((st,k)=>{
      const cx=padL+band*k+band/2,x=cx-bw/2;
      const yTop=yOf(Math.max(st.from,st.to)),h=Math.max(2,Math.abs(yOf(st.from)-yOf(st.to)));
      const col=st.val>=0?POS():NEG();
      const rect=el("rect",{x,y:yTop,width:bw,height:h,rx:4,fill:col,opacity:st.total?1:.9});
      if(st.total)rect.setAttribute("stroke",ACC()),rect.setAttribute("stroke-width",1.5);
      svg.appendChild(rect);
      // 连接虚线
      if(!st.total&&k<3){const yc=yOf(st.to);svg.appendChild(el("line",{x1:x+bw,y1:yc,x2:padL+band*(k+1)+band/2-bw/2,y2:yc,stroke:HAIR(),"stroke-dasharray":"3 3","stroke-width":1}));}
      const val=el("text",{x:cx,y:(st.val>=0?yTop-7:yTop+h+15),"text-anchor":"middle","font-size":12,"font-weight":700,fill:col});
      val.textContent=pct(st.val);svg.appendChild(val);
      const lab=el("text",{x:cx,y:H-padB+20,"text-anchor":"middle","font-size":13,fill:st.total?INK():INK3(),"font-weight":st.total?700:400});
      lab.textContent=st.label;svg.appendChild(lab);
    });
  }

  // 行业发散条
  function sectorsChart(){
    const svg=document.getElementById("sectors");svg.textContent="";
    const rows=R.sectors.slice().sort((x,y)=>y.total-x.total);
    const rowH=30,padL=88,padR=64,padT=10,padB=8,W=760;
    const plotW=W-padL-padR,H=padT+padB+rows.length*rowH;
    svg.setAttribute("viewBox",`0 0 ${W} ${H}`);
    const maxAbs=Math.max(1e-9,...rows.map(r=>Math.abs(r.total)))*1.15;
    const xz=padL+plotW/2,xOf=v=>xz+v/maxAbs*(plotW/2);
    svg.appendChild(el("line",{x1:xz,y1:padT,x2:xz,y2:H-padB,stroke:HAIRS(),"stroke-width":1.2}));
    rows.forEach((r,k)=>{
      const cy=padT+k*rowH+rowH/2,pos=r.total>=0,col=pos?POS():NEG();
      const x=pos?xz:xOf(r.total),w=Math.max(1.5,Math.abs(xOf(r.total)-xz));
      const bar=el("rect",{x,y:cy-8,width:w,height:16,rx:3,fill:col,"data-k":k,tabindex:0});
      bar.style.cursor="pointer";svg.appendChild(bar);
      const nm=el("text",{x:padL-10,y:cy+4,"text-anchor":"end","font-size":12.5,fill:INK()});
      nm.textContent=r.sector;svg.appendChild(nm);
      const vl=el("text",{x:pos?xOf(r.total)+6:xOf(r.total)-6,y:cy+4,"text-anchor":pos?"start":"end","font-size":12,"font-weight":600,fill:col});
      vl.textContent=pct(r.total);svg.appendChild(vl);
    });
    svg.querySelectorAll("rect[data-k]").forEach(b=>{
      const r=rows[+b.getAttribute("data-k")];
      const html=`<div class="t-m">${r.sector}</div>`+
        `<div class="row"><span>组合/基准权重</span><b>${pct0(r.wp)} / ${pct0(r.wb)}</b></div>`+
        `<div class="row"><span>配置</span><b>${pct(r.allocation)}</b></div>`+
        `<div class="row"><span>选股</span><b>${pct(r.selection)}</b></div>`+
        `<div class="row"><span>交互</span><b>${pct(r.interaction)}</b></div>`+
        `<div class="row"><span>合计</span><b>${pct(r.total)}</b></div>`;
      b.addEventListener("mousemove",e=>showTip(e,html));b.addEventListener("mouseleave",hideTip);
      b.addEventListener("focus",()=>{const bb=b.getBoundingClientRect();showTip({clientX:bb.left+bb.width/2,clientY:bb.top},html);});
      b.addEventListener("blur",hideTip);
    });
  }

  // 因子归因条形
  function factorsChart(){
    if(!R.factors){return;}
    document.getElementById("factor-sec").style.display="";
    const svg=document.getElementById("factors");svg.textContent="";
    const keys=Object.keys(R.factors).filter(k=>k!=="specific").concat(R.factors.specific!==undefined?["specific"]:[]);
    const rows=keys.map(k=>({name:k==="specific"?"特质/选股":k,val:R.factors[k]}));
    const rowH=30,padL=96,padR=64,padT=10,padB=8,W=760;
    const plotW=W-padL-padR,H=padT+padB+rows.length*rowH;
    svg.setAttribute("viewBox",`0 0 ${W} ${H}`);
    const maxAbs=Math.max(1e-9,...rows.map(r=>Math.abs(r.val)))*1.15;
    const xz=padL+plotW/2,xOf=v=>xz+v/maxAbs*(plotW/2);
    svg.appendChild(el("line",{x1:xz,y1:padT,x2:xz,y2:H-padB,stroke:HAIRS(),"stroke-width":1.2}));
    rows.forEach((r,k)=>{
      const cy=padT+k*rowH+rowH/2,pos=r.val>=0,col=pos?POS():NEG();
      const x=pos?xz:xOf(r.val),w=Math.max(1.5,Math.abs(xOf(r.val)-xz));
      svg.appendChild(el("rect",{x,y:cy-8,width:w,height:16,rx:3,fill:col,opacity:r.name.includes("特质")?.55:1}));
      const nm=el("text",{x:padL-10,y:cy+4,"text-anchor":"end","font-size":12.5,fill:INK()});nm.textContent=r.name;svg.appendChild(nm);
      const vl=el("text",{x:pos?xOf(r.val)+6:xOf(r.val)-6,y:cy+4,"text-anchor":pos?"start":"end","font-size":12,"font-weight":600,fill:col});
      vl.textContent=pct(r.val);svg.appendChild(vl);
    });
  }

  // 表格
  function table(){
    const tb=document.querySelector("#tbl tbody");
    const rows=R.sectors.slice().sort((x,y)=>y.total-x.total);
    const cls=v=>v>=0?"pos":"neg";
    let html=rows.map(r=>`<tr><td>${r.sector}</td><td>${pct0(r.wp)}</td><td>${pct0(r.wb)}</td>`+
      `<td class="${cls(r.allocation)}">${pct(r.allocation)}</td><td class="${cls(r.selection)}">${pct(r.selection)}</td>`+
      `<td class="${cls(r.interaction)}">${pct(r.interaction)}</td><td class="${cls(r.total)}">${pct(r.total)}</td></tr>`).join("");
    const e=R.effects;
    html+=`<tr><td>合计</td><td></td><td></td><td class="${cls(e.allocation)}">${pct(e.allocation)}</td>`+
      `<td class="${cls(e.selection)}">${pct(e.selection)}</td><td class="${cls(e.interaction)}">${pct(e.interaction)}</td>`+
      `<td class="${cls(R.active)}">${pct(R.active)}</td></tr>`;
    tb.innerHTML=html;
  }

  function drawAll(){waterfall();sectorsChart();factorsChart();}
  drawAll();table();
  new MutationObserver(drawAll).observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});
  matchMedia("(prefers-color-scheme:dark)").addEventListener("change",drawAll);
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# 数据读取与校验
# ---------------------------------------------------------------------------

def read_table(path):
    """读 parquet/csv。csv 的 date/symbol/sector 强制按字符串读——
    否则 A 股代码 '000001' 会被解析成整数 1，前导零丢失且与 'CASH'
    之类的字符串符号类型冲突。"""
    if str(path).endswith(".csv"):
        cols = pd.read_csv(path, nrows=0).columns
        dtype = {c: str for c in cols if c in STR_COLS}
        return pd.read_csv(path, dtype=dtype)
    df = pd.read_parquet(path)
    for c in df.columns:
        if c in STR_COLS:
            df[c] = df[c].astype(str)
    return df


def check_duplicates(df, keys, name):
    """(date, symbol) 等主键出现重复直接报错。重复行会在 merge 时被复制、
    权重被重复计入，导致归因悄悄算错——这是必须拦下的脏数据。"""
    dup = df.duplicated(subset=list(keys), keep=False)
    if dup.any():
        examples = df.loc[dup, list(keys)].drop_duplicates().head(5).to_dict("records")
        raise ValueError(
            f"{name} 存在重复主键 {tuple(keys)}（共 {int(dup.sum())} 行），例如 {examples}。"
            f"重复行会被重复计权导致归因错误，请先去重。"
        )


def check_return_sanity(ret, cap=MAX_ABS_RETURN):
    """收益合理性预警：|日收益| 超过阈值多为未复权/停牌复牌/新股等脏数据。

    仅告警、不修改数据——清洗是取数环节的职责，归因引擎不静默篡改收益，
    但会把可疑收益surface出来，避免脏数据污染结果却无人察觉。
    """
    bad = ret[ret["ret"].abs() > cap]
    if len(bad):
        worst = bad.reindex(bad["ret"].abs().sort_values(ascending=False).index).head(5)
        examples = [f"{r['date']} {r['symbol']} {r['ret']:+.1%}"
                    for _, r in worst.iterrows()]
        warnings.warn(
            f"{len(bad)} 条日收益绝对值超过 {cap:.0%}（A股单日涨跌幅一般 ≤20%），"
            f"疑似未复权/停牌复牌/异常数据，例如 {examples}。"
            f"请核对收益是否已前复权；归因不会自动剔除，脏收益会污染归因结果。"
        )


def check_weights(df, name):
    """校验每日权重加总为 1，超出容忍度直接报错而不是悄悄归一化。"""
    sums = df.groupby("date")["weight"].sum()
    bad = sums[(sums - 1.0).abs() > WEIGHT_SUM_TOL]
    if len(bad):
        worst = float((bad - 1.0).abs().max())
        raise ValueError(
            f"{name} 有 {len(bad)} 个交易日权重加总偏离 1（最大偏差 {worst:.6f}）。"
            f"请先在数据侧归一化，归因不替你做这个决定。"
        )


def build_panel(pw, bw, ret, sector):
    """把四张长表拼成逐期面板 [date, symbol, sector, wp, wb, ret]。"""
    check_duplicates(pw, ("date", "symbol"), "组合权重")
    check_duplicates(bw, ("date", "symbol"), "基准权重")
    check_duplicates(ret, ("date", "symbol"), "个股收益")
    check_duplicates(sector, ("symbol",), "行业分类")

    pw = pw.rename(columns={"weight": "wp"})
    bw = bw.rename(columns={"weight": "wb"})
    panel = pw.merge(bw, on=["date", "symbol"], how="outer")
    panel[["wp", "wb"]] = panel[["wp", "wb"]].fillna(0.0)

    panel = panel.merge(ret, on=["date", "symbol"], how="left")
    missing_ret = panel[panel["ret"].isna()]
    if len(missing_ret):
        examples = missing_ret[["date", "symbol"]].head(5).to_dict("records")
        raise ValueError(
            f"{len(missing_ret)} 条持仓记录缺少对应收益，例如 {examples}。"
            f"收益缺失会让归因恒等式失效，请补齐数据。"
        )

    check_return_sanity(panel[["date", "symbol", "ret"]])

    panel = panel.merge(sector, on="symbol", how="left")
    missing_sec = panel[panel["sector"].isna()]["symbol"].unique()
    if len(missing_sec):
        warnings.warn(
            f"{len(missing_sec)} 只股票缺少行业分类（如 {list(missing_sec[:5])}），"
            f"已归入 'UNCLASSIFIED'。"
        )
        panel["sector"] = panel["sector"].fillna("UNCLASSIFIED")
    return panel


# ---------------------------------------------------------------------------
# Brinson-Fachler 单期归因
# ---------------------------------------------------------------------------

def brinson_single_period(g):
    """单期 Brinson-Fachler 归因。

    g: 单个交易日的面板 [symbol, sector, wp, wb, ret]。
    返回 (行业明细 DataFrame, 组合收益 Rp, 基准收益 Rb)。

    约定：
    - 组合在某行业无持仓时，该行业组合收益按基准收益记，selection/interaction 自然为 0；
    - 基准在某行业无权重时，该行业基准收益按组合收益记，超额全部计入 allocation；
    - 某行业在组合与基准中权重均为 0 时，收益率填 0，三项效应恒为 0（防 0*NaN 产生 NaN）。
    """
    grp = g.groupby("sector")
    wp = grp["wp"].sum()
    wb = grp["wb"].sum()

    rp = (g["wp"] * g["ret"]).groupby(g["sector"]).sum() / wp.replace(0.0, np.nan)
    rb = (g["wb"] * g["ret"]).groupby(g["sector"]).sum() / wb.replace(0.0, np.nan)
    rp = rp.fillna(rb)
    rb = rb.fillna(rp)
    # 组合与基准该行业权重均为 0 时，rp/rb 仍为 NaN；此时权重差为 0，
    # 填 0 不影响任何效应，但可避免 0*NaN=NaN 混入明细表。
    rp = rp.fillna(0.0)
    rb = rb.fillna(0.0)

    Rp = float((g["wp"] * g["ret"]).sum())
    Rb = float((g["wb"] * g["ret"]).sum())

    out = pd.DataFrame(
        {
            "wp": wp,
            "wb": wb,
            "rp": rp,
            "rb": rb,
            "allocation": (wp - wb) * (rb - Rb),
            "selection": wb * (rp - rb),
            "interaction": (wp - wb) * (rp - rb),
        }
    )
    out["total"] = out[EFFECT_COLS].sum(axis=1)

    if out[EFFECT_COLS].isna().any().any():
        raise AssertionError("单期归因出现 NaN 效应，请检查输入权重/收益。")

    residual = out["total"].sum() - (Rp - Rb)
    if abs(residual) > IDENTITY_TOL:
        raise AssertionError(
            f"单期归因恒等式失效：各项加总与主动收益差 {residual:.2e}，请检查输入权重。"
        )
    return out, Rp, Rb


# ---------------------------------------------------------------------------
# Carino 多期几何链接
# ---------------------------------------------------------------------------

def _kappa(a, b):
    """Carino 链接系数 k = (ln(1+a) - ln(1+b)) / (a - b)，a==b 时取极限 1/(1+a)。"""
    if abs(a - b) < 1e-12:
        return 1.0 / (1.0 + a)
    return (np.log1p(a) - np.log1p(b)) / (a - b)


def _period_returns(panel):
    """逐期组合/基准收益，按日期排序。返回 dict: {date: (Rp, Rb)}。"""
    out = {}
    for date, g in panel.groupby("date", sort=True):
        out[date] = (float((g["wp"] * g["ret"]).sum()),
                     float((g["wb"] * g["ret"]).sum()))
    return out


def _carino_scales(period_ret):
    """给定 {date:(Rp,Rb)}，返回 (逐期缩放系数 dict, Rp_total, Rb_total)。
    缩放后逐期主动收益之和 ≡ 区间几何主动收益（Carino 平滑）。"""
    dates = list(period_ret.keys())
    rp_arr = np.array([period_ret[d][0] for d in dates])
    rb_arr = np.array([period_ret[d][1] for d in dates])
    Rp_total = float(np.prod(1.0 + rp_arr) - 1.0)
    Rb_total = float(np.prod(1.0 + rb_arr) - 1.0)
    K = _kappa(Rp_total, Rb_total)
    scales = {d: _kappa(period_ret[d][0], period_ret[d][1]) / K for d in dates}
    return scales, Rp_total, Rb_total


def brinson_multi_period(panel):
    """逐期 Brinson-Fachler + Carino 链接，输出跨期可加的行业归因。

    返回 dict：
      linked   跨期链接后的行业效应（allocation/selection/interaction/total）
      periods  每期明细（未缩放）
      Rp_total / Rb_total  区间几何累计收益
    """
    period_ret = _period_returns(panel)
    scales, Rp_total, Rb_total = _carino_scales(period_ret)

    scaled, period_rows = [], []
    for date, g in panel.groupby("date", sort=True):
        eff, Rp, Rb = brinson_single_period(g)
        scaled.append(eff[EFFECT_COLS + ["total"]] * scales[date])
        period_rows.append({"date": date, "Rp": Rp, "Rb": Rb, "active": Rp - Rb})
    linked = pd.concat(scaled).groupby(level=0).sum()

    residual = linked["total"].sum() - (Rp_total - Rb_total)
    if abs(residual) > IDENTITY_TOL * max(1, len(period_ret)):
        raise AssertionError(f"多期链接恒等式失效：残差 {residual:.2e}。")

    # 附上区间平均行业权重（先按日加总到行业，再跨期取均值），便于阅读
    avg_w = (panel.groupby(["date", "sector"])[["wp", "wb"]].sum()
             .groupby("sector").mean())
    linked = avg_w.join(linked, how="right").fillna(0.0)

    return {
        "linked": linked.sort_values("total", ascending=False),
        "periods": pd.DataFrame(period_rows),
        "Rp_total": Rp_total,
        "Rb_total": Rb_total,
    }


# ---------------------------------------------------------------------------
# 因子归因（与行业归因共用 Carino 口径，对同一总账）
# ---------------------------------------------------------------------------

def factor_attribution(panel, exposures, factor_cols=None):
    """基于横截面回归的因子归因，与 Brinson 面板对齐到同一区间主动收益。

    每期：r_i = c + X_i · f + e_i（OLS 估计因子收益 f），
    因子贡献 = 主动暴露 · f（主动暴露 = Σ_i (wp_i - wb_i) X_i），
    特质（选股）收益 = 该期全域主动收益 - 因子贡献合计（残差定义，恒等式必然成立）；
    再用与行业归因相同的 Carino 系数逐期缩放后跨期加总。
    因此因子面板合计 ≡ 行业面板合计 ≡ 区间主动收益。

    exposures: 宽表 [date, symbol, <因子列...>]。
    """
    if factor_cols is None:
        factor_cols = [c for c in exposures.columns if c not in ("date", "symbol")]
    if not factor_cols:
        raise ValueError("因子暴露表里没有找到因子列。")
    check_duplicates(exposures, ("date", "symbol"), "因子暴露")

    period_ret = _period_returns(panel)
    scales, Rp_total, Rb_total = _carino_scales(period_ret)

    merged = panel.merge(exposures, on=["date", "symbol"], how="left")
    coverage = 1.0 - merged[factor_cols[0]].isna().mean()
    if coverage < 0.95:
        warnings.warn(
            f"因子暴露覆盖率只有 {coverage:.1%}，缺暴露的持仓其主动收益将全部计入特质项。"
        )

    rows = []
    for date, g in merged.groupby("date", sort=True):
        # 全域主动收益（与 Brinson 同口径，含无暴露的股票）
        active_ret = float(((g["wp"] - g["wb"]) * g["ret"]).sum())

        have = g.dropna(subset=factor_cols)
        if len(have) > len(factor_cols) + 1:
            X = have[factor_cols].to_numpy(float)
            y = have["ret"].to_numpy(float)
            design = np.column_stack([np.ones(len(have)), X])
            coef, *_ = np.linalg.lstsq(design, y, rcond=None)
            f = coef[1:]
            active_expo = (have["wp"] - have["wb"]).to_numpy(float) @ X
        else:
            f = np.zeros(len(factor_cols))
            active_expo = np.zeros(len(factor_cols))

        contrib = active_expo * f
        specific = active_ret - float(contrib.sum())    # 残差定义，逐期恒等式成立

        s = scales[date]
        row = {"date": date, "active_ret": active_ret,
               "specific_scaled": specific * s}
        row.update({f"expo_{c}": e for c, e in zip(factor_cols, active_expo)})
        row.update({f"fret_{c}": v for c, v in zip(factor_cols, f)})
        row.update({f"contrib_{c}": v for c, v in zip(factor_cols, contrib)})
        row.update({f"contrib_scaled_{c}": v * s for c, v in zip(factor_cols, contrib)})
        rows.append(row)
    detail = pd.DataFrame(rows)

    # Carino 缩放后跨期加总：与行业归因对同一区间主动收益
    summary = {}
    for c in factor_cols:
        summary[c] = float(detail[f"contrib_scaled_{c}"].sum())
    summary["specific"] = float(detail["specific_scaled"].sum())
    summary["active_total"] = Rp_total - Rb_total

    residual = sum(summary[c] for c in factor_cols) + summary["specific"] - summary["active_total"]
    if abs(residual) > IDENTITY_TOL * max(1, len(period_ret)):
        raise AssertionError(f"因子归因恒等式失效：残差 {residual:.2e}。")

    return {"detail": detail, "summary": summary, "factor_cols": factor_cols}


# ---------------------------------------------------------------------------
# 报告输出
# ---------------------------------------------------------------------------

def render_text_report(brinson, factor=None):
    lines = []
    lines.append("组合绩效归因报告")
    lines.append("=" * 60)
    lines.append(f"区间组合收益  Rp = {brinson['Rp_total']:+.4%}")
    lines.append(f"区间基准收益  Rb = {brinson['Rb_total']:+.4%}")
    lines.append(f"区间主动收益      = {brinson['Rp_total'] - brinson['Rb_total']:+.4%}")
    lines.append("")
    lines.append("Brinson-Fachler 行业归因（Carino 链接，跨期可加）")
    lines.append("-" * 60)
    tbl = brinson["linked"].copy()
    tbl.index.name = "sector"
    lines.append(
        tbl[["wp", "wb"] + EFFECT_COLS + ["total"]]
        .rename(columns={"wp": "组合权重", "wb": "基准权重",
                         "allocation": "配置", "selection": "选股",
                         "interaction": "交互", "total": "合计"})
        .to_string(float_format=lambda x: f"{x:+.4%}")
    )
    total = tbl[EFFECT_COLS + ["total"]].sum()
    lines.append("-" * 60)
    lines.append(
        f"合计: 配置 {total['allocation']:+.4%} | 选股 {total['selection']:+.4%} | "
        f"交互 {total['interaction']:+.4%} | 总计 {total['total']:+.4%}"
    )

    if factor is not None:
        lines.append("")
        lines.append("因子归因（Carino 链接，与行业归因对同一区间主动收益）")
        lines.append("-" * 60)
        for c in factor["factor_cols"]:
            lines.append(f"  {c:<24s} {factor['summary'][c]:+.4%}")
        lines.append(f"  {'特质/选股':<22s} {factor['summary']['specific']:+.4%}")
        lines.append("-" * 60)
        lines.append(f"  {'因子归因合计':<21s} {factor['summary']['active_total']:+.4%}")
    return "\n".join(lines)


def _html_escape(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def render_html(report):
    """生成自包含 HTML 归因报告（内联 SVG + CSS + JS，零外部依赖、离线可用、明暗自适应）。

    包含：组合/基准/主动收益概览、主动收益瀑布分解（配置→选股→交互）、
    行业贡献发散条（红涨绿跌，按贡献排序）、因子归因条形、完整数据表。
    """
    meta = report["meta"]
    sectors = report["sector_attribution"]
    periods = report.get("period_returns", [])
    eff = {
        "allocation": sum(s.get("allocation", 0) for s in sectors),
        "selection": sum(s.get("selection", 0) for s in sectors),
        "interaction": sum(s.get("interaction", 0) for s in sectors),
    }
    date_range = ""
    if periods:
        date_range = f"{periods[0].get('date','')} ~ {periods[-1].get('date','')}"

    factors = None
    if "factor_attribution" in report:
        fs = report["factor_attribution"]["summary"]
        factors = {k: v for k, v in fs.items() if k != "active_total"}

    data = {
        "Rp": meta["Rp_total"], "Rb": meta["Rb_total"], "active": meta["active_total"],
        "periods": meta.get("periods"), "method": meta.get("method", ""),
        "dateRange": date_range, "effects": eff,
        "sectors": sectors, "factors": factors,
    }
    return (_HTML_REPORT_TEMPLATE
            .replace("__TITLE__", "组合绩效归因报告")
            .replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False)))


def build_json_report(brinson, factor=None):
    report = {
        "meta": {
            "method": "Brinson-Fachler + Carino linking",
            "periods": len(brinson["periods"]),
            "Rp_total": brinson["Rp_total"],
            "Rb_total": brinson["Rb_total"],
            "active_total": brinson["Rp_total"] - brinson["Rb_total"],
        },
        "sector_attribution": json.loads(
            brinson["linked"].reset_index()
            .rename(columns={"index": "sector"})
            .to_json(orient="records", force_ascii=False)
        ),
        "period_returns": json.loads(
            brinson["periods"].astype({"date": str}).to_json(orient="records")
        ),
    }
    if factor is not None:
        report["factor_attribution"] = {
            "summary": {k: float(v) for k, v in factor["summary"].items()},
            "detail": json.loads(
                factor["detail"].astype({"date": str}).to_json(orient="records")
            ),
        }
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="组合绩效归因（Brinson + 因子）")
    ap.add_argument("--portfolio", required=True, help="组合权重 parquet/csv")
    ap.add_argument("--benchmark", required=True, help="基准权重 parquet/csv")
    ap.add_argument("--returns", required=True, help="个股收益 parquet/csv")
    ap.add_argument("--sectors", required=True, help="行业分类 parquet/csv")
    ap.add_argument("--exposures", default=None, help="因子暴露 parquet/csv（可选）")
    ap.add_argument("--out", default=None, help="输出目录（写 txt + json + html）")
    ap.add_argument("--no-html", action="store_true", help="不生成 HTML 可视化报告")
    args = ap.parse_args(argv)

    pw = read_table(args.portfolio)
    bw = read_table(args.benchmark)
    ret = read_table(args.returns)
    sector = read_table(args.sectors)
    check_weights(pw, "组合")
    check_weights(bw, "基准")

    panel = build_panel(pw, bw, ret, sector)
    brinson = brinson_multi_period(panel)

    factor = None
    if args.exposures:
        factor = factor_attribution(panel, read_table(args.exposures))

    text = render_text_report(brinson, factor)
    print(text)

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        report = build_json_report(brinson, factor)
        with open(os.path.join(args.out, "attribution_report.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        with open(os.path.join(args.out, "attribution_report.txt"), "w",
                  encoding="utf-8") as fh:
            fh.write(text + "\n")
        outputs = "json + txt"
        if not args.no_html:
            with open(os.path.join(args.out, "attribution_report.html"), "w",
                      encoding="utf-8") as fh:
                fh.write(render_html(report))
            outputs += " + html"
        print(f"\n报告已写入 {args.out}/（{outputs}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
