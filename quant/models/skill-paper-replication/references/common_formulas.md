# Common Quantitative Formulas Reference

## Time-Series Momentum (TSMOM)

**Signal**: `sign(ret_{t-12, t-1})`

```python
signal = np.sign(close[-1] / close[-252] - 1)
```

**Reference**: Moskowitz, Ooi, Pedersen (2012) "Time series momentum"

---

## Cross-Sectional Momentum (CSMOM)

**Signal**: Rank assets by return, go long top decile, short bottom decile

```python
returns = close.pct_change(252)
ranks = returns.rank(axis=1, ascending=False)
long = ranks <= n_assets * 0.1   # Top 10%
short = ranks > n_assets * 0.9   # Bottom 10%
```

**Reference**: Jegadeesh & Titman (1993) "Returns to Buying Winners and Selling Losers"

---

## Risk Parity (RP)

**Weights**: `w ∝ Σ⁻¹ · σ` (long-only, risk contribution equalized)

```python
cov = returns.cov() * 252
vols = returns.std() * np.sqrt(252)
cov_reg = cov + np.eye(n) * 1e-6  # Regularization
cov_inv = np.linalg.inv(cov_reg)
weights = cov_inv @ vols
weights = np.maximum(weights, 0)  # Long-only
weights /= weights.sum()
```

**Reference**: Risk Parity portfolio theory, Bridgewater's All Weather

---

## Agnostic Risk Parity (ARP)

**Weights**: `w ∝ Σ⁻¹ · 1` (no signal, just diversification)

```python
weights = cov_inv @ np.ones(n)
weights = np.maximum(weights, 0)
weights /= weights.sum()
```

**Reference**: "Optimal trend following portfolios" (arxiv: 2201.06635)

---

## Trend on Risk Parity (ToRP)

**Weights**: `w_j ∝ (1/σ_j) × signal_j`

```python
for j in range(n):
    weights[j] = signal[j] / vol[j]
weights /= np.sum(np.abs(weights))
```

---

## Naive Markowitz (NM)

**Weights**: `w ∝ Σ⁻¹ · μ` (where μ = expected return ≈ signal)

```python
mu = signal.values  # Use signal as expected return proxy
weights = cov_inv @ mu
weights /= np.sum(np.abs(weights))
```

---

## Volatility Targeting

**Scale positions** to achieve target annual volatility:

```python
rolling_vol = returns.rolling(20).std() * np.sqrt(252)
scale = target_vol / rolling_vol
scale = scale.clip(0.1, 3.0)  # Cap leverage
scaled_positions = positions * scale
```

**Target Vol**: Typically 10% for papers

---

## Performance Metrics

### Sharpe Ratio
```
SR = (E[R] - Rf) / σ(R)
```
Risk-free rate (Rf) often set to 0 in futures papers.

### Maximum Drawdown
```
MDD = min((equity[t] - peak[:t]) / peak[:t])
```

### Calmar Ratio
```
Calmar = Annual Return / |Max Drawdown|
```

### Sortino Ratio
```
Sortino = (E[R] - Rf) / σ_downside
```
Only penalizes downside volatility.

---

## Position Sizing (Futures → Lots)

```python
contract_multiplier = 10  # tons per lot (varies by contract)
margin_rate = 0.10        # margin requirement

target_value = capital * weight
target_lots = int(target_value / (price * contract_multiplier * margin_rate))
```

### Common Chinese Futures Contract Specs

| Symbol | Exchange | Multiplier | Tick | Margin Rate |
|--------|----------|------------|------|-------------|
| rb     | SHFE     | 10         | 1    | 10%         |
| HC     | SHFE     | 10         | 1    | 10%         |
| IF     | CFFEX    | 300        | 0.2  | 12%         |
| IC     | CFFEX    | 200        | 0.2  | 14%         |
| AU     | SHFE     | 1000       | 0.02 | 8%          |
| CU     | SHFE     | 5          | 10   | 10%         |
| SC     | INE      | 1000       | 0.1  | 10%         |

---

## Covariance Regularization

Large covariance matrices can be unstable. Always add regularization:

```python
epsilon = 1e-6
cov_reg = cov + np.eye(n) * epsilon
```

Or use shrinkage:

```python
from sklearn.covariance import LedoitWolf
lw = LedoitWolf()
cov_shrunk = lw.fit(returns).covariance_
```

---

## Look-Ahead Bias Prevention

**Golden Rule**: Signal at time `t` uses only data up to `t-1`.

```python
# WRONG: Uses current bar's close
signal = (close[-1] - close[-252]) / close[-252]
trade_at_close(signal)  # You already know the close!

# CORRECT: Signal at close of bar t, trade at close of bar t+1
signal = (close[-2] - close[-253]) / close[-253]  # Previous bar
trade_at_close(signal)  # Or use shift(1) in pandas
```

In this standalone research pipeline, prefer explicit Pandas alignment:
compute signals from historical bars, then apply `weights.shift(1)` when calculating
portfolio returns so trades never use future information.
