#!/usr/bin/env python3
"""
Paper Reproduction Engine — 独立回测验证引擎

用法:
    python reproduce_paper.py --config reproduce_config.json
    python reproduce_paper.py --paper "momentum" --symbols rb,if,au --start 2020-01-01 --end 2024-12-31

功能:
  - 从 akshare/yfinance 获取期货数据
  - 实现常见论文策略（TS Momentum, Risk Parity, Cross-Section MOM 等）
  - 波动率目标化
  - 生成 equity curve 和指标报告
"""

import argparse
import json
import os
import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

# Try to import akshare
try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False


# ============================================================
# Data Loading
# ============================================================

def fetch_futures_daily(symbol, start="2020-01-01", end="2024-12-31"):
    """Fetch daily futures data from akshare."""
    if not HAS_AKSHARE:
        print("[ERROR] akshare not installed. pip install akshare")
        return None

    try:
        # akshare futures symbol format: e.g., "rb0" for continuous
        sym = symbol.lower()
        if not sym.endswith("0"):
            sym = f"{sym}0"

        df = ak.futures_zh_daily_sina(symbol=sym)
        df = df.rename(columns={
            "date": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
        })
        df["date"] = pd.to_datetime(df["date"])
        df = df[(df["date"] >= start) & (df["date"] <= end)]
        df = df.sort_values("date").reset_index(drop=True)
        df["symbol"] = symbol
        return df
    except Exception as e:
        print(f"[WARN] Failed to fetch {symbol}: {e}")
        return None


def load_futures_from_csv(csv_path):
    """Load futures data from CSV."""
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


# ============================================================
# Signal Functions
# ============================================================

def signal_tsmom(close, lookback=252):
    """Time-series momentum signal: sign of return over lookback."""
    ret = close.pct_change(lookback)
    return ret.apply(np.sign)


def signal_cross_sectional(close, lookback=252, top_n=None):
    """Cross-sectional momentum: rank assets by return."""
    ret = close.pct_change(lookback)
    if top_n:
        # Only keep top_n assets with positive momentum
        return ret.rank(axis=1, ascending=False).apply(lambda row: row.apply(
            lambda x: 1 if row[row > 0].index.tolist().index(row.name) < top_n else 0
        ), axis=1)
    return ret.rank(axis=1, ascending=False) / close.shape[1]


def signal_vol(close, lookback=20):
    """Volatility signal (inverse vol for weighting)."""
    returns = close.pct_change()
    vol = returns.rolling(lookback).std()
    return 1.0 / vol


def signal_vol_target(returns, target_vol=0.10, lookback=20):
    """Volatility targeting: scale positions to achieve target annual vol."""
    rolling_vol = returns.rolling(lookback).std() * np.sqrt(252)
    scale = target_vol / rolling_vol
    scale = scale.clip(0.1, 3.0)  # Cap leverage
    return scale


# ============================================================
# Portfolio Construction
# ============================================================

def build_portfolio(signals, prices, method="equal", target_vol=0.10):
    """
    Build portfolio weights from signals.

    Methods:
        equal: equal weight
        vol_inv: inverse volatility
        risk_parity: risk parity (approximate)
        signal: signal-weighted
    """
    n_assets = prices.shape[1]
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

    returns = prices.pct_change()

    for t in range(1, len(prices)):
        sig = signals.iloc[t]

        if method == "equal":
            # Equal weight for assets with non-zero signal
            active = sig[sig != 0].index
            if len(active) > 0:
                weights.iloc[t, prices.columns.get_indexer(active)] = 1.0 / len(active)
            else:
                weights.iloc[t] = 0.0

        elif method == "vol_inv":
            vol = returns.iloc[max(0, t - 20):t].std()
            inv_vol = 1.0 / vol.replace(0, np.nan)
            inv_vol = inv_vol.fillna(0)
            active = sig[sig != 0].index
            if len(active) > 0:
                inv_vol_active = inv_vol[active]
                total = inv_vol_active.sum()
                if total > 0:
                    weights.iloc[t, prices.columns.get_indexer(active)] = inv_vol_active / total

        elif method == "risk_parity":
            # Approximate risk parity: w ∝ Σ⁻¹·σ (long-only)
            ret_window = returns.iloc[max(0, t - 60):t]
            if len(ret_window) < 30:
                continue
            cov = ret_window.cov() * 252
            vols = ret_window.std() * np.sqrt(252)
            # Add regularization
            cov = cov + np.eye(cov.shape[0]) * 1e-6
            try:
                cov_inv = np.linalg.inv(cov.values)
                rp_weights = cov_inv @ vols.values
                rp_weights = np.maximum(rp_weights, 0)  # Long-only
                total = rp_weights.sum()
                if total > 0:
                    rp_weights /= total
                    weights.iloc[t] = rp_weights
            except:
                pass

        elif method == "signal":
            # Signal-weighted
            active = sig[sig != 0].index
            if len(active) > 0:
                sig_active = sig[active].abs()
                total = sig_active.sum()
                if total > 0:
                    weights.iloc[t, prices.columns.get_indexer(active)] = sig_active / total

    # Apply volatility targeting
    if target_vol > 0:
        port_returns = (weights.shift(1) * returns).sum(axis=1)
        vol_scale = signal_vol_target(port_returns, target_vol)
        weights = weights.multiply(vol_scale, axis=0)

    return weights.fillna(0)


# ============================================================
# Backtest Engine
# ============================================================

def run_backtest(prices, weights, initial_capital=1_000_000, transaction_cost=0.0001):
    """Run backtest with given prices and weights."""
    returns = prices.pct_change()

    # Portfolio returns (lagged weights to avoid look-ahead)
    port_returns = (weights.shift(1) * returns).sum(axis=1)

    # Transaction costs (weight turnover * cost)
    weight_changes = weights.diff().abs().sum(axis=1)
    costs = weight_changes * transaction_cost

    net_returns = port_returns - costs

    # Equity curve
    equity = initial_capital * (1 + net_returns).cumprod()
    equity = pd.concat([pd.Series(initial_capital, index=[equity.index[0] - pd.Timedelta(days=1)]),
                        equity])

    # Metrics
    total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
    n_years = (equity.index[-1] - equity.index[0]).days / 365.25
    ann_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0
    ann_vol = net_returns.std() * np.sqrt(252)
    sharpe = ann_return / ann_vol if ann_vol > 0 else 0

    # Max drawdown
    rolling_max = equity.expanding().max()
    drawdown = (equity - rolling_max) / rolling_max
    max_dd = drawdown.min()

    # Calmar ratio
    calmar = ann_return / abs(max_dd) if max_dd != 0 else 0

    metrics = {
        "total_return": total_return,
        "annual_return": ann_return,
        "annual_volatility": ann_vol,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_dd,
        "calmar_ratio": calmar,
        "n_years": n_years,
        "n_trading_days": len(net_returns),
    }

    return equity, net_returns, metrics


# ============================================================
# Strategy Registry
# ============================================================

STRATEGIES = {
    "tsmom": {
        "name": "Time-Series Momentum",
        "signal_fn": signal_tsmom,
        "signal_args": {"lookback": 252},
        "portfolio_method": "vol_inv",
        "default_target_vol": 0.10,
        "default_lookback": 252,
    },
    "csmom": {
        "name": "Cross-Sectional Momentum",
        "signal_fn": signal_cross_sectional,
        "signal_args": {"lookback": 252},
        "portfolio_method": "signal",
        "default_target_vol": 0.10,
    },
    "risk_parity": {
        "name": "Risk Parity",
        "signal_fn": lambda close: pd.DataFrame(1.0, index=close.index, columns=close.columns),
        "signal_args": {},
        "portfolio_method": "risk_parity",
        "default_target_vol": 0.10,
    },
    "trend_vol": {
        "name": "Trend + Vol Targeting",
        "signal_fn": signal_tsmom,
        "signal_args": {"lookback": 12},
        "portfolio_method": "vol_inv",
        "default_target_vol": 0.10,
    },
}


# ============================================================
# Main Pipeline
# ============================================================

def run_pipeline(symbols, strategy="tsmom", start="2020-01-01", end="2024-12-31",
                 target_vol=0.10, transaction_cost=0.0001, initial_capital=1_000_000,
                 output_dir="/home/coder/project/replication/paper-replication"):
    """Run the full research pipeline."""
    os.makedirs(output_dir, exist_ok=True)

    print(f"[*] Loading data for {len(symbols)} symbols: {symbols}")
    all_data = {}
    for sym in symbols:
        df = fetch_futures_daily(sym, start, end)
        if df is not None and len(df) > 0:
            all_data[sym] = df
            print(f"    {sym}: {len(df)} days ({df['date'].iloc[0].date()} → {df['date'].iloc[-1].date()})")
        else:
            print(f"    [WARN] No data for {sym}")

    if not all_data:
        print("[ERROR] No data loaded. Check symbols or data source.")
        return

    # Build price matrix
    prices = pd.DataFrame()
    for sym, df in all_data.items():
        prices[sym] = df.set_index("date")["close"]
    prices = prices.dropna(how="all").ffill().dropna()
    print(f"[*] Price matrix: {prices.shape[0]} days × {prices.shape[1]} assets")

    # Get strategy config
    if strategy not in STRATEGIES:
        print(f"[ERROR] Unknown strategy: {strategy}. Available: {list(STRATEGIES.keys())}")
        return

    strat = STRATEGIES[strategy]
    print(f"[*] Strategy: {strat['name']}")

    # Compute signals
    print(f"[*] Computing signals...")
    signals = strat["signal_fn"](prices, **strat["signal_args"])

    # Build portfolio
    print(f"[*] Building portfolio (method: {strat['portfolio_method']}, target_vol: {target_vol})...")
    weights = build_portfolio(signals, prices, method=strat["portfolio_method"], target_vol=target_vol)

    # Run backtest
    print(f"[*] Running backtest...")
    equity, port_returns, metrics = run_backtest(
        prices, weights,
        initial_capital=initial_capital,
        transaction_cost=transaction_cost,
    )

    # Print results
    print("\n" + "=" * 60)
    print(f"  BACKTEST RESULTS — {strat['name']}")
    print("=" * 60)
    print(f"  Period:           {prices.index[0].date()} → {prices.index[-1].date()}")
    print(f"  Assets:           {', '.join(prices.columns)}")
    print(f"  Initial Capital:  {initial_capital:,.0f}")
    print(f"  Final Capital:    {equity.iloc[-1]:,.0f}")
    print(f"  Total Return:     {metrics['total_return']:+.2%}")
    print(f"  Annual Return:    {metrics['annual_return']:+.2%}")
    print(f"  Annual Volatility: {metrics['annual_volatility']:.2%}")
    print(f"  Sharpe Ratio:     {metrics['sharpe_ratio']:.3f}")
    print(f"  Max Drawdown:     {metrics['max_drawdown']:+.2%}")
    print(f"  Calmar Ratio:     {metrics['calmar_ratio']:.3f}")
    print(f"  Trading Days:     {metrics['n_trading_days']}")
    print("=" * 60)

    # Save results
    results = {
        "strategy": strategy,
        "symbols": symbols,
        "start": start,
        "end": end,
        "target_vol": target_vol,
        "metrics": metrics,
    }

    # Save metrics JSON
    metrics_path = os.path.join(output_dir, f"metrics_{strategy}.json")
    with open(metrics_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n[*] Metrics saved to: {metrics_path}")

    # Save equity curve CSV
    equity_path = os.path.join(output_dir, f"equity_{strategy}.csv")
    equity.to_csv(equity_path)
    print(f"[*] Equity curve saved to: {equity_path}")

    # Save weights CSV
    weights_path = os.path.join(output_dir, f"weights_{strategy}.csv")
    weights.to_csv(weights_path)
    print(f"[*] Weights saved to: {weights_path}")

    # Plot equity curve if matplotlib is available
    try:
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams.update({
            "font.family": "DejaVu Sans",
            "axes.unicode_minus": False,
        })
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        axes[0].plot(equity.index, equity.values, linewidth=1)
        axes[0].set_title(f"{strat['name']} - Equity Curve")
        axes[0].set_ylabel("Equity")
        axes[0].grid(True, alpha=0.3)

        # Drawdown
        rolling_max = equity.expanding().max()
        dd = (equity - rolling_max) / rolling_max
        axes[1].fill_between(dd.index, dd.values, 0, alpha=0.5, color="red")
        axes[1].set_title("Drawdown")
        axes[1].set_ylabel("Drawdown %")
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        chart_path = os.path.join(output_dir, f"chart_{strategy}.png")
        plt.savefig(chart_path, dpi=150)
        plt.close()
        print(f"[*] Chart saved to: {chart_path}")
    except Exception as e:
        print(f"[WARN] Could not save chart: {e}")

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Paper Reproduction Backtest Engine")
    parser.add_argument("--symbols", default="rb,if,au", help="Comma-separated symbols")
    parser.add_argument("--strategy", default="tsmom", choices=list(STRATEGIES.keys()),
                       help="Strategy to run")
    parser.add_argument("--start", default="2020-01-01", help="Start date")
    parser.add_argument("--end", default="2024-12-31", help="End date")
    parser.add_argument("--target-vol", type=float, default=0.10, help="Target annual vol")
    parser.add_argument("--cost", type=float, default=0.0001, help="Transaction cost")
    parser.add_argument("--capital", type=float, default=1_000_000, help="Initial capital")
    parser.add_argument("--output-dir", default="/home/coder/project/replication/paper-replication", help="Output directory")
    parser.add_argument("--config", help="Config JSON file (overrides other args)")
    args = parser.parse_args()

    if args.config:
        with open(args.config) as f:
            cfg = json.load(f)
        symbols = cfg.get("symbols", ["rb", "if", "au"])
        strategy = cfg.get("strategy", "tsmom")
        start = cfg.get("start", "2020-01-01")
        end = cfg.get("end", "2024-12-31")
        target_vol = cfg.get("target_vol", 0.10)
        cost = cfg.get("cost", 0.0001)
        capital = cfg.get("capital", 1_000_000)
        output_dir = cfg.get("output_dir", "/home/coder/project/replication/paper-replication")
    else:
        symbols = [s.strip() for s in args.symbols.split(",")]
        strategy = args.strategy
        start = args.start
        end = args.end
        target_vol = args.target_vol
        cost = args.cost
        capital = args.capital
        output_dir = args.output_dir

    run_pipeline(
        symbols=symbols,
        strategy=strategy,
        start=start,
        end=end,
        target_vol=target_vol,
        transaction_cost=cost,
        initial_capital=capital,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
