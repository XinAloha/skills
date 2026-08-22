# Handoff Schema

这个文件定义 `factor-idea-generation` 与 `factor-pool-evolution` 之间的交接格式。

只有通过字段、未来信息、逻辑一致性和重复性自检的 shortlist 候选，才应转换为可执行 seed factor。

## 顶层格式

输出文件建议命名为 `custom_seed_factors.json`：

```json
{
  "factors": []
}
```

## 单个因子格式

```json
{
  "factors": [
    {
      "name": "factor_volume_exhaustion_reversal",
      "description": "放量下跌后量能衰竭的短期反转候选。",
      "formula": "negative_return_3d * volume_shock_3d * volume_decay_gate",
      "code": "def factor_volume_exhaustion_reversal(df):\n    data = df.copy()\n    ordered = data.sort_values(['instrument', 'date'])\n    grouped = ordered.groupby('instrument', group_keys=False)\n    ret_3d = grouped['close'].pct_change(3)\n    vol_avg_20d = grouped['volume'].transform(lambda s: s.rolling(20, min_periods=10).mean())\n    volume_shock = ordered['volume'] / vol_avg_20d.replace(0, np.nan)\n    volume_decay = -grouped['volume'].pct_change(3)\n    values = (-ret_3d) * volume_shock * volume_decay.clip(lower=0)\n    values = values.replace([np.inf, -np.inf], np.nan)\n    return values.reindex(df.index)\n",
      "metadata": {
        "source_skill": "factor-idea-generation",
        "source_layer": "price_volume_dynamics",
        "source_idea": "seed_volume_exhaustion_reversal",
        "source_lenses": [
          {
            "lens_id": "price_volume_coherence.volume_exhaustion",
            "origin": "builtin",
            "source_ids": []
          }
        ],
        "research_source_ids": [],
        "suggested_horizon_days": 5,
        "validation_status": "unvalidated_research_candidate"
      }
    }
  ]
}
```

## 代码约束

- 函数名应与 `name` 一致，或定义为 `alpha`。
- 函数接收一个长表 `pandas.DataFrame`，返回与输入等长且索引可对齐的 `pandas.Series`。
- 标准列为 `date`、`instrument`、`open`、`high`、`low`、`close`、`volume`。
- 时间序列计算前按 `instrument` 和 `date` 排序。
- rolling、shift、pct_change 只能使用当前时点和历史数据。
- 使用 `np`、`pd` 和 `math` 时不需要在代码字符串里 import；下游执行器会提供它们。
- 显式处理除零、`inf` 和 `NaN`。
- 不读取文件、网络、环境变量或凭证。
- 使用外部研究信息时，把 Lens 来源复制到 `metadata.source_lenses`，把引用来源 ID 复制到 `metadata.research_source_ids`。

## 交接步骤

1. 将 `custom_seed_factors.json` 放在用户可访问路径。
2. 在 `factor-pool-evolution` 的 `evolution_input.json` 中设置：

```json
{
  "custom_seed_factors_json_path": "custom_seed_factors.json"
}
```

3. 运行下游 skill 的 prepare / evaluate 流程。

## 边界

生成代码只表示“具备执行格式”，不表示因子有效。所有候选仍需经过语法检查、样本数据执行、未来信息检查、RankIC / RankICIR 评估和样本外验证。
