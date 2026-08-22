"""归因实现自检：用构造出已知答案的合成数据，验证归因的数学恒等式与护栏。

归因天然适合做恒等式测试——各效应加总必须精确等于主动收益，
纯配置组合的选股项必须为 0，纯选股组合的配置项必须为 0，
因子面板合计必须与行业面板合计对同一区间主动收益。
任何一条不满足，说明实现有 bug，直接 FAIL。

用法：python validate.py   （全部通过退出码 0，否则 1）
"""

import sys
import traceback

import numpy as np
import pandas as pd

from attribution import (
    EFFECT_COLS,
    brinson_multi_period,
    brinson_single_period,
    build_panel,
    check_duplicates,
    factor_attribution,
)

RNG = np.random.default_rng(20260721)
TOL = 1e-10


# ---------------------------------------------------------------------------
# 合成数据工具
# ---------------------------------------------------------------------------

def make_universe(n_symbols=40, n_sectors=5):
    symbols = [f"S{i:03d}" for i in range(n_symbols)]
    sectors = pd.DataFrame(
        {"symbol": symbols,
         "sector": [f"IND{i % n_sectors}" for i in range(n_symbols)]}
    )
    return symbols, sectors


def random_weights(symbols, dates, rng):
    rows = []
    for d in dates:
        w = rng.random(len(symbols))
        w /= w.sum()
        rows.extend({"date": d, "symbol": s, "weight": x}
                    for s, x in zip(symbols, w))
    return pd.DataFrame(rows)


def random_returns(symbols, dates, rng, scale=0.02):
    rows = []
    for d in dates:
        r = rng.normal(0.0, scale, len(symbols))
        rows.extend({"date": d, "symbol": s, "ret": x}
                    for s, x in zip(symbols, r))
    return pd.DataFrame(rows)


def make_panel(pw, bw, ret, sectors):
    return build_panel(pw.copy(), bw.copy(), ret.copy(), sectors.copy())


# ---------------------------------------------------------------------------
# 数学恒等式测试
# ---------------------------------------------------------------------------

def test_single_period_identity():
    """单期：配置+选股+交互 加总 == 主动收益（随机数据，逐日验证）。"""
    symbols, sectors = make_universe()
    dates = pd.date_range("2026-01-05", periods=10, freq="B")
    panel = make_panel(random_weights(symbols, dates, RNG),
                       random_weights(symbols, dates, RNG),
                       random_returns(symbols, dates, RNG), sectors)
    for _, g in panel.groupby("date"):
        eff, Rp, Rb = brinson_single_period(g)
        assert abs(eff["total"].sum() - (Rp - Rb)) < TOL


def test_zero_active():
    """组合 == 基准时，所有效应必须为 0。"""
    symbols, sectors = make_universe()
    dates = pd.date_range("2026-01-05", periods=5, freq="B")
    w = random_weights(symbols, dates, RNG)
    panel = make_panel(w, w, random_returns(symbols, dates, RNG), sectors)
    res = brinson_multi_period(panel)
    assert res["linked"][EFFECT_COLS].abs().max().max() < TOL
    assert abs(res["Rp_total"] - res["Rb_total"]) < TOL


def test_pure_allocation():
    """行业内个股收益一致（无选股空间）时，选股与交互必须为 0。"""
    symbols, sectors = make_universe()
    dates = pd.date_range("2026-01-05", periods=5, freq="B")
    sec_of = dict(zip(sectors["symbol"], sectors["sector"]))
    rows = []
    for d in dates:
        sec_ret = {s: RNG.normal(0, 0.02) for s in sectors["sector"].unique()}
        rows.extend({"date": d, "symbol": s, "ret": sec_ret[sec_of[s]]}
                    for s in symbols)
    panel = make_panel(random_weights(symbols, dates, RNG),
                       random_weights(symbols, dates, RNG),
                       pd.DataFrame(rows), sectors)
    res = brinson_multi_period(panel)
    assert res["linked"]["selection"].abs().max() < TOL
    assert res["linked"]["interaction"].abs().max() < TOL


def test_pure_selection():
    """行业权重与基准一致（组合内个股权重不同）时，配置与交互必须为 0。"""
    symbols, sectors = make_universe()
    dates = pd.date_range("2026-01-05", periods=5, freq="B")
    bw = random_weights(symbols, dates, RNG)
    merged = bw.merge(sectors, on="symbol")
    rows = []
    for (d, _), g in merged.groupby(["date", "sector"]):
        w = RNG.random(len(g))
        w = w / w.sum() * g["weight"].sum()
        rows.extend({"date": d, "symbol": s, "weight": x}
                    for s, x in zip(g["symbol"], w))
    pw = pd.DataFrame(rows)
    panel = make_panel(pw, bw, random_returns(symbols, dates, RNG), sectors)
    res = brinson_multi_period(panel)
    assert res["linked"]["allocation"].abs().max() < TOL
    assert res["linked"]["interaction"].abs().max() < TOL


def test_carino_linking_identity():
    """多期：链接后所有效应加总 == 区间几何主动收益。"""
    symbols, sectors = make_universe()
    dates = pd.date_range("2026-01-05", periods=60, freq="B")
    panel = make_panel(random_weights(symbols, dates, RNG),
                       random_weights(symbols, dates, RNG),
                       random_returns(symbols, dates, RNG), sectors)
    res = brinson_multi_period(panel)
    active = res["Rp_total"] - res["Rb_total"]
    assert abs(res["linked"]["total"].sum() - active) < 1e-8
    recomputed = res["linked"][EFFECT_COLS].sum(axis=1)
    assert (recomputed - res["linked"]["total"]).abs().max() < 1e-8


def test_factor_attribution_exact():
    """收益严格由因子暴露线性生成时，特质项必须为 0，因子贡献合计 == 区间主动收益。"""
    symbols, sectors = make_universe()
    dates = pd.date_range("2026-01-05", periods=10, freq="B")
    factor_cols = ["mom", "value", "size"]
    expo_rows, ret_rows = [], []
    for d in dates:
        X = RNG.normal(0, 1, (len(symbols), len(factor_cols)))
        f = RNG.normal(0, 0.01, len(factor_cols))
        y = 0.001 + X @ f          # 严格线性 + 截距，无特质噪声
        for i, s in enumerate(symbols):
            expo_rows.append({"date": d, "symbol": s,
                              **dict(zip(factor_cols, X[i]))})
            ret_rows.append({"date": d, "symbol": s, "ret": y[i]})
    panel = make_panel(random_weights(symbols, dates, RNG),
                       random_weights(symbols, dates, RNG),
                       pd.DataFrame(ret_rows), sectors)
    res = factor_attribution(panel, pd.DataFrame(expo_rows), factor_cols)
    assert abs(res["summary"]["specific"]) < 1e-8, "线性收益下特质项应为 0"
    contrib_sum = sum(res["summary"][c] for c in factor_cols)
    assert abs(contrib_sum - res["summary"]["active_total"]) < 1e-8


def test_factor_reconciles_brinson():
    """关键修复回归测试：任意（含噪声、非线性）收益下，因子面板合计
    （各因子贡献 + 特质）必须与 Brinson 行业面板合计对同一区间主动收益。
    早期版本因子归因用算术加总、行业归因用 Carino 几何链接，两者对不上账——此测试锁死。"""
    symbols, sectors = make_universe()
    dates = pd.date_range("2026-01-05", periods=30, freq="B")
    factor_cols = ["mom", "value"]
    expo_rows, ret_rows = [], []
    for d in dates:
        X = RNG.normal(0, 1, (len(symbols), len(factor_cols)))
        f = RNG.normal(0, 0.01, len(factor_cols))
        y = X @ f + RNG.normal(0, 0.02, len(symbols))    # 含大量特质噪声
        for i, s in enumerate(symbols):
            expo_rows.append({"date": d, "symbol": s, **dict(zip(factor_cols, X[i]))})
            ret_rows.append({"date": d, "symbol": s, "ret": y[i]})
    panel = make_panel(random_weights(symbols, dates, RNG),
                       random_weights(symbols, dates, RNG),
                       pd.DataFrame(ret_rows), sectors)
    bri = brinson_multi_period(panel)
    fac = factor_attribution(panel, pd.DataFrame(expo_rows), factor_cols)
    active = bri["Rp_total"] - bri["Rb_total"]
    fac_total = sum(fac["summary"][c] for c in factor_cols) + fac["summary"]["specific"]
    assert abs(bri["linked"]["total"].sum() - active) < 1e-7, "行业面板未对上区间主动收益"
    assert abs(fac_total - active) < 1e-7, "因子面板未对上区间主动收益（Carino 口径不一致）"


# ---------------------------------------------------------------------------
# 护栏测试
# ---------------------------------------------------------------------------

def test_csv_leading_zero_symbols():
    """回归测试：csv 里 A 股代码 '000001' 若按 pandas 默认 dtype 读取会变成整数 1——
    前导零丢失，且与 'CASH' 等字符串符号 merge 时直接抛类型错误。
    read_table 必须把 date/symbol/sector 按字符串读。"""
    import os
    import tempfile
    from attribution import read_table

    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "benchmark.csv")
        pd.DataFrame({
            "date": ["20250701", "20250701"],
            "symbol": ["000001", "600000"],
            "weight": [0.5, 0.5],
        }).to_csv(p, index=False)
        df = read_table(p)
        assert df["symbol"].tolist() == ["000001", "600000"], \
            f"前导零丢失: {df['symbol'].tolist()}"
        assert df["date"].dtype == object
        pw = pd.DataFrame({"date": ["20250701"], "symbol": ["CASH"], "weight": [1.0]})
        pw.merge(df, on=["date", "symbol"], how="outer")


def test_weight_sum_guard():
    """权重加总明显不为 1 时必须报错，而不是给出错误归因。"""
    from attribution import check_weights
    df = pd.DataFrame({"date": ["2026-01-05"] * 2,
                       "symbol": ["A", "B"],
                       "weight": [0.4, 0.4]})
    try:
        check_weights(df, "组合")
    except ValueError:
        return
    raise AssertionError("权重加总 0.8 未被拦截")


def test_duplicate_key_guard():
    """新增护栏：权重/收益表出现重复 (date, symbol) 必须报错，
    而不是在 merge 时静默重复计权（早期版本会算出错误归因）。"""
    dup = pd.DataFrame({
        "date": ["2026-01-05", "2026-01-05", "2026-01-05"],
        "symbol": ["A", "A", "B"],         # A 重复
        "weight": [0.6, 0.6, 0.4],
    })
    try:
        check_duplicates(dup, ("date", "symbol"), "组合权重")
    except ValueError:
        return
    raise AssertionError("重复主键 (A) 未被拦截")


def test_html_report_selfcontained():
    """HTML 报告必须自包含（无外部网络依赖）、含全部行业+因子数据、结构合法。"""
    from attribution import (render_html, brinson_multi_period,
                             factor_attribution, build_json_report)
    symbols, sectors = make_universe()
    dates = pd.date_range("2026-01-05", periods=8, freq="B")
    factor_cols = ["mom", "value"]
    expo_rows, ret_rows = [], []
    for d in dates:
        X = RNG.normal(0, 1, (len(symbols), len(factor_cols)))
        f = RNG.normal(0, 0.01, len(factor_cols))
        y = X @ f + RNG.normal(0, 0.02, len(symbols))
        for i, s in enumerate(symbols):
            expo_rows.append({"date": d, "symbol": s, **dict(zip(factor_cols, X[i]))})
            ret_rows.append({"date": d, "symbol": s, "ret": y[i]})
    panel = make_panel(random_weights(symbols, dates, RNG),
                       random_weights(symbols, dates, RNG),
                       pd.DataFrame(ret_rows), sectors)
    bri = brinson_multi_period(panel)
    fac = factor_attribution(panel, pd.DataFrame(expo_rows), factor_cols)
    html = render_html(build_json_report(bri, fac))

    assert "<svg" in html and "waterfall" in html and "sectors" in html
    assert html.count("<head>") == 1 and html.count("<body>") == 1
    for bad in ('src="http', 'href="http', '<link', '<script src', 'cdn.', '@import', 'url(http'):
        assert bad not in html, f"HTML 引用了外部资源: {bad}"
    # 数据嵌入且可定位
    assert '"sectors"' in html and '"factors"' in html and '"active"' in html


def test_return_sanity_warns():
    """收益合理性护栏：出现 |日收益|>21% 的脏值(未复权/停牌复牌)必须告警，
    但不修改数据(仅surface风险，清洗交给取数环节)。"""
    import warnings as _w
    from attribution import check_return_sanity
    ret = pd.DataFrame({"date": ["d1"] * 3, "symbol": ["A", "B", "C"],
                        "ret": [0.03, -0.67, 0.02]})   # B 为未复权送转导致的 -67%
    with _w.catch_warnings(record=True) as rec:
        _w.simplefilter("always")
        check_return_sanity(ret)
    assert any("复权" in str(x.message) or "异常" in str(x.message) for x in rec), \
        "脏收益未触发告警"
    # 全部正常收益不应告警
    ok = pd.DataFrame({"date": ["d1"] * 2, "symbol": ["A", "B"], "ret": [0.05, -0.08]})
    with _w.catch_warnings(record=True) as rec2:
        _w.simplefilter("always")
        check_return_sanity(ok)
    assert not rec2, "正常收益不应告警"


def test_zero_weight_sector_no_nan():
    """新增护栏：某行业在组合与基准中权重均为 0 时，效应必须为 0 且不产生 NaN。
    早期版本此处 0*NaN 会让 NaN 混入明细表且被 total 的 skipna 掩盖。"""
    pw = pd.DataFrame({"date": ["d1"] * 3, "symbol": ["A", "B", "Z"], "weight": [0.6, 0.4, 0.0]})
    bw = pd.DataFrame({"date": ["d1"] * 3, "symbol": ["A", "B", "Z"], "weight": [0.5, 0.5, 0.0]})
    ret = pd.DataFrame({"date": ["d1"] * 3, "symbol": ["A", "B", "Z"], "ret": [0.01, -0.01, 0.02]})
    sec = pd.DataFrame({"symbol": ["A", "B", "Z"], "sector": ["IND1", "IND1", "EMPTY"]})
    panel = build_panel(pw, bw, ret, sec)
    eff, Rp, Rb = brinson_single_period(panel)
    assert not eff[EFFECT_COLS].isna().any().any(), "零权重行业产生了 NaN 效应"
    assert eff.loc["EMPTY", EFFECT_COLS].abs().max() < TOL, "零权重行业效应应为 0"
    assert abs(eff["total"].sum() - (Rp - Rb)) < TOL


# ---------------------------------------------------------------------------
# 执行器
# ---------------------------------------------------------------------------

TESTS = [
    test_single_period_identity,
    test_zero_active,
    test_pure_allocation,
    test_pure_selection,
    test_carino_linking_identity,
    test_factor_attribution_exact,
    test_factor_reconciles_brinson,
    test_csv_leading_zero_symbols,
    test_weight_sum_guard,
    test_duplicate_key_guard,
    test_zero_weight_sector_no_nan,
    test_return_sanity_warns,
    test_html_report_selfcontained,
]


def main():
    passed = 0
    for fn in TESTS:
        name = fn.__name__
        try:
            fn()
            print(f"PASS  {name}")
            passed += 1
        except Exception:
            print(f"FAIL  {name}")
            traceback.print_exc()
    print(f"\n{passed}/{len(TESTS)} 通过")
    return 0 if passed == len(TESTS) else 1


if __name__ == "__main__":
    sys.exit(main())
