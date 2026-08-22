# 组合绩效归因方法论

本文件给出实现所依据的公式与口径，供 Agent 解释报告、复核结果时引用。

## 1. Brinson-Fachler 单期分解

设某行业组合权重 wp、基准权重 wb、组合内该行业收益 rp、基准内该行业收益 rb，
基准整体收益 Rb。单期主动收益分解为三项：

- 配置（allocation）= (wp − wb) × (rb − Rb)
- 选股（selection）= wb × (rp − rb)
- 交互（interaction）= (wp − wb) × (rp − rb)

三项对所有行业加总恒等于单期主动收益 Rp − Rb（Rp 为组合整体收益）。

与经典 Brinson-Hood-Beebower 的区别：配置项减去了基准整体收益 Rb（而非直接用 rb），
使"超配一个整体跑赢基准的行业"被正确归入正配置，是行业轮动语境下更常用的口径。

边界约定：
- 组合在某行业无持仓（wp=0）：rp 记为 rb，selection/interaction 自然为 0
- 基准在某行业无权重（wb=0）：rb 记为 rp，超额全部计入 allocation
- 组合与基准该行业权重均为 0：收益率记为 0，三项效应恒为 0（避免 0×NaN 产生 NaN）

## 2. Carino 多期几何链接

单期效应直接跨期相加会与几何累计的区间主动收益对不上（算术 vs 几何）。
Carino 链接对每期效应乘一个缩放系数，使缩放后逐期效应之和精确等于区间几何主动收益。

单期收益 r 的 Carino 系数：

- k(a, b) = (ln(1+a) − ln(1+b)) / (a − b)，当 a = b 时取极限 1/(1+a)

区间系数 K = k(Rp_total, Rb_total)，其中 Rp_total、Rb_total 为区间几何累计收益。
第 t 期第 i 项效应的缩放：effect_{t,i} × k(Rp_t, Rb_t) / K。

链接后各项跨期加总满足：Σ 缩放效应 ≡ Rp_total − Rb_total。

## 3. 因子归因（横截面回归）

每期对截面做 OLS：r_i = c + X_i · f + e_i，估计因子收益向量 f（X 为因子暴露矩阵）。

- 主动暴露：active_expo = Σ_i (wp_i − wb_i) X_i
- 因子贡献：contrib = active_expo · f
- 特质（选股）收益：specific = 该期全域主动收益 − contrib 合计（残差定义）

其中"全域主动收益"= Σ_i (wp_i − wb_i) r_i，在全部持仓上计算（含无因子暴露的股票），
与 Brinson 单期主动收益 Rp − Rb 恒等。因此逐期恒等式 active = Σ contrib + specific 必然成立。

**与行业归因对齐**：因子贡献与特质收益同样用第 2 节的 Carino 系数逐期缩放后跨期加总。
由于每期主动收益在两套方法中是同一个量，缩放系数也相同，故：

    因子面板合计（Σ 因子贡献 + 特质） ≡ 行业面板合计 ≡ Rp_total − Rb_total

三者对同一区间主动收益。这是本实现相较"因子用算术加总、行业用几何链接"的早期做法的关键修正。

截距项 c 在全域上因 Σ_i (wp_i − wb_i) = 0 而自然消去；当因子覆盖不足、回归在子集上进行时，
少量截距泄漏并入特质项（残差定义保证恒等式仍成立）。

## 4. 已知局限

- 假设每期按给定权重再平衡，不建模期内交易、费用、现金拖累
- 因子收益为普通 OLS，未做行业中性化或加权最小二乘（WLS）
- 因子暴露覆盖率低时，缺暴露持仓的主动收益全部计入特质项，会高估特质
- 单期恒等式在浮点精度内成立（残差容忍度 1e-8）

## 参考

- Brinson, Hood, Beebower (1986), "Determinants of Portfolio Performance"
- Brinson, Fachler (1985), "Measuring Non-US Equity Portfolio Performance"
- Carino (1999), "Combining Attribution Effects Over Time"
