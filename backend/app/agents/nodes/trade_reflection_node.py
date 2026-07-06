"""Trade Reflection Agent — post-fill trade analysis and memory update."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from loguru import logger

from app.domain.models.memory import LongTermMemory
from app.domain.models.order import Order
from app.domain.models.strategy import StrategyExecution

if TYPE_CHECKING:
    import uuid
    from decimal import Decimal

    from app.agents.interfaces.base import AgentDependencies

TRADE_REFLECTION_SYSTEM_PROMPT = """
You are a senior trading supervisor and quantitative analyst.
Your job is to perform a post-mortem review of a completed (filled) trade.

Analyze the trade using these criteria:
1. Was the prediction correct? (Did the trade result in a profit, or did the price move in the predicted direction?)
2. Was the risk appropriate? (Assess position size, entry level, stop-loss and take-profit setup relative to market structure.)
3. Did news matter? (Evaluate if news headlines or overall sentiment corresponded to the market move.)
4. Should confidence increase or decrease? (Based on how closely the outcome aligned with the reasoning.)

Output a JSON object with this exact schema (no markdown fences):
{
  "prediction_correct": true | false,
  "risk_appropriate": true | false,
  "news_mattered": true | false,
  "confidence_adjustment": "increase" | "decrease" | "no_change",
  "reflection_summary": "<brief summary of analysis>",
  "lessons_learned": ["<lesson 1>", "<lesson 2>"]
}
""".strip()

TRADE_REFLECTION_USER_TEMPLATE = """
Analyse the completed trade details:

## Strategy Context
- Symbol: {symbol}
- Side: {side} (Buy/Sell)
- Order Type: {order_type}

## Execution Performance
- Filled Qty: {quantity}
- Average Fill Price: {fill_price}
- Realized PnL: {realized_pnl} USDT
- Total Fee: {fee} {fee_currency}

## Original Decision Context
- Signal: {signal}
- Reasoning: {reasoning}
- News Sentiment: {news_summary}
- Indicators Summary: {indicators_summary}
- Performance Summary: {performance_summary}

Based on this completed trade, perform your post-mortem analysis now.
""".strip()


class TradeReflectionAgent:
    def __init__(self, deps: AgentDependencies) -> None:
        self._deps = deps

    async def reflect_on_trade(
        self, order_id: uuid.UUID, realized_pnl: Decimal
    ) -> dict[str, Any] | None:
        if self._deps.session is None:
            logger.error("DB session not available for trade reflection")
            return None

        # 1. Load Order
        order = await self._deps.session.get(Order, order_id)
        if not order or order.status != "filled":
            logger.warning(f"Order {order_id} not found or not filled")
            return None

        # 2. Get original decision context
        from sqlalchemy import select

        stmt = (
            select(StrategyExecution)
            .where(StrategyExecution.strategy_id == order.strategy_id)
            .order_by(StrategyExecution.created_at.desc())
            .limit(1)
        )
        result = await self._deps.session.execute(stmt)
        execution = result.scalar_one_or_none()

        reasoning = order.agent_reasoning or "N/A"
        news_summary = "N/A"
        indicators_summary = "N/A"
        performance_summary = "N/A"
        signal = str(order.side)
        run_id = f"TRADE-RUN-{order_id.hex[:8].upper()}"

        if execution:
            reasoning = execution.reasoning or reasoning
            signal = execution.signal or signal
            run_id = execution.run_id

            stmt_mem = (
                select(LongTermMemory).where(LongTermMemory.run_id == execution.run_id).limit(1)
            )
            result_mem = await self._deps.session.execute(stmt_mem)
            mem_record = result_mem.scalar_one_or_none()
            if mem_record:
                news_summary = mem_record.news_summary or news_summary
                indicators_summary = mem_record.indicators_summary or indicators_summary
                performance_summary = mem_record.performance_summary or performance_summary

        prompt = TRADE_REFLECTION_USER_TEMPLATE.format(
            symbol=order.symbol,
            side=str(order.side),
            order_type=str(order.order_type),
            quantity=str(order.quantity),
            fill_price=str(order.average_fill_price),
            realized_pnl=str(realized_pnl),
            fee=str(order.fee),
            fee_currency=order.fee_currency or "USDT",
            signal=signal,
            reasoning=reasoning,
            news_summary=news_summary,
            indicators_summary=indicators_summary,
            performance_summary=performance_summary,
        )

        analysis_dict = {}
        if self._deps.llm is not None:
            try:
                from langchain_core.messages import HumanMessage, SystemMessage

                response = await self._deps.llm.ainvoke(
                    [
                        SystemMessage(content=TRADE_REFLECTION_SYSTEM_PROMPT),
                        HumanMessage(content=prompt),
                    ]
                )
                content = getattr(response, "content", "")
                if not isinstance(content, str):
                    content = str(content)
                analysis_dict = json.loads(content)
            except Exception as e:
                logger.warning(f"LLM trade reflection failed: {e}. Using fallback.")
                analysis_dict = self._stub_reflection(realized_pnl)
        else:
            analysis_dict = self._stub_reflection(realized_pnl)

        # 3. Store lessons in long-term memory
        try:
            from app.infrastructure.repositories.memory_repository import MemoryRepository
            from app.services.embedding.embedding_service import EmbeddingService

            lessons_str = ", ".join(analysis_dict.get("lessons_learned", []))
            reflection_summary = analysis_dict.get("reflection_summary", "")

            embedding_text = (
                f"Trade Reflection: {order.symbol} {order.side}. Correct: {analysis_dict.get('prediction_correct')}. "
                f"Risk appropriate: {analysis_dict.get('risk_appropriate')}. News mattered: {analysis_dict.get('news_mattered')}. "
                f"Lessons: {lessons_str}. Summary: {reflection_summary}"
            )

            embed_service = EmbeddingService()
            embedding = await embed_service.embed_query(embedding_text)

            mem_record = LongTermMemory(
                strategy_id=order.strategy_id,
                run_id=run_id,
                symbol=order.symbol,
                signal=signal,
                confidence=float(order.quantity),  # mock placeholder
                reasoning=reasoning,
                news_summary=news_summary,
                indicators_summary=indicators_summary,
                performance_summary=f"Trade fill price: {order.average_fill_price}. Realized PnL: {realized_pnl} USDT",
                lessons_learned=lessons_str,
                reflection=reflection_summary,
                embedding_text=embedding_text,
                embedding=embedding,
            )

            mem_repo = MemoryRepository(self._deps.session)
            await mem_repo.create(mem_record)
            await self._deps.session.flush()
            logger.info(f"Saved trade reflection memory for order {order_id}")
        except Exception as e:
            logger.error(f"Failed to store trade reflection memory: {e}")

        return analysis_dict

    def _stub_reflection(self, realized_pnl: Decimal) -> dict[str, Any]:
        correct = realized_pnl >= 0
        return {
            "prediction_correct": correct,
            "risk_appropriate": True,
            "news_mattered": False,
            "confidence_adjustment": "no_change",
            "reflection_summary": f"Trade closed with PnL of {realized_pnl} USDT. Prediction was {'correct' if correct else 'incorrect'}.",
            "lessons_learned": [
                "Ensure entry levels align with trade volume.",
                "Manage risk size carefully.",
            ],
        }
