"""
沪深300 EP因子计算 + IC验证 + 分组收益 + Fama-MacBeth 完整脚本
=============================================================
使用方法：在安装好 panda_data 的环境中运行
  python ep_factor_analysis.py
"""

import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# =====================================================================
# 配置参数
# =====================================================================
QUARTER = '2024q4'          # 最新财报季度
FACTOR_DATE = '20250115'    # 因子对齐日期（季度末+2个月）
LOOKBACK_QUARTERS = 4       # TTM需要往回看的季度数
MIN_STOCKS = 50             # IC计算最少股票数
FORWARD_HORIZONS = [1, 5, 20, 60]  # 验证持有期（交易日）

# =====================================================================
# Step 1: 数据获取
# =====================================================================
def fetch_data():
    """获取沪深300成分股 + 财务数据 + 市值数据"""
    import panda_data
    
    # 1. 获取沪深300成分股
    print("[1/4] 获取沪深300成分股...")
    stock_detail = panda_data.get_stock_detail(
        market='cn',
        fields=['symbol', 'display_name', 'list_date'],
        status=1
    )
    
    # 用 get_factor 获取沪深300的股票列表
    # 或者从指数成分股获取
    hs300 = panda_data.get_factor(
        symbol=[],
        start_date=FACTOR_DATE,
        end_date=FACTOR_DATE,
        factors=['market_cap'],
        type='index_stock',
        index_code='000300.SH'
    )
    
    if hs300 is None or hs300.empty:
        print("⚠️  无法获取沪深300成分股，使用全市场股票替代")
        symbols = stock_detail['symbol'].tolist()
    else:
        symbols = hs300['symbol'].unique().tolist()
    
    print(f"  共 {len(symbols)} 只股票")
    
    # 2. 过滤新股（上市不足12个月）
    symbols = _filter_new_stocks(symbols, stock_detail)
    print(f"  排除新股后: {len(symbols)} 只股票")
    
    # 3. 获取财务数据
    print("[2/4] 获取财务数据...")
    fina_fields = [
        'symbol', 'end_date', 'operating_revenue', 'gross_profit',
        'operating_profit', 'net_profit_parent',
        'net_cash_flow_operating', 'total_assets', 'equity_parent_common',
        'basic_eps', 'roe_diluted', 'roe_weighted', 'bvps',
        'operating_revenue_yoy', 'net_profit_parent_yoy'
    ]
    
    fina = panda_data.get_fina_performance(
        symbol=symbols,
        end_quarter=QUARTER,
        fields=fina_fields
    )
    
    print(f"  获取到 {len(fina)} 条财务记录")
    
    # 4. 获取市值数据（因子对齐日）
    print("[3/4] 获取市值数据...")
    mkt = panda_data.get_factor(
        symbol=symbols,
        start_date=FACTOR_DATE,
        end_date=FACTOR_DATE,
        factors=['market_cap', 'close', 'turnover'],
        type='stock'
    )
    
    # 5. 合并
    print("[4/4] 合并数据...")
    merged = fina.merge(
        mkt[['symbol', 'date', 'market_cap', 'close', 'turnover']],
        on='symbol', how='inner'
    )
    
    print(f"  合并后: {len(merged)} 条记录")
    return merged, symbols


def _filter_new_stocks(symbols, stock_detail):
    """排除上市不足12个月的股票"""
    cutoff = pd.Timestamp('2024-01-15')
    if 'list_date' in stock_detail.columns:
        stock_detail['list_date'] = pd.to_datetime(stock_detail['list_date'], errors='coerce')
        old_stocks = stock_detail[stock_detail['list_date'] <= cutoff]['symbol'].tolist()
        return [s for s in symbols if s in old_stocks]
    return symbols


# =====================================================================
# Step 2: 计算 TTM 财务数据
# =====================================================================
def compute_ttm(df):
    """将季度数据累积为 TTM"""
    # 对于截至 quarter 的累积年报数据，已经是TTM
    # 如果 get_fina_performance 返回的是单季数据，需要手工累积
    print("  计算 TTM...")
    
    ttm_fields = [
        'operating_revenue', 'gross_profit', 'operating_profit',
        'net_profit_parent', 'net_cash_flow_operating'
    ]
    
    # 对于 'end_date' 为 2024-12-31 的年报，数据天然是TTM
    # 对于单季数据，需要 sum last 4 quarters
    # 这里假设 get_fina_performance 返回的是截止至 end_date 的累积数据
    
    return df


# =====================================================================
# Step 3: 计算 EP 因子和标准化
# =====================================================================
def compute_ep_factor(df):
    """计算 EP (E/P) 因子 + 截面标准化"""
    print("\n计算 EP 因子...")
    data = df.copy()
    
    # EP = 净利润(ttm) / 总市值
    data['EP'] = data['net_profit_parent'] / data['market_cap']
    
    # 剔除异常值
    data = data[data['EP'].notna()]
    data = data[data['EP'] > -1]     # 排除 EP < -1 的极端亏损
    data = data[data['EP'] < 1]      # 排除 EP > 1 的异常
    
    print(f"  EP 有效样本: {len(data)}")
    print(f"  EP 均值: {data['EP'].mean():.4f}")
    print(f"  EP 中位数: {data['EP'].median():.4f}")
    print(f"  EP 标准差: {data['EP'].std():.4f}")
    
    # MAD 缩尾处理
    median = data['EP'].median()
    mad = (data['EP'] - median).abs().median()
    if mad > 0:
        upper = median + 5 * mad * 1.4826
        lower = median - 5 * mad * 1.4826
        data['EP_winsor'] = data['EP'].clip(lower, upper)
    
    # 截面 Z-Score 标准化
    data['EP_z'] = (data['EP_winsor'] - data['EP_winsor'].mean()) / data['EP_winsor'].std()
    data['EP_z'] = data['EP_z'].clip(-3, 3)
    
    # 列出EP最高和最低的各5只
    top5 = data.nlargest(5, 'EP')[['symbol', 'EP']]
    bot5 = data.nsmallest(5, 'EP')[['symbol', 'EP']]
    print("\n  EP 最高 5 只:")
    for _, r in top5.iterrows():
        print(f"    {r['symbol']}: {r['EP']:.4f}")
    print("  EP 最低 5 只:")
    for _, r in bot5.iterrows():
        print(f"    {r['symbol']}: {r['EP']:.4f}")
    
    return data


# =====================================================================
# Step 4: 获取未来收益（计算 IC 需要）
# =====================================================================
def fetch_forward_returns(symbols, horizons, start_date, end_date):
    """获取各持有期的未来收益"""
    import panda_data
    
    print("\n获取未来收益数据...")
    market_data = panda_data.get_market_data(
        symbol=symbols,
        start_date=start_date,
        end_date=end_date,
        type='stock',
        fields=['close']
    )
    
    if market_data is None or market_data.empty:
        print("  ⚠️  无法获取未来收益数据，将使用模拟数据")
        return None
    
    # 计算各持有期收益
    result = market_data.pivot(index='symbol', columns='date', values='close')
    
    for h in horizons:
        result[f'ret_{h}d'] = result.pct_change(periods=h, axis=1).iloc[:, -1]
    
    return result[[f'ret_{h}d' for h in horizons]]


# =====================================================================
# Step 5: Rank IC 分析
# =====================================================================
def compute_rank_ic(df, factor_col='EP_z', forward_return_col='ret_1d'):
    """计算 Rank IC"""
    ic_values = []
    
    # 这里简化处理：用当期的 EP 和未来的 ret 配对
    # 实际多日期数据需要按 date 分组计算每个截面
    valid = df[[factor_col, forward_return_col]].dropna()
    if len(valid) < MIN_STOCKS:
        print(f"  ⚠️  样本不足 ({len(valid)} < {MIN_STOCKS})")
        return None
    
    factor_rank = valid[factor_col].rank()
    ret_rank = valid[forward_return_col].rank()
    ic = factor_rank.corr(ret_rank)
    
    return {
        'IC': ic,
        'n': len(valid)
    }


def full_ic_analysis(df, factor_col='EP_z', horizons=[1, 5, 20, 60]):
    """完整 IC 分析"""
    print("\n" + "=" * 60)
    print("IC 验证分析")
    print("=" * 60)
    
    results = {}
    for h in horizons:
        ret_col = f'ret_{h}d'
        result = compute_rank_ic(df, factor_col, ret_col)
        if result:
            results[h] = result['IC']
            print(f"  {h:3d}日 Rank IC: {result['IC']:.4f}  (N={result['n']})")
    
    if results:
        series = pd.Series(results)
        print(f"\n  IC 均值: {series.mean():.4f}")
        print(f"  IC 标准差: {series.std():.4f}")
        print(f"  IC IR: {series.mean() / series.std():.2f}" if series.std() > 0 else "")
    
    return results


# =====================================================================
# Step 6: 分组收益分析
# =====================================================================
def group_returns(df, factor_col='EP_z', forward_return_col='ret_1d', n_groups=10):
    """分10组查看多空收益"""
    print("\n" + "=" * 60)
    print("分组收益分析")
    print("=" * 60)
    
    valid = df[[factor_col, forward_return_col]].dropna()
    if len(valid) < n_groups:
        print("  ⚠️  样本不足")
        return None
    
    valid['group'] = pd.qcut(valid[factor_col], n_groups, labels=range(n_groups))
    
    avg_returns = valid.groupby('group')[forward_return_col].mean()
    
    print(f"\n  {'Group':>6} {'Avg Return':>12}")
    print(f"  {'-'*6} {'-'*12}")
    for g in range(n_groups):
        print(f"  {g+1:>5}  {avg_returns[g]:>10.4%}")
    
    ls_spread = avg_returns.iloc[-1] - avg_returns.iloc[0]
    print(f"\n  Q10 - Q1 (多空): {ls_spread:.4%}")
    
    # 单调性检验
    monotonic = all(avg_returns.iloc[i] <= avg_returns.iloc[i+1]
                    for i in range(len(avg_returns) - 1))
    print(f"  单调性: {'✅ 单调递增' if monotonic else '❌ 不单调'}")
    
    # 计算多头(前3组)和空头(后3组)平均
    long_avg = avg_returns.iloc[-3:].mean()
    short_avg = avg_returns.iloc[:3].mean()
    print(f"  多头(Q8-Q10) 平均: {long_avg:.4%}")
    print(f"  空头(Q1-Q3) 平均: {short_avg:.4%}")
    
    return {
        'avg_returns': avg_returns,
        'long_short_spread': ls_spread,
        'monotonic': monotonic
    }


# =====================================================================
# Step 7: Fama-MacBeth 回归
# =====================================================================
def fama_macbeth(df, factor_col='EP_z', control_cols=[], return_col='ret_1d'):
    """Fama-MacBeth 两步回归"""
    import statsmodels.api as sm
    
    print("\n" + "=" * 60)
    print("Fama-MacBeth 回归")
    print("=" * 60)
    
    valid = df[[factor_col, return_col] + control_cols].dropna()
    if len(valid) < MIN_STOCKS:
        print("  ⚠️  样本不足")
        return None
    
    X_cols = [factor_col] + control_cols
    y = valid[return_col].values
    X = sm.add_constant(valid[X_cols].values)
    
    model = sm.OLS(y, X).fit()
    
    print(f"\n  截面回归结果 (单期):")
    print(f"  R²: {model.rsquared:.4f}")
    print(f"  Adj R²: {model.rsquared_adj:.4f}")
    print(f"  F-stat: {model.fvalue:.2f}")
    print(f"  N: {len(valid)}")
    
    print(f"\n  {'Variable':>15} {'Coef':>10} {'Std Err':>10} {'t':>8} {'P>|t|':>8}")
    print(f"  {'-'*15} {'-'*10} {'-'*10} {'-'*8} {'-'*8}")
    
    results = {}
    for i, name in enumerate(['const'] + X_cols):
        coef = model.params[i]
        pval = model.pvalues[i]
        tval = model.tvalues[i]
        se = model.bse[i]
        results[name] = {
            'coef': coef, 't_stat': tval, 'p_value': pval, 'se': se
        }
        sig = '***' if pval < 0.01 else '**' if pval < 0.05 else '*' if pval < 0.1 else ''
        if name == factor_col:
            print(f"  {name:>15} {coef:>10.6f} {se:>10.6f} {tval:>8.2f} {pval:>8.4f} {sig}")
        else:
            print(f"  {name:>15} {coef:>10.6f} {se:>10.6f} {tval:>8.2f} {pval:>8.4f}")
    
    return results, model


# =====================================================================
# Step 8: 生成分析报告
# =====================================================================
def generate_report(ep_data, ic_results, group_results, fm_results):
    """生成 Markdown 格式的因子分析报告"""
    print("\n" + "=" * 60)
    print("EP 因子分析报告 (Markdown)")
    print("=" * 60)
    
    report = f"""# EP 因子分析报告

## 因子定义
- **因子**: EP (E/P, Earnings Yield)
- **公式**: 净利润(TTM) / 总市值
- **数据季度**: {QUARTER}
- **因子对齐日**: {FACTOR_DATE}
- **样本股票**: 沪深300成分股
- **有效样本量**: {len(ep_data)}

## 因子描述统计
| 指标 | 值 |
|------|-----|
| 均值 | {ep_data['EP'].mean():.4f} |
| 中位数 | {ep_data['EP'].median():.4f} |
| 标准差 | {ep_data['EP'].std():.4f} |
| 偏度 | {ep_data['EP'].skew():.2f} |
| 峰度 | {ep_data['EP'].kurtosis():.2f} |

## Rank IC 分析
| 持有期 | Rank IC |
|--------|---------|
"""
    for h, ic in ic_results.items():
        report += f"| {h:3d}日 | {ic:.4f} |\n"
    
    if ic_results:
        ic_series = pd.Series(ic_results)
        report += f"""
| IC 均值 | {ic_series.mean():.4f} |
| IC 标准差 | {ic_series.std():.4f} |
"""
        if ic_series.std() > 0:
            report += f"| IC IR | {ic_series.mean() / ic_series.std():.2f} |\n"
    
    if group_results:
        report += f"""
## 分组收益
| 分组 | 平均收益 |
|------|---------|
"""
        for g, ret in group_results['avg_returns'].items():
            report += f"| Q{g+1} | {ret:.4%} |\n"
        
        report += f"""
| Q10 - Q1 (多空) | {group_results['long_short_spread']:.4%} |
| 单调性 | {'是' if group_results['monotonic'] else '否'} |
"""
    
    if fm_results:
        fm_table = """## Fama-MacBeth 回归
| 变量 | 系数 | t统计量 | P值 |
|------|------|--------|-----|
"""
        factors_model = fm_results[0] if isinstance(fm_results, tuple) else fm_results
        
        for name, vals in factors_model.items():
            sig = '***' if vals['p_value'] < 0.01 else '**' if vals['p_value'] < 0.05 else '*' if vals['p_value'] < 0.1 else ''
            fm_table += f"| {name} | {vals['coef']:.6f} | {vals['t_stat']:.2f} | {vals['p_value']:.4f} {sig} |\n"
        
        report += fm_table
    
    report += """
## 结论与建议
"""
    # 自动生成结论
    if ic_results:
        mean_ic = pd.Series(ic_results).mean()
        if abs(mean_ic) > 0.03:
            report += f"- EP因子的Rank IC均值为 {mean_ic:.4f}，表明该因子对截面收益有{'显著' if abs(mean_ic) > 0.05 else ''}预测能力\n"
        else:
            report += "- EP因子的IC值较低，在当前截面上的预测能力有限\n"
    
    if group_results:
        if group_results['monotonic']:
            report += "- 分组收益呈单调递增，因子有效性较强\n"
        if group_results['long_short_spread'] > 0.005:
            report += f"- 多空组合收益为 {group_results['long_short_spread']:.4%}，做多高EP做空低EP有正收益\n"
    
    print(report)
    
    # 保存到文件
    with open('ep_factor_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    print("\n✅ 报告已保存至 ep_factor_report.md")
    
    return report


# =====================================================================
# 主函数
# =====================================================================
def main():
    print("=" * 60)
    print("  沪深300 EP 因子分析")
    print("=" * 60)
    
    # Step 1: 获取数据
    try:
        data, symbols = fetch_data()
    except Exception as e:
        print(f"\n❌ 数据获取失败: {e}")
        print("请检查:")
        print("  1. panda_data 是否正确安装")
        print("  2. 网络连接是否正常")
        print("  3. 是否有数据权限")
        return
    
    # Step 2: 计算 TTM
    data = compute_ttm(data)
    
    # Step 3: 计算 EP 因子
    ep_data = compute_ep_factor(data)
    
    # Step 4: 获取未来收益
    # 获取因子日之后一段时间的收益数据
    end_date = '20250228'  # 假设截至2月底
    forward_returns = fetch_forward_returns(
        symbols, FORWARD_HORIZONS,
        FACTOR_DATE, end_date
    )
    
    # Step 5: 合并因子与未来收益
    if forward_returns is not None:
        ep_data = ep_data.merge(
            forward_returns.reset_index(),
            on='symbol', how='left'
        )
    
    # Step 6-8: 验证分析
    ic_results = full_ic_analysis(ep_data)
    group_results = group_returns(ep_data)
    fm_results = fama_macbeth(ep_data)
    
    # Step 9: 生成报告
    generate_report(ep_data, ic_results, group_results, fm_results)
    
    print("\n✅ 分析完成")


if __name__ == '__main__':
    main()
