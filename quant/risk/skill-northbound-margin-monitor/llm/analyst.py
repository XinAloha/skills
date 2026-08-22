"""LLM macro analyst: interprets panorama signals holistically via DeepSeek/Claude API.

Unlike the per-stock screener, this produces ONE macro-level analysis per run,
synthesising all 12 northbound + margin signals, 4 resonance patterns, and the
composite score into a comprehensive market regime assessment.

Supports Anthropic Claude and DeepSeek (via Anthropic-compatible endpoint).
Set ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic for DeepSeek.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Prompt template
# ------------------------------------------------------------------

PANORAMA_PROMPT_TEMPLATE = """你是一位资深 A 股宏观策略分析师，专精于资金面和市场情绪分析。
以下是今日北向资金（沪深港通）+ 融资融券 + 股指期货全景监控的全部信号数据。
请基于这些信号，做一次专业的宏观资金面研判。

## 综合评分
{composite_summary}

## 北向资金信号（{nb_count}项）
{nb_signals_table}

## 融资融券信号（{mg_count}项）
{mg_signals_table}

## 股指期货信号
{futures_table}

## 共振/背离分析
{resonance_table}

## 关键宏观数据
{macro_data}

## 要求
1. **市场状态判断**：当前资金面处于什么阶段？（进攻/防守/观望）用一句话总结。
2. **三维交叉验证**：北向、融资、期货三个独立维度是否相互印证？如果有矛盾，哪个维度更可信？
3. **风险点识别**：列出 1-3 个最值得警惕的风险信号。
4. **机会点识别**：如果有积极信号，指出可能的机会方向。
5. **操作建议**：分别对短线交易者、中线投资者、长期配置资金给出差异化建议（各一句话）。
6. **次日观察清单**：列出明天需要重点关注的 2-3 个指标/数据。
7. 语言专业但不晦涩，用「可能」「倾向于」「值得关注」等概率化措辞，避免绝对判断。
8. 控制在 400-600 字。"""

SUMMARY_PROMPT_TEMPLATE = """你是一位资深 A 股宏观策略分析师。
以下是今日资金面全景监控的核心信号摘要。请做一次精简研判。

## 综合评分
{composite_summary}

## 核心信号摘要
{nb_signals_table}

{mg_signals_table}

{futures_table}

{resonance_table}

## 关键宏观数据
{macro_data}

## 要求
1. **市场状态**：用一句话判断当前资金面阶段（进攻/防守/观望）。
2. **核心矛盾**：指出当前最关键的 1-2 个多空博弈焦点。
3. **操作建议**：给出短线和中线各一句话建议。
4. 语言精炼，控制在 150-200 字。"""


def build_panorama_prompt(
    composite_score: float,
    composite_grade: str,
    composite_label: str,
    composite_summary: str,
    nb_signals: list,
    margin_signals: list,
    resonance_results: list,
    margin_balance_亿: float = 0,
    short_balance_亿: float = 0,
    margin_buy_亿: float = 0,
    top_industries: Optional[list[str]] = None,
    futures_signals: list | None = None,
    summary_mode: bool = False,
) -> str:
    """Build the LLM prompt from panorama signal results.

    Args:
        composite_score: 0-100 composite score.
        composite_grade: Letter grade (A+ to F-).
        composite_label: Chinese label.
        composite_summary: One-line summary from scorer.
        nb_signals: List of northbound SignalResult.
        margin_signals: List of margin SignalResult.
        resonance_results: List of ResonanceResult.
        margin_balance_亿: Total margin balance in 亿 CNY.
        short_balance_亿: Total short balance in 亿 CNY.
        margin_buy_亿: Total margin buy amount in 亿 CNY.
        top_industries: Top industry names for context.
        futures_signals: List of futures SignalResult (optional).
        summary_mode: If True, use shorter template for 150-200 word output.

    Returns:
        Formatted prompt string ready for the LLM.
    """
    # Composite summary line
    composite_line = (
        f"综合评分 {composite_score:.0f}/100（{composite_grade} — {composite_label}）\n"
        f"解读：{composite_summary}"
    )

    # Northbound signals table
    nb_lines: list[str] = []
    for s in nb_signals:
        direction_icon = {"bullish": "看多", "bearish": "看空", "neutral": "中性"}.get(s.direction, "中性")
        triggered = "触发" if s.triggered else "未触发"
        nb_lines.append(
            f"| {s.label} | {triggered} | {direction_icon} | 强度{s.strength:+.2f} | {s.summary} |"
        )
    nb_table = "\n".join(nb_lines) if nb_lines else "（无北向数据）"

    # Margin signals table
    mg_lines: list[str] = []
    for s in margin_signals:
        direction_icon = {"bullish": "看多", "bearish": "看空", "neutral": "中性"}.get(s.direction, "中性")
        triggered = "触发" if s.triggered else "未触发"
        mg_lines.append(
            f"| {s.label} | {triggered} | {direction_icon} | 强度{s.strength:+.2f} | {s.summary} |"
        )
    mg_table = "\n".join(mg_lines) if mg_lines else "（无融资融券数据）"

    # Resonance table
    res_lines: list[str] = []
    for r in resonance_results:
        direction_icon = {"bullish": "看多", "bearish": "看空", "neutral": "中性"}.get(r.direction, "中性")
        triggered = "触发" if r.triggered else "未触发"
        desc = r.description if r.description else r.summary
        res_lines.append(f"| {r.label} | {triggered} | {direction_icon} | {desc} |")
    resonance_table = "\n".join(res_lines) if res_lines else "（无共振/背离信号）"

    # Futures signals table
    futures_signals = futures_signals or []
    fut_lines: list[str] = []
    for s in futures_signals:
        direction_icon = {"bullish": "看多", "bearish": "看空", "neutral": "中性"}.get(s.direction, "中性")
        triggered = "触发" if s.triggered else "未触发"
        fut_lines.append(
            f"| {s.label} | {triggered} | {direction_icon} | 强度{s.strength:+.2f} | {s.summary} |"
        )
    futures_table = "\n".join(fut_lines) if fut_lines else "（无股指期货数据）"

    # Macro data
    industries_str = "、".join(top_industries[:5]) if top_industries else "数据不可用"
    macro_data = (
        f"- 融资余额：{margin_balance_亿:.0f} 亿元\n"
        f"- 融券余额：{short_balance_亿:.0f} 亿元\n"
        f"- 融资买入额：{margin_buy_亿:.0f} 亿元\n"
        + (f"- 融资/融券比：{margin_balance_亿 / short_balance_亿:.1f}\n" if short_balance_亿 > 0 else "")
        + f"- 重点行业：{industries_str}"
    )

    template = SUMMARY_PROMPT_TEMPLATE if summary_mode else PANORAMA_PROMPT_TEMPLATE
    return template.format(
        composite_summary=composite_line,
        nb_signals_table=nb_table,
        mg_signals_table=mg_table,
        resonance_table=resonance_table,
        futures_table=futures_table,
        macro_data=macro_data,
        nb_count=len(nb_signals),
        mg_count=len(margin_signals),
    )


# ------------------------------------------------------------------
# Fallback generation
# ------------------------------------------------------------------

def _generate_fallback(
    composite_score: float,
    composite_label: str,
    nb_triggered: int,
    mg_triggered: int,
    resonance_triggered: int,
    margin_balance_亿: float = 0,
    nb_signals: list | None = None,
    margin_signals: list | None = None,
    futures_signals: list | None = None,
    resonance_results: list | None = None,
) -> str:
    """Generate rule-based macro analysis when LLM is unavailable.

    Extracts precise metrics from signal ``detail`` dicts for richer
    fallback content, matching the quality of LLM-generated analysis
    as closely as possible without an API call.
    """
    # ── Extract precise metrics from signal details ──

    def _find_signal(signals, key):
        """Find a signal by key in a list of SignalResult / ResonanceResult."""
        for s in (signals or []):
            if getattr(s, "key", "") == key or getattr(s, "pattern", "") == key:
                return s
        return None

    # Margin metrics
    margin_buy_ratio = None
    margin_balance_trend_pct = None
    short_change_pct = None
    margin_short_ratio = None
    margin_short_ratio_change = None

    buy_ratio_sig = _find_signal(margin_signals, "margin_buy_ratio")
    if buy_ratio_sig and hasattr(buy_ratio_sig, "detail"):
        margin_buy_ratio = buy_ratio_sig.detail.get("estimated_ratio")
        margin_buy_亿_val = buy_ratio_sig.detail.get("margin_buy_亿")

    balance_sig = _find_signal(margin_signals, "margin_balance_trend")
    if balance_sig and hasattr(balance_sig, "detail"):
        margin_balance_trend_pct = balance_sig.detail.get("change_vs_ma20_pct")

    short_sig = _find_signal(margin_signals, "short_trend")
    if short_sig and hasattr(short_sig, "detail"):
        short_change_pct = short_sig.detail.get("change_rate_pct")

    msr_sig = _find_signal(margin_signals, "margin_short_ratio")
    if msr_sig and hasattr(msr_sig, "detail"):
        margin_short_ratio = msr_sig.detail.get("current_ratio")
        margin_short_ratio_change = msr_sig.detail.get("change_5d_pct")

    # Northbound metrics
    nb_consecutive_days = None
    nb_flow_direction = None
    cumulative_ma_gap = None
    cumulative_regime = None

    flow_sig = _find_signal(nb_signals, "flow_trend")
    if flow_sig and hasattr(flow_sig, "detail"):
        nb_consecutive_days = flow_sig.detail.get("consecutive_days")

    market_flow_sig = _find_signal(nb_signals, "market_flow_direction")
    if market_flow_sig and hasattr(market_flow_sig, "detail"):
        if market_flow_sig.detail.get("aligned"):
            nb_flow_direction = "沪股通+深股通方向一致"
        else:
            sh_d = market_flow_sig.detail.get("sh_direction", "")
            sz_d = market_flow_sig.detail.get("sz_direction", "")
            nb_flow_direction = f"沪{sh_d}/深{sz_d}分歧"

    cum_sig = _find_signal(nb_signals, "cumulative_trend")
    if cum_sig and hasattr(cum_sig, "detail"):
        cumulative_regime = cum_sig.detail.get("regime")
        cumulative_ma_gap = cum_sig.detail.get("gap")

    # Futures metrics
    futures_basis_pct = None
    futures_basis_count = None

    basis_sig = _find_signal(futures_signals, "futures_basis")
    if basis_sig and hasattr(basis_sig, "detail"):
        futures_basis_pct = basis_sig.detail.get("avg_basis_pct")
        futures_basis_count = basis_sig.detail.get("n_positive", 0)
        n_total = basis_sig.detail.get("n_total", 3)

    # Resonance
    resonance_labels = []
    for r in (resonance_results or []):
        if getattr(r, "triggered", False):
            resonance_labels.append(getattr(r, "label", ""))

    # ── Build analysis ──

    # Determine regime
    if composite_score >= 65:
        regime = "偏进攻"
        regime_detail = "资金面整体向好，北向与融资信号偏多"
    elif composite_score >= 45:
        regime = "观望偏多"
        regime_detail = "资金面中性，多空信号均衡，建议等待更明确的方向确认"
    elif composite_score >= 30:
        regime = "防御偏谨慎"
        regime_detail = "资金面偏空，存在需要关注的风险信号"
    else:
        regime = "防御"
        regime_detail = "资金面显著偏空，多项风险信号触发，建议降低仓位控制风险"

    # Cross-validation: compare dimensions
    cross_parts: list[str] = []
    nb_bullish = sum(1 for s in (nb_signals or []) if getattr(s, "direction", "") == "bullish" and getattr(s, "triggered", False))
    mg_bullish = sum(1 for s in (margin_signals or []) if getattr(s, "direction", "") == "bullish" and getattr(s, "triggered", False))

    if nb_bullish >= 2 and mg_bullish >= 2:
        cross_parts.append("北向与融资方向一致偏多，存在做多共振基础")
    elif nb_bullish <= 1 and mg_bullish <= 1:
        cross_parts.append("北向与融资均偏谨慎，市场缺乏明确方向")
    else:
        cross_parts.append("北向与融资信号存在方向分歧，多空博弈激烈")

    if futures_basis_pct is not None and futures_basis_pct < -1.0:
        cross_parts.append(f"期货深度贴水{futures_basis_pct:.1f}%，机构套保压力显著")
    elif futures_basis_pct is not None and futures_basis_pct > 1.0:
        cross_parts.append(f"期货升水{futures_basis_pct:.1f}%，机构情绪偏乐观")

    # Risk identification
    risks: list[str] = []
    if margin_buy_ratio is not None and margin_buy_ratio >= 0.15:
        risks.append(f"融资买入比{margin_buy_ratio*100:.0f}%（≥15%警戒线），过度杠杆风险显著")
    elif margin_buy_ratio is not None and margin_buy_ratio >= 0.10:
        risks.append(f"融资买入比{margin_buy_ratio*100:.0f}%（≥10%偏热），杠杆情绪升温")
    elif mg_triggered >= 5:
        risks.append("融资融券多项信号触发，杠杆情绪活跃，需关注过度杠杆风险")

    if resonance_triggered > 0 and resonance_labels:
        risks.append(f"共振/背离信号触发：{'、'.join(resonance_labels)}，跨市场信号需重点关注")
    elif resonance_triggered > 0:
        risks.append(f"共振/背离信号触发（{resonance_triggered}项），跨市场信号需重点关注")

    if margin_balance_亿 > 30000:
        risks.append(f"融资余额{margin_balance_亿:.0f}亿处于历史高位，去杠杆风险上升")

    if short_change_pct is not None and short_change_pct > 5:
        risks.append(f"融券余额{short_change_pct:.1f}%加速增长，空头情绪升温")

    if cumulative_regime and "加速流出" in str(cumulative_regime):
        risks.append(f"北向累计趋势处于「{cumulative_regime}」状态，外资中期偏空")

    if futures_basis_pct is not None:
        n_total_val = basis_sig.detail.get("n_total", 3) if basis_sig else 3
        if futures_basis_count is not None and futures_basis_count == 0 and n_total_val > 0:
            risks.append("三大期指全线贴水，专业机构一致避险")

    risk_text = "\n".join(f"  - {r}" for r in risks) if risks else "  - 当前无显著极端风险信号"

    # Signal overview
    nb_total = len(nb_signals) if nb_signals else 7
    mg_total = len(margin_signals) if margin_signals else 7
    nb_info = f"{nb_triggered}/{nb_total} 触发" if nb_triggered else "无触发"
    mg_info = f"{mg_triggered}/{mg_total} 触发" if mg_triggered else "无触发"

    # Build enriched summary line
    metric_details: list[str] = []
    if margin_buy_ratio is not None:
        metric_details.append(f"融资买入比{margin_buy_ratio*100:.0f}%{'（过热）' if margin_buy_ratio >= 0.15 else '（偏热）'}")
    if margin_balance_trend_pct is not None:
        metric_details.append(f"融资余额较MA20 {margin_balance_trend_pct:+.1f}%")
    if nb_consecutive_days is not None and abs(nb_consecutive_days) > 0:
        metric_details.append(f"北向连续{abs(nb_consecutive_days)}日{'净流入' if nb_consecutive_days > 0 else '净流出'}")
    if futures_basis_pct is not None:
        metric_details.append(f"期货{'贴水' if futures_basis_pct < 0 else '升水'}{abs(futures_basis_pct):.2f}%")

    cross_text = "；".join(cross_parts) if cross_parts else "多维度信号无显著交叉"

    return (
        f"## 市场状态\n\n"
        f"当前资金面处于 **{regime}** 阶段。{regime_detail}。\n\n"
        f"### 三维交叉验证\n\n"
        f"{cross_text}。\n\n"
        + (f"### 关键指标\n\n" + "\n".join(f"- {d}" for d in metric_details) + "\n\n" if metric_details else "")
        + f"## 信号概况\n\n"
        f"- 北向资金：{nb_info}\n"
        f"- 融资融券：{mg_info}\n"
        f"- 综合评分：{composite_score:.0f}/100（{composite_label}）\n\n"
        f"## 风险提示\n\n"
        f"{risk_text}\n\n"
        f"## 操作参考\n\n"
        f"- 短线：{'减少操作频率，等待信号明朗' if composite_score < 45 else '关注强势板块，快进快出'}\n"
        f"- 中线：{'控制仓位，等待右侧确认信号' if composite_score < 55 else '可适度参与，设好止盈止损'}\n"
        f"- 长线：{'分批布局优质标的，利用调整建仓' if composite_score >= 35 else '暂停加仓，等待系统性风险释放'}\n\n"
        f"> 此为规则引擎自动生成的基础分析（含精确指标提取），完整分析需配置 LLM 后运行。"
    )


# ------------------------------------------------------------------
# LLM Analyst
# ------------------------------------------------------------------

class LLMAnalyst:
    """Generate macro panorama analysis using Claude or DeepSeek API.

    Set ANTHROPIC_BASE_URL to use DeepSeek or other Anthropic-compatible endpoints.
    ANTHROPIC_MODEL selects the model (default: claude-sonnet-4-6).
    """

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._model = (
            os.getenv("ANTHROPIC_MODEL")
            or self._config.get("llm", {}).get("model", "claude-sonnet-4-6")
        )
        self._max_tokens = int(
            self._config.get("llm", {}).get("max_tokens", 2048)
        )
        self._base_url = os.getenv("ANTHROPIC_BASE_URL") or None
        self._timeout = float(self._config.get("llm", {}).get("timeout", 120.0))
        self._max_retries_http = int(self._config.get("llm", {}).get("max_retries", 2))
        self._max_retries_llm = int(self._config.get("llm", {}).get("llm_retries", 3))
        self._client = None
        self._api_key: Optional[str] = None

    @property
    def client(self):
        """Lazy-init the Anthropic client.

        API key resolution (in order):
        1. ANTHROPIC_API_KEY env var
        2. ANTHROPIC_AUTH_TOKEN env var (used by DeepSeek deployments)
        3. llm.api_key in config.json
        """
        if self._client is not None:
            return self._client

        import anthropic

        self._api_key = (
            os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("ANTHROPIC_AUTH_TOKEN")
            or self._config.get("llm", {}).get("api_key", "")
        )

        if not self._api_key or self._api_key == "sk-xxx":
            raise RuntimeError(
                "LLM API key not configured. Set one of:\n"
                "  - ANTHROPIC_API_KEY\n"
                "  - ANTHROPIC_AUTH_TOKEN\n"
                "  - llm.api_key in config.json"
            )

        client_kwargs: dict = {
            "api_key": self._api_key,
            "timeout": self._timeout,
            "max_retries": self._max_retries_http,
        }
        if self._base_url:
            client_kwargs["base_url"] = self._base_url
        self._client = anthropic.Anthropic(**client_kwargs)
        return self._client

    def _call_llm_with_retry(self, prompt: str) -> str:
        """Call the LLM API with exponential backoff retry on transient errors.

        Retries on: RateLimitError, APIConnectionError, InternalServerError,
        APITimeoutError. Gives up after ``self._max_retries_llm`` attempts.

        Returns the raw response text, or raises the last exception.
        """
        from tenacity import (
            retry,
            stop_after_attempt,
            wait_exponential,
            retry_if_exception_type,
        )
        from anthropic import (
            RateLimitError,
            APIConnectionError,
            InternalServerError,
            APITimeoutError,
        )

        retryable = (RateLimitError, APIConnectionError, InternalServerError, APITimeoutError)

        @retry(
            stop=stop_after_attempt(self._max_retries_llm),
            wait=wait_exponential(multiplier=2, min=2, max=10),
            retry=retry_if_exception_type(retryable),
            reraise=True,
        )
        def _call() -> str:
            client = self.client
            resp = client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            text_parts: list[str] = []
            blocks = getattr(resp, "content", None) or []
            for block in blocks:
                if hasattr(block, "type") and getattr(block, "type", "") in (
                    "thinking", "thinking_delta", "redacted_thinking",
                ):
                    continue
                if hasattr(block, "text") and block.text:
                    text_parts.append(block.text)
            text = "".join(text_parts).strip()
            if not text and hasattr(resp, "text"):
                raw_text = getattr(resp, "text", None)
                if isinstance(raw_text, str) and raw_text.strip():
                    text = raw_text.strip()
            if not text:
                raise RuntimeError("LLM returned empty response")
            return text

        return _call()

    def analyze(
        self,
        composite_score: float,
        composite_grade: str,
        composite_label: str,
        composite_summary: str,
        nb_signals: list,
        margin_signals: list,
        resonance_results: list,
        margin_balance_亿: float = 0,
        short_balance_亿: float = 0,
        margin_buy_億: float = 0,
        top_industries: Optional[list[str]] = None,
        futures_signals: list | None = None,
        summary_mode: bool = False,
    ) -> tuple[str, str, str]:
        """Generate macro panorama analysis via LLM.

        Args:
            (all the signal + data inputs for the prompt)
            summary_mode: If True, generate a shorter 150-200 word summary.

        Returns:
            (analysis_text, source, model) where source is "real" or "fallback"
            and model is the actual model identifier used.
        """
        nb_triggered = sum(1 for s in nb_signals if s.triggered)
        mg_triggered = sum(1 for s in margin_signals if s.triggered)
        res_triggered = sum(1 for r in resonance_results if r.triggered)

        prompt = build_panorama_prompt(
            composite_score=composite_score,
            composite_grade=composite_grade,
            composite_label=composite_label,
            composite_summary=composite_summary,
            nb_signals=nb_signals,
            margin_signals=margin_signals,
            resonance_results=resonance_results,
            margin_balance_亿=margin_balance_亿,
            short_balance_亿=short_balance_亿,
            margin_buy_亿=margin_buy_億,
            top_industries=top_industries,
            futures_signals=futures_signals,
            summary_mode=summary_mode,
        )

        # Try API call
        try:
            client = self.client
        except RuntimeError as e:
            logger.warning("LLM not available: %s — using fallback", e)
            fallback = _generate_fallback(
                composite_score, composite_label,
                nb_triggered, mg_triggered, res_triggered,
                margin_balance_亿,
                nb_signals=nb_signals,
                margin_signals=margin_signals,
                futures_signals=futures_signals,
                resonance_results=resonance_results,
            )
            return fallback, "fallback", self._model

        try:
            text = self._call_llm_with_retry(prompt)
            logger.info("LLM analysis generated (%d chars, model=%s)", len(text), self._model)
            return text, "real", self._model

        except Exception as e:
            logger.warning("LLM API call failed: %s — using fallback", e)
            fallback = _generate_fallback(
                composite_score, composite_label,
                nb_triggered, mg_triggered, res_triggered,
                margin_balance_亿,
                nb_signals=nb_signals,
                margin_signals=margin_signals,
                futures_signals=futures_signals,
                resonance_results=resonance_results,
            )
            return fallback, "fallback", self._model
