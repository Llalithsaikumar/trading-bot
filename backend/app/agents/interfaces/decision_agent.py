"""IDecisionAgent — contract for LLM-based trading signal generation."""
from __future__ import annotations

from decimal import Decimal
from typing import Protocol, runtime_checkable

from app.agents.graph.state import TradingState
from app.domain.enums.trading import TradingSignal


@runtime_checkable
class IDecisionAgent(Protocol):
    """
    Structural interface for the Decision Agent node.

    Implementations build a rich LLM prompt from market data, technical
    indicators, sentiment, and portfolio context, then call the configured
    LLM (Claude / GPT) and parse the structured JSON response into a
    TradingSignal + confidence + reasoning.
    """

    async def decide(
        self,
        state: TradingState,
    ) -> tuple[TradingSignal, float, str]:
        """
        Generate a trading signal from the current state.

        Args:
            state: Full TradingState with market, technical, and portfolio
                   data already populated by upstream nodes.

        Returns:
            Tuple of:
              - signal:     TradingSignal enum value
              - confidence: Float in [0.0, 1.0]
              - reasoning:  Concise text explanation from the LLM
        """
        ...

    async def build_context_prompt(
        self,
        state: TradingState,
    ) -> str:
        """
        Construct the user-facing portion of the LLM prompt.

        Args:
            state: TradingState with all upstream fields populated.

        Returns:
            Formatted prompt string ready for the LLM.
        """
        ...

    async def parse_llm_response(
        self,
        raw_response: str,
    ) -> tuple[TradingSignal, float, str, Decimal | None, Decimal | None, Decimal | None]:
        """
        Parse the LLM's JSON response into typed fields.

        Returns:
            Tuple: (signal, confidence, reasoning, entry, stop_loss, take_profit)
        """
        ...
