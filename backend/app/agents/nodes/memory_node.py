"""
Memory Agent node — loads historical context at graph start.

Reads past signals, reflections, and market patterns from Redis / DB
to provide the Decision Agent with relevant historical context.
"""

from __future__ import annotations

from typing import Any

from app.agents.graph.state import MemoryContext, TradingState
from app.agents.interfaces.base import AgentDependencies, BaseAgent


class MemoryAgent(BaseAgent):
    """
    Implements IMemoryAgent.

    Graph position: FIRST node (entry point).
    Populates: state.memory_context

    On save (called by ReflectionAgent after the cycle ends):
      Persists outcome + reflection to Redis (TTL) and PostgreSQL (permanent).
    """

    def __init__(self, deps: AgentDependencies) -> None:
        super().__init__(deps)

    async def run(self, state: TradingState) -> dict[str, Any]:
        if state.memory_context and state.memory_context.context_key:
            self._log_info("memory context already loaded, skipping for idempotency")
            return {"memory_context": state.memory_context}

        self._log_info("loading historical context", strategy=state.strategy_id)
        try:

            context = await self.load_context(
                strategy_id=state.strategy_id,
                exchange=state.exchange,
                symbols=state.symbols,
                timeframe=state.timeframe,
            )
            self._log_info(
                "context loaded",
                past_signals=len(context.past_signals),
                past_reflections=len(context.past_reflections),
            )
            return {"memory_context": context}
        except Exception as exc:
            return self._node_error(state, exc)

    # ── IMemoryAgent implementation ───────────────────────────────────────────

    async def load_context(
        self,
        strategy_id: str,
        exchange: str,
        symbols: list[str],
        timeframe: str,
        limit: int = 10,
    ) -> MemoryContext:
        import json

        from sqlalchemy import select

        from app.domain.models.strategy import StrategyExecution

        context_key = await self.build_context_key(strategy_id, symbols, timeframe)

        past_signals = []
        if self._deps.redis is not None:
            try:
                raw = await self._deps.redis.lrange(f"{context_key}:signals", 0, limit - 1)
                for item in raw:
                    past_signals.append(json.loads(item))
            except Exception:
                pass

        past_reflections = []
        if self._deps.session is not None:
            try:
                import uuid

                stmt = (
                    select(StrategyExecution)
                    .where(StrategyExecution.strategy_id == uuid.UUID(strategy_id))
                    .order_by(StrategyExecution.created_at.desc())
                    .limit(limit)
                )
                result = await self._deps.session.execute(stmt)
                executions = result.scalars().all()
                for exe in executions:
                    past_reflections.append(
                        {
                            "run_id": exe.run_id,
                            "signal": exe.signal,
                            "reasoning": exe.reasoning,
                            "error": exe.error_message,
                            "timestamp": exe.created_at.isoformat() if exe.created_at else None,
                        }
                    )
            except Exception:
                pass

        # ── Long-Term Memory (Semantic Search) ─────────────────────────────────
        retrieved_memories = []
        if self._deps.session is not None:
            try:
                import uuid

                from app.infrastructure.repositories.memory_repository import MemoryRepository
                from app.services.embedding.embedding_service import EmbeddingService

                # 1. Build a semantic context query text from recent status
                primary_symbol = symbols[0] if symbols else ""
                ticker_price = ""
                try:
                    from app.services.market_data.market_data_service import MarketDataService

                    market_service = MarketDataService(self._deps.session)
                    ticker_resp = await market_service.get_ticker(exchange, primary_symbol)
                    if ticker_resp:
                        ticker_price = f"price {ticker_resp.last}"
                except Exception:
                    pass

                recent_news_str = ""
                try:
                    from app.agents.nodes.news_node import NewsAgent

                    news_agent = NewsAgent(self._deps)
                    news_items = await news_agent.fetch_news(symbols, limit=3)
                    recent_news_str = " ".join([item.title for item in news_items])
                except Exception:
                    pass

                query_text = f"Strategy execution for {primary_symbol} {ticker_price}. Recent market news: {recent_news_str}"

                # 2. Generate embedding
                embed_service = EmbeddingService()
                query_vector = await embed_service.embed_query(query_text)

                # 3. Perform semantic search
                mem_repo = MemoryRepository(self._deps.session)
                retrieved_memories = await mem_repo.search_semantic(
                    strategy_id=uuid.UUID(strategy_id),
                    query_vector=query_vector,
                    limit=3,
                )
            except Exception as e:
                self._log_warning("semantic search failed", error=str(e))

        # Format and insert long-term memories
        for mem in retrieved_memories:
            past_reflections.append(
                {
                    "run_id": mem.run_id,
                    "symbol": mem.symbol,
                    "signal": mem.signal,
                    "confidence": mem.confidence,
                    "reasoning": mem.reasoning,
                    "news_summary": mem.news_summary,
                    "indicators_summary": mem.indicators_summary,
                    "performance_summary": mem.performance_summary,
                    "lessons_learned": mem.lessons_learned,
                    "reflection": mem.reflection,
                    "timestamp": mem.created_at.isoformat() if mem.created_at else None,
                    "type": "long_term",
                }
            )

        return MemoryContext(
            context_key=context_key,
            past_signals=past_signals,
            past_reflections=past_reflections,
            market_patterns=[],
            relevant_news=[],
        )

    async def save_context(
        self,
        strategy_id: str,
        run_id: str,
        outcome: dict[str, Any],
        reflection: Any,  # ReflectionResult
    ) -> None:
        import json
        from datetime import UTC, datetime

        self._log_info("saving context", strategy=strategy_id, run_id=run_id)

        # ── Short-term Redis cache update ────────────────────────────────────
        if self._deps.redis is not None:
            try:
                symbols = outcome.get("symbols", [])
                timeframe = outcome.get("timeframe", "")
                context_key = await self.build_context_key(strategy_id, symbols, timeframe)
                signal_data = {
                    "run_id": run_id,
                    "signal": outcome.get("signal"),
                    "confidence": outcome.get("confidence"),
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                key = f"{context_key}:signals"
                await self._deps.redis.lpush(key, json.dumps(signal_data))
                await self._deps.redis.ltrim(key, 0, 19)
                await self._deps.redis.expire(key, 7 * 86400)
            except Exception as e:
                self._log_warning("failed to save context to Redis", error=str(e))

        # ── Long-term DB memory update ──────────────────────────────────────
        if self._deps.session is not None:
            try:
                import uuid

                from app.domain.models.memory import LongTermMemory
                from app.infrastructure.repositories.memory_repository import MemoryRepository
                from app.services.embedding.embedding_service import EmbeddingService

                symbol = outcome.get("symbols", [""])[0] if outcome.get("symbols") else ""
                lessons_str = (
                    ", ".join(reflection.lessons_learned) if reflection.lessons_learned else ""
                )

                embedding_text = (
                    f"Strategy: {strategy_id}. Symbol: {symbol}. Signal: {outcome.get('signal')}. "
                    f"Reasoning: {outcome.get('reasoning')}. News: {outcome.get('news_summary')}. "
                    f"Indicators: {outcome.get('indicators_summary')}. Performance: {outcome.get('performance_summary')}. "
                    f"Reflection Summary: {reflection.summary}. Lessons Learned: {lessons_str}"
                )

                # Generate embedding
                embed_service = EmbeddingService()
                embedding = await embed_service.embed_query(embedding_text)

                # Persist memory
                mem_record = LongTermMemory(
                    strategy_id=uuid.UUID(strategy_id),
                    run_id=run_id,
                    symbol=symbol,
                    signal=outcome.get("signal"),
                    confidence=float(outcome.get("confidence") or 0.0),
                    reasoning=outcome.get("reasoning"),
                    news_summary=outcome.get("news_summary"),
                    indicators_summary=outcome.get("indicators_summary"),
                    performance_summary=outcome.get("performance_summary"),
                    lessons_learned=lessons_str,
                    reflection=reflection.summary,
                    embedding_text=embedding_text,
                    embedding=embedding,
                )

                mem_repo = MemoryRepository(self._deps.session)
                await mem_repo.create(mem_record)
                await self._deps.session.flush()
                self._log_info("long-term memory saved successfully", run_id=run_id)
            except Exception as e:
                self._log_warning("failed to save long-term memory to DB", error=str(e))

    async def build_context_key(
        self,
        strategy_id: str,
        symbols: list[str],
        timeframe: str,
    ) -> str:
        symbol_str = "-".join(sorted(symbols))
        return f"memory:{strategy_id}:{symbol_str}:{timeframe}"
