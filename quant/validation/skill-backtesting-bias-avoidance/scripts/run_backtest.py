#!/usr/bin/env python3
"""
run_backtest.py — Backtesting & Bias Avoidance 的可执行骨架 v3。

默认离线（合成数据，已知"真实"边际）：
  - 无前视回测引擎（信号滞后一bar执行；成本=线性 + 平方根律市场冲击）
  - 前视偏差量化：同一信号 干净 vs 泄漏（毛口径，隔离前视）
  - 夏普显著性两口径：Newey-West HAC（报方差膨胀因子与 N_eff=T/因子）+ 按持仓段独立下注
  - 过拟合：CSCV→PBO（含自助置信区间）；多重检验：Deflated Sharpe（声明自由度下界）
  - 蒙特卡洛：数百条独立 AR(1) 路径 → PBO/DSR/样本外夏普的分布与伪发现率
  - 净值曲线 + 回撤图（PNG）
所有头条数字一律 all-in 净口径（线性成本 + 市场冲击）。

措辞纪律：样本外不显著时输出“无显著净边际”，不写“策略无效”。

用法：
  python run_backtest.py
  python run_backtest.py --mc-paths 300 --n-trials 60
  python run_backtest.py --source yfinance --symbol AAPL --start 2018-01-01
"""
import argparse, math, os
from itertools import combinations
import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis

PHI = 0.05
GAMMA = 0.5772156649015329
LOOKBACKS = list(range(5, 130, 5))
DISP = [5, 10, 20, 40, 60, 120]


# ============ 1. 数据 ============
def load_prices(source, symbol, start, end):
    if source == "synthetic":
        return _synthetic_prices(phi=PHI)
    if source == "yfinance":
        import yfinance as yf
        raw = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
        if raw is None or len(raw) == 0:
            raise ValueError(f"yfinance 返回空：{symbol}")
        s = raw["Close"]
        if hasattr(s, "columns"):
            s = s.iloc[:, 0]
        s = s.dropna().astype(float); s.name = symbol
        if len(s) < 250:
            raise ValueError(f"样本不足（{len(s)} 行）")
        return s
    raise ValueError(f"unknown source: {source}")


def _synthetic_prices(n=1500, phi=0.05, vol=0.012, seed=7):
    rng = np.random.default_rng(seed)
    eps = rng.normal(0, vol, n)
    r = np.zeros(n)
    for t in range(1, n):
        r[t] = phi * r[t - 1] + eps[t]
    idx = pd.bdate_range("2018-01-01", periods=n)
    return pd.Series(100 * np.exp(np.cumsum(r)), index=idx, name="SYN")


# ============ 2. 信号 / 成本 / 引擎 ============
def momentum_position(prices, lookback):
    return np.sign(prices.pct_change(lookback)).fillna(0.0)


def trade_cost(turn, linear, impact):
    return turn * linear + impact * np.power(turn, 1.5)


def run_clean(prices, pos, linear, impact):
    ret = prices.pct_change().fillna(0.0)
    gross = pos.shift(1).fillna(0.0) * ret
    turn = pos.diff().abs().fillna(0.0)
    net = gross - trade_cost(turn, linear, impact)
    return gross, net, turn


def run_leaky(prices, pos):
    return pos * prices.pct_change().fillna(0.0)


# ============ 3. 显著性：HAC 与 按下注 ============
def _nw_lrv(r, L):
    r = r - r.mean(); T = len(r)
    g0 = float(r @ r) / T; s = g0
    for k in range(1, L + 1):
        s += 2 * (1 - k / (L + 1)) * float(r[k:] @ r[:-k]) / T
    return max(s, 1e-18), max(g0, 1e-18)


def sharpe_stats(r, bw, freq=252):
    """HAC 夏普统计。vif=方差膨胀因子(=长期方差/即时方差)，N_eff=T/vif。"""
    r = np.asarray(r, float); r = r[~np.isnan(r)]; T = len(r)
    out = dict(sr=0.0, t=0.0, ci=(0.0, 0.0), T=T, neff=float(T), vif=1.0)
    if T < 5 or r.std() == 0:
        return out
    mu = r.mean(); L = max(1, min(int(bw), T // 3))
    lrv, g0 = _nw_lrv(r, L); sd = math.sqrt(g0)
    vif = lrv / g0                                  # 方差膨胀因子
    se_mu = math.sqrt(lrv / T); t = mu / se_mu
    sr_ann = (mu / sd) * math.sqrt(freq)
    se_sr_ann = (se_mu / sd) * math.sqrt(freq)
    out.update(sr=sr_ann, t=t, ci=(sr_ann - 1.96 * se_sr_ann, sr_ann + 1.96 * se_sr_ann),
               T=T, neff=T / vif, vif=vif)
    return out


def segment_stats(net, pos, freq=252):
    """按持仓段聚合为每段总收益 → 独立下注口径。"""
    s = pd.Series(np.asarray(net, float)).reset_index(drop=True)
    p = pd.Series(np.asarray(pos, float)).reset_index(drop=True)
    gid = (p != p.shift()).cumsum()
    g = pd.DataFrame({"r": s.values, "p": p.values, "g": gid.values})
    seg = g.groupby("g").agg(pnl=("r", "sum"), pos=("p", "first"))
    seg = seg[seg["pos"] != 0]; nb = len(seg)
    out = dict(n=nb, sr=0.0, t=0.0, ci=(0.0, 0.0))
    if nb < 3 or seg["pnl"].std(ddof=1) == 0:
        return out
    mu, sd = seg["pnl"].mean(), seg["pnl"].std(ddof=1)
    t = mu / (sd / math.sqrt(nb)); bpy = nb / (len(s) / freq)
    sr_ann = mu / sd * math.sqrt(bpy); se = math.sqrt(bpy) / math.sqrt(nb)
    out.update(n=nb, sr=sr_ann, t=t, ci=(sr_ann - 1.96 * se, sr_ann + 1.96 * se))
    return out


def metrics(r, freq=252):
    r = np.asarray(r, float); r = r[~np.isnan(r)]
    out = dict(ann=0.0, sharpe=0.0, sortino=0.0, mdd=0.0, calmar=0.0, hit=0.0)
    if len(r) == 0 or r.std() == 0:
        return out
    out["ann"] = r.mean() * freq
    out["sharpe"] = r.mean() / r.std() * math.sqrt(freq)
    dn = r[r < 0]
    out["sortino"] = (r.mean() / dn.std() * math.sqrt(freq)) if len(dn) and dn.std() > 0 else float("inf")
    eq = np.cumprod(1 + r); pk = np.maximum.accumulate(eq)
    out["mdd"] = float(((eq - pk) / pk).min())
    out["calmar"] = (out["ann"] / abs(out["mdd"])) if out["mdd"] < 0 else float("inf")
    out["hit"] = float((r > 0).mean())
    return out


def _sr_pp_vec(X):
    mu = X.mean(axis=0); sd = X.std(axis=0); sd[sd == 0] = np.nan
    return np.nan_to_num(mu / sd)


def _fmt(x, d=2):
    return f"{x:.{d}f}" if np.isfinite(x) else "∞"


# ============ 4. CSCV → PBO (+自助CI) ============
def cscv_pbo(R, S=10):
    T, N = R.shape; m = (T // S) * S; R = R[:m]
    blocks = np.array_split(np.arange(m), S); lams = []
    for combo in combinations(range(S), S // 2):
        ir = np.concatenate([blocks[i] for i in combo])
        orr = np.concatenate([blocks[i] for i in range(S) if i not in combo])
        is_sr, oos_sr = _sr_pp_vec(R[ir]), _sr_pp_vec(R[orr])
        ns = int(np.argmax(is_sr)); rank = int((oos_sr <= oos_sr[ns]).sum())
        w = min(max(rank / (N + 1), 1e-6), 1 - 1e-6)
        lams.append(math.log(w / (1 - w)))
    return float((np.array(lams) <= 0).mean()), np.array(lams)


def pbo_bootstrap_ci(lam, B=2000, seed=1):
    rng = np.random.default_rng(seed); n = len(lam)
    ps = [(lam[rng.integers(0, n, n)] <= 0).mean() for _ in range(B)]
    return float(np.percentile(ps, 2.5)), float(np.percentile(ps, 97.5))


# ============ 5. Deflated Sharpe ============
def deflated_sharpe(sel_returns, all_sr_pp, N, T):
    r = np.asarray(sel_returns, float); r = r[~np.isnan(r)]; sd = r.std(ddof=1)
    if sd == 0 or T < 3:
        return 0.0, 0.0
    sr = r.mean() / sd; sk = float(skew(r)); ku = float(kurtosis(r, fisher=False))
    v = np.var(all_sr_pp, ddof=1)
    sr0 = math.sqrt(v) * ((1 - GAMMA) * norm.ppf(1 - 1.0 / N) + GAMMA * norm.ppf(1 - 1.0 / (N * math.e)))
    den = math.sqrt(max(1 - sk * sr + (ku - 1) / 4 * sr ** 2, 1e-9))
    return float(norm.cdf((sr - sr0) * math.sqrt(T - 1) / den)), sr0


# ============ 6. 单路径计算（详细报告 & 蒙特卡洛共用） ============
def compute_path(prices, cost, impact, n_trials, S=10):
    n = len(prices); split = int(n * 0.7)
    cols, full_sr, scan = [], [], []
    for Lk in LOOKBACKS:
        pos = momentum_position(prices, Lk)
        _, net, _ = run_clean(prices, pos, cost, impact)
        cols.append(net.to_numpy())
        full_sr.append(net.mean() / net.std() if net.std() > 0 else 0.0)
        scan.append((Lk, metrics(net.iloc[:split])["sharpe"], metrics(net.iloc[split:])["sharpe"]))
    R = np.column_stack(cols)
    best = max(scan, key=lambda x: x[1]); L = best[0]
    pos = momentum_position(prices, L)
    gross, net, _ = run_clean(prices, pos, cost, impact)
    oos = sharpe_stats(net.iloc[split:], L)
    pbo, lam = cscv_pbo(R, S=S)
    dsr, sr0 = deflated_sharpe(net.to_numpy(), np.array(full_sr), N=n_trials, T=len(net))
    return dict(n=n, split=split, scan=scan, best=best, L=L, R=R, full_sr=full_sr,
                pos=pos, gross=gross, net=net, oos=oos, pbo=pbo, lam=lam, dsr=dsr, sr0=sr0)


def monte_carlo(M, cost, impact, n_trials, phi):
    """M 条独立 AR(1) 路径，收集 PBO/DSR/样本外净夏普分布与伪发现率。"""
    pbos, dsrs, oos_sr, sig_pos = [], [], [], []
    for s in range(M):
        pr = _synthetic_prices(phi=phi, seed=1000 + s)
        r = compute_path(pr, cost, impact, n_trials)
        pbos.append(r["pbo"]); dsrs.append(r["dsr"]); oos_sr.append(r["oos"]["sr"])
        sig_pos.append(1.0 if r["oos"]["ci"][0] > 0 else 0.0)   # 样本外显著为正
    q = lambda a, p: float(np.percentile(a, p))
    return dict(M=M,
                pbo=(np.median(pbos), q(pbos, 5), q(pbos, 95)),
                dsr=(np.median(dsrs), q(dsrs, 5), q(dsrs, 95)),
                oos=(np.median(oos_sr), q(oos_sr, 5), q(oos_sr, 95)),
                fdr=float(np.mean(sig_pos)))


# ============ 7. 净值 / 回撤图 ============
def make_equity_plot(net, png_path):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    r = np.nan_to_num(net.to_numpy()); eq = np.cumprod(1 + r)
    pk = np.maximum.accumulate(eq); dd = eq / pk - 1; idx = net.index
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 5), sharex=True, height_ratios=[2, 1])
    a1.plot(idx, eq, color="#1976d2", lw=1.3)
    a1.set_title("Net equity curve (all-in: linear cost + impact)")
    a1.set_ylabel("Equity (x)"); a1.grid(alpha=.3)
    a2.fill_between(idx, dd, 0, color="#c62828", alpha=.45)
    a2.set_title("Drawdown"); a2.set_ylabel("DD"); a2.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(png_path, dpi=110); plt.close(fig)


# ============ 8. 审计规则 ============
def audit_flags(oos, seg_oos, pbo, pbo_ci, dsr, sh_clean, sh_leaky, gross_sh, net_sh,
                n_scanned, source):
    f = []
    if pbo > 0.5:
        f.append(("🔴 高", "过拟合概率高", "PBO>50%", f"PBO={pbo:.0%}（自助95%CI [{pbo_ci[0]:.0%},{pbo_ci[1]:.0%}]）"))
    if dsr < 0.95:
        f.append(("🔴 高", "多重检验后不显著", "DSR<95%", f"DSR={dsr:.0%}（≥{n_scanned}次试验，为乐观上界）"))
    if gross_sh > 0 and net_sh <= 0:
        f.append(("🔴 高", "扣费后归零", "净Sharpe≤0而毛>0", f"毛={gross_sh:.2f}/净={net_sh:.2f}"))
    if sh_leaky - sh_clean > 0.5:
        f.append(("🔴 高", "前视偏差显著", "泄漏>>干净(毛)", f"{sh_clean:.2f}→{sh_leaky:.2f}"))
    if oos["ci"][0] <= 0 <= oos["ci"][1]:
        f.append(("🟡 中", "样本外无显著净边际", "HAC 95%CI 含 0", f"t={oos['t']:.2f}, CI=[{oos['ci'][0]:.2f},{oos['ci'][1]:.2f}]"))
    if seg_oos["n"] < 35 or oos["neff"] < 60:
        f.append(("🟡 中", "有效样本/独立下注偏少", "独立下注<35 或 N_eff小",
                  f"下注≈{seg_oos['n']}笔, HAC N_eff≈{oos['neff']:.0f}（方差膨胀×{oos['vif']:.2f}）"))
    if 0.25 < pbo <= 0.5:
        f.append(("🟡 中", "过拟合风险中等", "25%<PBO≤50%", f"PBO={pbo:.0%}"))
    if source != "synthetic":
        f.append(("🟡 中", "幸存者/时点未核", "真实数据未验证幸存者与时点对齐", "需人工确认"))
    if not f:
        f.append(("🟢 低", "未触发高/中规则", "—", "通过显著性/PBO/DSR/前视审计"))
    return f


# ============ 9. 报告 ============
def write_report(args, prices, P, seg_is, seg_oos, seg_full, clean_stat, leaky_stat,
                 net_stat, m_net, pbo_ci, mc, png_name, flags, path):
    n, split, L = P["n"], P["split"], P["L"]
    n_oos = n - split; oos = P["oos"]; cl, lk, ns = clean_stat, leaky_stat, net_stat
    # 让显示的 N_eff 严格 = T / (显示的方差膨胀因子)，确保按报告数字可整除核验
    oos_vif = round(oos["vif"], 2); oos_neff = round(n_oos / oos_vif)
    ns_vif = round(ns["vif"], 2); ns_neff = round(ns["T"] / ns_vif)
    is_best = P["best"][1]
    sig = "无显著净边际" if (oos["ci"][0] <= 0 <= oos["ci"][1]) else "存在显著净边际"
    disp = [(Lk, ish, osh) for (Lk, ish, osh) in P["scan"] if Lk in DISP or Lk == L]
    nt = args.n_trials
    Lines = [
        f"# 回测与偏差审计报告：{'合成动量演示' if args.source=='synthetic' else args.symbol}",
        f"\n> 数据源：`{args.source}`｜样本：{prices.index.min().date()} ~ {prices.index.max().date()}，"
        f"共 {n} 个交易日｜信号：{L}日动量｜成本：线性{args.cost*1e4:.0f}bp + 冲击{args.impact}"
        f"｜显著性：Newey-West HAC（带宽={L}）\n",
        "## 1. 摘要与结论",
        f"- **诚实结论（样本外·all-in净·无前视·HAC）**：夏普 = **{oos['sr']:.2f}**"
        f"（t={oos['t']:.2f}，95%CI=[{oos['ci'][0]:.2f}, {oos['ci'][1]:.2f}]）→ **该{'合成' if args.source=='synthetic' else ''}信号{sig}**。",
        f"  - **显著性两口径**：① HAC：方差膨胀因子 **×{oos_vif:.2f}**，N_eff = {n_oos}/{oos_vif:.2f} ≈ **{oos_neff:.0f}**；"
        f"② 按独立下注：样本外仅 **{seg_oos['n']} 笔**（t={seg_oos['t']:.2f}）。二者孰宽取决于段内噪声，并看为准。",
        f"  - 这是“未发现正向优势”，**不等于**“策略一定无用”。",
        f"- **全样本 all-in 净夏普 = {ns['sr']:.2f}**（线性{args.cost*1e4:.0f}bp+冲击；= 第6章 {args.cost*1e4:.0f}bp 行）。",
        f"- **PBO = {P['pbo']:.0%}**（CSCV，自助95%CI [{pbo_ci[0]:.0%}, {pbo_ci[1]:.0%}]）；"
        f"**DSR = {P['dsr']:.0%}**（≥{nt}次试验校正，为乐观上界）。",
        f"- **前视偏差（毛口径，仅隔离前视）**：忘记滞后使夏普由 {cl['sr']:.2f} 虚高到 {lk['sr']:.2f}。",
    ]
    if mc:
        Lines.append(
            f"- **蒙特卡洛（{mc['M']}条独立路径，非单路径点值）**：PBO 中位 {mc['pbo'][0]:.0%} [5–95%: {mc['pbo'][1]:.0%}–{mc['pbo'][2]:.0%}]，"
            f"DSR 中位 {mc['dsr'][0]:.0%} [{mc['dsr'][1]:.0%}–{mc['dsr'][2]:.0%}]，样本外显著为正的占比（伪发现率）= **{mc['fdr']:.0%}**。")
    Lines += [
        f"- 最高风险等级 **{flags[0][0]}**（详见第 8 章）。",
        "- ⚠️ **使用须知**：市场冲击为无 ADV 的平方根律近似；HAC 带宽取信号回看期；"
        f"DSR 的 {nt} 次试验只含显式窗口扫描，成本/带宽/多空规则等研究自由度未计入，真实自由度更高、故 **PBO 为过拟合下界、DSR 为显著性上界**；"
        "幸存者/时点偏差合成数据下不适用、真实数据需另行核对。**仅供学习研究，不可用于真实交易**。",
        "\n## 2. 数据与策略设定",
        f"标的：{'合成序列（已知真实动量 φ='+str(PHI)+'）' if args.source=='synthetic' else args.symbol}；"
        f"信号：{L} 日动量；共 {n} 天，训练 {split} / 样本外 {n_oos}（约70/30）；过拟合另用 CSCV 多路径划分。",
        "\n## 3. 回测引擎设定（防前视 + 成本 + 显著性口径）",
        "| 设定 | 取值 | 作用 |", "|---|---|---|",
        "| 决策→执行滞后 | 1 个交易日 | 杜绝未来信息 |",
        f"| 线性成本 | 单边 {args.cost*1e4:.0f}bp × |Δw| | 佣金+价差 |",
        f"| 市场冲击 | {args.impact} × |Δw|^1.5 | 平方根律近似（无ADV） |",
        f"| 夏普显著性 | Newey-West HAC，带宽={L} | 修正序列相关，报方差膨胀因子与 N_eff=T/因子 |",
        "| 口径 | 头条=all-in 净；毛仅隔离前视 | 成本与冲击全程进头条 |",
        "\n## 4. 偏差检测：前视偏差（毛口径，仅隔离前视影响）",
        "| 版本 | 做法 | 年化Sharpe | t(HAC) | 95%CI |", "|---|---|---|---|---|",
        f"| ✅ 干净（无前视） | 滞后一bar | {cl['sr']:.2f} | {cl['t']:.2f} | [{cl['ci'][0]:.2f}, {cl['ci'][1]:.2f}] |",
        f"| ❌ 泄漏（前视） | 忘记滞后 | {lk['sr']:.2f} | {lk['t']:.2f} | [{lk['ci'][0]:.2f}, {lk['ci'][1]:.2f}] |",
        f"\n忘记滞后一个交易日，夏普凭空增加 {lk['sr']-cl['sr']:.2f}（毛口径，隔离前视；含成本净值见第 7 章）。",
        "\n## 5. 过拟合检验：CSCV/PBO + 蒙特卡洛分布",
        f"**单路径 PBO = {P['pbo']:.0%}**（{len(LOOKBACKS)} 个窗口，S=10，252 种划分；自助 95%CI [{pbo_ci[0]:.0%}, {pbo_ci[1]:.0%}]，"
        "因 252 种划分相互重叠，该 CI 偏窄）。",
    ]
    if mc:
        Lines += [
            f"\n**蒙特卡洛（{mc['M']} 条独立 AR(1) 路径，同一管线）——把点值变成分布：**",
            "| 量 | 中位数 | 5% | 95% |", "|---|---|---|---|",
            f"| PBO | {mc['pbo'][0]:.0%} | {mc['pbo'][1]:.0%} | {mc['pbo'][2]:.0%} |",
            f"| DSR | {mc['dsr'][0]:.0%} | {mc['dsr'][1]:.0%} | {mc['dsr'][2]:.0%} |",
            f"| 样本外净Sharpe | {mc['oos'][0]:.2f} | {mc['oos'][1]:.2f} | {mc['oos'][2]:.2f} |",
            f"\n伪发现率（样本外 HAC 显著为正的路径占比）= **{mc['fdr']:.0%}**——"
            "“样本内挑最优”这一动作，在数百条路径上极少产出真正的样本外正向显著，单路径的 PBO/DSR 只是该分布上的一个抽样。",
        ]
    Lines += ["\n单路径直观对照（净口径；样本内挑最优 → 样本外验证）：",
              "| 回看窗口 | 样本内Sharpe | 样本外Sharpe |", "|---|---|---|"]
    for Lk, ish, osh in disp:
        Lines.append(f"| {Lk} 日 | {ish:.2f} | {osh:.2f}{' ⬅样本内最优' if Lk==L else ''} |")
    Lines += [
        f"\n样本内最优 {L} 日（IS {is_best:.2f}）样本外仅 {oos['sr']:.2f}。单路径只是直觉，PBO/蒙卡分布才是严格度量。",
        "\n## 6. 成本敏感性（含市场冲击；净口径）",
        "| 线性成本(bp) | 全样本净Sharpe |", "|---|---|",
    ]
    for c_bp, sh in P["cost_rows"]:
        Lines.append(f"| {c_bp:.0f} | {sh:.2f}{' ←头条口径' if abs(c_bp-args.cost*1e4)<1e-6 else ''} |")
    Lines.append(f"\n（每行均含 {args.impact}×|Δw|^1.5 冲击。）盈亏平衡线性成本约 {P['breakeven']}。")
    Lines += [
        "\n## 7. 绩效、显著性与净值曲线（all-in 净，全样本）",
        "| 指标 | 数值 |", "|---|---|",
        f"| 年化收益（净） | {m_net['ann']:.2%} |",
        f"| Sharpe（净, HAC日频） | {ns['sr']:.2f}（t={ns['t']:.2f}, 95%CI=[{ns['ci'][0]:.2f}, {ns['ci'][1]:.2f}]） |",
        f"| Sharpe（净, 按下注·全样本） | {seg_full['sr']:.2f}（n={seg_full['n']}笔, t={seg_full['t']:.2f}, CI=[{seg_full['ci'][0]:.2f}, {seg_full['ci'][1]:.2f}]） |",
        f"| 有效样本 N_eff（HAC） | ≈{ns_neff:.0f}（= {ns['T']}/方差膨胀{ns_vif:.2f}） |",
        f"| 独立下注（IS/OOS/全样本） | {seg_is['n']} / {seg_oos['n']} / {seg_full['n']} 笔 |",
        f"| Sortino（净） | {_fmt(m_net['sortino'])} |",
        f"| 最大回撤（净） | {m_net['mdd']:.2%} |",
        f"| Calmar（净） | {_fmt(m_net['calmar'])} |",
        f"| 胜率 | {m_net['hit']:.1%} |",
        f"| Deflated Sharpe (DSR) | {P['dsr']:.0%}（基准 SR₀={P['sr0']:.3f}/期，≥{nt}次试验，乐观上界） |",
        f"\n**换手率诊断**：IS {seg_is['n']/split:.3f}/天 vs OOS {seg_oos['n']/n_oos:.3f}/天"
        f"（OOS 约 {(seg_oos['n']/n_oos)/(seg_is['n']/split):.1f} 倍）——样本内趋势(少翻仓)、样本外被反复打脸(频繁翻仓)，是过拟合/换regime的指纹。",
        f"\n**净值与回撤**（{m_net['mdd']:.1%} 的回撤集中在少数区间，故附图判断是否被一两段行情主导）：",
        f"\n![净值与回撤]({png_name})\n",
        "\n## 8. 偏差审计清单",
        "| 风险等级 | 信号 | 触发规则 | 证据 |", "|---|---|---|---|",
    ]
    for lv, s, rule, ev in flags:
        Lines.append(f"| {lv} | {s} | {rule} | {ev} |")
    Lines += [
        "\n**定性核查项（需人工确认）**：",
        "- 幸存者偏差：标的池是否含已退市/破产标的？",
        "- 时点对齐：价格/财务/成分是否为当时真实可得？",
        "- 研究自由度：真实尝试过的成本/带宽/规则数（影响 DSR）是否已如实计入？",
        "\n## 9. 方法附录",
        "| 分析阶段 | 方法 | 窗口/样本 | 结果 |", "|---|---|---|---|",
        f"| 显著性 | Newey-West HAC（带宽={L}）+ 按下注 | 全样本 | 净 t={ns['t']:.2f}, N_eff≈{ns_neff:.0f}, 方差膨胀×{ns_vif:.2f} |",
        f"| 前视检测 | 干净vs泄漏（毛） | 全样本 | {cl['sr']:.2f}→{lk['sr']:.2f} |",
        f"| 过拟合 | CSCV/PBO + 自助CI | 252划分 | PBO={P['pbo']:.0%} [{pbo_ci[0]:.0%},{pbo_ci[1]:.0%}] |",
        (f"| 蒙特卡洛 | {mc['M']}条AR(1) | 多路径 | PBO中位{mc['pbo'][0]:.0%}, 伪发现率{mc['fdr']:.0%} |" if mc else "| 蒙特卡洛 | 未启用(--mc-paths 0 或真实数据) | — | — |"),
        f"| 多重检验 | Deflated Sharpe | ≥{nt}次试验 | DSR={P['dsr']:.0%}（上界） |",
        f"| 成本 | 线性+平方根冲击 | 全样本 | 平衡≈{P['breakeven']} |",
        "\n---",
        "本报告基于公开数据与规则化分析生成，仅供研究参考，不构成任何投资建议。",
    ]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(Lines))


# ============ main ============
def main():
    global PHI
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="synthetic", choices=["synthetic", "yfinance"])
    ap.add_argument("--symbol", default="AAPL")
    ap.add_argument("--start", default="2018-01-01"); ap.add_argument("--end", default="2025-01-01")
    ap.add_argument("--signal-strength", type=float, default=None, dest="signal_strength")
    ap.add_argument("--cost", type=float, default=0.0005)
    ap.add_argument("--impact", type=float, default=0.0005)
    ap.add_argument("--n-trials", type=int, default=len(LOOKBACKS), dest="n_trials",
                    help="DSR 试验数（默认=扫描窗口数；真实研究自由度更高，可调大）")
    ap.add_argument("--mc-paths", type=int, default=200, dest="mc_paths",
                    help="蒙特卡洛路径数（合成数据，0=关闭）")
    ap.add_argument("--out", default="backtest_report.md")
    args = ap.parse_args()
    if args.signal_strength is not None:
        PHI = args.signal_strength

    prices = load_prices(args.source, args.symbol, args.start, args.end)
    P = compute_path(prices, args.cost, args.impact, args.n_trials)
    L, split, net = P["L"], P["split"], P["net"]
    pos = P["pos"]; gross = P["gross"]

    clean_stat = sharpe_stats(gross, L)
    leaky_stat = sharpe_stats(run_leaky(prices, pos), L)
    net_stat = sharpe_stats(net, L)
    seg_is = segment_stats(net.iloc[:split], pos.iloc[:split])
    seg_oos = segment_stats(net.iloc[split:], pos.iloc[split:])
    seg_full = segment_stats(net, pos)
    m_net = metrics(net)
    gross_sh, net_sh = metrics(gross)["sharpe"], metrics(net)["sharpe"]
    pbo_ci = pbo_bootstrap_ci(P["lam"])

    cost_rows, breakeven, prev = [], "≥40bp", None
    for c_bp in [0, 5, 10, 20, 40]:
        _, net_c, _ = run_clean(prices, pos, c_bp / 1e4, args.impact)
        sh = metrics(net_c)["sharpe"]; cost_rows.append((c_bp, sh))
        if prev is not None and prev > 0 >= sh:
            breakeven = f"{cost_rows[-2][0]:.0f}~{c_bp:.0f}bp"
        prev = sh
    P["cost_rows"], P["breakeven"] = cost_rows, breakeven

    mc = None
    if args.mc_paths > 0 and args.source == "synthetic":
        mc = monte_carlo(args.mc_paths, args.cost, args.impact, args.n_trials, PHI)

    png_path = os.path.splitext(args.out)[0] + "_equity.png"
    make_equity_plot(net, png_path)
    png_name = os.path.basename(png_path)

    flags = audit_flags(P["oos"], seg_oos, P["pbo"], pbo_ci, P["dsr"], clean_stat["sr"],
                        leaky_stat["sr"], gross_sh, net_sh, args.n_trials, args.source)
    write_report(args, prices, P, seg_is, seg_oos, seg_full, clean_stat, leaky_stat,
                 net_stat, m_net, pbo_ci, mc, png_name, flags, args.out)

    print(f"[done] {('合成' if args.source=='synthetic' else args.symbol)} | 最优{L}日 | "
          f"样本外净Sharpe={P['oos']['sr']:.2f}(t={P['oos']['t']:.2f}, N_eff≈{P['oos']['neff']:.0f}, 下注{seg_oos['n']}笔)")
    print(f"  PBO={P['pbo']:.0%}[{pbo_ci[0]:.0%},{pbo_ci[1]:.0%}] | DSR={P['dsr']:.0%} | "
          f"全样本净={net_stat['sr']:.2f} | top={flags[0][0]}"
          + (f" | MC伪发现率={mc['fdr']:.0%}" if mc else ""))
    print(f"  report -> {args.out} | 图 -> {png_name}")


if __name__ == "__main__":
    main()
