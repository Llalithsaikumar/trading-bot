"""IMemoryAgent — contract for loading and persisting agent memory."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.agents.graph.state import MemoryContext, ReflectionResult


@runtime_checkable
class IMemoryAgent(Protocol):
    """
    Structural interface for the Memory Agent node.

    The Memory Agent runs twice per cycle:
      • At graph start (load_context) — hydrates MemoryContext with
        relevant historical signals, patterns, and past reflections.
      • After Reflection (save_context) — persists the reflection output
        and the decision outcome back to the memory store.

    The concrete implementation may use Redis (short-term), PostgreSQL
    (long-term), or a vector store (semantic retrieval).
    """

    async def load_context(
        self,
        strategy_id: str,
        exchange: str,
        symbols: list[str],
        timeframe: str,
        limit: int = 10,
    ) -> MemoryContext:
        """
        Retrieve historical context relevant to the current run.

        Args:
            strategy_id: Strategy UUID string.
            exchange:    Exchange name (e.g. "binance").
            symbols:     Trading pairs (e.g. ["BTC/USDT"]).
            timeframe:   Candle interval (e.g. "1h").
            limit:       Number of past signals / reflections to include.

        Returns:
            MemoryContext with past_signals, past_reflections, and
            market_patterns populated.
        """
        ...

    async def save_context(
        self,
        strategy_id: str,
        run_id: str,
        outcome: dict[str, Any],
        reflection: ReflectionResult,
    ) -> None:
        """
        Persist the outcome of the current run to the memory store.

        Args:
            strategy_id: Strategy UUID string.
            run_id:      Unique run identifier (LangGraph run ID).
            outcome:     Dict summarising the run result
                         (signal, confidence, order_placed, etc.).
            reflection:  Reflection Agent output for this cycle.
        """
        ...

    async def build_context_key(
        self,
        strategy_id: str,
        symbols: list[str],
        timeframe: str,
    ) -> str:
        """Generate the canonical Redis / DB key for this context."""
        ...
