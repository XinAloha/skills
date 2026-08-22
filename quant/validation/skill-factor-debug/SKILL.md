---
name: factor-debug
description: Use when an agent needs to debug failed, unstable, suspicious, or numerically
  broken quantitative factors, including NaN checks, signal validation, look-ahead
  bias probes, horizon mismatch, checksum drift, and correlation violations.
quantSkills:
  project_type: skill
  category: tooling
  tags:
  - factor-debug
  - look-ahead-bias
  - signal-validation
  - data-integrity
  - quant-research
  platforms:
  - claude-code
  - codex
  - openclaw
  - cursor
  status: stable
  validation_level: listed
  maintainer_type: community
  summary_zh: 不是 IDE 调试器，而是因子崩溃 / 失效 / 数值异常的诊断手册：按"症状 → 候选病因 → 验证手段"组织的 9 类速查表，专治"因子跑挂"和"看似太好怀疑有
    bug"。
  summary_en: Factor debugging playbook for NaNs, signal validation failures, look-ahead
    bias, horizon mismatch, checksum drift, and correlation violations.
  license: GPL-3.0
---

```json qsh-form
{
  "version": 1,
  "task": {
    "placeholder": "请粘贴报错、异常表现、日志路径、相关代码或最小复现信息",
    "required": true
  },
  "fields": [
    {
      "key": "factor",
      "label": "内置因子",
      "type": "select",
      "default": "momentum_20",
      "help": "若填写了自定义表达式，则以表达式为准",
      "options": [
        { "value": "momentum_20", "label": "动量（20日）" },
        { "value": "reversal_5", "label": "反转（5日）" },
        { "value": "lowvol_20", "label": "低波动（20日）" },
        { "value": "alpha101_101", "label": "Alpha101 #101" },
        { "value": "alpha101_12", "label": "Alpha101 #12" },
        { "value": "corr_open_vol", "label": "量价背离" }
      ]
    },
    {
      "key": "expr",
      "label": "自定义因子表达式",
      "type": "textarea",
      "placeholder": "如：-1 * correlation(rank(open), rank(volume), 10)"
    },
    {
      "key": "universe",
      "label": "股票池",
      "type": "select",
      "default": "000300.SH",
      "options": [
        { "value": "000300.SH", "label": "沪深300" },
        { "value": "000905.SH", "label": "中证500" },
        { "value": "399006.SZ", "label": "创业板指" },
        { "value": "000852.SH", "label": "中证1000" }
      ]
    },
    {
      "key": "horizon",
      "label": "预测周期",
      "type": "select",
      "default": "5",
      "options": [
        { "value": "1", "label": "未来1日" },
        { "value": "5", "label": "未来5日" },
        { "value": "10", "label": "未来10日" }
      ]
    }
  ],
  "prompt_template": "{{#task}}任务与材料：\n{{task}}\n\n{{/task}}{{#attachments}}用户上传的材料（已放入工作区）：\n{{attachments}}\n\n{{/attachments}}若任务材料中已指明出问题的因子/表达式，以材料为准；否则默认调试因子 {{factor}}{{#expr}}（自定义表达式优先：{{expr}}）{{/expr}}。在股票池 {{universe}}、预测周期 {{horizon}} 日下排查失败、数值异常或可疑结果，先依据日志和最小复现定位根因，再检查 NaN、信号契约、未来函数、周期错配、校验和、相关性与不确定性，输出中文报告。"
}
```

# Factor Debug

> 因子跑挂 / 跑出来不对劲 / 怀疑有未来函数。本 skill 是按"症状 → 候选病因 → 验证手段"组织的诊断手册。

## 核心规则

1. **先看错误日志**：`journal/last_failed/run_XXXX_error.txt` 是第一现场
2. **症状速查表先用**（见下面"工作流"），90% 问题 5 类
3. **未来函数自检**：信号通过校验但 IC > 0.15 → 几乎一定是 bug，不是真信号
4. **不要盲改**：先二分定位是哪个因子 / 哪一行的问题
5. **revert 不是修复**：找到病因再改，否则下次还崩

## 症状速查表（按出现频率）

| 症状 | 最可能病因 | 跳到 references |
|---|---|---|
| `PermissionError: 黑名单` | alpha.py 含禁词 | `forbidden-tokens.md` |
| `ValueError: HORIZON not in (1,3,5,10,20)` | HORIZON 不在白名单 | `horizon-mismatch.md` |
| `ValueError: 截面 mean/std 不在阈值` | 信号未 z-score / 被极端值拉跨 | `signal-validation.md` |
| `RuntimeError: checksum mismatch` | parquet 数据被改 | `data-integrity.md` |
| 信号校验通过但 IC > 0.20 | **未来函数** | `look-ahead-bias.md` |
| 回测全空仓 / 全 NaN | universe 错 / 涨跌停剔过狠 | `backtest-anomaly.md` |
| 因子相关性 > 0.85 报错 | 新因子换皮 | `correlation-violation.md` |
| Sharpe 远 > IC_IR | close 当成交价 / 没扣手续费 / T+0 | `look-ahead-bias.md` |
| 同代码两次结果不同 | 顺序 / 种子 / 浮点 reduction | `nondeterminism.md` |

## 工作流（5 步）

```
1. 看错误日志：cat journal/last_failed/run_XXXX_error.txt
2. 用症状速查表定位病因类型
3. 读对应 references 修复
4. 隔离最小复现：python -c "import alpha; alpha.run(...)"
5. 跑 smoke test → py runner.py once
```

## 二分定位法（崩溃但报错不明确时）

```
1. 把 FACTORS 列表减半（前一半 / 后一半）
2. 跑 smoke test，看哪一半崩
3. 重复二分，直到锁定单个因子
4. 看那个因子的实现：是数值异常（除零）/ 长 lookback NaN / 还是其它
```

## 接口映射

| 概念 | 你的项目对应 |
|---|---|
| 错误日志 | `journal/last_failed/` / `logs/` / stderr |
| 黑名单禁词 | `program.md §6.1` / runner 的静态扫描器 |
| 信号校验 | `prepare.validate_signal()` / 你的 `validate_signal` |
| 数据 checksum | `cache/splits.json` / 项目内的 hash 校验 |

## 按需加载

| 何时读 | 文件 |
|---|---|
| 看到 PermissionError 黑名单 | `references/forbidden-tokens.md` |
| 信号校验失败 | `references/signal-validation.md` |
| HORIZON 报错 | `references/horizon-mismatch.md` |
| 怀疑未来函数 | `references/look-ahead-bias.md` |
| 回测异常 | `references/backtest-anomaly.md` |
| 相关性过高 | `references/correlation-violation.md` |
| checksum 报错 | `references/data-integrity.md` |
| 不可复现 | `references/nondeterminism.md` |

## QA 检查清单（修复后）

- [ ] 真的找到病因，不是只 revert？
- [ ] 隔离最小复现验证过修复有效？
- [ ] 修完跑了 smoke test？
- [ ] 修完跑了 runner once 看主分？
- [ ] 如果是未来函数，三段 IC 已经分别验证过？

## 跨工具适配

- OpenAI Codex / Assistants → `agents/openai.yaml`
- Cursor → `agents/cursor-rule.mdc`
- 无原生 skill 机制 → `agents/portable-loader.md`

---

## 项目边界（量化研究合规声明）

> 按 QUANTSKILLS 社区规则 §8 声明。

- **数据来源**：本 skill 不附带任何市场数据；使用者需自行准备行情面板（OHLCV / 涨跌停 / 停牌状态等），数据合法性与许可由使用者负责。
- **假设与参数**：默认假设见各 references（T+1 开盘成交、Top 10% 等权、双边 15bp 手续费、A 股涨跌停规则等）。这些是**研究阶段的标准化假设**，不等同于真实交易。
- **已知限制**：
  - 不模拟市场冲击、不模拟集合竞价滑点、不模拟券池融券约束
  - 不处理分红除权除息 / 配股 / 重大事件停牌的复杂情形
  - 默认 pooled cross-section 范式，对单股序列建模、时序模型不适用
- **风险边界**：本 skill 输出的因子分数 / 回测净值 / IC 诊断结果，**仅反映在历史数据 + 假设条件下的统计表现**，不代表未来表现。
- **用途定位**：**仅供量化研究、教育与方法论参考**。不构成任何形式的投资建议、交易信号或获利保证。使用者据此进行实盘交易的全部后果由使用者自负。
