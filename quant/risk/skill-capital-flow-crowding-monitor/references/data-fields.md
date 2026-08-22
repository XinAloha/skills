# 数据字段映射 (data-fields) — 2026-07-27 实测确认

## get_margin（融资融券 · 杠杆情绪）
| 字段 | 含义 | 风险/资金语义 |
|---|---|---|
| margin_balance | 融资余额 | **杠杆资金主轴**：余额增=加杠杆看多，减=去杠杆 |
| short_balance | 融券余额 | 融券做空规模 |
| total_balance | 总余额 | 两融合计 |
| buy_on_margin_value | 融资买入额 | 当日新增融资买入 |
| short_sell_quantity | 融券卖出量 | 当日做空量 |
| margin_type | cash=融资 / stock=融券 | 区分买卖方向 |

> 资金强度用 `margin_balance` 窗口变化率的 z-score。融资余额持续上升 = 杠杆情绪升温（散户/杠杆盘做多）。

## get_hsgt_hold（北向持股 · 外资/聪明钱）
| 字段 | 含义 | 风险/资金语义 |
|---|---|---|
| holding_ratio | 持股比例(%) | **外资态度主轴**：比例升=外资加仓，降=减仓 |
| shares_num | 持股数量 | 持股绝对量（受股本变动影响，比例更稳） |
| adjusted_holding_ratio | 调整后持股比例 | 口径调整后的比例 |

> 资金强度用 `holding_ratio` 逐日差分（百分点变化）的 z-score。北向常被视为"聪明钱"，与两融背离时提示分歧。

## get_block_trade（大宗交易 · 机构/大股东）
| 字段 | 含义 | 风险/资金语义 |
|---|---|---|
| price | 成交价 | 折溢价分子 |
| volume | 成交量 | 规模 |
| amount | 成交额 | **净承接额主轴** |
| buyer | 买方营业部 | 含"机构专用"=机构承接 |
| seller | 卖方营业部 | 含"机构专用"=机构出货 |
| sequence_id | 序列号 | — |

> ⚠️ **无现成"折溢价"字段**——须自算：`(price − close) / close × 100`，`close` 取自 `get_stock_daily`。
> 溢价成交=承接意愿强（看多），折价成交=甩卖/出货。机构专用买方=承接(+)，机构专用卖方=出货(−)。

## get_stock_daily（个股日线 · 大宗折溢价分母）
| 字段 | 含义 | 用途 |
|---|---|---|
| close | 当日收盘价 | 大宗折溢价分母（自算折溢价） |

## get_industry_constituents / get_concept_constituents（板块展开）
输入行业/概念名，展开成成分股代码，逐只跑三源资金画像后聚合。

## 注意
- 网关模式返回行数受套餐配额限制，大板块需分批。
- 北向持股披露滞后，须按披露日对齐；口径调整用 adjusted_holding_ratio。
- 大宗交易 T+N 披露，当日可能无记录属正常。
- 日期统一 YYYYMMDD。
