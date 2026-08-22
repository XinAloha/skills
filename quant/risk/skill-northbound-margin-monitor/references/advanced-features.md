# 高级功能参考

## Streamlit 仪表盘

```bash
streamlit run dashboard/app.py
```

仪表盘提供以下视图：
- 综合情绪仪表（评分趋势 + 五维雷达图）
- 北向资金历史流向图
- 融资融券热力图
- 股指期货基差/持仓监控
- 共振/背离信号时间线

访问 `http://localhost:8501` 查看。

---

## MCP Server

MCP Server 允许通过 Claude Desktop 或其他 MCP 客户端直接调用全景监控功能。

### 启动

```bash
python mcp_server.py           # stdio 模式（默认，适用于 Claude Desktop）
python mcp_server.py --sse     # SSE 模式（适用于远程调用）
```

### 可用工具

| 工具 | 说明 | 关键参数 |
|------|------|----------|
| `run_panorama_monitor` | 运行全景监控分析 | `date` (YYYYMMDD), `top_n`, `use_llm` |
| `get_latest_report` | 获取最新报告 | `full_content` (true=全文) |
| `check_trading_day` | 检查 A 股交易日 | `date` (YYYYMMDD) |

### Claude Desktop 配置

```json
{
  "mcpServers": {
    "panorama-monitor": {
      "command": "python",
      "args": ["D:/python/PandaAI/Pandaai_skill_02/mcp_server.py"],
      "env": {
        "ANTHROPIC_AUTH_TOKEN": "your-api-key",
        "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
        "ANTHROPIC_MODEL": "claude-sonnet-4-20250514"
      }
    }
  }
}
```

---

## 回测框架

验证信号体系的历史有效性：

```python
from core.backtest import run_ic_backtest

# IC 分析
result = run_ic_backtest(nb_history, margin_history, min_window=60)
print(result.ic_summary)           # Spearman rank IC 统计
print(result.detector_ic_stats)    # 每个检测器的 IC 表现
print(result.by_regime)            # 按市场状态的 IC 分解

# 分层回测
from core.backtest import run_stratified_backtest
strat = run_stratified_backtest(scores, forward_returns, n_groups=5)
print(strat.group_returns)         # 各组等权收益
print(strat.cumulative_returns)    # 累计收益曲线
```

### 回测指标

| 指标 | 说明 |
|------|------|
| Rank IC | Spearman 秩相关系数（评分 vs N日远期收益） |
| IC IR | 平均 IC / IC 标准差 |
| IC 胜率 | IC > 0 的交易日占比 |
| IC 衰减 | 多期限 IC 分析（1/3/5/10/20 日） |
| 分层收益 | 按总分分 5 组等权收益 |
| 按状态分解 | 牛/熊/震荡市各自 IC |

回测数据来自 `output/` 目录的历史 JSON 报告。至少需要 60 个交易日数据。

---

## 缓存管理

```bash
# 清理 N 天前的缓存
python run.py --cleanup-cache 30

# 手动管理
ls cache/                    # 查看缓存目录
# YYYYMMDD/                  # 每日数据缓存
# nb_flow_history.parquet    # 北向流向历史（持久化，跨运行保留）
# sw_industry_mapping.parquet # 申万行业缓存（30天有效期）
# shenwan_backup.parquet     # 申万离线备份（永不过期）
```

缓存策略：
- 每日数据缓存：按日期分区，30 天后自动清理
- 北向流向历史：持续累积，不自动清理
- 申万行业：30 天缓存 + 离线永备 + API 三级降级链

---

## 报告校验

```bash
# 校验指定日期的报告
python scripts/validate_report.py --date 20260630

# 校验最新报告
python scripts/validate_report.py --latest

# JSON 输出（用于 CI）
python scripts/validate_report.py --date 20260630 --json
```

校验规则：
- 12 节结构完整性检查
- 数据源标签覆盖率检查
- 评分分项一致性检查
- 措辞合规检查（禁止投资建议表述）
- 25 个信号检测器覆盖率检查
