"""
Decision Agent node — LLM-based trading signal generation.
Builds a rich multi-section prompt from the full TradingState (Market, TA, Portfolio, Risk),
calls the configured LLM using structured outputs, and maps signals to BUY/SELL/WAIT.
"""

from __future__ import annotations

from decimal import Decimal
import json
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from app.agents.interfaces.base import AgentDependencies, BaseAgent
from app.agents.prompts.templates import DECISION_SYSTEM_PROMPT, DECISION_USER_TEMPLATE
from app.domain.enums.trading import TradingSignal

if TYPE_CHECKING:
    from app.agents.graph.state import TradingState


class TradingDecision(BaseModel):
    """Structured output schema for LLM decisions."""

    signal: str = Field(description="Actionable trading signal: MUST be one of 'BUY', 'SELL', or 'WAIT'")
    confidence: float = Field(description="Confidence score for the signal, between 0.0 and 1.0")
    reasoning: str = Field(description="Step-by-step technical analysis reasoning explaining the decision")
    suggested_entry: str | None = Field(default=None, description="Suggested entry price if BUY/SELL")
    suggested_stop_loss: str | None = Field(default=None, description="Suggested stop loss price if BUY/SELL")
    suggested_take_profit: str | None = Field(default=None, description="Suggested take profit price if BUY/SELL")


class DecisionAgent(BaseAgent):
    """
    Implements IDecisionAgent.
    Graph position: sixth (after PortfolioAgent).
    Populates: state.signal, state.confidence, state.reasoning,
               state.analysis, state.suggested_entry,
               state.suggested_stop_loss, state.suggested_take_profit
    """

    def __init__(self, deps: AgentDependencies) -> None:
        super().__init__(deps)

    async def run(self, state: TradingState) -> dict[str, Any]:
        if state.signal is not None and state.signal != TradingSignal.NEUTRAL:
            self._log_info("signal already computed, skipping for idempotency")
            return {
                "signal": state.signal,
                "confidence": state.confidence,
                "reasoning": state.reasoning,
                "analysis": state.analysis,
                "suggested_entry": state.suggested_entry,
                "suggested_stop_loss": state.suggested_stop_loss,
                "suggested_take_profit": state.suggested_take_profit,
            }

        primary_symbol = state.symbols[0] if state.symbols else "UNKNOWN"
        self._log_info("running LLM decision", symbol=primary_symbol)

        try:
            signal, confidence, reasoning, entry, sl, tp = await self._run_decision(state)
            self._log_info(
                "decision produced",
                signal=str(signal),
                confidence=confidence,
            )
            return {
                "signal": signal,
                "confidence": confidence,
                "reasoning": reasoning,
                "analysis": reasoning,  # extended narrative via LLM
                "suggested_entry": entry,
                "suggested_stop_loss": sl,
                "suggested_take_profit": tp,
            }
        except Exception as exc:
            return {
                **self._node_error(state, exc),
                "signal": TradingSignal.NEUTRAL,
                "confidence": 0.0,
                "reasoning": f"Decision agent error: {exc}",
            }

    # ── IDecisionAgent implementation ─────────────────────────────────────────

    async def decide(
        self,
        state: TradingState,
    ) -> tuple[TradingSignal, float, str]:
        signal, confidence, reasoning, *_ = await self._run_decision(state)
        return signal, confidence, reasoning

    async def build_context_prompt(self, state: TradingState) -> str:
        primary_symbol = state.symbols[0] if state.symbols else ""
        ticker = state.tickers.get(primary_symbol, {})
        ohlcv = state.ohlcv.get(primary_symbol, [])
        indicators = state.indicators.get(primary_symbol, {})

        ohlcv_table = self._format_ohlcv(ohlcv[-10:])
        indicator_str = self._format_indicators(indicators)
        headlines = self._format_headlines(state.news_items[:5])
        positions_str = self._format_positions(state.open_positions)
        memory_str = self._format_memory(state.memory_context)
        prediction_insights_str = self._format_prediction_insights(state.prediction_sentiment)

        # Build Risk context input string
        risk_context_str = (
            f"- Drawdown Limit: 10%\n"
            f"- Account Risk Limit: 1% per trade\n"
            f"- Leverage Limit: 2x\n"
            f"- Max Open Positions: 5\n"
            f"- Daily Loss Limit: 5.0%"
        )

        return DECISION_USER_TEMPLATE.format(
            symbol=primary_symbol,
            exchange=state.exchange,
            timeframe=state.timeframe,
            strategy_id=state.strategy_id,
            last_price=ticker.get("last", "N/A"),
            bid=ticker.get("bid", "N/A"),
            ask=ticker.get("ask", "N/A"),
            change_24h_pct=ticker.get("change_24h_pct", "N/A"),
            volume_24h=ticker.get("volume_24h", "N/A"),
            ohlcv_count=len(ohlcv),
            ohlcv_table=ohlcv_table,
            indicators=indicator_str,
            sentiment_score=round(state.sentiment.overall_score, 3) if state.sentiment else 0.0,
            sentiment_label=state.sentiment.label if state.sentiment else "neutral",
            headlines=headlines,
            prediction_insights=prediction_insights_str,
            available_balance=state.available_balance,
            open_positions_count=len(state.open_positions),
            open_positions=positions_str,
            memory_context=memory_str,
            risk_context=risk_context_str,
        )

    async def parse_llm_response(
        self,
        raw_response: str,
    ) -> tuple[TradingSignal, float, str, Decimal | None, Decimal | None, Decimal | None]:
        try:
            data = json.loads(raw_response)
            sig_str = str(data.get("signal", "WAIT")).upper()

            if sig_str == "BUY":
                signal = TradingSignal.BUY
            elif sig_str == "SELL":
                signal = TradingSignal.SELL
            else:
                signal = TradingSignal.NEUTRAL

            confidence = float(data.get("confidence", 0.0))
            reasoning = data.get("reasoning", "")
            entry = Decimal(str(data["suggested_entry"])) if data.get("suggested_entry") else None
            sl = (
                Decimal(str(data["suggested_stop_loss"]))
                if data.get("suggested_stop_loss")
                else None
            )
            tp = (
                Decimal(str(data["suggested_take_profit"]))
                if data.get("suggested_take_profit")
                else None
            )
            return signal, confidence, reasoning, entry, sl, tp
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            self._log_warning("failed to parse LLM response", error=str(exc))
            return TradingSignal.NEUTRAL, 0.0, "Parse error", None, None, None

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _run_decision(
        self, state: TradingState
    ) -> tuple[TradingSignal, float, str, Decimal | None, Decimal | None, Decimal | None]:
        if self._deps.llm is None:
            # No LLM configured — return a safe neutral stub
            self._log_warning("LLM not configured; using neutral WAIT stub")
            return TradingSignal.NEUTRAL, 0.0, "LLM not configured", None, None, None

        prompt = await self.build_context_prompt(state)
        from langchain_core.messages import HumanMessage, SystemMessage

        # Attempt structured output using LangChain with fallback to raw JSON string parsing
        if hasattr(self._deps.llm, "with_structured_output"):
            try:
                structured_llm = self._deps.llm.with_structured_output(TradingDecision)
                res = await structured_llm.ainvoke(
                    [
                        SystemMessage(content=DECISION_SYSTEM_PROMPT),
                        HumanMessage(content=prompt),
                    ]
                )
                sig_str = res.signal.upper()
                if sig_str == "BUY":
                    signal = TradingSignal.BUY
                elif sig_str == "SELL":
                    signal = TradingSignal.SELL
                else:
                    signal = TradingSignal.NEUTRAL

                entry = Decimal(str(res.suggested_entry)) if res.suggested_entry else None
                sl = Decimal(str(res.suggested_stop_loss)) if res.suggested_stop_loss else None
                tp = Decimal(str(res.suggested_take_profit)) if res.suggested_take_profit else None

                return signal, res.confidence, res.reasoning, entry, sl, tp
            except Exception as e:
                self._log_warning("structured output invocation failed; falling back", error=str(e))

        response = await self._deps.llm.ainvoke(
            [
                SystemMessage(content=DECISION_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
        content = getattr(response, "content", "")
        if not isinstance(content, str):
            content = str(content)
        return await self.parse_llm_response(content)

    @staticmethod
    def _format_ohlcv(candles: list[dict[str, Any]]) -> str:
        if not candles:
            return "No OHLCV data available"
        header = "| timestamp | open | high | low | close | volume |"
        sep = "|" + "|".join(["---"] * 6) + "|"
        rows = [
            f"| {c.get('timestamp', '')} | {c.get('open', '')} | "
            f"{c.get('high', '')} | {c.get('low', '')} | "
            f"{c.get('close', '')} | {c.get('volume', '')} |"
            for c in candles
        ]
        return "\n".join([header, sep, *rows])

    @staticmethod
    def _format_indicators(indicators: dict[str, Any]) -> str:
        if not indicators:
            return "No indicators computed"
        return "\n".join(f"- {k}: {v}" for k, v in indicators.items())

    @staticmethod
    def _format_headlines(items: list[Any]) -> str:
        if not items:
            return "No recent news"
        return "\n".join(f"  • [{item.source}] {item.title}" for item in items)

    @staticmethod
    def _format_positions(positions: list[dict[str, Any]]) -> str:
        if not positions:
            return "  No open positions"
        return "\n".join(
            f"  • {p.get('symbol')} {p.get('side')} qty={p.get('quantity')} "
            f"entry={p.get('entry_price')} pnl={p.get('unrealized_pnl', 'N/A')}"
            for p in positions
        )

    @staticmethod
    def _format_memory(ctx: Any) -> str:
        lines = []
        if ctx.past_signals:
            lines.append("Recent Signals:")
            for sig in ctx.past_signals[-3:]:
                lines.append(
                    f"  • {sig.get('timestamp', '?')}: {sig.get('signal', '?')} (confidence={sig.get('confidence', '?')})"
                )

        long_term = [ref for ref in ctx.past_reflections if ref.get("type") == "long_term"]
        if long_term:
            lines.append("\nRelevant Long-Term Memories:")
            for item in long_term[:3]:
                lines.append(
                    f"  • Past execution on {item.get('symbol')} (Signal: {item.get('signal')}, Confidence: {item.get('confidence')})"
                )
                if item.get("reasoning"):
                    lines.append(f"    Reasoning: {item.get('reasoning')[:150]}...")
                if item.get("lessons_learned"):
                    lines.append(f"    Lessons Learned: {item.get('lessons_learned')}")
                if item.get("reflection"):
                    lines.append(f"    Reflection: {item.get('reflection')}")

        if not lines:
            return "No historical context available"
        return "\n".join(lines)

    @staticmethod
    def _format_prediction_insights(sentiment: Any) -> str:
        if not sentiment or not sentiment.insights:
            return "No prediction market data available"
        lines = [
            f"- Signal Strength: {sentiment.signal_strength:.2f} (from {sentiment.bullish_count} bullish vs {sentiment.bearish_count} bearish markets)",
            f"- Avg Probability: {sentiment.avg_probability:.1%}",
            f"- Total Liquidity: ${sentiment.total_liquidity:,.2f}",
            "Key Prediction Markets:"
        ]
        for insight in sentiment.insights[:5]:
            lines.append(
                f"  • {insight.question} → YES probability: {insight.probability:.1%} (liq: ${insight.liquidity:,.0f}, vol: ${insight.volume:,.0f})"
            )
        return "\n".join(lines)

