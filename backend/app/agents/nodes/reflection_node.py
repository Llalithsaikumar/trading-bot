"""
Reflection Agent node — post-cycle analysis and memory update.

The final node in the graph.  Analyses the entire cycle from raw data
through decision, risk, and execution, and produces a ReflectionResult
that is persisted to memory for future runs.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.graph.state import ReflectionResult, TradingState
from app.agents.interfaces.base import AgentDependencies, BaseAgent
from app.agents.interfaces.reflection_agent import IReflectionAgent
from app.agents.prompts.templates import REFLECTION_SYSTEM_PROMPT, REFLECTION_USER_TEMPLATE


class ReflectionAgent(BaseAgent):
    """
    Implements IReflectionAgent.

    Graph position: LAST (ninth) — runs after execution or after risk rejection.
    Populates: state.reflection

    Also triggers memory persistence as a side effect (calls MemoryAgent.save_context
    if deps.redis is available).
    """

    def __init__(self, deps: AgentDependencies) -> None:
        super().__init__(deps)

    async def run(self, state: TradingState) -> dict[str, Any]:
        self._log_info(
            "reflecting on cycle",
            signal=str(state.signal),
            risk_approved=state.risk_approved,
            order_placed=state.order_placed,
        )
        try:
            result = await self.reflect(state)
            self._log_info(
                "reflection complete",
                signal_quality=result.signal_quality_score,
                process_quality=result.process_quality_score,
            )

            # Trigger MemoryAgent context saving
            from app.agents.nodes.memory_node import MemoryAgent

            memory_agent = MemoryAgent(self._deps)

            outcome = {
                "symbols": state.symbols,
                "timeframe": state.timeframe,
                "signal": str(state.signal),
                "confidence": state.confidence,
                "reasoning": state.reasoning,
                "order_placed": state.order_placed,
                "news_summary": f"Sentiment score: {state.sentiment.overall_score} ({state.sentiment.label}). Headlines: "
                + " | ".join([item.title for item in state.news_items[:3]]),
                "indicators_summary": str(state.indicators),
                "performance_summary": f"Available balance: {state.available_balance} USDT. "
                f"Unrealized PnL: {state.portfolio_metrics.unrealized_pnl} USDT, "
                f"Realized PnL: {state.portfolio_metrics.realized_pnl} USDT.",
            }
            await memory_agent.save_context(state.strategy_id, state.run_id, outcome, result)

            return {"reflection": result}
        except Exception as exc:
            return self._node_error(state, exc)

    # ── IReflectionAgent implementation ───────────────────────────────────────

    async def reflect(self, state: TradingState) -> ReflectionResult:
        if self._deps.llm is None:
            return self._stub_reflection(state)

        try:
            prompt = await self.build_reflection_prompt(state)
            from langchain_core.messages import HumanMessage, SystemMessage

            response = await self._deps.llm.ainvoke(
                [
                    SystemMessage(content=REFLECTION_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
            )
            content = getattr(response, "content", "")
            if not isinstance(content, str):
                content = str(content)
            return await self._parse_response(content, state)
        except Exception as e:
            self._log_warning("LLM reflection failed, using stub", error=str(e))
            return self._stub_reflection(state)

    async def build_reflection_prompt(self, state: TradingState) -> str:
        return REFLECTION_USER_TEMPLATE.format(
            run_id=state.run_id,
            strategy_id=state.strategy_id,
            exchange=state.exchange,
            symbols=", ".join(state.symbols),
            timeframe=state.timeframe,
            signal=str(state.signal),
            confidence=state.confidence,
            reasoning=state.reasoning[:500] if state.reasoning else "N/A",
            risk_approved=state.risk_approved,
            risk_violations=", ".join(v.rule for v in state.risk_violations) or "None",
            risk_score=state.risk_score,
            order_placed=state.order_placed,
            order_id=state.order_id or "N/A",
            execution_error=state.execution_error or "None",
            ohlcv_symbols=", ".join(state.ohlcv.keys()) or "None",
            indicator_symbols=", ".join(state.indicators.keys()) or "None",
            news_count=len(state.news_items),
            sentiment_label=state.sentiment.label,
            sentiment_score=state.sentiment.overall_score,
            node_errors=json.dumps(state.node_errors, indent=2) if state.node_errors else "None",
        )

    async def score_signal_quality(self, state: TradingState) -> float:
        score = 0.0
        # Confidence contributes 50%
        score += state.confidence * 0.5
        # Having indicators contributes 30%
        if state.indicators:
            score += 0.3
        # Having market data contributes 20%
        if state.ohlcv:
            score += 0.2
        return min(score, 1.0)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _stub_reflection(self, state: TradingState) -> ReflectionResult:
        signal_q = 0.0
        # Simple heuristic: confidence drives signal quality
        signal_q = state.confidence
        # process quality: penalise for node errors
        process_q = 1.0 - (len(state.node_errors) * 0.2)

        lessons: list[str] = []
        if not state.ohlcv:
            lessons.append("Market data was not populated — check ExchangeClient")
        if not state.indicators:
            lessons.append("Indicators were not computed — check TechnicalAgent")
        if state.node_errors:
            lessons.append(f"Node errors occurred: {list(state.node_errors.keys())}")

        return ReflectionResult(
            summary=(
                f"Cycle completed. Signal: {state.signal}, confidence: {state.confidence:.2f}. "
                f"Risk: {'approved' if state.risk_approved else 'rejected'}. "
                f"Order: {'placed' if state.order_placed else 'not placed'}."
            ),
            lessons_learned=lessons,
            signal_quality_score=round(signal_q, 3),
            process_quality_score=max(0.0, round(process_q, 3)),
            data_quality_issues=[
                k for k in ("ohlcv", "indicators", "tickers") if not getattr(state, k)
            ],
            memory_updates=[
                {
                    "run_id": state.run_id,
                    "signal": str(state.signal),
                    "confidence": state.confidence,
                    "risk_approved": state.risk_approved,
                    "order_placed": state.order_placed,
                }
            ],
        )

    async def _parse_response(self, raw: str, state: TradingState) -> ReflectionResult:
        try:
            data = json.loads(raw)
            return ReflectionResult(
                summary=data.get("summary", ""),
                lessons_learned=data.get("lessons_learned", []),
                signal_quality_score=float(data.get("signal_quality_score", 0.0)),
                process_quality_score=float(data.get("process_quality_score", 0.0)),
                data_quality_issues=data.get("data_quality_issues", []),
                recommended_adjustments=data.get("recommended_adjustments", []),
            )
        except (json.JSONDecodeError, ValueError):
            return self._stub_reflection(state)
