"""B10 一键演示脚本。

面向第一次接触本 BUILD 的人：用合成的 60 天 × 200 股因子面板，串完
"validate_input → make_report → write_report (HTML) → write_production (Parquet)"
全链路，把产物落到 ``开发产物/demo_output/``，在没有真实因子库 / 没有
PandaAI 凭证的情况下也能在本地完整看到 B10 跑通。

用法（在 ``build-b10-factor-evaluation/开发产物/`` 下执行）：

    python scripts/demo.py                    # 五分组 + 全A股
    python scripts/demo.py --group-mode decile  # 十分组
    python scripts/demo.py --bootstrap-n 200 --cost-grid-bps 1,3,5  # 高级诊断

产物（默认在 ``demo_output/``）：

- ``demo_panel.csv``         合成的标准评价面板，可拿去当其它 BUILD 的输入样例
- ``demo_report.html``       科研级 HTML 报告（双击浏览器打开即可）
- ``demo_production.parquet`` 生产库格式的 Parquet（可被 ``生产产物/`` 读端兼容）
- 控制台打印 summary（RankIC / ICIR / 多空累计 / 单调性 / quality 是否通过）

红线
----
- 本脚本是 **演示**，不联网、不依赖外部因子库；用 numpy 合成因子，作为"标准面板
  长啥样"的活样例。
- 跑完后的 HTML 和 Parquet 与生产路径产物结构 100% 等价（同一套 ``run /
  write_report / write_production`` 入口），区别只是因子从合成数据来。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from build import run, write_production  # noqa: E402
from visual_report import write_report  # noqa: E402


def _make_demo_panel(
    n_days: int = 60,
    n_assets: int = 200,
    seed: int = 20260607,
    signal_strength: float = 0.012,
    noise_scale: float = 0.020,
) -> pd.DataFrame:
    """合成一个"信号略强于噪声"的标准评价面板。

    口径与 ``tests/fixtures.make_pool_sample`` 一致，扩展到 60 天 × 200 股，并
    带上多周期 ``forward_return_{n}d`` 和 ``is_pool_*`` 标签，演示衰减曲线和
    股票池下拉的真实效果。
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2026-01-02", periods=n_days, freq="B")
    assets = [f"{i:06d}.SZ" for i in range(1, n_assets + 1)]
    rows = []
    for date in dates:
        factor = rng.normal(size=n_assets)
        # forward_return = 信号 + 噪声，确保 demo 报告真的体现 RankIC > 0
        base_return = signal_strength * factor + rng.normal(scale=noise_scale, size=n_assets)
        for asset, fv, fr in zip(assets, factor, base_return):
            rows.append(
                {
                    "trade_date": date,
                    "ts_code": asset,
                    "factor_value": float(fv),
                    "forward_return": float(fr),
                    # 多周期收益：让 RankIC 衰减曲线非平凡（持有期越长信号越散）
                    "forward_return_1d": float(fr),
                    "forward_return_2d": float(fr * 0.85 + rng.normal(scale=noise_scale * 0.5)),
                    "forward_return_3d": float(fr * 0.70 + rng.normal(scale=noise_scale * 0.6)),
                    "forward_return_5d": float(fr * 0.50 + rng.normal(scale=noise_scale * 0.7)),
                    "forward_return_10d": float(fr * 0.25 + rng.normal(scale=noise_scale * 0.9)),
                    "forward_return_20d": float(rng.normal(scale=noise_scale)),
                }
            )
    df = pd.DataFrame(rows)
    # 股票池标签：演示 HTML 顶部"股票池下拉"
    numeric = df["ts_code"].str.slice(0, 6).astype(int)
    df["is_pool_all_a"] = True
    df["is_pool_hs300"] = numeric <= 50
    df["is_pool_zz500"] = numeric.between(51, 100)
    df["is_pool_zz1000"] = numeric.between(101, 150)
    df["is_pool_zz2000"] = numeric.between(151, 200)
    df["stock_pool_memberships"] = "全A股"
    df.loc[df["is_pool_hs300"], "stock_pool_memberships"] = "全A股|沪深300"
    df.loc[df["is_pool_zz500"], "stock_pool_memberships"] = "全A股|中证500"
    df.loc[df["is_pool_zz1000"], "stock_pool_memberships"] = "全A股|中证1000"
    df.loc[df["is_pool_zz2000"], "stock_pool_memberships"] = "全A股|中证2000"
    df["primary_stock_pool"] = df["stock_pool_memberships"].str.split("|").str[-1]
    return df


def _parse_int_list(value: str | None) -> list[int]:
    if not value:
        return []
    return [int(item.strip()) for item in str(value).split(",") if item.strip()]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="B10 一键演示：合成因子 → 评估 → HTML + 生产 Parquet")
    parser.add_argument("--n-days", type=int, default=60)
    parser.add_argument("--n-assets", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260607)
    parser.add_argument(
        "--group-mode",
        default="quintile",
        choices=["quintile", "decile", "5", "10", "五分组", "十分组"],
    )
    parser.add_argument(
        "--stock-pool",
        default="all_a",
        choices=["all_a", "hs300", "zz500", "zz1000", "zz2000"],
    )
    parser.add_argument("--target-id", default="b10-demo-synthetic-factor")
    parser.add_argument("--data-version", default="b10-demo-v1")
    parser.add_argument("--bootstrap-n", type=int, default=0, help="RankIC 噪声基线 shuffle 次数；0 表示关闭")
    parser.add_argument("--cost-grid-bps", default="", help="交易成本敏感性扫描，逗号分隔，如 '1,3,5'")
    parser.add_argument("--output-dir", default="demo_output", help="演示产物输出目录")
    parser.add_argument("--no-report", action="store_true", help="只跑评估与生产库写入，不生成 HTML")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    panel = _make_demo_panel(args.n_days, args.n_assets, args.seed)
    panel_path = output_dir / "demo_panel.csv"
    panel.to_csv(panel_path, index=False, encoding="utf-8-sig")

    config = {
        "target_id": args.target_id,
        "data_version": args.data_version,
        "group_mode": args.group_mode,
        "stock_pool": args.stock_pool,
        "bootstrap_n": args.bootstrap_n,
        "cost_grid_bps": _parse_int_list(args.cost_grid_bps),
    }

    # 1) run() 一行结果，控制台展示 summary 关键指标
    result = run(panel, config)
    report = json.loads(result.loc[0, "result_json"])
    summary = report["summary"]

    # 2) 生产 Parquet（按主键 upsert，原子写）
    production_path = output_dir / "demo_production.parquet"
    write_production(panel, production_path, config, mode="overwrite")

    # 3) HTML 报告（默认）
    report_path = None
    if not args.no_report:
        report_path = output_dir / "demo_report.html"
        write_report(panel, report_path, config)

    # 4) 控制台输出
    print("=" * 64)
    print("B10 一键演示完成")
    print("=" * 64)
    print(f"合成面板:    {panel_path}  ({len(panel):>6d} 行)")
    print(f"生产 Parquet: {production_path}")
    if report_path is not None:
        print(f"HTML 报告:   {report_path}  (双击浏览器打开)")
    print("-" * 64)
    print("评估摘要:")
    print(f"  样本     : {summary['date_count']} 天 × {summary['asset_count']} 股 = {summary['sample_count']} 行")
    print(f"  股票池   : {summary['stock_pool_label']} ({summary['stock_pool']})")
    print(f"  分组数   : {summary['group_count']} ({summary['group_mode']})")
    print(f"  RankIC    : {summary['rank_ic']:+.4f}    ICIR(rank): {summary['rank_icir']:+.3f}")
    print(f"  多空累计  : {summary['long_short_cumulative_return']:+.4f}    多空 IR: {summary['long_short_ir']:+.3f}")
    print(f"  顶组换手率: {summary['average_turnover']:+.4f}")
    print(f"  单调性    : {'通过' if summary['monotonicity_passed'] else '未通过'}")
    print(f"  优质达标  : {'是' if summary['quality_check_passed'] else '研究中'}")
    if report.get("bootstrap_baseline"):
        b = report["bootstrap_baseline"]
        print(f"  bootstrap : observed={b['observed']:+.4f}  p={b['p_two_sided']:.4f}  n_boot={b['n_boot']}")
    if report.get("transaction_cost", {}).get("sweep"):
        sweep = report["transaction_cost"]["sweep"]
        sweep_lines = [
            "{:.0f}bps -> {:+.4f}".format(row["cost_bps"], row["net_long_short_cumulative_return"])
            for row in sweep
        ]
        print(f"  cost sweep: {sweep_lines}")
    print("=" * 64)
    print(
        "提示：上面 result_json 已写入 demo_production.parquet 的 result_json 列；\n"
        "      可用 ``pd.read_parquet`` 读出，或用 daily_runner.py 把别的因子接进来。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
